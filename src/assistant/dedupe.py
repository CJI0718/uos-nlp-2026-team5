"""Event identity: one schedule row per event, even when many articles mention it."""

from __future__ import annotations

import difflib
import re
from datetime import date

_TOKEN = re.compile(r"[0-9a-z가-힣]+")
#: Words that say nothing about which event it is.
GENERIC = frozenset("""
event events keynote live stream livestream showcase presentation broadcast official
announce announced announcement date time launch release released the a an of and in on at for
행사 이벤트 발표 발표회 공개 출시 출시일 일정 개최 생중계 방송 기조연설 신제품 공식
""".split())


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall((text or "").lower())
            if t not in GENERIC and not re.fullmatch(r"(19|20)\d\d", t)]


def normalize(name: str) -> str:
    return " ".join(tokens(name))


def event_key(interest: str, name: str, start: str) -> str:
    """interest + normalized name + claimed date.

    The date keeps recurring events apart (several Nintendo Directs a year,
    WWDC 2021 and 2026). A later article that moves the date by a day or two
    is matched to the same row by `find_match`, not by the key.
    """
    day = (start or "")[:10] or "unknown"
    return f"{interest}:{normalize(name) or 'untitled'}:{day}"


def key_name(key: str) -> str:
    """The normalized event name inside an event_key."""
    parts = key.split(":")
    return parts[1] if len(parts) == 3 and parts[1] != "untitled" else ""


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "")[:10])
    except ValueError:
        return None


def find_match(existing: list[dict], interest: str, name: str, start: str,
               window_days: int = 3) -> dict | None:
    """Same key, or a similar name within `window_days` of the same date."""
    key = event_key(interest, name, start)
    for ev in existing:
        if ev["event_key"] == key:
            return ev
    wanted, norm = _date(start), normalize(name)
    if wanted is None:
        return None
    best, best_score = None, 0.0
    for ev in existing:
        if ev["interest"] != interest:
            continue
        other = _date(ev.get("start_kst"))
        if other is None or abs((wanted - other).days) > window_days:
            continue
        stored = key_name(ev["event_key"]) or normalize(ev["title"])
        score = difflib.SequenceMatcher(None, norm, stored).ratio()
        if score > best_score:
            best, best_score = ev, score
    return best if best_score >= 0.8 else None
