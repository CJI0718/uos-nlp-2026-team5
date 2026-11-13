"""Offline mock backend for corpus and web tools.

Lets the MCP server, tools, retriever, and cache tests run offline with zero
network access and zero cost.
"""

from __future__ import annotations

from task_a.retrieve import BigramTokenizer
from task_a.schema import EvidenceUnit

tokenize = BigramTokenizer().tokenize


class MockBackend:
    """Serves a fixed in-memory corpus. No network, no filesystem."""

    def __init__(self, corpus: list[EvidenceUnit], web: list[dict] | None = None,
                 pages: dict[str, str] | None = None) -> None:
        self.corpus = {u.evidence_id: u for u in corpus}
        self.web = web or []
        self.pages = pages or {}
        self.calls: list[tuple[str, dict]] = []

    def search_corpus(self, query: str, top_k: int) -> list[tuple[EvidenceUnit, float]]:
        self.calls.append(("search_corpus", {"query": query, "top_k": top_k}))
        q = set(tokenize(query))
        if not q:
            return []
        scored = []
        for unit in self.corpus.values():
            doc = tokenize(f"{unit.title} {unit.text}")
            if not doc:
                continue
            overlap = len(q & set(doc))
            if overlap:
                scored.append((unit, overlap / len(doc) ** 0.5))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def lookup(self, evidence_id: str) -> EvidenceUnit | None:
        self.calls.append(("lookup", {"evidence_id": evidence_id}))
        return self.corpus.get(evidence_id)

    def web_search(self, query: str, top_k: int) -> list[dict]:
        self.calls.append(("web_search", {"query": query, "top_k": top_k}))
        return self.web[:top_k]

    def fetch(self, url: str) -> str:
        self.calls.append(("fetch", {"url": url}))
        if url not in self.pages:
            raise ConnectionError(f"no mock page for {url}")
        return self.pages[url]
