"""Policy behaviour and the provider client, both without any network call."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from task_a.llm import PRICES, OpenAICompatibleClient, Pricing, estimate_cost
from task_a.loop import FINISH_TOOL, LLMResponse, ReActAgent, ToolCall
from task_a.mock import MockBackend, ScriptedLLM, finish_response, tool_call_response
from task_a.policies import (
    POLICIES, ClosedBookPolicy, FixedWorkflowPolicy, ReactPolicy, get_policy,
)
from task_a.schema import Claim, EpisodeState, EvidenceUnit, Usage, Verdict
from task_a.tools import ToolRegistry

CLAIM = Claim(claim_id="FC002", text="비전 프로 사전예약은 한국시간 오전 5시에 시작한다.")
DOC = EvidenceUnit(evidence_id="EV1", title="Apple Newsroom",
                   text="Pre-orders begin January 19 at 5:00 a.m. PST")
ALL_TOOLS = ["search_evidence", "read_evidence", "calculate_comparison",
             "search_web", "fetch_url", FINISH_TOOL]


def state(events=None, step=1):
    return EpisodeState(claim=CLAIM, step=step, events=events or [])


def event(tool, evidence_ids=None):
    from task_a.schema import ExecutionStatus, ToolEvent, ToolStatus
    return ToolEvent(step=1, tool=tool, args={}, status=ToolStatus.OK,
                     observation_chars=1, elapsed_ms=0,
                     evidence_ids=evidence_ids or [])


# --- policies --------------------------------------------------------------

def test_react_policy_never_forces_and_allows_everything():
    policy = ReactPolicy()

    assert policy.force(state()) is None
    assert policy.allowed_tools(ALL_TOOLS, state()) == ALL_TOOLS


def test_fixed_workflow_forces_search_then_read():
    policy = FixedWorkflowPolicy()

    first = policy.force(state())
    assert first.name == "search_evidence"
    assert first.args == {"query": CLAIM.text}

    after_search = state([event("search_evidence", ["EV1", "EV2"])])
    second = policy.force(after_search)
    assert second.name == "read_evidence"
    assert second.args == {"evidence_id": "EV1"}      # the best-ranked hit

    after_read = state([event("search_evidence", ["EV1"]), event("read_evidence", ["EV1"])])
    assert policy.force(after_read) is None


def test_fixed_workflow_stops_reading_when_search_found_nothing():
    policy = FixedWorkflowPolicy()

    assert policy.force(state([event("search_evidence", [])])) is None


def test_fixed_workflow_withholds_tools_once_gathering_is_done():
    """The point of 'fixed': the model cannot decide to search more."""
    policy = FixedWorkflowPolicy()
    gathered = state([event("search_evidence", ["EV1"]), event("read_evidence", ["EV1"])])

    assert policy.allowed_tools(ALL_TOOLS, state()) == ALL_TOOLS
    assert policy.allowed_tools(ALL_TOOLS, gathered) == [FINISH_TOOL]


def test_closed_book_offers_no_retrieval_at_all():
    policy = ClosedBookPolicy()

    assert policy.allowed_tools(ALL_TOOLS, state()) == [FINISH_TOOL]
    assert policy.force(state()) is None


def test_closed_book_prompt_differs_from_react():
    assert ClosedBookPolicy().system_prompt != ReactPolicy().system_prompt


def test_get_policy_rejects_unknown_name():
    assert get_policy("react").name == "react"
    with pytest.raises(ValueError, match="unknown policy"):
        get_policy("rl_controller")


def test_policy_registry_covers_the_three_compared_arms():
    assert set(POLICIES) == {"react", "fixed_workflow", "closed_book"}


def test_fixed_workflow_runs_end_to_end():
    """Same loop, same tools, same budget - only the decision rule differs."""
    backend = MockBackend([DOC])
    llm = ScriptedLLM([finish_response("refuted", ["EV1"], "공식은 PST다",
                                       "evidence_sufficient")])
    agent = ReActAgent(llm, ToolRegistry(backend), policy=FixedWorkflowPolicy())

    result = agent.run(CLAIM)

    assert result.verdict == Verdict.REFUTED
    assert [e.tool for e in result.events] == ["search_evidence", "read_evidence"]
    # The two retrieval steps were forced, so the model was asked only once.
    assert result.usage.llm_calls == 1
    assert len(llm.seen_messages) == 1


def test_closed_book_makes_no_tool_calls():
    backend = MockBackend([DOC])
    llm = ScriptedLLM([finish_response("not_enough_evidence", [], "외부 자료가 없다",
                                       "no_further_tools_helpful", abstain=True)])
    agent = ReActAgent(llm, ToolRegistry(backend), policy=ClosedBookPolicy())

    result = agent.run(CLAIM)

    assert result.events == []
    assert backend.calls == []
    assert result.abstain is True


def test_forced_call_produces_a_valid_transcript():
    """A tool message must follow an assistant message declaring that call."""
    backend = MockBackend([DOC])
    llm = ScriptedLLM([finish_response("supported", ["EV1"], "ok", "evidence_sufficient")])
    ReActAgent(llm, ToolRegistry(backend), policy=FixedWorkflowPolicy()).run(CLAIM)

    roles = [m["role"] for m in llm.seen_messages[0]]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "tool"]
    assistant = llm.seen_messages[0][2]
    assert assistant["tool_calls"][0]["function"]["name"] == "search_evidence"


# --- provider client -------------------------------------------------------

def stub_response(content=None, tool_calls=(), prompt_tokens=100, completion_tokens=20,
                  cached_tokens=0):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content,
                                                         tool_calls=list(tool_calls)))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens)))


def stub_tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(id=call_id,
                           function=SimpleNamespace(name=name, arguments=arguments))


class StubCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.kwargs = []

    def create(self, **kwargs):
        self.kwargs.append(kwargs)
        return self.responses.pop(0)


def make_client(responses, **kwargs):
    completions = StubCompletions(responses)
    stub = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    client = OpenAICompatibleClient("test-model", client=stub, **kwargs)
    return client, completions


def test_tool_calls_are_translated():
    client, _ = make_client([stub_response(tool_calls=[
        stub_tool_call("search_evidence", '{"query": "비전 프로"}')])])

    response = client.complete([], [])

    assert response.tool_calls == [ToolCall(id="call_1", name="search_evidence",
                                            args={"query": "비전 프로"})]


def test_arguments_are_passed_as_a_json_string():
    client, completions = make_client([stub_response(content="done")])

    client.complete([{"role": "user", "content": "hi"}], [{"type": "function"}])

    sent = completions.kwargs[0]
    assert sent["model"] == "test-model"
    assert sent["temperature"] == 0.0
    assert sent["tools"] == [{"type": "function"}]
    assert sent["tool_choice"] == "auto"


def test_tools_are_omitted_when_the_policy_allows_none():
    """C0 offers only finish_verification, but an empty list must not be sent."""
    client, completions = make_client([stub_response(content="x")])

    client.complete([], [])

    assert "tools" not in completions.kwargs[0]


def test_seed_and_max_tokens_are_forwarded():
    client, completions = make_client([stub_response()], seed=7, max_tokens=256)

    client.complete([], [])

    assert completions.kwargs[0]["seed"] == 7
    assert completions.kwargs[0]["max_tokens"] == 256


def test_cached_tokens_are_recorded_separately():
    client, _ = make_client([stub_response(prompt_tokens=1000, completion_tokens=50,
                                           cached_tokens=800)])

    usage = client.complete([], []).usage

    assert (usage.input_tokens, usage.output_tokens, usage.cached_tokens) == (1000, 50, 800)


def test_cost_is_none_without_a_price_quote():
    """No invented prices: an unpriced model reports unknown, not zero."""
    client, _ = make_client([stub_response(prompt_tokens=1_000_000, completion_tokens=0)])

    response = client.complete([], [])

    assert response.usage.cost_usd == 0.0
    assert client.unpriced_calls == 1
    assert client.pricing_note()["pricing_available"] is False


def test_cost_uses_the_quote_and_discounts_cached_input():
    pricing = Pricing(input_per_million=3.0, output_per_million=15.0,
                      cached_input_per_million=0.3, quoted_at="2026-11-07")
    client, _ = make_client([stub_response(prompt_tokens=1_000_000, completion_tokens=100_000,
                                           cached_tokens=400_000)], pricing=pricing)

    usage = client.complete([], []).usage

    # 600k fresh input * 3 + 400k cached * 0.3 + 100k output * 15, per million
    assert usage.cost_usd == pytest.approx((600_000 * 3.0 + 400_000 * 0.3
                                            + 100_000 * 15.0) / 1_000_000)
    assert client.unpriced_calls == 0


def test_estimate_cost_without_cached_pricing_charges_full_rate():
    usage = Usage(input_tokens=1_000_000, cached_tokens=500_000)
    pricing = Pricing(input_per_million=2.0, output_per_million=0.0)

    assert estimate_cost(usage, pricing) == pytest.approx(1.0)
    assert estimate_cost(usage, None) is None


def test_price_table_starts_empty():
    """Guard against someone committing a guessed price."""
    assert PRICES == {}


def test_malformed_arguments_are_preserved_not_dropped():
    client, _ = make_client([stub_response(tool_calls=[
        stub_tool_call("search_evidence", "{not json")])])

    response = client.complete([], [])

    assert response.tool_calls[0].args == {"_unparsed": "{not json"}


def test_provider_errors_propagate_so_the_loop_can_record_them():
    """No retry: the loop turns this into PROVIDER_ERROR exactly once."""
    class Exploding:
        def create(self, **kwargs):
            raise RuntimeError("429")

    client = OpenAICompatibleClient("m", client=SimpleNamespace(
        chat=SimpleNamespace(completions=Exploding())))

    with pytest.raises(RuntimeError, match="429"):
        client.complete([], [])

    backend = MockBackend([DOC])
    agent = ReActAgent(client, ToolRegistry(backend))
    assert agent.run(CLAIM).execution_status.value == "provider_error"
