"""One assistant run: discover → match → verify → decide → store, with a live activity log.

Runs one at a time. Nothing is retried: a failed search, model call or
verification is recorded and the run moves on (or stops at a budget cap).
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from assistant import db
from assistant.activity import EventBus
from assistant.budget import Budget, BudgetExceeded
from assistant.config import load_settings
from assistant.dedupe import event_key, find_match, key_name
from assistant.discover import extract_candidates, search_interest
from assistant.policy import decide, explain
from assistant.verify import Candidate, claimed_kst, verify_candidate
from task_a.mcp_server import AgentEnvironment
from task_a.missions import is_date_only

#: States a newly discovered duplicate does not reopen (the user or policy already decided).
SETTLED = ("auto_added", "added", "pending_approval", "rejected", "undone", "changed")


class RunBusy(RuntimeError):
    pass


@dataclass
class AppContext:
    data_dir: Path
    bus: EventBus
    client_factory: Callable[[dict], object]
    web_factory: Callable[[dict], object]
    mode: str = "live"            # "live" or "demo"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "assistant.sqlite"

    @property
    def settings_path(self) -> Path:
        return self.data_dir / "settings.json"

    def settings(self) -> dict:
        return load_settings(self.settings_path)

    def connect(self):
        return db.connect(self.db_path)


_lock = threading.Lock()


def start_background(ctx: AppContext, trigger: str) -> None:
    """Start a run in a thread; RunBusy if one is already going."""
    if not _lock.acquire(blocking=False):
        raise RunBusy("이미 실행 중입니다.")
    threading.Thread(target=_locked_run, args=(ctx, trigger), daemon=True).start()


def run_now(ctx: AppContext, trigger: str = "manual") -> int:
    if not _lock.acquire(blocking=False):
        raise RunBusy("이미 실행 중입니다.")
    return _locked_run(ctx, trigger)


def is_running() -> bool:
    return _lock.locked()


def _locked_run(ctx: AppContext, trigger: str) -> int:
    try:
        return _run(ctx, trigger)
    finally:
        _lock.release()


def _run(ctx: AppContext, trigger: str) -> int:
    settings = ctx.settings()
    conn = ctx.connect()
    run_id = db.start_run(conn, trigger, ctx.mode)
    budget = Budget(conn, settings)
    caps = settings["budget"]
    stats = {"candidates": 0, "verified": 0}
    outcomes: dict[str, int] = {}

    def emit(kind: str, label: str, detail: str | None = None, key: str | None = None) -> None:
        step = db.add_step(conn, run_id, kind, label, detail, key)
        ctx.bus.publish({"type": "step", **step})

    ctx.bus.publish({"type": "run_started", "run_id": run_id, "trigger": trigger, "mode": ctx.mode})
    emit("info", "실행 시작" + (" (시연용 가짜 모델·웹)" if ctx.mode == "demo" else ""),
         f"오늘 남은 예산 ${budget.remaining()['cost_usd']:.2f}, 검색 {budget.remaining()['searches']}회")
    status, error = "ok", None
    try:
        client = ctx.client_factory(settings)
        web = ctx.web_factory(settings)
        env = _environment(ctx, settings, web, run_id, client)
        today = db.today_kst()
        queue = _rechecks(conn) + _discover(settings, web, client, budget, today, emit)
        stats["candidates"] = len(queue)
        for cand in queue[: caps["max_candidates_per_run"]]:
            result = _handle(conn, ctx, env, client, budget, cand, settings, today, run_id, emit)
            if result:
                stats["verified"] += result != "skipped"
                outcomes[result] = outcomes.get(result, 0) + 1
    except BudgetExceeded as exc:
        status, error = "budget_stop", str(exc)
        emit("budget", "예산 상한에서 멈춤", str(exc))
    except Exception as exc:   # recorded, never retried
        status, error = "failed", f"{type(exc).__name__}: {exc}"[:300]
        emit("error", "실행 실패", error)
        traceback.print_exc()
    summary = ", ".join(f"{_STATUS_KO.get(k, k)} {n}" for k, n in outcomes.items()) or "새 일정 없음"
    db.finish_run(conn, run_id, status, {**stats, **budget.run}, summary, error)
    emit("done", f"실행 끝: {summary}",
         f"모델 {budget.run['llm_calls']}회 · ${budget.run['cost_usd']:.4f} · 검색 {budget.run['search_calls']}회")
    ctx.bus.publish({"type": "run_finished", "run_id": run_id, "status": status})
    conn.close()
    return run_id


_STATUS_KO = {"auto_added": "자동 등록", "pending_approval": "승인 대기", "tracking": "추적",
              "rejected": "제외", "error": "오류", "skipped": "이미 있음"}


def _environment(ctx: AppContext, settings: dict, web, run_id: int, client) -> AgentEnvironment:
    caps = settings["budget"]
    return AgentEnvironment(
        claims_path=None, allow_user_claims=True, arm="C2", web_provider=web, web_only=True,
        gate="provenance", provenance_mode="auto", show_provenance=True, tokenizer="bigram",
        out_path=ctx.data_dir / "runlog.jsonl", missions_dir=ctx.data_dir / "missions",
        cache_path=None, max_tool_calls=caps["max_tool_calls"],
        max_external_calls=caps["max_external_calls"], run_id=f"assistant-{run_id}",
        model_id=f"assistant+{getattr(client, 'model', 'unknown')}", data_version="assistant-v1",
        prompt_version="assistant-v1")


def _discover(settings, web, client, budget, today, emit) -> list[Candidate]:
    caps, out = settings["budget"], []
    for interest in settings["interests"]:
        if not interest.get("enabled", True):
            continue
        results = search_interest(web, interest, budget, emit, caps["queries_per_interest"])
        out += extract_candidates(client, budget, interest, results, today,
                                  caps["max_candidates_per_run"], emit)
    return out


def _rechecks(conn) -> list[Candidate]:
    """Tracked events whose next check is due, re-verified before new discoveries."""
    now = db.now_iso()
    out = []
    for ev in db.list_events(conn, ("tracking",)):
        if ev.get("next_check_at") and ev["next_check_at"] > now:
            continue
        out.append(Candidate(interest=ev["interest"], name=_name_from_key(ev["event_key"], ev["title"]),
                             title_ko=ev["title"], claim_text=ev["claim_text"],
                             start=ev.get("start_kst") or "", tz="Asia/Seoul",
                             source_url=ev.get("source_url"), recheck_of=ev["id"]))
    return out


def _name_from_key(key: str, fallback: str) -> str:
    return key_name(key) or fallback


def _handle(conn, ctx, env, client, budget, cand: Candidate, settings, today, run_id, emit) -> str | None:
    interest = next((i for i in settings["interests"] if i["id"] == cand.interest), None)
    if interest is None:
        return None
    claimed = claimed_kst(cand)
    existing_all = db.events_in_interest(conn, cand.interest)
    match = find_match(existing_all, cand.interest, cand.name, claimed or cand.start)
    key = match["event_key"] if match else event_key(cand.interest, cand.name, claimed or cand.start)
    if cand.recheck_of is None and match and match["status"] in SETTLED:
        emit("skip", f"이미 있음: {match['title']}", None, key)
        return "skipped"

    emit("candidate", f"검증: {cand.title_ko}", f"주장: {cand.claim_text}", key)
    outcome = verify_candidate(env, client, cand, budget,
                               lambda k, label, detail=None: emit(k, label, detail, key),
                               max_turns=settings["budget"]["max_llm_turns"])
    base = {"event_key": key, "interest": cand.interest, "title": cand.title_ko or cand.name,
            "claim_text": cand.claim_text, "source_url": cand.source_url, "local_tz": cand.tz}
    if outcome.verified is None:
        fields = {**base, "status": "error", "precision": _precision(claimed), "start_kst": claimed,
                  "reasons": ["ERROR"], "justification": outcome.error}
        db.save_event(conn, fields, actor="policy", reason=outcome.error or "error", run_id=run_id)
        emit("error", f"검증 실패: {cand.title_ko}", outcome.error, key)
        _publish_event(ctx, conn, key)
        return "error"

    v = outcome.verified
    on_schedule = [e for e in existing_all if e["status"] in db.ON_SCHEDULE and e["event_key"] != key]
    conflict = any(e["title"] == base["title"] and e.get("start_kst") != v.event_start for e in on_schedule)
    decision = decide(v, name=[cand.name, cand.title_ko], claimed_start=claimed, local_tz=cand.tz,
                      official_domains=interest["official_domains"], today=today, conflict=conflict)
    start = v.event_start if decision.status in ("auto_added", "pending_approval") and v.event_start else claimed
    fields = {**base, "status": decision.status, "precision": _precision(start), "start_kst": start,
              "verdict": v.verdict, "distortion_type": v.distortion_type, "correction": v.correction,
              "justification": v.justification, "reasons": decision.reasons,
              "gate_error": decision.gate_error, "official_url": decision.official_url,
              "next_check_at": _tomorrow() if decision.status == "tracking" else None}
    event_id = db.save_event(conn, fields, actor="policy",
                             reason=", ".join(explain(decision.reasons)) or "모든 검사 통과", run_id=run_id)
    db.replace_evidence(conn, event_id, decision.evidence, run_id)
    label = {"auto_added": "✅ 자동 등록", "pending_approval": "🟡 승인 대기", "tracking": "⏸ 추적",
             "rejected": "✖ 제외"}[decision.status]
    emit("decision", f"{label}: {base['title']}" + (f" · {start}" if start else ""),
         " / ".join(explain(decision.reasons)) or "공식 출처에서 일시를 확인함", key)
    _publish_event(ctx, conn, key)
    return decision.status


def _precision(start: str | None) -> str:
    return "date" if start and is_date_only(start) else "datetime"


def _tomorrow() -> str:
    return (datetime.fromisoformat(db.now_iso()) + timedelta(days=1)).isoformat()


def _publish_event(ctx, conn, key: str) -> None:
    ev = db.find_event_by_key(conn, key)
    if ev:
        ctx.bus.publish({"type": "event_changed", "event_id": ev["id"], "status": ev["status"]})
