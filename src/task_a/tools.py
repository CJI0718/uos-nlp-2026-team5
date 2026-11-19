"""The six tools the agent may call.

Design constraints from the team docs:
- tools.md section 2 defines these signatures.
- tools.md section 4: read-only, host allowlist, no local file access, and
  tool status is separate from the claim's truth.
- The agent gets NO filesystem tool. Gold lives in evaluation.md inside this
  repository, so file access would be answer leakage.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Protocol
from urllib.parse import urlsplit

from task_a.schema import EvidenceUnit, ToolResult, ToolStatus

MAX_SNIPPET_CHARS = 600
MAX_FETCH_CHARS = 4000
#: source_type values that describe provenance (shown to the agent when enabled).
PROVENANCE_SOURCE_TYPES = frozenset({"official", "primary", "news", "reprint", "blog", "sns"})


class ToolBackend(Protocol):
    """Swappable so tests run offline. Mock and live share this shape."""

    def search_corpus(self, query: str, top_k: int) -> list[tuple[EvidenceUnit, float]]: ...

    def web_search(self, query: str, top_k: int, end_date: str | None = None) -> list[dict]: ...

    def fetch(self, url: str) -> str: ...


# --------------------------------------------------------------------------
# calculate_comparison — whitelisted operations only, no eval, no exec.
# tools.md: 'missing·0 분모·NaN·불일치 기간은 계산 실패로 반환한다.'
# --------------------------------------------------------------------------

TIMEZONE_OFFSETS = {
    "UTC": 0, "KST": 9, "JST": 9, "PST": -8, "PDT": -7,
    "EST": -5, "EDT": -4, "CST": -6, "CDT": -5, "MST": -7, "MDT": -6,
}

# value -> (target unit, multiplier). Units the 50 cases actually need.
UNIT_SCALE = {
    ("billion", "million"): 1_000.0,
    ("million", "billion"): 0.001,
    ("억", "만"): 10_000.0,
    ("만", "억"): 0.0001,
    ("조", "억"): 10_000.0,
    ("gb", "mb"): 1_024.0,
    ("tb", "gb"): 1_024.0,
    ("mb", "kb"): 1_024.0,
}


def _parse_time(value: str) -> datetime:
    text = re.sub(r"\s+", " ", str(value).strip())
    meridiem = ""
    for korean, english in (("오전", "AM"), ("오후", "PM")):
        if korean in text:
            meridiem = english
            text = text.replace(korean, "").strip()
    upper = text.upper()
    # The meridiem form must be tried first, or '오후 05:00' parses as 05:00.
    candidates = [f"{upper} {meridiem}", upper] if meridiem else [upper]
    formats = ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%I:%M %p", "%H:%M")
    for candidate in candidates:
        for fmt in formats:
            try:
                parsed = datetime.strptime(candidate, fmt)
            except ValueError:
                continue
            if parsed.year == 1900:  # time-only input; date is not part of the claim
                parsed = parsed.replace(year=2000, month=1, day=1)
            return parsed
    raise ValueError(f"unparseable time: {value!r}")


def _cutoff_date(value: str | None) -> str | None:
    """'2026-10-30T01:37:43+09:00' -> '2026-10-30'; None when absent or unparseable."""
    if not value:
        return None
    match = re.match(r"(\d{4}-\d{2}-\d{2})", str(value).strip())
    return match.group(1) if match else None


def calculate_comparison(op: str, **kwargs) -> ToolResult:
    """Whitelisted arithmetic. Returns a failure status rather than a guess."""
    try:
        if op == "diff":
            a, b = float(kwargs["a"]), float(kwargs["b"])
            value = a - b
            return ToolResult(
                ToolStatus.OK,
                f"{a:g} - {b:g} = {value:g}",
                {"op": op, "formula": "a - b", "inputs": {"a": a, "b": b}, "value": value},
            )

        if op == "pct_change":
            old, new = float(kwargs["old"]), float(kwargs["new"])
            if old == 0:
                return ToolResult(ToolStatus.INVALID_INPUT, "0 분모: 기준값이 0이라 변화율을 계산할 수 없음")
            value = (new - old) / old * 100
            return ToolResult(
                ToolStatus.OK,
                f"({new:g} - {old:g}) / {old:g} x 100 = {value:.4g}%  (절대 변화 {new - old:g}, "
                f"{abs(value):.4g}%p 아님: %p는 두 비율의 차이에만 사용)",
                {"op": op, "formula": "(new - old) / old * 100",
                 "inputs": {"old": old, "new": new}, "value": value,
                 "absolute_change": new - old},
            )

        if op == "percentage_point_gap":
            a, b = float(kwargs["a"]), float(kwargs["b"])
            value = a - b
            return ToolResult(
                ToolStatus.OK,
                f"{a:g}% - {b:g}% = {value:g}%p",
                {"op": op, "formula": "a - b (in %p)", "value": value, "unit": "%p"},
            )

        if op == "tz_convert":
            moment = _parse_time(kwargs["time"])
            src = kwargs["from_tz"].strip().upper()
            dst = kwargs["to_tz"].strip().upper()
            if src not in TIMEZONE_OFFSETS or dst not in TIMEZONE_OFFSETS:
                return ToolResult(ToolStatus.INVALID_INPUT, f"지원하지 않는 시간대: {src}/{dst}")
            shift = TIMEZONE_OFFSETS[dst] - TIMEZONE_OFFSETS[src]
            converted = moment + timedelta(hours=shift)
            return ToolResult(
                ToolStatus.OK,
                f"{kwargs['time']} {src} -> {dst}: {shift:+d}시간 = "
                f"{converted:%Y-%m-%d %H:%M} {dst}",
                {"op": op, "inputs": {"time": kwargs["time"], "from_tz": src, "to_tz": dst},
                 "offset_hours": shift, "value": f"{converted:%Y-%m-%d %H:%M}"},
            )

        if op == "scale_unit":
            value_in = float(kwargs["value"])
            pair = (str(kwargs["from_unit"]).strip().lower(), str(kwargs["to_unit"]).strip().lower())
            if pair not in UNIT_SCALE:
                return ToolResult(ToolStatus.INVALID_INPUT, f"지원하지 않는 단위 변환: {pair[0]} -> {pair[1]}")
            factor = UNIT_SCALE[pair]
            converted = value_in * factor
            return ToolResult(
                ToolStatus.OK,
                f"{value_in:g} {pair[0]} = {converted:g} {pair[1]} (x{factor:g})",
                {"op": op, "inputs": {"value": value_in, **dict(zip(("from_unit", "to_unit"), pair))},
                 "factor": factor, "value": converted},
            )

        if op == "multiply":
            a, b = float(kwargs["a"]), float(kwargs["b"])
            value = a * b
            return ToolResult(
                ToolStatus.OK,
                f"{a:g} x {b:g} = {value:g}",
                {"op": op, "formula": "a * b", "inputs": {"a": a, "b": b}, "value": value},
            )

        if op == "ratio":
            a, b = float(kwargs["a"]), float(kwargs["b"])
            if b == 0:
                return ToolResult(ToolStatus.INVALID_INPUT, "0 분모: 기준값이 0이라 비율을 계산할 수 없음")
            value = a / b
            return ToolResult(
                ToolStatus.OK,
                f"{a:g} / {b:g} = {value:.6g} ({value * 100:.4g}%)",
                {"op": op, "formula": "a / b", "inputs": {"a": a, "b": b},
                 "value": value, "percentage": value * 100},
            )

        return ToolResult(ToolStatus.INVALID_INPUT, f"허용되지 않은 연산: {op!r}")
    except (KeyError, TypeError) as exc:
        return ToolResult(ToolStatus.INVALID_INPUT, f"입력 누락: {exc}")
    except ValueError as exc:
        return ToolResult(ToolStatus.INVALID_INPUT, str(exc))


# --------------------------------------------------------------------------
# fetch_url guard — tools.md section 4: allow scheme/host, block private/local.
# --------------------------------------------------------------------------

RESERVED_SUFFIXES = (".local", ".localdomain", ".internal", ".intranet", ".localhost", ".lan")
RESERVED_NAMES = frozenset({"localhost", "local", "internal", "intranet", "metadata",
                            "ip6-localhost", "ip6-loopback"})


def _is_non_public_host(host: str) -> bool:
    """IP-literal check via stdlib ipaddress, so IPv6 is covered too.

    Limitation: a public-looking hostname that resolves to a private address is
    not caught here, because that needs a DNS lookup. The allowlist in
    `check_url` is the real defence; this is depth behind it.
    """
    if host in RESERVED_NAMES or host.endswith(RESERVED_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a public hostname, not an IP literal
    return (ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified)


def check_url(url: str, allowed_hosts: frozenset[str] | None) -> str | None:
    """Return a rejection reason, or None when the URL may be fetched."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "url 파싱 실패"
    if parts.scheme not in ("http", "https"):
        return f"허용 scheme 아님: {parts.scheme or '(없음)'}"
    host = (parts.hostname or "").lower().strip("[]")
    if not host:
        return "host 없음"
    if _is_non_public_host(host):
        return f"사설망·로컬·예약 주소 차단: {host}"
    if allowed_hosts and not any(host == h or host.endswith("." + h) for h in allowed_hosts):
        return f"허용 목록 밖 host: {host}"
    return None


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., ToolResult]
    external: bool = False


class ToolRegistry:
    """Builds the tool list for one episode and executes calls."""

    def __init__(
        self,
        backend: ToolBackend,
        top_k: int = 5,
        allowed_hosts: frozenset[str] | None = None,
        show_provenance: bool = True,
    ) -> None:
        self.backend = backend
        self.show_provenance = show_provenance
        #: The active claim's evidence_cutoff; set by the environment per episode.
        self.evidence_cutoff: str | None = None
        self.top_k = top_k
        self.allowed_hosts = allowed_hosts
        #: Pages opened with fetch_url in this episode, so read_evidence can page
        #: through them without another network call.
        self.fetched: dict[str, dict] = {}
        self.specs: dict[str, ToolSpec] = {}
        self._register()

    def _register(self) -> None:
        self._add(ToolSpec(
            "search_evidence",
            "고정 코퍼스에서 근거 문서를 검색한다. 외부 네트워크를 사용하지 않는다.",
            {"type": "object",
             "properties": {"query": {"type": "string", "description": "검색 질의"},
                            "top_k": {"type": "integer", "description": "반환 개수 (기본값 사용 권장)"}},
             "required": ["query"]},
            self._search_evidence))
        self._add(ToolSpec(
            "read_evidence",
            (f"문서 본문을 {MAX_FETCH_CHARS}자씩 읽는다. 코퍼스 evidence_id 또는 이번 에피소드에서 "
             "fetch_url로 연 URL을 받는다. 본문이 길면 응답 끝의 offset으로 이어 읽는다."),
            {"type": "object",
             "properties": {"evidence_id": {"type": "string"},
                            "offset": {"type": "integer",
                                       "description": "읽기 시작할 글자 위치(선택, 기본 0)"},
                            "section": {"type": "string",
                                        "description": "이 문구가 처음 나오는 곳부터 읽기(선택)"}},
             "required": ["evidence_id"]},
            self._read_evidence))
        self._add(ToolSpec(
            "calculate_comparison",
            "허용된 연산만 수행하는 계산기. op: diff, pct_change, percentage_point_gap, "
            "tz_convert, scale_unit, multiply, ratio. 임의 수식 평가는 지원하지 않는다.",
            {"type": "object",
             "properties": {
                 "op": {"type": "string", "enum": ["diff", "pct_change", "percentage_point_gap",
                                                   "tz_convert", "scale_unit", "multiply", "ratio"]},
                 "a": {"type": "number"}, "b": {"type": "number"},
                 "old": {"type": "number"}, "new": {"type": "number"},
                 "value": {"type": "number"},
                 "time": {"type": "string"}, "from_tz": {"type": "string"}, "to_tz": {"type": "string"},
                 "from_unit": {"type": "string"}, "to_unit": {"type": "string"}},
             "required": ["op"]},
            lambda **kw: calculate_comparison(**kw)))
        self._add(ToolSpec(
            "search_web",
            "외부 웹 검색. 코퍼스에서 결정적 근거를 찾지 못했을 때만 사용한다.",
            {"type": "object",
             "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
             "required": ["query"]},
            self._search_web, external=True))
        self._add(ToolSpec(
            "fetch_url",
            (f"허용된 host의 웹 페이지 본문(메뉴·광고 제외)을 앞 {MAX_FETCH_CHARS}자까지 연다. "
             "로컬·사설 주소는 차단된다. 이어 읽기는 read_evidence(evidence_id=URL, offset)로 한다."),
            {"type": "object",
             "properties": {"url": {"type": "string"}},
             "required": ["url"]},
            self._fetch_url, external=True))

    def reset_episode(self, evidence_cutoff: str | None = None) -> None:
        self.evidence_cutoff = evidence_cutoff
        self.fetched = {}

    def _add(self, spec: ToolSpec) -> None:
        self.specs[spec.name] = spec

    @property
    def schemas(self) -> list[dict]:
        return [{"type": "function",
                 "function": {"name": s.name, "description": s.description,
                              "parameters": s.parameters}}
                for s in self.specs.values()]

    def call(self, name: str, args: dict) -> tuple[ToolResult, bool]:
        """Returns (result, is_external). Unknown tools are invalid_input."""
        spec = self.specs.get(name)
        if spec is None:
            return ToolResult(ToolStatus.INVALID_INPUT, f"존재하지 않는 도구: {name!r}"), False
        try:
            return spec.handler(**(args or {})), spec.external
        except TypeError as exc:
            return ToolResult(ToolStatus.INVALID_INPUT, f"인자 오류: {exc}"), spec.external

    # -- handlers ----------------------------------------------------------

    def _search_evidence(self, query: str, top_k: int | None = None) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(ToolStatus.INVALID_INPUT, "빈 질의")
        k = min(top_k or self.top_k, self.top_k)
        hits = self.backend.search_corpus(query.strip(), k)
        if not hits:
            # empty means 'no results', never 'the claim is false'.
            return ToolResult(ToolStatus.EMPTY, "코퍼스에서 일치하는 근거를 찾지 못했다.")
        lines, ids, ranks, flags = [], [], [], []
        for rank, (unit, score) in enumerate(hits, start=1):
            snippet = unit.text[:MAX_SNIPPET_CHARS]
            meta = self._provenance_line(unit, sep=" | ")
            lines.append(f"[{rank}] {unit.evidence_id} | {unit.title} | 관련도 {score:.3f}{meta}\n"
                         f"    {snippet}")
            ids.append(unit.evidence_id)
            ranks.append(rank)
            if unit.is_misleading:
                flags.append(unit.evidence_id)
        return ToolResult(ToolStatus.OK, "\n\n".join(lines),
                          {"query": query, "top_k": k, "count": len(hits), "misleading_ids": flags},
                          evidence_ids=ids, ranks=ranks)

    def _provenance_line(self, unit: EvidenceUnit, sep: str) -> str:
        """Source type and provenance group, or nothing when the condition hides them."""
        if not self.show_provenance:
            return ""
        parts = []
        if unit.source_type in PROVENANCE_SOURCE_TYPES:  # not file formats such as html/pdf
            parts.append(f"출처유형:{unit.source_type}")
        if unit.provenance_group:
            parts.append(f"출처군:{unit.provenance_group}")
        return (sep + " · ".join(parts)) if parts else ""

    def _read_evidence(self, evidence_id: str, section: str | None = None,
                       offset: int | None = None) -> ToolResult:
        if evidence_id in self.fetched:
            doc = self.fetched[evidence_id]
            return self._page(evidence_id, doc["title"], evidence_id, doc.get("published_at"),
                              doc["text"], "", section, offset, {"url": evidence_id})
        unit = self.backend.lookup(evidence_id) if hasattr(self.backend, "lookup") else None
        if unit is None:
            return ToolResult(ToolStatus.INVALID_INPUT,
                              f"없는 evidence_id: {evidence_id!r}. 코퍼스 문서는 search_evidence로, "
                              f"웹 문서는 fetch_url로 먼저 연다.")
        return self._page(unit.evidence_id, unit.title, unit.source_url or "unknown",
                          unit.published_at, unit.text, self._provenance_line(unit, sep=chr(10)),
                          section, offset,
                          {"evidence_id": unit.evidence_id, "source_url": unit.source_url,
                           "published_at": unit.published_at,
                           "provenance_group": unit.provenance_group,
                           "content_hash": unit.content_hash
                           or hashlib.sha256(unit.text.encode()).hexdigest()[:16]})

    @staticmethod
    def _page(doc_id: str, title: str, source: str, published: str | None, text: str,
              provenance: str, section: str | None, offset: int | None, payload: dict) -> ToolResult:
        """One window of a document, with where to continue when more remains."""
        try:
            start = max(0, int(offset or 0))
        except (TypeError, ValueError):
            return ToolResult(ToolStatus.INVALID_INPUT, f"offset은 정수여야 한다: {offset!r}")
        if section and section.strip() and not offset:
            idx = text.lower().find(section.strip().lower())
            if idx >= 0:
                start = max(0, idx - 200)
        if start >= len(text) and text:
            return ToolResult(ToolStatus.INVALID_INPUT,
                              f"offset {start}이 본문 길이({len(text)}자)를 넘는다.")
        end = min(len(text), start + MAX_FETCH_CHARS)
        if start == 0 and end == len(text):
            position = ""
        else:
            more = (f" 이어 읽기: read_evidence(evidence_id=\"{doc_id}\", offset={end})"
                    if end < len(text) else " 끝까지 읽음.")
            position = f"\n\n(전체 {len(text)}자 중 {start}~{end}자.{more})"
        head = f"{doc_id} | {title}\n출처: {source}\n발행: {published or '미상'}{provenance}\n\n"
        return ToolResult(ToolStatus.OK, head + text[start:end] + position,
                          {**payload, "offset": start, "end": end, "chars": len(text),
                           "full_text": text},
                          evidence_ids=[doc_id])

    def _search_web(self, query: str, top_k: int | None = None) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(ToolStatus.INVALID_INPUT, "빈 질의")
        cutoff = _cutoff_date(self.evidence_cutoff)
        try:
            k = min(top_k or self.top_k, self.top_k)
            hits = (self.backend.web_search(query.strip(), k, end_date=cutoff) if cutoff
                    else self.backend.web_search(query.strip(), k))
        except Exception as exc:  # network/provider failure is not a fact verdict
            return ToolResult(ToolStatus.SOURCE_UNAVAILABLE, f"웹 검색 실패: {exc}")
        kept, dropped = [], []
        for h in hits:
            published = (h.get("published_date") or "")[:10]
            (dropped if cutoff and published and published > cutoff else kept).append(h)
        note = (f"\n\n(근거 허용 시점 {cutoff} 이후 발행된 결과 {len(dropped)}건은 제외했다.)"
                if dropped else "")
        if not kept:
            return ToolResult(ToolStatus.EMPTY, "웹 검색 결과가 없다. 근거 부족을 의미하지는 않는다." + note,
                              {"query": query, "dropped_after_cutoff": [h.get("url") for h in dropped]})
        lines = [f"[{i}] {h.get('title', '')}\n    {h.get('url', '')}"
                 f"\n    발행: {(h.get('published_date') or '미상')[:10]}\n    {h.get('snippet', '')}"
                 for i, h in enumerate(kept, start=1)]
        return ToolResult(ToolStatus.OK, "\n\n".join(lines) + note,
                          {"query": query, "count": len(kept), "urls": [h.get("url") for h in kept],
                           "dropped_after_cutoff": [h.get("url") for h in dropped]})

    def _fetch_url(self, url: str) -> ToolResult:
        denied = check_url(url, self.allowed_hosts)
        if denied:
            return ToolResult(ToolStatus.BLOCKED, f"차단: {denied}")
        try:
            raw = self.backend.fetch(url)
        except Exception as exc:
            return ToolResult(ToolStatus.SOURCE_UNAVAILABLE, f"조회 실패: {exc}")
        doc = raw if isinstance(raw, dict) else {"text": raw or ""}
        text = (doc.get("text") or "").strip()
        if not text:
            return ToolResult(ToolStatus.EMPTY, "본문이 비어 있다.")
        published = doc.get("published_at")
        cutoff = _cutoff_date(self.evidence_cutoff)
        if cutoff and published and str(published)[:10] > cutoff:
            # A page written after the cutoff could reveal how the event turned out.
            return ToolResult(ToolStatus.BLOCKED,
                              f"근거 허용 시점({cutoff}) 이후 발행된 문서다(발행 {str(published)[:10]}). "
                              f"인용할 수 없다.", {"url": url, "published_at": published})
        shown = published
        if published and doc.get("date_source") == "htmldate":
            shown = f"{published} (페이지에서 추정한 날짜, 수정일일 수 있음)"
        doc = {"text": text, "title": doc.get("title") or "", "published_at": shown}
        self.fetched[url] = doc
        # The URL is the citation id for web evidence, so record it as read.
        return self._page(url, doc["title"], url, shown, text, "", None, None,
                          {"url": url, "published_at": published, "extractor": raw.get("extractor")
                           if isinstance(raw, dict) else None,
                           "content_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
                           "truncated": len(text) > MAX_FETCH_CHARS})


# `finish_verification` is not a registry tool: it is the episode's exit signal.
FINISH_TOOL = "finish_verification"

FINISH_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["supported", "refuted", "not_enough_evidence"]},
        "abstain": {"type": "boolean",
                    "description": "판정을 유보하면 true. verdict와 별개 필드다."},
        "cited_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "justification": {"type": "string", "description": "짧은 판정 이유"},
        "correction": {"type": "string", "description": "반박 시 정정 사실"},
        "stop_reason": {"type": "string",
                        "enum": ["evidence_sufficient", "budget_exhausted",
                                 "no_further_tools_helpful", "conflict_unresolved"]},
        "distortion_type": {
            "type": "string",
            "enum": ["none", "numeric_error", "unit_or_scale_error", "timezone_or_date_error",
                     "missing_condition_or_scope", "overgeneralization", "forecast_as_fact",
                     "source_misattribution", "unverified_claim"],
            "description": "원문과 주장을 대조해 식별한 왜곡/오류 유형(선택)",
        },
        "problematic_span": {
            "type": "string",
            "description": "주장 또는 입력 글에서 왜곡이 발생한 구체적 구절(선택)",
        },
        "mission_type": {
            "type": "string",
            "enum": ["no_op", "event_manager", "news_to_artifact", "opportunity_execution",
                     "app_safe_trial", "continuous_tracking", "hold_abstain"],
            "description": ("검증 결과에 따라 실행할 후속 업무(Mission) 유형(선택). 서버가 이 제출의 "
                            "최종 판정·인용 근거·정정으로 검증 게이트를 적용한 뒤 실행한다."),
        },
        "mission_title": {"type": "string", "description": "미션 결과물 제목(선택)"},
        "mission_summary": {"type": "string", "description": "미션 결과물에 들어갈 검증 요약(선택)"},
        "event_start_kst": {
            "type": "string",
            "description": "event_manager용 검증된 KST 시각 'YYYY-MM-DD HH:MM'. 반박이면 correction에 같은 HH:MM이 있어야 한다.",
        },
        "tracking_condition": {"type": "string", "description": "continuous_tracking용 재검증 조건"},
        "tracking_queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "abstain", "cited_evidence_ids", "justification", "stop_reason"],
}
