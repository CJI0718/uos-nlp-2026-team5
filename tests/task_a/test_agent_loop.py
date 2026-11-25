"""Offline tests for the OpenAI-compatible episode loop (no model is called)."""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import pytest

from assistant.llm import ChatReply, ScriptedClient, ToolCall
from task_a.agent_loop import (
    Budget, BudgetExceeded, Price, openai_tools, run_episode, system_prompt,
)
from task_a.mcp_server import AgentEnvironment
from task_a.schema import Claim, write_jsonl

ROOT = Path(__file__).resolve().parents[2]

CLAIM = Claim(
    claim_id="FC900",
    text="한국은행은 2025년 5월 29일 기준금리를 0.50%포인트 낮췄다.",
    target_period="2025-05-29 금통위",
    input_body="[입력 본문 — 게시물 전사]\n기준금리를 0.50%포인트(p) 인하했다.",
)
DOC = {"evidence_id": "DOC_bok", "title": "한국은행 기준금리 추이",
       "text": "변경일자 기준금리 2025 05월 29일 2.50 2025 02월 25일 2.75", "publisher": "한국은행"}
PRICE = Price(input=0.3, output=1.2)


def _env(tmp_path, arm="C1"):
    claims = tmp_path / "claims.jsonl"
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(claims, [CLAIM.to_dict()])
    write_jsonl(corpus, [DOC])
    return AgentEnvironment(claims_path=claims, out_path=tmp_path / "run.jsonl", arm=arm,
                            corpus_path=corpus if arm != "C0" else None,
                            missions_dir=tmp_path / "missions", tokenizer="bigram")


def _reply(*calls, usage=(1000, 100)):
    return ChatReply(content="", usage={"prompt_tokens": usage[0], "completion_tokens": usage[1]},
                     tool_calls=[ToolCall(id=f"c{i}", name=n, arguments=a) for i, (n, a) in enumerate(calls)])


FINISH = ("finish_verification", {
    "verdict": "refuted", "abstain": False, "cited_evidence_ids": ["DOC_bok"],
    "justification": "2.75%에서 2.50%로 0.25%p 인하", "correction": "0.25%포인트 인하",
    "stop_reason": "evidence_sufficient"})


def _scripted(replies):
    it = iter(replies)
    seen = []

    def responder(messages, tools, json_mode):
        seen.append((json.loads(json.dumps(messages)), tools))
        return next(it)
    return ScriptedClient(responder), seen


def test_episode_runs_through_the_server_and_logs_the_verdict(tmp_path):
    env = _env(tmp_path)
    client, seen = _scripted([
        _reply(("search_evidence", {"query": "기준금리 2025"})),
        _reply(("read_evidence", {"evidence_id": "DOC_bok"})),
        _reply(FINISH),
    ])
    out = run_episode(env, client, "FC900", price=PRICE, budget=Budget(1.0))

    assert out.finished and out.verdict == "refuted" and out.execution_status == "ok"
    assert out.turns == 3
    assert out.cost_usd == pytest.approx(3 * PRICE.cost(1000, 100))
    row = json.loads((tmp_path / "run.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["result"]["verdict"] == "refuted"
    assert [e["tool"] for e in row["result"]["events"]] == ["search_evidence", "read_evidence"]
    # The model saw the start_episode payload, the Skill, and no episode-control tools.
    first_messages, tools = seen[0]
    assert "FC900" in first_messages[1]["content"] and "0.50%포인트" in first_messages[1]["content"]
    assert "Fact-Check" in first_messages[0]["content"]
    names = {t["function"]["name"] for t in tools}
    assert not names & {"start_episode", "list_claims", "submit_claim"}
    assert "finish_verification" in names


def test_c0_offers_only_finish(tmp_path):
    env = _env(tmp_path, arm="C0")
    assert [t["function"]["name"] for t in openai_tools(env)] == ["finish_verification"]


def test_invalid_finish_keeps_the_episode_open(tmp_path):
    env = _env(tmp_path)
    bad = ("finish_verification", {"verdict": "refuted"})   # no justification
    client, seen = _scripted([_reply(bad), _reply(FINISH)])
    out = run_episode(env, client, "FC900", price=PRICE, budget=Budget(1.0))

    assert out.finished and out.invalid_tool_calls == 1
    tool_msg = [m for m in seen[1][0] if m["role"] == "tool"][0]
    assert "justification" in tool_msg["content"]


def test_model_that_stops_calling_tools_is_a_logged_failure(tmp_path):
    env = _env(tmp_path)
    text_only = ChatReply(content="반박입니다.", usage={"prompt_tokens": 10, "completion_tokens": 5})
    client, _ = _scripted([text_only] * 3)
    out = run_episode(env, client, "FC900", price=PRICE, budget=Budget(1.0))

    assert not out.finished and out.execution_status == "parse_error" and out.nudges == 3
    row = json.loads((tmp_path / "run.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["result"]["execution_status"] == "parse_error" and row["result"]["verdict"] is None
    assert env.active is None


def test_turn_limit_is_a_logged_failure(tmp_path):
    env = _env(tmp_path)
    client, _ = _scripted([_reply(("search_evidence", {"query": "금리"}))] * 3)
    out = run_episode(env, client, "FC900", price=PRICE, budget=Budget(1.0), max_turns=3)

    assert out.execution_status == "budget_exceeded" and "턴 한도" in out.error


def test_provider_error_is_not_retried(tmp_path):
    env = _env(tmp_path)
    calls = []

    def responder(messages, tools, json_mode):
        calls.append(1)
        raise RuntimeError("HTTP 500: upstream")
    out = run_episode(env, ScriptedClient(responder), "FC900", price=PRICE, budget=Budget(1.0))

    assert len(calls) == 1 and out.execution_status == "provider_error"


def test_money_cap_stops_mid_episode_and_logs_it(tmp_path):
    env = _env(tmp_path)
    expensive = _reply(("search_evidence", {"query": "금리"}), usage=(1_000_000, 0))  # $0.30
    client, _ = _scripted([expensive] * 5)
    budget = Budget(0.5)
    with pytest.raises(BudgetExceeded):
        run_episode(env, client, "FC900", price=PRICE, budget=budget)
    row = json.loads((tmp_path / "run.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["result"]["execution_status"] == "budget_exceeded"
    assert budget.spent == pytest.approx(0.6)


def test_reasoning_chunks_are_not_sent_back(tmp_path):
    env = _env(tmp_path)
    first = _reply(("search_evidence", {"query": "금리"}))
    first.message = {"role": "assistant",
                     "content": [{"type": "thinking", "thinking": [{"type": "text", "text": "생각"}]},
                                 {"type": "text", "text": "검색합니다"}],
                     "tool_calls": [{"id": "c0", "type": "function",
                                     "function": {"name": "search_evidence", "arguments": "{\"query\": \"금리\"}"}}]}
    client, seen = _scripted([first, _reply(FINISH)])
    run_episode(env, client, "FC900", price=PRICE, budget=Budget(1.0))

    assistant = [m for m in seen[1][0] if m["role"] == "assistant"][0]
    assert assistant["content"] == "검색합니다"


def test_cached_tokens_use_the_cached_price():
    p = Price(input=0.3, output=1.2, cached_input=0.007)
    assert p.cost(1_000_000, 0, cached=1_000_000) == pytest.approx(0.007)
    assert Price(0.3, 1.2).cost(1_000_000, 0, cached=1_000_000) == pytest.approx(0.3)


def test_system_prompt_is_the_skill_plus_the_harness_note():
    text = system_prompt()
    assert "finish_verification" in text and "이미 시작" in text


# --- runner helpers ------------------------------------------------------------

def _runner():
    spec = importlib.util.spec_from_file_location("run_task_a", ROOT / "scripts/run_task_a.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_counting_web_declares_end_date_and_counts_searches():
    mod = _runner()

    class Fake:
        def search(self, query, top_k=5, end_date=None, start_date=None):
            return [{"url": "https://x", "end": end_date}]

        def fetch(self, url):
            return {"text": "t"}

    counter = mod.TavilyCounter(cap=2, used_before=1)
    web = mod.CountingWeb(Fake(), counter)
    assert "end_date" in inspect.signature(web.search).parameters
    assert web.search("q", 5, end_date="2025-01-01")[0]["end"] == "2025-01-01"
    with pytest.raises(RuntimeError):
        web.search("q2")
    assert web.searches == 1 and counter.used == 2
    web.fetch("https://x")   # fetches are not Tavily searches
    assert counter.used == 2


def test_reference_matching_by_doc_id_or_same_url():
    mod = _runner()
    ref = {"docs": {"DOC_a"}, "urls": {mod._norm_url("https://www.bok.or.kr/portal/x?menuNo=1")}}
    assert mod.cites_reference({"cited_evidence_ids": ["DOC_a"]}, ref)
    assert mod.cites_reference({"cited_evidence_ids": ["http://bok.or.kr/portal/x/?menuNo=1"]}, ref)
    assert not mod.cites_reference({"cited_evidence_ids": ["https://bok.or.kr/portal/y"]}, ref)


def test_unread_citations_are_flagged():
    mod = _runner()
    result = {"cited_evidence_ids": ["DOC_a", "DOC_b"],
              "events": [{"tool": "read_evidence", "status": "ok", "evidence_ids": ["DOC_a"]},
                         {"tool": "search_evidence", "status": "ok", "evidence_ids": ["DOC_b"]}]}
    assert mod.unread_citations(result) == ["DOC_b"]


def test_ledger_totals_sum_every_run(tmp_path):
    mod = _runner()
    path = tmp_path / "ledger.jsonl"
    mod.ledger_append({"cost_usd": 0.1, "tavily_searches": 3}, path)
    mod.ledger_append({"cost_usd": 0.25, "tavily_searches": 0}, path)
    assert mod.ledger_totals(path) == {"cost_usd": 0.35, "tavily_searches": 3, "episodes": 2}
