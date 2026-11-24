"""SQLite store for the schedule, its evidence, decisions, runs and budget.

Article text is never stored: an evidence row keeps the URL, title, date,
provenance group and one short quoted sentence.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
SCHEMA_VERSION = 2
MAX_QUOTE_CHARS = 300

#: Schedule states. 'auto_added' and 'added' are on the schedule.
STATUSES = ("auto_added", "added", "pending_approval", "tracking", "changed",
            "rejected", "undone", "expired", "occurred", "error")
ON_SCHEDULE = ("auto_added", "added")

#: (from, to) pairs a user action may perform.
USER_TRANSITIONS = {
    "approve": {"pending_approval", "undone", "changed"},   # on 'changed': take the new start
    "keep": {"changed"},                                     # keep the old start
    "reject": {"pending_approval", "undone", "tracking", "changed", "error"},
    "undo": {"auto_added", "added"},
}
USER_TARGET = {"approve": "added", "keep": "added", "reject": "rejected", "undo": "undone"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  event_key TEXT NOT NULL UNIQUE,
  interest TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  precision TEXT NOT NULL DEFAULT 'datetime',
  start_kst TEXT,
  local_tz TEXT,
  claim_text TEXT NOT NULL,
  source_url TEXT,
  verdict TEXT,
  distortion_type TEXT,
  correction TEXT,
  justification TEXT,
  reasons_json TEXT NOT NULL DEFAULT '[]',
  gate_error TEXT,
  official_url TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  next_check_at TEXT,
  last_run_id INTEGER,
  proposed_start TEXT,
  last_checked_at TEXT
);
CREATE INDEX IF NOT EXISTS events_status ON events(status, start_kst);
CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  title TEXT,
  published_at TEXT,
  provenance_group TEXT,
  derivative INTEGER NOT NULL DEFAULT 0,
  official INTEGER NOT NULL DEFAULT 0,
  cited INTEGER NOT NULL DEFAULT 0,
  quote TEXT,
  run_id INTEGER
);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  from_status TEXT,
  to_status TEXT NOT NULL,
  actor TEXT NOT NULL,
  reason TEXT,
  run_id INTEGER,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  trigger TEXT NOT NULL,
  status TEXT NOT NULL,
  mode TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  candidates INTEGER NOT NULL DEFAULT 0,
  verified INTEGER NOT NULL DEFAULT 0,
  llm_calls INTEGER NOT NULL DEFAULT 0,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL NOT NULL DEFAULT 0,
  search_calls INTEGER NOT NULL DEFAULT 0,
  fetch_calls INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  error TEXT
);
CREATE TABLE IF NOT EXISTS run_steps (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,
  label TEXT NOT NULL,
  detail TEXT,
  event_key TEXT
);
CREATE INDEX IF NOT EXISTS run_steps_run ON run_steps(run_id, seq);
CREATE TABLE IF NOT EXISTS budget_ledger (
  day TEXT PRIMARY KEY,
  cost_usd REAL NOT NULL DEFAULT 0,
  llm_calls INTEGER NOT NULL DEFAULT 0,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  search_calls INTEGER NOT NULL DEFAULT 0,
  fetch_calls INTEGER NOT NULL DEFAULT 0
);
"""


class IllegalTransition(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


def today_kst() -> str:
    return datetime.now(KST).date().isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(SCHEMA)
    have = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
    for column in ("proposed_start", "last_checked_at"):   # v1 databases
        if column not in have:
            conn.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT")
    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    conn.commit()
    return conn


def _row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    out = dict(row)
    if "reasons_json" in out:
        out["reasons"] = json.loads(out.pop("reasons_json") or "[]")
    return out


# --- events -------------------------------------------------------------------

def find_event_by_key(conn, event_key: str) -> dict | None:
    return _row(conn.execute("SELECT * FROM events WHERE event_key=?", (event_key,)).fetchone())


def get_event(conn, event_id: int) -> dict | None:
    event = _row(conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone())
    if event is None:
        return None
    event["evidence"] = [dict(r) for r in conn.execute(
        "SELECT url, title, published_at, provenance_group, derivative, official, cited, quote "
        "FROM evidence WHERE event_id=? ORDER BY cited DESC, official DESC, id", (event_id,))]
    event["decisions"] = [dict(r) for r in conn.execute(
        "SELECT from_status, to_status, actor, reason, run_id, created_at FROM decisions "
        "WHERE event_id=? ORDER BY id", (event_id,))]
    return event


def list_events(conn, statuses: tuple[str, ...] | None = None) -> list[dict]:
    sql, args = "SELECT * FROM events", ()
    if statuses:
        sql += f" WHERE status IN ({','.join('?' * len(statuses))})"
        args = tuple(statuses)
    sql += " ORDER BY (start_kst IS NULL), start_kst, id"
    return [_row(r) for r in conn.execute(sql, args)]


def events_in_interest(conn, interest: str) -> list[dict]:
    return [_row(r) for r in conn.execute("SELECT * FROM events WHERE interest=?", (interest,))]


def save_event(conn, fields: dict, *, actor: str, reason: str, run_id: int | None) -> int:
    """Insert a new event or update the one with the same event_key.

    Status changes are recorded as decisions. The policy and user actions are
    the only callers, so a schedule entry always has a recorded reason.
    """
    now = now_iso()
    data = dict(fields)
    data["reasons_json"] = json.dumps(data.pop("reasons", []), ensure_ascii=False)
    existing = find_event_by_key(conn, data["event_key"])
    cols = ("interest", "title", "status", "precision", "start_kst", "local_tz", "claim_text",
            "source_url", "verdict", "distortion_type", "correction", "justification",
            "reasons_json", "gate_error", "official_url", "next_check_at")
    if existing is None:
        conn.execute(
            f"INSERT INTO events (event_key, {', '.join(cols)}, created_at, updated_at, last_run_id) "
            f"VALUES (?, {', '.join('?' * len(cols))}, ?, ?, ?)",
            (data["event_key"], *(data.get(c) for c in cols), now, now, run_id))
        event_id = conn.execute("SELECT id FROM events WHERE event_key=?",
                                (data["event_key"],)).fetchone()[0]
        from_status = None
    else:
        event_id, from_status = existing["id"], existing["status"]
        changed = any(existing.get(c) != data.get(c) for c in ("start_kst", "precision"))
        conn.execute(
            f"UPDATE events SET {', '.join(f'{c}=?' for c in cols)}, updated_at=?, last_run_id=?, "
            f"version=version+? WHERE id=?",
            (*(data.get(c) for c in cols), now, run_id, 1 if changed else 0, event_id))
    if from_status != data["status"]:
        add_decision(conn, event_id, from_status, data["status"], actor, reason, run_id)
    conn.commit()
    return event_id


def record_check(conn, event_id: int, next_check_at: str | None, run_id: int | None,
                 reason: str | None = None) -> None:
    """A recheck that changed nothing: remember when it ran and when to look again."""
    conn.execute("UPDATE events SET last_checked_at=?, next_check_at=?, last_run_id=? WHERE id=?",
                 (now_iso(), next_check_at, run_id, event_id))
    if reason:
        ev = conn.execute("SELECT status FROM events WHERE id=?", (event_id,)).fetchone()
        add_decision(conn, event_id, ev[0], ev[0], "policy", reason, run_id)
    conn.commit()


def propose_change(conn, event_id: int, proposed_start: str | None, reasons: list[str],
                   justification: str, run_id: int | None) -> None:
    """A scheduled event looks different now: keep it, mark it 'changed', ask the user."""
    ev = conn.execute("SELECT status FROM events WHERE id=?", (event_id,)).fetchone()
    conn.execute("UPDATE events SET status='changed', proposed_start=?, reasons_json=?, justification=?, "
                 "last_checked_at=?, next_check_at=NULL, updated_at=?, last_run_id=? WHERE id=?",
                 (proposed_start, json.dumps(reasons, ensure_ascii=False), justification, now_iso(),
                  now_iso(), run_id, event_id))
    add_decision(conn, event_id, ev[0], "changed", "policy",
                 f"새 일시 제안: {proposed_start}" if proposed_start else "취소·연기 가능성", run_id)
    conn.commit()


def housekeep(conn, now: str) -> int:
    """Past scheduled events become 'occurred'; tracked ones whose date passed 'expired'."""
    changed = 0
    today = now[:10]
    for ev in list_events(conn, ("auto_added", "added", "tracking")):
        start = ev.get("start_kst") or ""
        if start and start[:10] < today:
            target = "expired" if ev["status"] == "tracking" else "occurred"
            conn.execute("UPDATE events SET status=?, next_check_at=NULL, updated_at=? WHERE id=?",
                         (target, now, ev["id"]))
            add_decision(conn, ev["id"], ev["status"], target, "policy", "날짜가 지남", None)
            changed += 1
    conn.commit()
    return changed


def add_decision(conn, event_id, from_status, to_status, actor, reason, run_id) -> None:
    conn.execute("INSERT INTO decisions (event_id, from_status, to_status, actor, reason, run_id, "
                 "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (event_id, from_status, to_status, actor, reason, run_id, now_iso()))


def replace_evidence(conn, event_id: int, rows: list[dict], run_id: int | None) -> None:
    conn.execute("DELETE FROM evidence WHERE event_id=?", (event_id,))
    for r in rows:
        conn.execute(
            "INSERT INTO evidence (event_id, url, title, published_at, provenance_group, derivative, "
            "official, cited, quote, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, r["url"], r.get("title"), r.get("published_at"), r.get("provenance_group"),
             int(bool(r.get("derivative"))), int(bool(r.get("official"))), int(bool(r.get("cited"))),
             (r.get("quote") or "")[:MAX_QUOTE_CHARS] or None, run_id))
    conn.commit()


def user_action(conn, event_id: int, action: str) -> dict:
    if action not in USER_TRANSITIONS:
        raise IllegalTransition(f"알 수 없는 동작: {action}")
    event = get_event(conn, event_id)
    if event is None:
        raise KeyError(event_id)
    if event["status"] not in USER_TRANSITIONS[action]:
        raise IllegalTransition(f"'{event['status']}' 상태에서는 {action}할 수 없습니다.")
    target = USER_TARGET[action]
    start = event.get("start_kst")
    reason = action
    if event["status"] == "changed" and action == "approve":
        if not event.get("proposed_start"):
            raise IllegalTransition("새 일시가 없는 변경입니다. 기존 유지 또는 일정에서 빼기를 고르세요.")
        reason = f"새 일시로 변경: {start} → {event['proposed_start']}"
        start = event["proposed_start"]
    if action == "approve" and not start:
        raise IllegalTransition("검증된 일시가 없는 일정은 승인할 수 없습니다.")
    precision = "date" if start and len(start.strip()) == 10 else event.get("precision", "datetime")
    conn.execute("UPDATE events SET status=?, start_kst=?, precision=?, proposed_start=NULL, updated_at=?, "
                 "version=version+? WHERE id=?",
                 (target, start, precision, now_iso(), int(start != event.get("start_kst")), event_id))
    add_decision(conn, event_id, event["status"], target, "user", reason, None)
    conn.commit()
    return get_event(conn, event_id)


# --- runs and steps -----------------------------------------------------------

def start_run(conn, trigger: str, mode: str) -> int:
    cur = conn.execute("INSERT INTO runs (trigger, status, mode, started_at) VALUES (?, 'running', ?, ?)",
                       (trigger, mode, now_iso()))
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id: int, status: str, stats: dict, summary: str, error: str | None = None):
    conn.execute(
        "UPDATE runs SET status=?, finished_at=?, candidates=?, verified=?, llm_calls=?, tokens_in=?, "
        "tokens_out=?, cost_usd=?, search_calls=?, fetch_calls=?, summary=?, error=? WHERE id=?",
        (status, now_iso(), stats.get("candidates", 0), stats.get("verified", 0),
         stats.get("llm_calls", 0), stats.get("tokens_in", 0), stats.get("tokens_out", 0),
         round(stats.get("cost_usd", 0.0), 6), stats.get("search_calls", 0),
         stats.get("fetch_calls", 0), summary, error, run_id))
    conn.commit()


def add_step(conn, run_id: int, kind: str, label: str, detail: str | None = None,
             event_key: str | None = None) -> dict:
    seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM run_steps WHERE run_id=?",
                       (run_id,)).fetchone()[0]
    ts = now_iso()
    conn.execute("INSERT INTO run_steps (run_id, seq, ts, kind, label, detail, event_key) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?)", (run_id, seq, ts, kind, label, detail, event_key))
    conn.commit()
    return {"run_id": run_id, "seq": seq, "ts": ts, "kind": kind, "label": label,
            "detail": detail, "event_key": event_key}


def list_runs(conn, limit: int = 30) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))]


def get_run(conn, run_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        return None
    run = dict(row)
    run["steps"] = [dict(r) for r in conn.execute(
        "SELECT seq, ts, kind, label, detail, event_key FROM run_steps WHERE run_id=? ORDER BY seq",
        (run_id,))]
    return run


def mark_interrupted_runs(conn) -> int:
    """Runs left 'running' by a stopped server are recorded as interrupted, not resumed."""
    cur = conn.execute("UPDATE runs SET status='interrupted', finished_at=? WHERE status='running'",
                       (now_iso(),))
    conn.commit()
    return cur.rowcount


# --- budget ledger --------------------------------------------------------------

def ledger(conn, day: str) -> dict:
    row = conn.execute("SELECT * FROM budget_ledger WHERE day=?", (day,)).fetchone()
    return dict(row) if row else {"day": day, "cost_usd": 0.0, "llm_calls": 0, "tokens_in": 0,
                                  "tokens_out": 0, "search_calls": 0, "fetch_calls": 0}


def ledger_add(conn, day: str, **delta) -> None:
    conn.execute("INSERT OR IGNORE INTO budget_ledger (day) VALUES (?)", (day,))
    sets = ", ".join(f"{k}={k}+?" for k in delta)
    conn.execute(f"UPDATE budget_ledger SET {sets} WHERE day=?", (*delta.values(), day))
    conn.commit()
