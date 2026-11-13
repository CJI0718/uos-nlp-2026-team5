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


class ToolBackend(Protocol):
    """Swappable so tests run offline. Mock and live share this shape."""

    def search_corpus(self, query: str, top_k: int) -> list[tuple[EvidenceUnit, float]]: ...

    def web_search(self, query: str, top_k: int) -> list[dict]: ...

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
    ) -> None:
        self.backend = backend
        self.top_k = top_k
        self.allowed_hosts = allowed_hosts
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
            "코퍼스 문서의 본문을 읽는다. 검색 결과에서 받은 evidence_id만 사용할 수 있다.",
            {"type": "object",
             "properties": {"evidence_id": {"type": "string"},
                            "section": {"type": "string", "description": "필요한 구간(선택)"}},
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
            "허용된 host의 원문을 조회한다. 로컬·사설 주소는 차단된다.",
            {"type": "object",
             "properties": {"url": {"type": "string"}},
             "required": ["url"]},
            self._fetch_url, external=True))

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
            meta = f" | 출처군:{unit.provenance_group}" if unit.provenance_group else ""
            lines.append(f"[{rank}] {unit.evidence_id} | {unit.title} | 관련도 {score:.3f}{meta}\n"
                         f"    {snippet}")
            ids.append(unit.evidence_id)
            ranks.append(rank)
            if unit.is_misleading:
                flags.append(unit.evidence_id)
        return ToolResult(ToolStatus.OK, "\n\n".join(lines),
                          {"query": query, "top_k": k, "count": len(hits), "misleading_ids": flags},
                          evidence_ids=ids, ranks=ranks)

    def _read_evidence(self, evidence_id: str, section: str | None = None) -> ToolResult:
        unit = self.backend.lookup(evidence_id) if hasattr(self.backend, "lookup") else None
        if unit is None:
            return ToolResult(ToolStatus.INVALID_INPUT,
                              f"코퍼스에 없는 evidence_id: {evidence_id!r}. 먼저 search_evidence로 찾아라.")
        body = unit.text
        if section and section.strip().lower() in body.lower():
            idx = body.lower().index(section.strip().lower())
            body = body[max(0, idx - 200): idx + MAX_FETCH_CHARS]
        else:
            body = body[:MAX_FETCH_CHARS]
        return ToolResult(
            ToolStatus.OK,
            f"{unit.evidence_id} | {unit.title}\n출처: {unit.source_url or 'unknown'}\n"
            f"발행: {unit.published_at or 'unknown'}\n\n{body}",
            {"evidence_id": unit.evidence_id, "source_url": unit.source_url,
             "published_at": unit.published_at, "provenance_group": unit.provenance_group,
             "content_hash": unit.content_hash or hashlib.sha256(unit.text.encode()).hexdigest()[:16]},
            evidence_ids=[unit.evidence_id])

    def _search_web(self, query: str, top_k: int | None = None) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(ToolStatus.INVALID_INPUT, "빈 질의")
        try:
            hits = self.backend.web_search(query.strip(), min(top_k or self.top_k, self.top_k))
        except Exception as exc:  # network/provider failure is not a fact verdict
            return ToolResult(ToolStatus.SOURCE_UNAVAILABLE, f"웹 검색 실패: {exc}")
        if not hits:
            return ToolResult(ToolStatus.EMPTY, "웹 검색 결과가 없다. 근거 부족을 의미하지는 않는다.")
        lines = [f"[{i}] {h.get('title', '')}\n    {h.get('url', '')}\n    {h.get('snippet', '')}"
                 for i, h in enumerate(hits, start=1)]
        return ToolResult(ToolStatus.OK, "\n\n".join(lines),
                          {"query": query, "count": len(hits), "urls": [h.get("url") for h in hits]})

    def _fetch_url(self, url: str) -> ToolResult:
        denied = check_url(url, self.allowed_hosts)
        if denied:
            return ToolResult(ToolStatus.BLOCKED, f"차단: {denied}")
        try:
            body = self.backend.fetch(url)
        except Exception as exc:
            return ToolResult(ToolStatus.SOURCE_UNAVAILABLE, f"조회 실패: {exc}")
        if not body or not body.strip():
            return ToolResult(ToolStatus.EMPTY, "본문이 비어 있다.")
        return ToolResult(ToolStatus.OK, body[:MAX_FETCH_CHARS],
                          {"url": url, "chars": len(body),
                           "content_hash": hashlib.sha256(body.encode()).hexdigest()[:16],
                           "truncated": len(body) > MAX_FETCH_CHARS})


# `finish_verification` is not a registry tool: it is the loop's exit signal,
# parsed from the model's final structured answer rather than executed.

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
            "description": "검증 결과에 따라 결정한 후속 업무(Mission) 유형(선택)",
        },
        "mission_output": {
            "type": "object",
            "description": "생성한 후속 Mission 결과물 정보 또는 장기 추적 등록 명세(선택)",
        },
    },
    "required": ["verdict", "abstain", "cited_evidence_ids", "justification", "stop_reason"],
}
