"""FC002 end-to-end with mock tools and a scripted model. Zero API cost.

FC002 (evaluation.md): a Korean article says Vision Pro pre-orders open
"이달 19일 오전 5시(한국시간)". Apple's newsroom says 5:00 a.m. PST.
PST -> KST is +17 hours, so the correct local time is 22:00 KST and the
reference verdict is Refuted.
"""

from __future__ import annotations

import pytest

from task_a.loop import FINISH_TOOL, SYSTEM_PROMPT, Budget, ReActAgent
from task_a.mock import MockBackend, ScriptedLLM, finish_response, tool_call_response
from task_a.schema import Claim, EvidenceUnit, ExecutionStatus, ToolStatus, Verdict
from task_a.tools import ToolRegistry

FC002 = Claim(
    claim_id="FC002",
    text="미국 비전 프로 사전예약은 2024년 1월 19일 한국시간 오전 5시에 시작한다.",
    language="ko",
    source_url="https://v.daum.net/v/2vbOybyj9G",
    source_type="korean_news",
    claim_date="2024-01-09T00:38:00+09:00",
    target_period="2024-01-19 사전예약 개시",
    input_body="사전예약은 이달 19일 오전 5시(한국시간)부터 받는다.",
)

APPLE = EvidenceUnit(
    evidence_id="EV_FC002_apple",
    title="Apple Vision Pro available in the US on February 2",
    text=("Apple Vision Pro will be available in the US on Friday, February 2, 2024. "
          "Pre-orders begin on January 19, 2024 at 5:00 a.m. PST."),
    source_url="https://www.apple.com/newsroom/2024/01/apple-vision-pro-available-in-the-us-on-february-2/",
    publisher="Apple",
    source_type="official_announcement",
    provenance_group="pg_apple_visionpro_launch",
    published_at="2024-01-08",
    document_validity="valid",
    claim_evidence_relation="refutes",
    evidence_condition="sufficient",
)

DISTRACTOR = EvidenceUnit(
    evidence_id="EV_FC002_preview",
    title="애플 비전 프로 체험기",
    text="애플의 혼합현실 헤드셋 비전 프로를 미리 사용해 봤다. 무게와 착용감이 인상적이다.",
    source_url="https://example.com/vision-pro-hands-on",
    publisher="example",
    source_type="korean_news",
    document_validity="valid",
    claim_evidence_relation="irrelevant",
    evidence_condition="sufficient",
)


def make_agent(script: list, corpus: list[EvidenceUnit] | None = None,
               budget: Budget | None = None) -> tuple[ReActAgent, MockBackend]:
    backend = MockBackend(corpus if corpus is not None else [APPLE, DISTRACTOR])
    llm = ScriptedLLM(list(script))
    return ReActAgent(llm, ToolRegistry(backend), budget or Budget()), backend


def test_fc002_end_to_end():
    """The model chooses search -> read -> calculate -> finish. Nothing is hardcoded."""
    script = [
        tool_call_response("search_evidence", {"query": "Vision Pro 사전예약 2024년 1월 19일 시작 시각"}),
        tool_call_response("read_evidence", {"evidence_id": "EV_FC002_apple"}),
        tool_call_response("calculate_comparison",
                           {"op": "tz_convert", "time": "2024-01-19 05:00",
                            "from_tz": "PST", "to_tz": "KST"}),
        finish_response(
            verdict="refuted",
            cited=["EV_FC002_apple"],
            justification="공식 발표는 2024-01-19 05:00 PST이며 한국시간이 아니다. PST는 KST보다 17시간 느리다.",
            correction="사전예약 시작은 2024-01-19 22:00 KST",
            stop_reason="evidence_sufficient"),
    ]
    agent, backend = make_agent(script)

    result = agent.run(FC002)

    assert result.execution_status == ExecutionStatus.OK
    assert result.verdict == Verdict.REFUTED
    assert result.abstain is False
    assert result.cited_evidence_ids == ["EV_FC002_apple"]
    assert "22:00" in (result.correction or "")
    assert result.stop_reason == "evidence_sufficient"

    # The agent chose four steps and three tools, in that order.
    assert result.steps == 4
    assert [e.tool for e in result.events] == [
        "search_evidence", "read_evidence", "calculate_comparison"]
    assert all(e.status == ToolStatus.OK for e in result.events)
    assert result.searched_externally is False
    assert result.usage.tool_calls == 3
    assert result.usage.llm_calls == 4

    # Retrieval actually surfaced the decisive document and ranked it first.
    search_event = result.events[0]
    assert "EV_FC002_apple" in search_event.evidence_ids
    assert search_event.ranks[0] == 1
    assert backend.calls[0][0] == "search_corpus"


def test_messages_are_rebuilt_per_episode():
    """Q19-6: no session state carries over. Each episode starts clean."""
    script = [finish_response("supported", ["EV_FC002_preview"], "ok", "evidence_sufficient")]
    agent, _ = make_agent(script * 2)

    agent.run(FC002)
    first_len = len(agent.llm.seen_messages[0])
    agent.run(FC002)
    second_len = len(agent.llm.seen_messages[1])

    assert first_len == second_len == 2
    assert agent.llm.seen_messages[1][0]["content"] == SYSTEM_PROMPT


def test_agent_has_no_filesystem_tool():
    """Gold labels live in evaluation.md inside this repo.

    If the agent could read files it could read the answer key, so the tool
    list is the leakage boundary and this test pins it.
    """
    agent, _ = make_agent([])
    names = {s["function"]["name"] for s in agent.registry.schemas} | {FINISH_TOOL}

    assert names == {"search_evidence", "read_evidence", "calculate_comparison",
                     "search_web", "fetch_url", FINISH_TOOL}
    assert not any(n in names for n in {"read_file", "list_dir", "run_shell", "execute_code"})


def test_empty_search_is_not_a_false_verdict():
    """tools.md: `empty` means no results, never that the claim is false."""
    agent, _ = make_agent([
        tool_call_response("search_evidence", {"query": "zzz 없는 질의 zzz"}),
        finish_response("not_enough_evidence", [], "코퍼스에서 근거를 찾지 못했다",
                        "no_further_tools_helpful", abstain=True),
    ], corpus=[DISTRACTOR])

    result = agent.run(FC002)

    assert result.events[0].status == ToolStatus.EMPTY
    assert result.verdict == Verdict.NOT_ENOUGH_EVIDENCE
    assert result.abstain is True
    assert result.execution_status == ExecutionStatus.OK


def test_budget_is_enforced_without_retry():
    agent, backend = make_agent(
        [tool_call_response("search_evidence", {"query": f"반복 {i}"}) for i in range(10)],
        budget=Budget(max_steps=3, max_tool_calls=2, max_external_calls=1))

    result = agent.run(FC002)

    assert result.execution_status == ExecutionStatus.BUDGET_EXCEEDED
    assert result.verdict is None
    assert result.valid_verdict is False
    assert "max_tool_calls 2" in result.stop_reason
    assert sum(1 for c in backend.calls if c[0] == "search_corpus") == 2


def test_provider_failure_is_recorded_not_retried():
    class FailingLLM:
        model_id = "failing"

        def complete(self, messages, tools):
            raise RuntimeError("provider down")

    backend = MockBackend([APPLE])
    agent = ReActAgent(FailingLLM(), ToolRegistry(backend))

    result = agent.run(FC002)

    assert result.execution_status == ExecutionStatus.PROVIDER_ERROR
    assert backend.calls == []


def test_prose_answer_without_finish_is_a_parse_error():
    from task_a.loop import LLMResponse
    from task_a.schema import Usage

    class ProseLLM:
        model_id = "prose"

        def complete(self, messages, tools):
            return LLMResponse(content="그 주장은 틀렸습니다.", usage=Usage(llm_calls=1))

    agent = ReActAgent(ProseLLM(), ToolRegistry(MockBackend([APPLE])))

    result = agent.run(FC002)

    assert result.execution_status == ExecutionStatus.PARSE_ERROR


def test_unknown_tool_is_invalid_input():
    agent, _ = make_agent([
        tool_call_response("read_gold_answers", {"path": "evaluation.md"}),
        finish_response("supported", [], "ok", "evidence_sufficient"),
    ])

    result = agent.run(FC002)

    assert result.events[0].status == ToolStatus.INVALID_INPUT
    # ToolEvent stays lean (Q36 minimum fields); the refusal is what the model saw.
    tool_messages = [m for m in agent.llm.seen_messages[1] if m.get("role") == "tool"]
    assert "존재하지 않는 도구" in tool_messages[0]["content"]
    assert result.execution_status == ExecutionStatus.OK


@pytest.mark.parametrize("url,expected", [
    ("https://www.apple.com/newsroom/x", ToolStatus.OK),
    ("file:///etc/passwd", ToolStatus.BLOCKED),
    ("http://localhost:8000/gold", ToolStatus.BLOCKED),
    ("http://127.0.0.1/gold", ToolStatus.BLOCKED),
    ("http://192.168.1.5/gold", ToolStatus.BLOCKED),
    ("http://169.254.169.254/latest/meta-data", ToolStatus.BLOCKED),
    ("ftp://example.com/x", ToolStatus.BLOCKED),
])
def test_fetch_url_guard(url, expected):
    backend = MockBackend([APPLE], pages={"https://www.apple.com/newsroom/x": "본문"})
    registry = ToolRegistry(backend)

    result, is_external = registry.call("fetch_url", {"url": url})

    assert result.status == expected
    assert is_external is True
