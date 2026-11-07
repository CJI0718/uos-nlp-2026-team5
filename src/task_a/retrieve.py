"""Fixed-corpus retrieval: the C1 environment.

Two tokenizers are provided because they answer different questions. Kiwi does
real Korean morphological analysis and is the intended default (tools.md
section 6 plans Kiwi+BM25). The bigram tokenizer is dependency-free, so tests
and offline demos do not pay the model load cost. Swapping them is a retrieval
ablation, not a fallback path.

A backend built without a web provider IS the C1 condition: fixed corpus only,
no external access. C2 adds a provider. That distinction is the experiment, so
it is expressed in construction rather than in a runtime flag.
"""

from __future__ import annotations

import re
from typing import Protocol

from rank_bm25 import BM25Okapi

from task_a.schema import EvidenceUnit

_LATIN = re.compile(r"[A-Za-z0-9]+")
_HANGUL_RUN = re.compile(r"[가-힣]+")


class Tokenizer(Protocol):
    name: str

    def tokenize(self, text: str) -> list[str]: ...


class BigramTokenizer:
    """Latin/digit words plus Korean bigrams.

    Single Korean characters match nearly every document, so runs are split into
    bigrams. Coarser than morphological analysis: '사전예약은' stays one run
    instead of becoming 사전/예약/은.
    """

    name = "bigram"

    def tokenize(self, text: str) -> list[str]:
        tokens = [t.lower() for t in _LATIN.findall(text or "")]
        for run in _HANGUL_RUN.findall(text or ""):
            if len(run) == 1:
                tokens.append(run)
            else:
                tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
        return tokens


class KiwiTokenizer:
    """Korean morphological analysis. The model loads on first use."""

    name = "kiwi"

    def __init__(self) -> None:
        self._kiwi = None

    @property
    def kiwi(self):
        if self._kiwi is None:
            from kiwipiepy import Kiwi
            self._kiwi = Kiwi()
        return self._kiwi

    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        return [t.form.lower() for t in self.kiwi.tokenize(text)]


def make_tokenizer(name: str = "kiwi") -> Tokenizer:
    if name == "kiwi":
        return KiwiTokenizer()
    if name == "bigram":
        return BigramTokenizer()
    raise ValueError(f"unknown tokenizer: {name!r} (kiwi | bigram)")


class BM25Index:
    """Okapi BM25 over the fixed corpus. The index is built once and frozen."""

    def __init__(self, units: list[EvidenceUnit], tokenizer: Tokenizer) -> None:
        self.units = list(units)
        self.tokenizer = tokenizer
        self._tokens = [tokenizer.tokenize(f"{u.title}\n{u.text}") for u in self.units]
        self._bm25 = BM25Okapi(self._tokens) if self.units else None

    def __len__(self) -> int:
        return len(self.units)

    def search(self, query: str, top_k: int) -> list[tuple[EvidenceUnit, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(self.tokenizer.tokenize(query))
        ranked = sorted(((self.units[i], float(scores[i])) for i in range(len(self.units))),
                        key=lambda pair: pair[1], reverse=True)
        # BM25 gives negative scores to documents missing every query term.
        return [(unit, score) for unit, score in ranked[:top_k] if score > 0]


class WebProvider(Protocol):
    """C2 only. Implementations must record the query and the raw response."""

    def search(self, query: str, top_k: int) -> list[dict]: ...

    def fetch(self, url: str) -> str: ...


class CorpusBackend:
    """Serves the fixed corpus, and external tools only if a provider is given."""

    def __init__(self, corpus: list[EvidenceUnit], tokenizer: Tokenizer | None = None,
                 web: WebProvider | None = None, top_k: int = 5) -> None:
        self.index = BM25Index(corpus, tokenizer or BigramTokenizer())
        self.web = web
        self.top_k = top_k
        self._by_id = {u.evidence_id: u for u in self.index.units}

    def search_corpus(self, query: str, top_k: int) -> list[tuple[EvidenceUnit, float]]:
        return self.index.search(query, min(top_k, self.top_k))

    def lookup(self, evidence_id: str) -> EvidenceUnit | None:
        return self._by_id.get(evidence_id)

    def web_search(self, query: str, top_k: int) -> list[dict]:
        if self.web is None:
            raise PermissionError("C1 조건: 외부 검색이 비활성화되어 있다")
        return self.web.search(query, top_k)

    def fetch(self, url: str) -> str:
        if self.web is None:
            raise PermissionError("C1 조건: 외부 조회가 비활성화되어 있다")
        return self.web.fetch(url)


def load_corpus(rows: list[dict]) -> list[EvidenceUnit]:
    """Build corpus documents from JSONL rows."""
    return [EvidenceUnit(**{k: v for k, v in row.items() if k in EvidenceUnit.__dataclass_fields__})
            for row in rows]
