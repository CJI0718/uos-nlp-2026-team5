"""Offline doubles: a mock corpus backend and a scripted LLM.

These let the whole agent run with zero API calls and zero cost, which is how
`--dry-run` works and how the tests verify the loop. They are test/demo
infrastructure, not a substitute for the live backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from task_a.loop import LLMResponse, ToolCall
from task_a.retrieve import BigramTokenizer
from task_a.schema import EvidenceUnit, Usage
from task_a.tools import ToolBackend

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


@dataclass
class ScriptedLLM:
    """Replays a fixed sequence of model decisions.

    Used to prove the loop honours whatever the model chooses: which tool, in
    what order, and when to stop. A real client is swapped in at run time.
    """

    responses: list[LLMResponse] = field(default_factory=list)
    model_id: str = "scripted-mock"
    seen_messages: list[list[dict]] = field(default_factory=list)

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.seen_messages.append([dict(m) for m in messages])
        if not self.responses:
            raise AssertionError("ScriptedLLM ran out of responses")
        return self.responses.pop(0)


def tool_call_response(name: str, args: dict, call_id: str | None = None,
                       tokens: tuple[int, int] = (0, 0)) -> LLMResponse:
    return LLMResponse(
        tool_calls=[ToolCall(id=call_id or f"call_{name}", name=name, args=args)],
        usage=Usage(input_tokens=tokens[0], output_tokens=tokens[1], llm_calls=1))


def finish_response(verdict: str, cited: list[str], justification: str,
                    stop_reason: str, correction: str | None = None,
                    abstain: bool = False, tokens: tuple[int, int] = (0, 0)) -> LLMResponse:
    args = {"verdict": verdict, "abstain": abstain, "cited_evidence_ids": cited,
            "justification": justification, "stop_reason": stop_reason}
    if correction:
        args["correction"] = correction
    return tool_call_response("finish_verification", args, tokens=tokens)
