"""HTTP API of the local app, driven with the demo agent (no model, no network)."""

from __future__ import annotations

import http.client
import json
import threading
import time
from datetime import date, datetime

import pytest

from assistant import db, demo, pipeline
from assistant.activity import EventBus
from assistant.config import DEFAULTS, save_settings
from assistant.pipeline import AppContext
from assistant.scheduler import Scheduler
from assistant.server import make_server

TODAY = date(2026, 11, 24)


@pytest.fixture
def served(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "today_kst", lambda: TODAY.isoformat())
    data = demo.build(TODAY)
    save_settings(tmp_path / "settings.json", demo.demo_settings(DEFAULTS))
    ctx = AppContext(tmp_path, EventBus(), lambda s: demo.demo_client(data),
                     lambda s: demo.DemoWeb(data), mode="demo")
    server = make_server(ctx, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield ctx, server.server_address[1]
    server.shutdown()
    server.server_close()


def call(port, method, path, body=None, headers=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    h = {"Content-Type": "application/json", "X-Requested-With": "assistant"}
    h.update(headers or {})
    if host:
        h["Host"] = host
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
    resp = conn.getresponse()
    raw = resp.read()
    ctype = resp.getheader("Content-Type", "")
    conn.close()
    return resp.status, (json.loads(raw) if "json" in ctype else raw.decode())


def wait_idle(timeout=10):
    end = time.time() + timeout
    time.sleep(0.05)
    while pipeline.is_running() and time.time() < end:
        time.sleep(0.05)


def test_ui_and_state_are_served(served):
    _, port = served
    status, html = call(port, "GET", "/")
    assert status == 200 and "일정 비서" in html
    status, state = call(port, "GET", "/api/state")
    assert status == 200 and state["mode"] == "demo" and state["budget"]["cap_usd"] == 1.0
    assert call(port, "GET", "/static/../server.py")[0] == 404


def test_requests_from_other_hosts_and_without_header_are_refused(served):
    _, port = served
    assert call(port, "GET", "/api/state", host="evil.example")[0] == 403
    assert call(port, "POST", "/api/runs", headers={"X-Requested-With": ""})[0] == 403


def test_run_approve_and_export(served):
    _, port = served
    assert call(port, "POST", "/api/runs")[0] == 202
    wait_idle()
    status, events = call(port, "GET", "/api/events")
    assert status == 200 and len(events) == 5
    pending = [e for e in events if e["status"] == "pending_approval"]
    assert pending and all(e["reasons_text"] for e in pending)
    star = next(e for e in pending if e["precision"] == "date")
    status, ev = call(port, "POST", f"/api/events/{star['id']}/approve")
    assert status == 200 and ev["status"] == "added"
    assert call(port, "POST", f"/api/events/{star['id']}/approve")[0] == 409
    status, ics = call(port, "GET", "/api/export.ics")
    assert status == 200 and ics.count("BEGIN:VEVENT") == 3   # two auto-added + one approved
    status, runs = call(port, "GET", "/api/runs")
    assert runs[0]["status"] == "ok"
    status, run = call(port, "GET", f"/api/runs/{runs[0]['id']}")
    assert any(s["kind"] == "decision" for s in run["steps"])


def test_settings_are_validated(served):
    _, port = served
    assert call(port, "PUT", "/api/settings", {"schedule": {"daily_at": "25:00"}})[0] == 400
    assert call(port, "PUT", "/api/settings", {"budget": {"daily_cost_usd": 50}})[0] == 400
    status, s = call(port, "PUT", "/api/settings", {"schedule": {"enabled": True, "daily_at": "08:30"},
                                                     "budget": {"daily_searches": 100}})
    assert status == 200 and s["schedule"]["enabled"] and "MISTRAL_API_KEY" in s["secrets"]


def test_scheduler_runs_once_and_daily(served):
    ctx, port = served
    sched = Scheduler(ctx)
    call(port, "PUT", "/api/settings", {"schedule": {"run_in_minutes": 1}})
    once_at = datetime.fromisoformat(ctx.settings()["schedule"]["once_at"])
    assert sched.tick(once_at.replace(year=2000)) is None    # not yet due
    assert sched.tick(once_at) == "once"
    wait_idle()
    assert ctx.settings()["schedule"]["once_at"] is None
    call(port, "PUT", "/api/settings", {"schedule": {"enabled": True, "daily_at": "09:00"}})
    morning = datetime(2026, 11, 25, 9, 1, tzinfo=db.KST)
    assert sched.tick(morning) == "daily"
    wait_idle()
    assert sched.tick(morning) is None   # once per day


def test_interests_can_be_edited_and_are_validated(served):
    _, port = served
    status, s = call(port, "GET", "/api/settings")
    interests = s["interests"]
    interests[1]["keywords"] = ["닌텐도 다이렉트", "GTA", "GTA"]
    interests.append({"name": "콘서트 예매", "keywords": ["아이유 콘서트"], "official_domains": ["https://www.melon.com/"]})
    status, out = call(port, "PUT", "/api/settings", {"interests": interests, "onboarded": True})
    assert status == 200 and out["onboarded"] is True
    assert out["interests"][1]["keywords"] == ["닌텐도 다이렉트", "GTA"]
    assert out["interests"][2]["official_domains"] == ["melon.com"] and out["interests"][2]["id"]
    bad = interests[:1] + [{"name": "x", "keywords": ["k"], "official_domains": ["not a domain"]}]
    assert call(port, "PUT", "/api/settings", {"interests": bad})[0] == 400
    assert call(port, "PUT", "/api/settings", {"interests": [{"name": "빈 분야"}]})[0] == 400


def test_keyword_queries():
    from assistant.discover import keyword_query
    assert keyword_query("GTA", "2026-11-24") == "GTA November 2026 date announced"
    assert keyword_query("갤럭시", "2026-11-24") == "갤럭시 2026년 11월 일정 발표"
