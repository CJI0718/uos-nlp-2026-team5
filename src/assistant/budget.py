"""Daily caps on model cost and web searches, checked before every paid call."""

from __future__ import annotations

from assistant import db
from assistant.llm import cost_usd


class BudgetExceeded(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class Budget:
    """Reads today's ledger and refuses a call that would start past a cap.

    A model call is refused once today's cost has reached the cap, so one call
    may end slightly above it; the cap is a stop line, not an exact limit.
    """

    def __init__(self, conn, settings: dict, day: str | None = None) -> None:
        self.conn = conn
        self.caps = settings["budget"]
        self.llm_settings = settings["llm"]
        self.day = day or db.today_kst()
        self.run = {"llm_calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
                    "search_calls": 0, "fetch_calls": 0}

    def today(self) -> dict:
        return db.ledger(self.conn, self.day)

    def check_llm(self) -> None:
        spent = self.today()["cost_usd"]
        if spent >= self.caps["daily_cost_usd"]:
            raise BudgetExceeded("cost", f"오늘 모델 비용 상한(${self.caps['daily_cost_usd']:.2f})에 도달했습니다.")

    def charge_llm(self, usage: dict) -> float:
        cost = cost_usd(usage, self.llm_settings)
        delta = {"llm_calls": 1, "tokens_in": usage.get("prompt_tokens", 0),
                 "tokens_out": usage.get("completion_tokens", 0), "cost_usd": cost}
        db.ledger_add(self.conn, self.day, **delta)
        for k, v in delta.items():
            self.run[k] += v
        return cost

    def check_search(self) -> None:
        if self.today()["search_calls"] >= self.caps["daily_searches"]:
            raise BudgetExceeded("search", f"오늘 웹 검색 상한({self.caps['daily_searches']}회)에 도달했습니다.")

    def charge_search(self) -> None:
        db.ledger_add(self.conn, self.day, search_calls=1)
        self.run["search_calls"] += 1

    def charge_fetch(self) -> None:
        db.ledger_add(self.conn, self.day, fetch_calls=1)
        self.run["fetch_calls"] += 1

    def remaining(self) -> dict:
        t = self.today()
        return {"cost_usd": max(0.0, self.caps["daily_cost_usd"] - t["cost_usd"]),
                "searches": max(0, self.caps["daily_searches"] - t["search_calls"]),
                "spent_usd": t["cost_usd"], "searches_used": t["search_calls"],
                "cap_usd": self.caps["daily_cost_usd"], "cap_searches": self.caps["daily_searches"]}
