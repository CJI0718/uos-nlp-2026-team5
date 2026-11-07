"""Policies: who decides the next action.

This is the axis the whole comparison turns on. C1 -> C2 mixes two effects -
more information access and better decisions - so Q03 requires a fixed
procedure at the same model, tools and maximum budget to separate them. All
three policies here run through the same loop, the same tools and the same
budget; only the decision rule differs.

- ReactPolicy         the model chooses every action, including when to stop
- FixedWorkflowPolicy retrieval order is fixed by rule; the model only judges
- ClosedBookPolicy    no tools at all, so C0 and C1 cannot be confused
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from task_a.loop import FINISH_TOOL, SYSTEM_PROMPT, ToolCall
from task_a.schema import EpisodeState


class Policy(Protocol):
    name: str
    system_prompt: str

    def allowed_tools(self, all_tools: list[str], state: EpisodeState) -> list[str]: ...

    def force(self, state: EpisodeState) -> ToolCall | None: ...


@dataclass
class ReactPolicy:
    """Adaptive: the model picks the tool, the query and the stopping point."""

    name: str = "react"
    system_prompt: str = SYSTEM_PROMPT

    def allowed_tools(self, all_tools: list[str], state: EpisodeState) -> list[str]:
        return list(all_tools)

    def force(self, state: EpisodeState) -> ToolCall | None:
        return None


@dataclass
class FixedWorkflowPolicy:
    """A strong fixed procedure, not a strawman.

    Search the claim text once, read the best hit, then judge. The model still
    writes the verdict and the justification, so this measures the value of
    adaptive search rather than the value of having a model at all. Once the two
    retrieval steps have run, only finish_verification is offered - the model
    cannot go looking for more, which is exactly what makes it 'fixed'.
    """

    name: str = "fixed_workflow"
    system_prompt: str = (
        SYSTEM_PROMPT
        + "\n\n이 실험 조건에서는 검색 순서가 고정되어 있다. search_evidence와 read_evidence는 "
          "시스템이 정한 순서로 자동 실행되며, 당신은 마지막 판정만 내린다."
    )

    def allowed_tools(self, all_tools: list[str], state: EpisodeState) -> list[str]:
        if self.force(state) is None:
            return [t for t in all_tools if t == FINISH_TOOL]
        return list(all_tools)

    def force(self, state: EpisodeState) -> ToolCall | None:
        if not state.observations_for("search_evidence"):
            return ToolCall(id="fixed_search", name="search_evidence",
                            args={"query": state.claim.text})
        if not state.observations_for("read_evidence"):
            top = state.retrieved_ids[0] if state.retrieved_ids else None
            if top is None:
                return None           # nothing to read; let the model finish
            return ToolCall(id="fixed_read", name="read_evidence", args={"evidence_id": top})
        return None


@dataclass
class ClosedBookPolicy:
    """C0: the claim and nothing else. No corpus, no web.

    Only finish_verification is offered, so the model cannot retrieve even if
    it wanted to. That makes C0 structurally incapable of citing evidence, which
    is why GSR is not a meaningful comparison for this arm (Q03).
    """

    name: str = "closed_book"
    system_prompt: str = (
        "너는 팩트체크 판정기다. 외부 자료를 조회할 수 없다. 주어진 주장만으로 "
        "supported / refuted / not_enough_evidence 중 하나를 판단하고 이유를 적는다. "
        "확실하지 않으면 not_enough_evidence와 abstain=true로 종료한다. "
        "근거를 지어내거나 인용 목록을 채우지 않는다."
    )

    def allowed_tools(self, all_tools: list[str], state: EpisodeState) -> list[str]:
        return [FINISH_TOOL]

    def force(self, state: EpisodeState) -> ToolCall | None:
        return None


POLICIES: dict[str, Policy] = {
    "react": ReactPolicy(),
    "fixed_workflow": FixedWorkflowPolicy(),
    "closed_book": ClosedBookPolicy(),
}


def get_policy(name: str) -> Policy:
    if name not in POLICIES:
        raise ValueError(f"unknown policy: {name!r} (choose from {sorted(POLICIES)})")
    return POLICIES[name]
