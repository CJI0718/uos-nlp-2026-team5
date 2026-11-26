"""Check the values an action writes against what the episode read (harness v3).

The claim gate checks the verdict; this checks the artifact. Every number in a
mission's title, summary and correction, and the event time of a calendar
file, must come from one of:

- a cited document the agent read in this episode (or its title and date);
- a calculator result in this episode whose inputs themselves came from those
  documents (so a wrong input cannot launder a wrong output);
- for a refuted claim, the claim itself, which the artifact may restate.

Matching is by value, not by spelling: '99만 원' matches '990,000원', and
'26 million' matches '2,600만'. A rounded number matches a more precise one
('14.1%' and 14.14). A number cut out of a longer one does not: '99만' is not in
'199만'. Single-digit integers are not checked; they are list markers and days
as often as amounts.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime

from task_a.schema import ToolStatus
from task_a.tools import calculate_comparison

_UNITS = {
    "조": 1e12, "억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "천": 1e3,
    "trillion": 1e12, "billion": 1e9, "million": 1e6, "thousand": 1e3,
}
_KOREAN_ORDER = ("조", "억", "천만", "백만", "만", "천")
_NUMBER = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\d,]*\d)"
    r"\s*(조|억|천만|백만|만|천|trillion|billion|million|thousand)?", re.IGNORECASE)
_SUFFIXED = re.compile(r"(?<![\d.,])(\d+(?:\.\d+)?)\s?([KMB])\b")
_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9}
_SPACED = re.compile(r"(?<![\d.,])\d{1,3}(?:[ \u00a0\u202f\u2009]\d{3})+(?![\d.,])")
_URL = re.compile(r"https?://\S+|\b[\w.-]+\.(?:com|org|net|io|kr|go\.kr|co\.kr|gov|edu)(?:/\S*)?", re.IGNORECASE)
_CLAIM_ID = re.compile(r"\bFC\d{3}\b")
_SCALES = (1.0, 1e3, 1e4, 1e6, 1e8, 1e9, 1e12)


@dataclass(frozen=True)
class Number:
    text: str
    #: Every reading, for a source: as written, scaled by its unit, compound.
    values: tuple[float, ...]
    #: The reading an artifact is held to, with half its written precision:
    #: '31억' must be 31억 (±0.5억), not any 31 in the source.
    check: tuple[float, float]


def _number(text: str, raw: float, step: float, scaled: float | None = None,
            unit: float = 1.0, compound: float | None = None) -> Number:
    values = tuple(v for v in (raw, scaled, compound) if v is not None)
    held = compound if compound is not None else scaled if scaled is not None else raw
    return Number(text, values, (held, step * unit / 2))


def prepare(text: str) -> str:
    """The text numbers are read from: links and claim ids blanked, Korean
    thousands written out ('4천405억' → '4405억', '1천억' → '1000억')."""
    text = _CLAIM_ID.sub(" ", _URL.sub(" ", text or ""))
    text = re.sub(r"(?<![\d.,])(\d)\s?천\s?(\d{3})(?=\s?(?:조|억|만|원|명|개|건|달러))", r"\1\2", text)
    return re.sub(r"(?<![\d.,])(\d)\s?천\s?(?=억|조)", r"\g<1>000", text)


def numbers(text: str) -> list[Number]:
    """Numbers with their unit-scaled values.

    Korean compounds also count as one value: '195조 2,532억', '35만9000원',
    '107조4천405억' (= 107조 4405억).
    """
    text = prepare(text)
    out: list[Number] = []
    prev: tuple[float, float, int] | None = None   # (compound so far, its last unit, end)
    for m in _NUMBER.finditer(text):
        whole, frac, unit_word = m.group(1).replace(",", ""), m.group(2) or "", (m.group(3) or "").lower()
        raw = float(whole + frac)
        step = 10 ** -(len(frac) - 1) if frac else 1.0
        unit = _UNITS.get(unit_word, 1.0)
        compound = None
        if prev and (unit_word in _KOREAN_ORDER or not unit_word) and unit < prev[1] \
                and raw * unit < prev[1] and m.start() - prev[2] <= 1:
            compound = prev[0] + raw * unit
        out.append(_number(m.group(0).strip(), raw, step, raw * unit if unit_word else None, unit, compound))
        current = compound if compound is not None else raw * unit
        prev = (current, unit, m.end()) if unit_word in _KOREAN_ORDER else None
    # '671B' or '12M' may mean billions or millions (or bytes): an extra reading
    # a source offers, while the artifact is still held to the number as written.
    for m in _SUFFIXED.finditer(text):
        raw = float(m.group(1))
        out.append(Number(m.group(0), (raw, raw * _SUFFIX[m.group(2)]), (raw, 0.0)))
    # Thousands grouped by spaces ('1 200 TWh'), as an extra reading.
    for m in _SPACED.finditer(text):
        out.append(_number(m.group(0), float(re.sub(r"\s", "", m.group(0))), 1.0))
    return out


class Pool:
    """Values a mission may use, sorted for lookup."""

    def __init__(self, values: list[float]):
        self.values = sorted({abs(v) for v in values})

    def near(self, value: float, tol: float) -> bool:
        value = abs(value)
        tol += 1e-9 * max(1.0, value)
        i = bisect_left(self.values, value - tol)
        return i < len(self.values) and self.values[i] <= value + tol

    def has(self, number: Number) -> bool:
        return self.near(*number.check)


def _source_values(texts: list[str]) -> list[float]:
    return [v for t in texts for n in numbers(t) for v in n.values]


def grounded_calculations(calls: list[dict], sources: list[str]) -> list[dict]:
    """Calculator results whose numeric inputs all came from the sources.

    `calls` are {'op': ..., **args} in the order made; an earlier grounded
    result may feed a later call.
    """
    pool_values = _source_values(sources)
    out = []
    for call in calls:
        args = {k: v for k, v in call.items() if k != "op"}
        res = calculate_comparison(str(call.get("op")), **args)
        if res.status != ToolStatus.OK:
            continue
        if res.payload.get("op") == "tz_convert":
            if datetime_in(str(res.payload["inputs"]["time"]), sources):
                out.append(res.payload)
            continue
        pool = Pool(pool_values)
        inputs = [v for k, v in args.items() if isinstance(v, (int, float, str)) and k not in ("from_unit", "to_unit")]
        if all(_number_grounded(v, pool) for v in inputs):
            payload = dict(res.payload)
            # Inputs written in one unit ('99 - 85' for 99만, 85만) give a difference
            # in that unit: 14 is also 14만.
            payload["scaled"] = [res.payload[key] * k for k in _common_scales(inputs, pool)
                                 for key in ("value", "absolute_change")
                                 if res.payload.get("op") in ("diff", "pct_change")
                                 and isinstance(res.payload.get(key), (int, float))]
            out.append(payload)
            pool_values += _payload_values(payload)
    return out


def _common_scales(inputs: list, pool: Pool) -> list[float]:
    try:
        xs = [float(v) for v in inputs]
    except (TypeError, ValueError):
        return []
    return [k for k in _SCALES[1:] if all(pool.near(x * k, 0.0) for x in xs)]


def _number_grounded(value, pool: Pool) -> bool:
    """A calculator input must equal a source value ('990000' matches '99만')."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return False
    # Written in full ('990000' for '99만') or in a unit ('107.4405' for 107조 4405억).
    return any(pool.near(x * k, 0.0) for k in _SCALES)


def _payload_values(payload: dict) -> list[float]:
    out = []
    for key in ("value", "percentage", "absolute_change"):
        v = payload.get(key)
        if isinstance(v, (int, float)):
            out.append(float(v))
    out += [float(v) for v in payload.get("scaled", [])]
    if isinstance(payload.get("value"), str):
        out += [v for n in numbers(payload["value"]) for v in n.values]
    return out


def ungrounded_numbers(text: str, sources: list[str], calcs: list[dict],
                       claim: str | None = None) -> list[str]:
    """Numbers in `text` that none of the allowed origins contain."""
    values = _source_values(sources + ([claim] if claim else []))
    for payload in calcs:
        values += _payload_values(payload)
    pool = Pool(values)
    # '×100' turning a ratio into a percentage is part of a formula, not a value.
    text = re.sub(r"[×*]\s*100(?![\d,.])", " ", text or "")
    return [n.text for n in numbers(text)
            if not (len(n.values) == 1 and n.check[0] < 10 and n.check[0] == int(n.check[0]))
            and not pool.has(n) and not _scaled_decimal(n, pool)]


def _scaled_decimal(n: Number, pool: Pool) -> bool:
    """'107.4405' written for 107조 4405억: a bare decimal read in a larger unit."""
    value, tol = n.check
    if len(n.values) > 1 or value == int(value):
        return False
    return any(pool.near(value * k, tol * k) for k in _SCALES[1:])


# --------------------------------------------------------------------------
# Dates and times written in prose.
# --------------------------------------------------------------------------

_MONTHS = {m: i for i, names in enumerate((
    ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",),
    ("jun", "june"), ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"),
    ("oct", "october"), ("nov", "november"), ("dec", "december")), start=1) for m in names}
_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"


def _month(word: str) -> int:
    return _MONTHS[word.lower().rstrip(".")[:3]]


_DATE_PATTERNS = (
    (re.compile(r"(?<!\d)(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})(?!\d)"), lambda g: (int(g[1]), int(g[2]))),
    (re.compile(r"(?<!\d)(\d{1,2})\s*월\s*(\d{1,2})\s*일"), lambda g: (int(g[0]), int(g[1]))),
    (re.compile(_MONTH + r"\s+(\d{1,2})(?:st|nd|rd|th)?(?!\d)", re.IGNORECASE), lambda g: (_month(g[0]), int(g[1]))),
    (re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MONTH, re.IGNORECASE), lambda g: (_month(g[1]), int(g[0]))),
)
_TIME_PATTERNS = (
    re.compile(r"(?<![\d:])(\d{1,2}):(\d{2})(?!\d)(?:\s*([ap])\.?\s?m\b\.?)?", re.IGNORECASE),
    re.compile(r"(?<![\d:])(\d{1,2})()\s*([ap])\.?\s?m\b\.?", re.IGNORECASE),
    re.compile(r"(오전|오후|새벽|아침|낮|저녁|밤)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분|\s*(반))?"),
)
#: How far apart a date and a time may be written and still belong together.
DATE_TIME_WINDOW = 160


def _dates(text: str) -> list[tuple[int, tuple[int, int]]]:
    out = []
    for pattern, read in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            try:
                month, day = read(m.groups())
            except (KeyError, IndexError):
                continue
            if 1 <= month <= 12 and 1 <= day <= 31:
                out.append((m.start(), (month, day)))
    return out


def _times(text: str) -> list[tuple[int, tuple[int, int]]]:
    out = []
    for i, pattern in enumerate(_TIME_PATTERNS):
        for m in pattern.finditer(text):
            if i < 2:
                hour, minute, half = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
                if half == "p" and hour < 12:
                    hour += 12
                elif half == "a" and hour == 12:
                    hour = 0
            else:
                period, hour = m.group(1), int(m.group(2))
                minute = 30 if m.group(4) else int(m.group(3) or 0)
                if period in ("오후", "저녁", "밤") and hour < 12:
                    hour += 12
                elif period in ("오전", "새벽", "아침") and hour == 12:
                    hour = 0
            if hour <= 24 and minute < 60:
                out.append((m.start(), (hour % 24, minute)))
    for word, clock in (("자정", (0, 0)), ("정오", (12, 0)), ("midnight", (0, 0)), ("noon", (12, 0))):
        out += [(m.start(), clock) for m in re.finditer(word, text, re.IGNORECASE)]
    return out


def _parse_stamp(stamp: str) -> datetime | None:
    stamp = re.sub(r"\s+", " ", (stamp or "").strip()).replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(stamp, fmt)
        except ValueError:
            continue
    return None


def datetime_in(stamp: str, texts: list[str]) -> bool:
    """True when the stamp's day (and time, if it has one) is written in a text,
    the time within DATE_TIME_WINDOW characters of the date."""
    moment = _parse_stamp(stamp)
    if moment is None:
        return False
    has_time = bool(re.search(r"\d:\d", stamp))
    day, clock = (moment.month, moment.day), (moment.hour, moment.minute)
    for text in texts:
        dates = [pos for pos, d in _dates(text) if d == day]
        if not dates:
            continue
        if not has_time:
            return True
        times = [pos for pos, t in _times(text) if t == clock]
        if any(abs(d - t) <= DATE_TIME_WINDOW for d in dates for t in times):
            return True
    return False


def event_time_grounded(event_start_kst: str, sources: list[str], calcs: list[dict]) -> bool:
    """The KST start is written in a source, or is a KST conversion of a source time."""
    moment = _parse_stamp(event_start_kst)
    if moment is None:
        return False
    if datetime_in(event_start_kst, sources):
        return True
    wanted = moment.strftime("%Y-%m-%d %H:%M")
    return any(p.get("op") == "tz_convert" and p.get("value") == wanted
               and _is_kst(str(p["inputs"].get("to_tz", ""))) for p in calcs)


def _is_kst(label: str) -> bool:
    label = label.upper().replace(" ", "")
    return "KST" in label or label in ("UTC+9", "UTC+09", "UTC+09:00", "UTC+9:00")


def check_action_values(*, mission_type: str, verdict: str, title: str, summary: str,
                        correction: str | None, event_start_kst: str | None, claim: str,
                        sources: list[str], calls: list[dict]) -> str | None:
    """None when every value the action would write is grounded, else the reason."""
    calcs = grounded_calculations(calls, sources)
    if mission_type == "event_manager":
        if not event_start_kst or not event_time_grounded(event_start_kst, sources, calcs):
            return (f"값 대조 차단: event_start_kst({event_start_kst})의 날짜·시각이 인용한 문서에 없고, "
                    "인용 문서의 시각을 KST로 변환한 계산 결과도 아닙니다.")
        if verdict == "refuted" and not datetime_in(event_start_kst, [correction or ""]):
            return (f"값 대조 차단: 반박된 일정의 correction에 event_start_kst({event_start_kst})와 같은 "
                    "날짜·시각이 없습니다.")
    text = "\n".join(s for s in (title, summary, correction) if s)
    missing = ungrounded_numbers(text, sources, calcs, claim if verdict == "refuted" else None)
    if missing:
        return ("값 대조 차단: 결과물의 수치가 인용한 문서나 그 문서 값으로 한 계산 결과에 없습니다: "
                f"{missing[:8]}. 원문 값을 그대로 쓰거나 calculate_comparison으로 계산한 값만 쓰세요.")
    return None
