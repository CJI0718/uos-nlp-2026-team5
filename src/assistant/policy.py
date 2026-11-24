"""Decide what happens to a verified event: add it, ask the user, track it, or drop it.

Deterministic. The Task A gate is the floor (cited documents were read; a
primary source or two independent provenance groups; a refuted event carries
its corrected time). On top of it come two rules learned in exp-004:

- the date (and time) must be written in a cited document the agent read,
  not only in a search snippet (RW10: the time came from an undated snippet);
- the event must be the one the candidate names, and a correction may not move
  it by more than two days (RW11: a different Apple event was substituted).

Anything that fails a rule goes to the approval queue with a reason code.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from assistant.dedupe import tokens
from task_a.missions import is_date_only, validate_mission_gate

KST = ZoneInfo("Asia/Seoul")
#: Zones tried when the source's own time zone is unknown: the document may
#: state the time in any of them, and it must convert to the verified KST time.
COMMON_ZONES = ("Asia/Seoul", "America/Los_Angeles", "America/New_York", "America/Chicago",
                "Europe/London", "Europe/Paris", "Europe/Berlin", "Asia/Tokyo", "UTC")
MAX_CORRECTION_SHIFT_DAYS = 2

REASON_TEXT = {
    "GATE_BLOCKED": "검증 게이트가 막음",
    "TIME_NOT_IN_CITED_TEXT": "인용한 문서에 이 날짜·시각이 없음",
    "IDENTITY_MISMATCH": "인용한 문서가 다른 행사를 다루는 것 같음",
    "LARGE_DATE_CHANGE": "정정이 날짜를 크게 바꿈(다른 행사일 수 있음)",
    "CORRECTION_REVIEW": "시간대·날짜 외의 정정",
    "NO_TIME": "검증된 일시가 없음",
    "CONFLICT": "같은 행사에 다른 시각이 이미 있음",
    "NO_OFFICIAL_SOURCE": "공식 출처 없이 독립 출처 2개로 확인",
    "NOT_ENOUGH_EVIDENCE": "아직 확인되지 않음(추적 중)",
    "REFUTED": "주장이 틀렸고 정정할 일정이 없음",
    "PAST": "이미 지난 일정",
    "ERROR": "검증 중 오류",
}

_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
           "september", "october", "november", "december"]


@dataclass
class Verified:
    """What the verification episode produced, plus what it read."""

    verdict: str
    abstain: bool
    event_start: str | None          # KST 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'
    correction: str | None
    distortion_type: str | None
    cited: list[str]
    observed: list[str]
    texts: dict[str, str]             # full text of each read document
    docs: dict[str, dict]             # url -> {title, published_at}
    meta: dict[str, dict]             # url -> {provenance_group, derivative, source_type}
    justification: str = ""


@dataclass
class Decision:
    status: str                       # auto_added | pending_approval | tracking | rejected
    reasons: list[str] = field(default_factory=list)
    gate_error: str | None = None
    official_url: str | None = None
    evidence: list[dict] = field(default_factory=list)


def is_official(url: str, official_domains: list[str]) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in official_domains)


# --- literal date / time in text ------------------------------------------------

def _norm(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"a\.\s?m\.?", "am", t)
    t = re.sub(r"p\.\s?m\.?", "pm", t)
    return re.sub(r"\s+", " ", t)


def _date_patterns(d: date) -> list[str]:
    full = _MONTHS[d.month - 1]
    month = rf"(?:{full}|{full[:3]}\.?)"
    day = rf"0?{d.day}(?:st|nd|rd|th)?"
    return [
        rf"{d.year}-{d.month:02d}-{d.day:02d}",
        rf"{d.year}\s*[./]\s*0?{d.month}\s*[./]\s*0?{d.day}(?!\d)",
        rf"(?<!\d)0?{d.month}\s*월\s*0?{d.day}\s*일",
        rf"\b{month}\s+{day}\b",
        rf"(?<!\d){day}\s+(?:of\s+)?{month}\b",
    ]


def _time_patterns(h: int, m: int) -> list[str]:
    h12, ampm = (h % 12) or 12, ("am" if h < 12 else "pm")
    kor = r"(?:오전|새벽|아침)" if h < 12 else r"(?:오후|밤|저녁|낮)"
    pats = [rf"(?<!\d)0?{h}:{m:02d}(?!\d)(?!\s*[ap]m)", rf"(?<!\d){h12}:{m:02d}\s*{ampm}\b"]
    if m == 0:
        pats += [rf"(?<!\d){h12}\s*{ampm}\b", rf"{kor}\s*{h12}\s*시", rf"(?<!\d){h}\s*시(?!\s*간)"]
    else:
        pats += [rf"{kor}\s*{h12}\s*시\s*{m}\s*분", rf"(?<!\d){h}\s*시\s*{m}\s*분"]
    return pats


def _find(patterns: list[str], text: str) -> re.Match | None:
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match
    return None


def literal_match(text: str, event_start: str, local_tz: str | None = None) -> re.Match | None:
    """Where the document states this event's date (and time), in some time zone.

    A timed event matches when one zone's local date and local time both
    appear; an all-day event needs only its date.
    """
    norm = _norm(text)
    if is_date_only(event_start):
        return _find(_date_patterns(date.fromisoformat(event_start.strip())), norm)
    try:
        kst = datetime.strptime(event_start.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    except ValueError:
        return None
    zones = ([local_tz] if local_tz else []) + [z for z in COMMON_ZONES if z != local_tz]
    for zone in zones:
        try:
            local = kst.astimezone(ZoneInfo(zone))
        except Exception:
            continue
        date_hit = _find(_date_patterns(local.date()), norm)
        if date_hit and _find(_time_patterns(local.hour, local.minute), norm):
            return date_hit
    return None


def _quote(text: str, match: re.Match | None, width: int = 140) -> str | None:
    if not match:
        return None
    norm = _norm(text)
    start, end = max(0, match.start() - width), min(len(norm), match.end() + width)
    snippet = norm[start:end].strip()
    return ("…" if start else "") + snippet + ("…" if end < len(norm) else "")


def identity_ok(name: str | list[str], text: str, title: str = "") -> bool:
    """The distinctive words of the event name appear in the document.

    A name of one or two words needs all of them ("Nintendo Direct", "Acme
    Orbit"): the company name alone matches every event of that company.
    Longer names need two thirds. Several spellings (source name, Korean
    title) may be given; any one matching is enough.
    """
    have = set(tokens(f"{title} {text}"))
    for one in ([name] if isinstance(name, str) else name):
        wanted = set(tokens(one))
        if not wanted:
            continue
        need = len(wanted) if len(wanted) <= 2 else math.ceil(2 * len(wanted) / 3)
        if len(wanted & have) >= need:
            return True
    return False


def _day(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "")[:10])
    except ValueError:
        return None


# --- decision ---------------------------------------------------------------------

def decide(v: Verified, *, name: str | list[str], claimed_start: str | None, local_tz: str | None,
           official_domains: list[str], today: str, conflict: bool = False) -> Decision:
    official_urls = [u for u in v.observed if is_official(u, official_domains)]
    evidence = _evidence_rows(v, official_domains)

    if v.abstain or v.verdict == "not_enough_evidence":
        claimed = _day(claimed_start)
        if claimed and claimed.isoformat() < today:
            return Decision("rejected", ["PAST"], evidence=evidence)
        return Decision("tracking", ["NOT_ENOUGH_EVIDENCE"], evidence=evidence)
    if v.verdict == "refuted" and not (v.correction or "").strip():
        return Decision("rejected", ["REFUTED"], evidence=evidence)

    reasons: list[str] = []
    if not v.event_start or not (is_date_only(v.event_start) or re.fullmatch(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", v.event_start.strip())):
        return Decision("pending_approval", ["NO_TIME"], evidence=evidence)
    if v.verdict == "refuted" and v.distortion_type != "timezone_or_date_error":
        reasons.append("CORRECTION_REVIEW")

    # Task A gate, with official domains marked as primary sources.
    meta = {c: {**(v.meta.get(c) or {}),
                **({"source_type": "official"} if is_official(c, official_domains) else {})}
            for c in v.cited}
    gate_error = validate_mission_gate(
        "event_manager", v.verdict, abstain=v.abstain, correction=v.correction,
        cited_evidence_ids=v.cited, observed_evidence_ids=set(v.observed),
        event_start_kst=v.event_start, evidence_meta=meta, require_independent=True,
        allow_date_only=True)
    if gate_error:
        reasons.append("GATE_BLOCKED")

    # The date/time must be written in a cited document that was read.
    supporting = None
    for url in v.cited:
        if url in v.texts and literal_match(v.texts[url], v.event_start, local_tz):
            supporting = url
            break
    if supporting is None:
        reasons.append("TIME_NOT_IN_CITED_TEXT")
    elif not identity_ok(name, v.texts[supporting], (v.docs.get(supporting) or {}).get("title", "")):
        reasons.append("IDENTITY_MISMATCH")

    claimed, verified = _day(claimed_start), _day(v.event_start)
    if (v.verdict == "refuted" and claimed and verified
            and abs((verified - claimed).days) > MAX_CORRECTION_SHIFT_DAYS):
        reasons.append("LARGE_DATE_CHANGE")
    if conflict:
        reasons.append("CONFLICT")

    cited_official = [u for u in v.cited if u in official_urls]
    if not reasons and not cited_official:
        # Passed the gate on two independent groups. Allowed (Task A rule), but shown.
        return Decision("auto_added", ["NO_OFFICIAL_SOURCE"], official_url=None, evidence=evidence)
    status = "pending_approval" if reasons else "auto_added"
    return Decision(status, reasons, gate_error=gate_error,
                    official_url=cited_official[0] if cited_official else None, evidence=evidence)


def _evidence_rows(v: Verified, official_domains: list[str]) -> list[dict]:
    rows = []
    for url in v.observed:
        text = v.texts.get(url, "")
        match = literal_match(text, v.event_start, None) if v.event_start else None
        doc, meta = v.docs.get(url) or {}, v.meta.get(url) or {}
        rows.append({"url": url, "title": doc.get("title"), "published_at": doc.get("published_at"),
                     "provenance_group": meta.get("provenance_group"),
                     "derivative": meta.get("derivative", False),
                     "official": is_official(url, official_domains), "cited": url in v.cited,
                     "quote": _quote(text, match)})
    return rows


def explain(reasons: list[str]) -> list[str]:
    return [REASON_TEXT.get(r, r) for r in reasons]
