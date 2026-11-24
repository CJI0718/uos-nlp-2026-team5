"""Settings (interests, budget, schedule, model) kept as one JSON file.

Secrets never live here: API keys come from the environment or an allow-listed
.env loader, and only their presence is reported.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from task_a.web import load_env_file

#: Keys the app may take from a .env file. Nothing else is imported.
SECRET_KEYS = ("MISTRAL_API_KEY", "TAVILY_API_KEY")

DEFAULT_INTERESTS = [
    {
        "id": "tech",
        "name": "테크 행사·신제품 발표",
        "enabled": True,
        # {month} {next_month} {year} {next_year} are filled in at run time,
        # so searches look for upcoming events rather than last season's.
        "queries": [
            "tech event keynote {month} {year} date time announced",
            "product launch event {next_month} {year} date announced",
            "CES {next_year} keynote schedule date time",
            "Galaxy Unpacked {next_year} date announced",
        ],
        "official_domains": ["apple.com", "samsung.com", "google.com", "blog.google",
                             "microsoft.com", "ces.tech"],
    },
    {
        "id": "game",
        "name": "게임 쇼케이스·출시일",
        "enabled": True,
        "queries": [
            "game showcase {month} {year} date time announced",
            "Nintendo Direct {month} {year}",
            "The Game Awards {year} date time",
            "game release date {next_month} {year} officially announced",
        ],
        "official_domains": ["nintendo.com", "nintendo.co.kr", "playstation.com", "xbox.com",
                             "rockstargames.com", "ea.com", "ubisoft.com", "thegameawards.com"],
    },
]

DEFAULTS: dict = {
    "interests": DEFAULT_INTERESTS,
    "llm": {
        "provider": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "api_key_env": "MISTRAL_API_KEY",
        # USD per 1M tokens. List prices read on 2026-11-24; check before relying on cost figures.
        "price_input": 0.15,
        "price_cached_input": 0.015,
        "price_output": 0.60,
        "timeout_s": 60,
    },
    "budget": {
        "daily_cost_usd": 1.00,
        "daily_searches": 100,
        "max_candidates_per_run": 10,
        "queries_per_interest": 3,
        "recent_days": 21,             # discovery searches only recent coverage
        "max_tool_calls": 12,
        "max_external_calls": 6,
        "max_llm_turns": 10,
    },
    "schedule": {
        "enabled": False,      # demo use; turn on in Settings
        "daily_at": "09:00",   # local time of the machine
        "once_at": None,       # ISO time for a one-off run ("run in N minutes")
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_settings(path: str | Path) -> dict:
    path = Path(path)
    stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _merge(DEFAULTS, stored)


def save_settings(path: str | Path, settings: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_secrets(env_path: str | Path) -> list[str]:
    """Load allow-listed keys from .env; return the names that were set, never values."""
    return load_env_file(env_path, keys=SECRET_KEYS)


def secret_status() -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in SECRET_KEYS}


def public_settings(settings: dict) -> dict:
    """Settings as the UI may see them, with key presence instead of values."""
    return {**copy.deepcopy(settings), "secrets": secret_status()}
