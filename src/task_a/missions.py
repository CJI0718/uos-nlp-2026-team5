"""Verification-Gated Mission & Continuous Tracking Executor.

Implements STEP 3~4 and Continuous Claim Tracking from
`docs/research/fact_checking/README.md` section 8, connected directly to Task A
verification results:

1. Verification Gate ('Garbage In, Action Out' prevention):
   - Actionable missions (`event_manager`, `news_to_artifact`,
     `opportunity_execution`, `app_safe_trial`) CANNOT be executed when the
     claim is unverified (`not_enough_evidence` or `abstain=True`).
   - When a claim is `refuted`, an actionable mission MUST use the verified
     `correction` (e.g., corrected KST time or corrected figure) rather than
     propagating the distorted claim text.
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


def validate_mission_gate(
    mission_type: str,
    verdict: str | Verdict | None,
    *,
    abstain: bool = False,
    correction: str | None = None,
) -> str | None:
    """Return an error reason if the mission violates the verification gate."""
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
        if verdict_val == Verdict.REFUTED.value and not (correction and correction.strip()):
            return (
                f"검증 게이팅 차단: 반박(refuted)된 주장에 대해 실행형 미션({mission_type})을 "
                f"수행하려면 반드시 정정된 사실(correction)을 함께 제공해야 합니다."
            )
    return None


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
    ) -> ToolResult:
        gate_error = validate_mission_gate(
            mission_type, verdict, abstain=abstain, correction=correction
        )
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
