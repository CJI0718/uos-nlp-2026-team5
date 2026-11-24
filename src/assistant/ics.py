"""iCalendar export of schedule rows (RFC 5545).

Timed events are written in UTC so no VTIMEZONE block is needed; all-day
events (release dates) use VALUE=DATE.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def _escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> list[str]:
    """Fold lines longer than 75 octets, as RFC 5545 requires."""
    out, current = [], ""
    for ch in line:
        if len((current + ch).encode("utf-8")) > 75:
            out.append(current)
            current = " " + ch
        else:
            current += ch
    out.append(current)
    return out


def vevent(ev: dict, stamp: str) -> list[str]:
    start = ev["start_kst"]
    lines = ["BEGIN:VEVENT", f"UID:{ev['event_key']}@uos-nlp-team5-assistant", f"DTSTAMP:{stamp}"]
    if ev.get("precision") == "date" or len(start.strip()) == 10:
        day = date.fromisoformat(start.strip())
        lines += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
                  f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}"]
    else:
        begin = datetime.strptime(start, "%Y-%m-%d %H:%M").replace(tzinfo=KST).astimezone(timezone.utc)
        lines += [f"DTSTART:{begin:%Y%m%dT%H%M%SZ}", f"DTEND:{begin + timedelta(hours=1):%Y%m%dT%H%M%SZ}"]
    desc = [f"검증 판정: {ev.get('verdict') or '-'}"]
    if ev.get("correction"):
        desc.append(f"정정: {ev['correction']}")
    if ev.get("official_url"):
        desc.append(f"공식 출처: {ev['official_url']}")
    lines += [f"SUMMARY:{_escape(ev['title'])}", f"DESCRIPTION:{_escape(chr(10).join(desc))}"]
    if ev.get("official_url") or ev.get("source_url"):
        lines.append(f"URL:{ev.get('official_url') or ev.get('source_url')}")
    lines.append("END:VEVENT")
    return lines


def to_ics(events: list[dict]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//UOS NLP Team 5//Schedule Assistant//KO",
             "CALSCALE:GREGORIAN"]
    for ev in events:
        if ev.get("start_kst"):
            lines += vevent(ev, stamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n"
