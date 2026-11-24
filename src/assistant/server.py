"""Local web app: JSON API, live activity stream (SSE) and the static UI.

Bound to 127.0.0.1. Requests whose Host header is not local are refused (DNS
rebinding), and state-changing requests need the X-Requested-With header the
UI sends (a cross-site form cannot set it).
"""

from __future__ import annotations

import json
import queue
import re
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from assistant import db
from assistant.budget import Budget
from assistant.config import public_settings, save_settings
from assistant.ics import to_ics
from assistant.pipeline import AppContext, RunBusy, is_running, start_background
from assistant.policy import explain

STATIC_DIR = Path(__file__).resolve().parent / "web"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
CSRF_HEADER = "X-Requested-With"
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
SHOWN = ("auto_added", "added", "pending_approval", "changed", "tracking")
HEARTBEAT_S = 15


def _event_view(ev: dict) -> dict:
    ev = dict(ev)
    ev["reasons_text"] = explain(ev.get("reasons") or [])
    ev["corrected"] = ev.get("verdict") == "refuted"
    return ev


class Api:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    def state(self) -> dict:
        conn = self.ctx.connect()
        try:
            settings = self.ctx.settings()
            counts = {s: 0 for s in db.STATUSES}
            for row in conn.execute("SELECT status, COUNT(*) n FROM events GROUP BY status"):
                counts[row["status"]] = row["n"]
            runs = db.list_runs(conn, 1)
            return {"mode": self.ctx.mode, "running": is_running(), "now": db.now_iso(),
                    "counts": counts, "budget": Budget(conn, settings).remaining(),
                    "schedule": settings["schedule"], "last_run": runs[0] if runs else None,
                    "model": settings["llm"]["model"] if self.ctx.mode == "live" else "demo-scripted",
                    "secrets": public_settings(settings)["secrets"]}
        finally:
            conn.close()

    def events(self, statuses: tuple[str, ...]) -> list[dict]:
        conn = self.ctx.connect()
        try:
            return [_event_view(e) for e in db.list_events(conn, statuses)]
        finally:
            conn.close()

    def event(self, event_id: int) -> dict | None:
        conn = self.ctx.connect()
        try:
            ev = db.get_event(conn, event_id)
            return _event_view(ev) if ev else None
        finally:
            conn.close()

    def act(self, event_id: int, action: str) -> dict:
        conn = self.ctx.connect()
        try:
            ev = _event_view(db.user_action(conn, event_id, action))
        finally:
            conn.close()
        self.ctx.bus.publish({"type": "event_changed", "event_id": event_id, "status": ev["status"]})
        return ev

    def update_settings(self, body: dict) -> dict:
        settings = self.ctx.settings()
        sched, caps = body.get("schedule") or {}, body.get("budget") or {}
        if "enabled" in sched:
            settings["schedule"]["enabled"] = bool(sched["enabled"])
        if "daily_at" in sched:
            if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(sched["daily_at"])):
                raise ValueError("daily_at은 HH:MM 형식이어야 합니다.")
            settings["schedule"]["daily_at"] = sched["daily_at"]
        if "run_in_minutes" in sched:
            minutes = int(sched["run_in_minutes"])
            if not 1 <= minutes <= 24 * 60:
                raise ValueError("run_in_minutes는 1~1440 사이여야 합니다.")
            settings["schedule"]["once_at"] = (datetime.now(db.KST) + timedelta(minutes=minutes)).replace(
                microsecond=0).isoformat()
        if sched.get("cancel_once"):
            settings["schedule"]["once_at"] = None
        if "daily_cost_usd" in caps:
            value = float(caps["daily_cost_usd"])
            if not 0 <= value <= 5:
                raise ValueError("하루 비용 상한은 $0~5 사이로 둡니다.")
            settings["budget"]["daily_cost_usd"] = value
        if "daily_searches" in caps:
            value = int(caps["daily_searches"])
            if not 0 <= value <= 1000:
                raise ValueError("하루 검색 상한은 0~1000회 사이로 둡니다.")
            settings["budget"]["daily_searches"] = value
        save_settings(self.ctx.settings_path, settings)
        return public_settings(settings)


def make_handler(ctx: AppContext):
    api = Api(ctx)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ScheduleAssistant/0.1"

        def log_message(self, fmt, *args):   # keep the console quiet; runs are logged in the DB
            pass

        # --- helpers -----------------------------------------------------------
        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].lower()
            return host in LOCAL_HOSTS

        def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload, status: int = 200) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _error(self, status: int, message: str) -> None:
            self._json({"error": message}, status)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > 64_000:
                raise ValueError("요청 본문이 너무 큽니다.")
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw or b"{}")
            if not isinstance(data, dict):
                raise ValueError("JSON 객체가 필요합니다.")
            return data

        # --- GET -----------------------------------------------------------------
        def do_GET(self) -> None:
            if not self._host_ok():
                return self._error(HTTPStatus.FORBIDDEN, "local only")
            url = urlsplit(self.path)
            path, query = url.path, parse_qs(url.query)
            try:
                if path in ("/", "/index.html"):
                    return self._static("index.html")
                if path.startswith("/static/"):
                    return self._static(path.removeprefix("/static/"))
                if path == "/api/state":
                    return self._json(api.state())
                if path == "/api/events":
                    raw = (query.get("status") or [",".join(SHOWN)])[0]
                    statuses = tuple(s for s in raw.split(",") if s in db.STATUSES) or SHOWN
                    return self._json(api.events(statuses))
                m = re.fullmatch(r"/api/events/(\d+)(\.ics)?", path)
                if m:
                    ev = api.event(int(m.group(1)))
                    if ev is None:
                        return self._error(404, "없는 일정")
                    if m.group(2):
                        if not ev.get("start_kst"):
                            return self._error(409, "검증된 일시가 없습니다.")
                        return self._ics([ev], f"event-{ev['id']}.ics")
                    return self._json(ev)
                if path == "/api/export.ics":
                    return self._ics(api.events(db.ON_SCHEDULE), "schedule.ics")
                if path == "/api/runs":
                    conn = ctx.connect()
                    try:
                        return self._json(db.list_runs(conn))
                    finally:
                        conn.close()
                m = re.fullmatch(r"/api/runs/(\d+)", path)
                if m:
                    conn = ctx.connect()
                    try:
                        run = db.get_run(conn, int(m.group(1)))
                    finally:
                        conn.close()
                    return self._json(run) if run else self._error(404, "없는 실행")
                if path == "/api/settings":
                    return self._json(public_settings(ctx.settings()))
                if path == "/api/stream":
                    return self._stream()
                return self._error(404, "not found")
            except (BrokenPipeError, ConnectionResetError):
                return None

        def _static(self, name: str) -> None:
            target = (STATIC_DIR / name).resolve()
            if STATIC_DIR not in target.parents or not target.is_file():
                return self._error(404, "not found")
            self._send(200, target.read_bytes(), CONTENT_TYPES.get(target.suffix, "application/octet-stream"))

        def _ics(self, events: list[dict], filename: str) -> None:
            self._send(200, to_ics(events).encode("utf-8"), "text/calendar; charset=utf-8",
                       {"Content-Disposition": f'attachment; filename="{filename}"'})

        def _stream(self) -> None:
            q = ctx.bus.subscribe()
            if q is None:
                return self._error(503, "열린 스트림이 너무 많습니다.")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=HEARTBEAT_S)
                        data = json.dumps(msg, ensure_ascii=False)
                        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                ctx.bus.unsubscribe(q)

        # --- POST / PUT ----------------------------------------------------------
        def _mutating_ok(self) -> bool:
            if not self._host_ok():
                self._error(HTTPStatus.FORBIDDEN, "local only")
                return False
            if self.headers.get(CSRF_HEADER) != "assistant":
                self._error(HTTPStatus.FORBIDDEN, f"{CSRF_HEADER} 헤더가 필요합니다.")
                return False
            return True

        def do_POST(self) -> None:
            if not self._mutating_ok():
                return
            path = urlsplit(self.path).path
            try:
                if path == "/api/runs":
                    try:
                        start_background(ctx, "manual")
                    except RunBusy as exc:
                        return self._error(409, str(exc))
                    return self._json({"started": True}, 202)
                m = re.fullmatch(r"/api/events/(\d+)/(approve|reject|undo)", path)
                if m:
                    return self._json(api.act(int(m.group(1)), m.group(2)))
                return self._error(404, "not found")
            except db.IllegalTransition as exc:
                return self._error(409, str(exc))
            except KeyError:
                return self._error(404, "없는 일정")

        def do_PUT(self) -> None:
            if not self._mutating_ok():
                return
            if urlsplit(self.path).path != "/api/settings":
                return self._error(404, "not found")
            try:
                return self._json(api.update_settings(self._body()))
            except (ValueError, TypeError) as exc:
                return self._error(400, str(exc))

    return Handler


def make_server(ctx: AppContext, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(ctx))
    server.daemon_threads = True
    return server
