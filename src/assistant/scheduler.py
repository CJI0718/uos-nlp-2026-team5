"""Background trigger inside the app server: a daily time and an optional one-off run.

Runs only while the server is running. Off by default (settings.schedule.enabled).
"""

from __future__ import annotations

import threading
from datetime import datetime

from assistant import db
from assistant.config import save_settings
from assistant.pipeline import AppContext, RunBusy, is_running, start_background

CHECK_EVERY_S = 20


class Scheduler:
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx
        self._stop = threading.Event()
        self._last_daily: str | None = None

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True, name="assistant-scheduler").start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(CHECK_EVERY_S):
            try:
                self.tick(datetime.now(db.KST))
            except Exception as exc:   # never let the scheduler thread die silently
                self.ctx.bus.publish({"type": "notice", "text": f"예약 실행 오류: {exc}"})

    def tick(self, now: datetime) -> str | None:
        """Start a run if one is due. Returns the trigger used, for tests."""
        settings = self.ctx.settings()
        sched = settings["schedule"]
        if is_running():
            return None
        once = sched.get("once_at")
        if once and now >= datetime.fromisoformat(once):
            sched["once_at"] = None
            save_settings(self.ctx.settings_path, settings)
            return self._start("once")
        if sched.get("enabled") and now.strftime("%H:%M") >= sched.get("daily_at", "09:00"):
            today = now.date().isoformat()
            if self._last_daily != today:
                self._last_daily = today
                return self._start("daily")
        return None

    def _start(self, trigger: str) -> str | None:
        try:
            start_background(self.ctx, f"schedule:{trigger}")
        except RunBusy:
            return None
        self.ctx.bus.publish({"type": "notice", "text": "예약된 실행을 시작했어요."})
        return trigger
