"""Verification-Gated Mission & Continuous Tracking Executor.

Implements STEP 3~4 and Continuous Claim Tracking from
`docs/research/fact_checking/README.md` section 8, connected directly to Task A
verification results:

1. Verification Gate ('Garbage In, Action Out' prevention):
   - The gate reads the episode's FINAL verdict. `AgentEnvironment` runs a
     mission only from `finish_verification`, so an agent cannot unlock an
     action with one verdict and then submit another.
   - Actionable missions (`event_manager`, `news_to_artifact`,
     `opportunity_execution`, `app_safe_trial`) CANNOT be executed when the
     claim is unverified (`not_enough_evidence` or `abstain=True`).
   - Actionable missions must cite evidence, and every cited id must have been
     read in this episode (`read_evidence` or `fetch_url`). A citation the
     agent never opened does not count as verification.
   - When a claim is `refuted`, an actionable mission MUST use the verified
     `correction` (e.g., corrected KST time or corrected figure) rather than
     propagating the distorted claim text. For `event_manager` the scheduled
     time must appear in that correction.
2. Concrete Outputs:
   - `event_manager`: writes an RFC 5545 `.ics` file under `missions/events/`.
   - `news_to_artifact` / `opportunity_execution` / `app_safe_trial`: writes a
     structured Markdown verification & action artifact under `missions/artifacts/`.
   - `continuous_tracking`: appends a structured tracking record to
     `missions/tracking/tracking_registry.jsonl`.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from task_a.schema import ToolResult, ToolStatus, Verdict

ACTIONABLE_MISSIONS = frozenset({
    "event_manager",
    "news_to_artifact",
    "opportunity_execution",
    "app_safe_trial",
})

ALL_MISSIONS = ACTIONABLE_MISSIONS | {"no_op", "continuous_tracking", "hold_abstain"}


@dataclass(frozen=True)
class MissionRecord:
    claim_id: str
    mission_type: str
    verdict: str
    title: str
    summary: str
    cited_evidence_ids: list[str] = field(default_factory=list)
    used_correction: str | None = None
    distortion_type: str | None = None
    artifact_path: str | None = None
    tracking_condition: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_HHMM = re.compile(r"(\d{1,2}):(\d{2})")
_DATE_ONLY = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")


def is_date_only(event_start: str | None) -> bool:
    """'2027-02-26' (an all-day event such as a release date) rather than a clock time."""
    return bool(_DATE_ONLY.match(event_start or ""))


def _date_in_correction(event_start: str, correction: str) -> bool:
    """True when the all-day event's date is written in the correction.

    Accepts the ISO date or the Korean '2월 26일' form; nothing looser.
    """
    match = _DATE_ONLY.match(event_start or "")
    if not match:
        return False
    y, m, d = match.groups()
    text = correction or ""
    return f"{y}-{m}-{d}" in text or bool(re.search(rf"(?<!\d){int(m)}월\s*{int(d)}일", text))


def _time_in_correction(event_start_kst: str, correction: str) -> bool:
    """True when the event's HH:MM appears in the correction text.

    Deterministic and deliberately narrow: '22:00' must be written as a clock
    time in the correction. A correction phrased only as '오후 10시' is
    rejected rather than interpreted.
    """
    match = _HHMM.search(event_start_kst or "")
    if not match:
        return False
    hh, mm = int(match.group(1)), match.group(2)
    return any(int(h) == hh and m == mm for h, m in _HHMM.findall(correction or ""))


def validate_mission_gate(
    mission_type: str,
    verdict: str | Verdict | None,
    *,
    abstain: bool = False,
    correction: str | None = None,
    cited_evidence_ids: list[str] | None = None,
    observed_evidence_ids: set[str] | frozenset[str] | None = None,
    event_start_kst: str | None = None,
    evidence_meta: dict[str, dict] | None = None,
    require_independent: bool = False,
    allow_date_only: bool = False,
) -> str | None:
    """Return an error reason if the mission violates the verification gate.

    `observed_evidence_ids` is the set the environment saw the agent read. When
    it is None (direct library use) only the presence of citations is checked.

    With `require_independent`, an action also needs its cited documents to
    include a primary source or to span at least two provenance groups:
    five reprints of one article are one source, not five (`evidence_meta`
    maps evidence_id to its `source_type` and `provenance_group`).

    `allow_date_only` (off for experiments) lets an all-day event_start
    ('YYYY-MM-DD') through; a refuted one then needs that date in the correction
    instead of an HH:MM.
    """
    if mission_type not in ALL_MISSIONS:
        return f"알 수 없는 mission_type: {mission_type!r} (허용: {sorted(ALL_MISSIONS)})"

    verdict_val = verdict.value if isinstance(verdict, Verdict) else str(verdict or "")
    if mission_type in ACTIONABLE_MISSIONS:
        if abstain or verdict_val == Verdict.NOT_ENOUGH_EVIDENCE.value or not verdict_val:
            return (
                f"검증 게이팅 차단: 판정이 보류(abstain)이거나 근거 부족({verdict_val})인 정보로는 "
                f"실행형 미션({mission_type})을 수행할 수 없습니다. "
                f"'continuous_tracking' 또는 'hold_abstain'을 선택하세요."
            )
        cited = [c for c in (cited_evidence_ids or []) if str(c).strip()]
        if not cited:
            return (
                f"검증 게이팅 차단: 실행형 미션({mission_type})은 판정 근거(cited_evidence_ids)를 "
                f"하나 이상 인용해야 합니다."
            )
        if observed_evidence_ids is not None:
            unread = [c for c in cited if c not in observed_evidence_ids]
            if unread:
                return (
                    f"검증 게이팅 차단: 이번 에피소드에서 read_evidence/fetch_url로 읽지 않은 근거를 "
                    f"인용했습니다: {unread}"
                )
        if require_independent:
            reason = independence_error(cited, evidence_meta or {})
            if reason:
                return reason
        if verdict_val == Verdict.REFUTED.value and not (correction and correction.strip()):
            return (
                f"검증 게이팅 차단: 반박(refuted)된 주장에 대해 실행형 미션({mission_type})을 "
                f"수행하려면 반드시 정정된 사실(correction)을 함께 제공해야 합니다."
            )
        if (mission_type == "event_manager" and verdict_val == Verdict.REFUTED.value
                and allow_date_only and is_date_only(event_start_kst)):
            if not _date_in_correction(event_start_kst or "", correction or ""):
                return ("검증 게이팅 차단: 반박된 종일 일정의 날짜(YYYY-MM-DD)가 correction에 없습니다. "
                        "정정된 날짜로만 일정을 만들 수 있습니다.")
        elif (mission_type == "event_manager" and verdict_val == Verdict.REFUTED.value
                and not _time_in_correction(event_start_kst or "", correction or "")):
            return (
                "검증 게이팅 차단: 반박된 일정의 event_start_kst 시각(HH:MM)이 correction에 "
                "없습니다. 정정된 시각으로만 일정을 만들 수 있습니다."
            )
    return None


PRIMARY_SOURCE_TYPES = frozenset({"official", "primary"})


def independence_error(cited: list[str], evidence_meta: dict[str, dict]) -> str | None:
    """None when the cited documents include a primary source or two independent groups."""
    metas = [evidence_meta.get(c) or {} for c in cited]
    if any(m.get("source_type") in PRIMARY_SOURCE_TYPES for m in metas):
        return None
    # A document that passes on another report is not an independent source.
    groups = {m.get("provenance_group") or f"solo:{c}"
              for c, m in zip(cited, metas) if not m.get("derivative")}
    if len(groups) >= 2:
        return None
    return (
        "검증 게이팅 차단: 인용한 근거가 모두 같은 출처군"
        f"({sorted(groups) or '없음'})이거나 다른 보도를 옮긴 2차 문서이고, 1차 출처(공식 발표·원문)가 "
        "없습니다. 같은 원문을 옮긴 문서는 여러 개여도 독립 근거 하나입니다. 1차 출처를 읽어 인용하거나 "
        "실행을 보류하세요."
    )


def _format_ics_datetime(dt_str: str) -> str:
    """Convert 'YYYY-MM-DD HH:MM' into 'YYYYMMDDTHHMM00' for iCalendar."""
    cleaned = re.sub(r"\s+", " ", dt_str.strip())
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y%m%dT%H%M00")
        except ValueError:
            continue
    raise ValueError(f"유효하지 않은 일정 시각 형식: {dt_str!r} ('YYYY-MM-DD HH:MM' 권장)")


class MissionExecutor:
    """Executes verification-gated follow-up missions and writes artifacts."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.events_dir = self.root_dir / "events"
        self.artifacts_dir = self.root_dir / "artifacts"
        self.tracking_file = self.root_dir / "tracking" / "tracking_registry.jsonl"

    def execute_mission(
        self,
        *,
        claim_id: str,
        mission_type: str,
        verdict: str,
        title: str,
        summary: str,
        cited_evidence_ids: list[str] | None = None,
        abstain: bool = False,
        correction: str | None = None,
        distortion_type: str | None = None,
        event_start_kst: str | None = None,
        tracking_condition: str | None = None,
        tracking_queries: list[str] | None = None,
        observed_evidence_ids: set[str] | frozenset[str] | None = None,
        enforce_gate: bool = True,
        evidence_meta: dict[str, dict] | None = None,
        require_independent: bool = False,
    ) -> ToolResult:
        """Run a mission. `enforce_gate=False` exists only for the ungated
        baseline conditions of action-safety experiments."""
        if enforce_gate:
            gate_error = validate_mission_gate(
                mission_type, verdict, abstain=abstain, correction=correction,
                cited_evidence_ids=cited_evidence_ids,
                observed_evidence_ids=observed_evidence_ids,
                event_start_kst=event_start_kst,
                evidence_meta=evidence_meta,
                require_independent=require_independent,
            )
        elif mission_type not in ALL_MISSIONS:
            gate_error = f"알 수 없는 mission_type: {mission_type!r} (허용: {sorted(ALL_MISSIONS)})"
        else:
            gate_error = None
        if gate_error:
            return ToolResult(ToolStatus.INVALID_INPUT, gate_error)

        cited = list(cited_evidence_ids or [])
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if mission_type in ("no_op", "hold_abstain"):
            record = MissionRecord(
                claim_id=claim_id,
                mission_type=mission_type,
                verdict=verdict,
                title=title,
                summary=summary,
                cited_evidence_ids=cited,
                used_correction=correction,
                distortion_type=distortion_type,
                created_at=now_iso,
            )
            return ToolResult(
                ToolStatus.OK,
                f"[{mission_type}] 추가 결과물 생성 없이 종료 기록: {summary}",
                record.to_dict(),
                evidence_ids=cited,
            )

        if mission_type == "event_manager":
            if not event_start_kst:
                return ToolResult(
                    ToolStatus.INVALID_INPUT,
                    "event_manager 미션에는 검증·정정된 일정 시각(event_start_kst, 예: '2024-01-19 22:00')이 필요합니다.",
                )
            try:
                ics_dt = _format_ics_datetime(event_start_kst)
            except ValueError as exc:
                return ToolResult(ToolStatus.INVALID_INPUT, str(exc))

            self.events_dir.mkdir(parents=True, exist_ok=True)
            out_path = self.events_dir / f"{claim_id.lower()}_event.ics"
            ics_body = "\n".join([
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//UOS NLP Team 5//FactCheck Mission Agent//KO",
                "BEGIN:VEVENT",
                f"UID:{claim_id}@uos-nlp-team5",
                f"DTSTART;TZID=Asia/Seoul:{ics_dt}",
                f"SUMMARY:{title}",
                f"DESCRIPTION:검증 판정: {verdict}\\n"
                + (f"정정 반영: {correction}\\n" if correction else "")
                + f"인용 근거: {', '.join(cited)}\\n요약: {summary}",
                "END:VEVENT",
                "END:VCALENDAR",
                "",
            ])
            out_path.write_text(ics_body, encoding="utf-8")
            record = MissionRecord(
                claim_id=claim_id,
                mission_type=mission_type,
                verdict=verdict,
                title=title,
                summary=summary,
                cited_evidence_ids=cited,
                used_correction=correction,
                distortion_type=distortion_type,
                artifact_path=str(out_path),
                created_at=now_iso,
            )
            return ToolResult(
                ToolStatus.OK,
                f"[event_manager] 검증된 일정 파일 생성 완료: {out_path.name} ({event_start_kst} KST)",
                record.to_dict(),
                evidence_ids=cited,
            )

        if mission_type == "continuous_tracking":
            self.tracking_file.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "claim_id": claim_id,
                "verdict_at_registration": verdict,
                "title": title,
                "summary": summary,
                "tracking_condition": tracking_condition or "후속 공식 발표 또는 실측 근거 공개 시 재검증",
                "tracking_queries": list(tracking_queries or []),
                "cited_evidence_ids": cited,
                "created_at": now_iso,
            }
            with self.tracking_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            record = MissionRecord(
                claim_id=claim_id,
                mission_type=mission_type,
                verdict=verdict,
                title=title,
                summary=summary,
                cited_evidence_ids=cited,
                artifact_path=str(self.tracking_file),
                tracking_condition=entry["tracking_condition"],
                created_at=now_iso,
            )
            return ToolResult(
                ToolStatus.OK,
                f"[continuous_tracking] 장기 추적 등록 완료: {claim_id} ({entry['tracking_condition']})",
                record.to_dict(),
                evidence_ids=cited,
            )

        # news_to_artifact, opportunity_execution, app_safe_trial
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.artifacts_dir / f"{claim_id.lower()}_{mission_type}.md"
        md_lines = [
            f"# [{mission_type}] {title}",
            "",
            f"- **사례 ID**: `{claim_id}`",
            f"- **검증 판정**: `{verdict}`",
            f"- **왜곡 유형**: `{distortion_type or 'none'}`",
            f"- **인용 근거 ID**: `{', '.join(cited) if cited else '(없음)'}`",
        ]
        if correction:
            md_lines.append(f"- **반영된 정정 사실**: {correction}")
        md_lines.extend([
            "",
            "## 검증 기반 요약 및 실행 내역",
            "",
            summary,
            "",
        ])
        out_path.write_text("\n".join(md_lines), encoding="utf-8")
        record = MissionRecord(
            claim_id=claim_id,
            mission_type=mission_type,
            verdict=verdict,
            title=title,
            summary=summary,
            cited_evidence_ids=cited,
            used_correction=correction,
            distortion_type=distortion_type,
            artifact_path=str(out_path),
            created_at=now_iso,
        )
        return ToolResult(
            ToolStatus.OK,
            f"[{mission_type}] 검증 아티팩트 생성 완료: {out_path.name}",
            record.to_dict(),
            evidence_ids=cited,
        )
