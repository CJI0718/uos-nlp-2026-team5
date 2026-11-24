"""In-process publish/subscribe for the live activity stream (SSE)."""

from __future__ import annotations

import queue
import threading

MAX_SUBSCRIBERS = 8


class EventBus:
    def __init__(self) -> None:
        self._subs: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue | None:
        with self._lock:
            if len(self._subs) >= MAX_SUBSCRIBERS:
                return None
            q: queue.Queue = queue.Queue(maxsize=500)
            self._subs.append(q)
            return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def publish(self, message: dict) -> None:
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(message)
            except queue.Full:
                pass   # a stalled browser tab loses messages; it reloads state on reconnect
