"""End-to-end runs with the scripted demo agent and fake web: no model, no network."""

from __future__ import annotations

import json
import os
from datetime import date

import pytest

from assistant import db, demo
from assistant.activity import EventBus
from assistant.budget import Budget, BudgetExceeded
from assistant.config import DEFAULTS, public_settings, save_settings
from assistant.ics import to_ics
from assistant.llm import ChatReply, OpenAICompatClient, LLMError, parse_reply
from assistant.pipeline import AppContext, RunBusy, run_now

TODAY = date(2026, 11, 24)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "today_kst", lambda: TODAY.isoformat())
    data = demo.build(TODAY)
    save_settings(tmp_path / "settings.json", demo.demo_settings(DEFAULTS))
    return AppContext(tmp_path, EventBus(), lambda s: demo.demo_client(data),
                      lambda s: demo.DemoWeb(data), mode="demo")


def _by_title(conn):
    return {e["title"]: e for e in db.list_events(conn)}


def test_demo_run_reaches_every_policy_outcome(ctx):
    run_id = run_now(ctx)
    conn = ctx.connect()
    run = db.get_run(conn, run_id)
    assert run["status"] == "ok" and run["candidates"] == 5
    ev = _by_title(conn)
    assert ev["노바랩스 호라이즌 키노트"]["status"] == "auto_added"
    pixel = ev["픽셀포지 쇼케이스"]
    assert pixel["status"] == "auto_added" and pixel["verdict"] == "refuted"
    assert pixel["start_kst"].endswith(("23:00", "22:00"))   # CET or CEST
    assert ev["스타폴 출시"]["status"] == "pending_approval" and ev["스타폴 출시"]["precision"] == "date"
    assert ev["오르빗모바일 언팩"]["status"] == "tracking"
    quasar = ev["퀘이사 데브데이"]
    # The time came only from a search snippet: it is dropped (all-day), and the
    # single non-official blog still needs approval.
    assert quasar["status"] == "pending_approval" and quasar["precision"] == "date"
    assert {"GATE_BLOCKED", "TIME_UNCONFIRMED"} <= set(quasar["reasons"])
    # Evidence keeps URLs and a short quote, never the page text.
    full = db.get_event(conn, ev["노바랩스 호라이즌 키노트"]["id"])
    assert full["evidence"] and all(len(e["quote"] or "") <= db.MAX_QUOTE_CHARS for e in full["evidence"])
    assert {s["kind"] for s in run["steps"]} >= {"search", "read", "calc", "verdict", "decision", "done"}


def test_second_run_does_not_duplicate(ctx):
    run_now(ctx)
    run_id = run_now(ctx)
    conn = ctx.connect()
    assert len(db.list_events(conn)) == 5
    assert "이미 있음 4" in db.get_run(conn, run_id)["summary"]   # rechecks run, nothing duplicated


def test_user_actions_follow_the_state_rules(ctx):
    run_now(ctx)
    conn = ctx.connect()
    ev = _by_title(conn)
    star = ev["스타폴 출시"]["id"]
    assert db.user_action(conn, star, "approve")["status"] == "added"
    assert db.user_action(conn, star, "undo")["status"] == "undone"
    with pytest.raises(db.IllegalTransition):
        db.user_action(conn, ev["오르빗모바일 언팩"]["id"], "approve")   # tracking: nothing verified
    decisions = db.get_event(conn, star)["decisions"]
    assert [d["actor"] for d in decisions] == ["policy", "user", "user"]


def test_budget_cap_stops_the_run(ctx):
    conn = ctx.connect()
    db.ledger_add(conn, TODAY.isoformat(), search_calls=100)
    run_id = run_now(ctx)
    run = db.get_run(conn, run_id)
    assert run["status"] == "budget_stop" and "검색" in run["error"]
    assert db.list_events(conn) == []


def test_cost_cap_refuses_model_calls(tmp_path):
    conn = db.connect(tmp_path / "a.sqlite")
    settings = json.loads(json.dumps(DEFAULTS))
    budget = Budget(conn, settings, day="2026-11-24")
    budget.charge_llm({"prompt_tokens": 7_000_000, "completion_tokens": 0})   # $1.05
    with pytest.raises(BudgetExceeded):
        budget.check_llm()


def test_one_run_at_a_time(ctx, monkeypatch):
    from assistant import pipeline
    pipeline._lock.acquire()
    try:
        with pytest.raises(RunBusy):
            run_now(ctx)
    finally:
        pipeline._lock.release()


def test_ics_export_has_all_day_and_utc_events(ctx):
    run_now(ctx)
    conn = ctx.connect()
    text = to_ics(db.list_events(conn, db.ON_SCHEDULE + ("pending_approval",)))
    assert "DTSTART;VALUE=DATE:" in text and "Z\r\n" in text and text.endswith("END:VCALENDAR\r\n")
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))


def test_openai_compat_client_parses_tool_calls_without_network(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "secret-value")
    seen = {}

    def transport(url, headers, body, timeout):
        seen.update(url=url, body=body, auth=headers["Authorization"])
        return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "c1", "type": "function",
                "function": {"name": "search_web", "arguments": "{\"query\": \"x\"}"}}]}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2}}

    client = OpenAICompatClient("https://api.example/v1", "m", "TEST_KEY", transport=transport)
    reply = client.complete([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert reply.tool_calls[0].arguments == {"query": "x"} and reply.usage["prompt_tokens"] == 10
    assert seen["url"].endswith("/chat/completions") and seen["body"]["parallel_tool_calls"] is False
    monkeypatch.delenv("TEST_KEY")
    with pytest.raises(LLMError, match="TEST_KEY"):
        client.complete([])


def test_bad_json_arguments_are_reported_not_crashing():
    reply = parse_reply({"choices": [{"message": {"tool_calls": [
        {"id": "c", "function": {"name": "fetch_url", "arguments": "{not json"}}]}}]})
    assert "__invalid_json__" in reply.tool_calls[0].arguments


def test_public_settings_never_contain_key_values(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-should-not-appear")
    out = json.dumps(public_settings(DEFAULTS))
    assert "sk-should-not-appear" not in out and '"MISTRAL_API_KEY": true' in out


def test_queries_look_ahead():
    from assistant.discover import fill_query
    assert fill_query("Nintendo Direct {month} {year}", "2026-11-24") == "Nintendo Direct November 2026"
    assert fill_query("{next_month} {next_year}", "2026-12-24") == "January 2027"


def test_dropped_candidates_are_counted_with_reasons(tmp_path):
    from assistant.discover import extract_candidates
    conn = db.connect(tmp_path / "a.sqlite")
    budget = Budget(conn, json.loads(json.dumps(DEFAULTS)), day="2026-11-24")
    results = [{"url": "https://a.example/x", "title": "x", "snippet": "s"}]
    events = [{"name": "Past", "start": "2026-01-01", "source_url": "https://a.example/x"},
              {"name": "Made up", "start": "2026-12-01", "source_url": "https://other.example"},
              {"name": "Good", "start": "2026-12-01T10:00:00", "tz": "Mars/Base",
               "source_url": "https://a.example/x"}]
    client = demo.ScriptedClient(lambda m, t, j: ChatReply(content=json.dumps({"events": events})))
    steps = []
    out = extract_candidates(client, budget, {"id": "tech", "name": "테크"}, results, "2026-11-24", 5,
                             lambda kind, label, detail=None: steps.append(detail))
    assert [c.name for c in out] == ["Good"] and out[0].start == "2026-12-01 10:00" and out[0].tz is None
    assert "지난 일정 1" in steps[0] and "검색 결과에 없는 주소 1" in steps[0]


def test_extracted_claims_name_their_event(tmp_path):
    from assistant.discover import extract_candidates
    conn = db.connect(tmp_path / "a.sqlite")
    budget = Budget(conn, json.loads(json.dumps(DEFAULTS)), day="2026-11-24")
    results = [{"url": "https://a.example/x", "title": "x", "snippet": "s"}]
    events = [{"name": "Piece by Piece", "title_ko": "피스 바이 피스", "start": "2026-11-25",
               "claim_text": "2026년 11월 25일에 출시될 예정이다.", "source_url": "https://a.example/x"}]
    client = demo.ScriptedClient(lambda m, t, j: ChatReply(content=json.dumps({"events": events})))
    out = extract_candidates(client, budget, {"id": "game", "name": "게임"}, results, "2026-11-24", 5,
                             lambda *a, **k: None)
    assert out[0].claim_text.startswith("피스 바이 피스:")


def test_a_moved_event_is_flagged_and_the_user_decides(ctx):
    run_now(ctx)
    run_id = run_now(ctx)                       # Nova Labs moved its keynote one hour later
    conn = ctx.connect()
    ev = _by_title(conn)
    nova = db.get_event(conn, ev["노바랩스 호라이즌 키노트"]["id"])
    assert nova["status"] == "changed" and nova["proposed_start"] and nova["proposed_start"] != nova["start_kst"]
    assert "SCHEDULE_CHANGED" in nova["reasons"]
    # The unchanged Pixel Forge entry was confirmed again, not touched.
    assert ev["픽셀포지 쇼케이스"]["status"] == "auto_added" and ev["픽셀포지 쇼케이스"]["last_checked_at"]
    assert ev["오르빗모바일 언팩"]["status"] == "tracking"
    assert "변경 감지 1" in db.get_run(conn, run_id)["summary"]
    new = nova["proposed_start"]
    after = db.user_action(conn, nova["id"], "approve")
    assert after["status"] == "added" and after["start_kst"] == new and after["proposed_start"] is None


def test_keep_the_old_time_and_housekeeping(ctx):
    run_now(ctx)
    run_now(ctx)
    conn = ctx.connect()
    nova = _by_title(conn)["노바랩스 호라이즌 키노트"]
    old = nova["start_kst"]
    kept = db.user_action(conn, nova["id"], "keep")
    assert kept["status"] == "added" and kept["start_kst"] == old
    assert db.housekeep(conn, "2030-01-01T00:00:00+09:00") >= 3
    statuses = {e["status"] for e in db.list_events(conn)}
    assert "occurred" in statuses and "expired" in statuses
