"""Scoring command. Separate from the runner so it can read gold.

The runner process never opens gold.jsonl; this one does, and that separation is
the leakage control. Metrics that need no human judgement are computed from the
run log alone. Metrics that do (GSR's E and T, exposure, adoption) are refused
rather than defaulted, because a GSR of zero produced by missing grades is
indistinguishable from a GSR of zero produced by a failing system.
"""

from __future__ import annotations

from pathlib import Path

from task_a.schema import ExecutionStatus, Verdict, read_jsonl
from task_a.scorer import (
    Arm, Graded, accuracy, abstain_rate, coverage, degradation, external_search_rate,
    failure_rate, macro_f1, report, transitions,
)

NEEDS_GRADING = ("gsr", "degradation", "exposure_rate", "false_adoption_rate")


def load_gold(path: str | Path) -> dict[str, Verdict | None]:
    """Map claim_id to its label. 판정 보류 stays None and is excluded, not relabelled."""
    out = {}
    for row in read_jsonl(path):
        label = row.get("label")
        out[row["claim_id"]] = Verdict(label) if label else None
    return out


def load_grades(path: str | Path | None) -> dict[tuple[str, str, str], dict]:
    """Human or judge rubric grades, keyed by (claim_id, arm, condition).

    Expected row shape:
        {"claim_id": ..., "arm": "C1", "condition": "misleading",
         "e": true, "t": true,
         "misleading_exposed": true, "misleading_adopted": false,
         "annotator": ..., "rubric_version": ...}
    """
    if path is None or not Path(path).exists():
        return {}
    return {(r["claim_id"], r["arm"], r["condition"]): r for r in read_jsonl(path)}


def to_graded(rows: list[dict], gold: dict[str, Verdict | None],
              grades: dict[tuple[str, str, str], dict] | None = None) -> list[Graded]:
    grades = grades or {}
    out = []
    for row in rows:
        config, result = row["config"], row["result"]
        claim_id = result["claim_id"]
        label = gold.get(claim_id)
        grade = grades.get((claim_id, config["arm"], config["condition"]), {})
        verdict = Verdict(result["verdict"]) if result.get("verdict") else None
        out.append(Graded(
            claim_id=claim_id, arm=config["arm"], condition=config["condition"],
            gold_label=label, verdict=verdict,
            v=bool(label is not None and verdict == label),
            e=bool(grade.get("e", False)), t=bool(grade.get("t", False)),
            abstain=bool(result.get("abstain", False)),
            searched_externally=any(ev.get("external") for ev in result.get("events", [])),
            execution_status=ExecutionStatus(result["execution_status"]),
            misleading_exposed=bool(grade.get("misleading_exposed", False)),
            misleading_adopted=bool(grade.get("misleading_adopted", False)),
            cost_usd=result.get("usage", {}).get("cost_usd", 0.0),
            graded_for_label=label is not None))
    return out


def score_run(rows: list[dict], gold: dict[str, Verdict | None],
              grades: dict | None = None) -> dict:
    """Metrics for one arm/condition, with ungraded ones refused rather than faked."""
    graded = to_graded(rows, gold, grades)
    summary = report(graded)
    has_grades = bool(grades)

    for condition in summary["conditions"]:
        rows_for = [g for g in graded
                    if g.arm == condition["arm"] and g.condition == condition["condition"]]
        if not has_grades:
            for key in ("gsr", "exposure_rate", "false_adoption_rate"):
                condition[key] = None
            condition["requires_grading"] = list(NEEDS_GRADING)
        else:
            condition.pop("requires_grading", None)
        condition["graded_episodes"] = sum(1 for g in rows_for if g.graded_for_label)

    summary["grading"] = {
        "e_t_supplied": has_grades,
        "grade_rows": len(grades or {}),
        "note": ("E와 T는 사람 또는 judge rubric 결과다. 미공급 시 GSR·노출·채택은 "
                 "0이 아니라 계산 불가로 표시한다." if not has_grades else
                 "rubric 등급이 공급되어 GSR·노출·채택을 계산했다."),
    }
    return summary


def score_transition(c1_rows: list[dict], c2_rows: list[dict],
                     gold: dict[str, Verdict | None], grades: dict | None = None,
                     *, on: str = "v") -> dict:
    """Recovery and harm between two arms on the same claims."""
    c1 = [g for g in to_graded(c1_rows, gold, grades) if g.arm == Arm.C1]
    c2 = [g for g in to_graded(c2_rows, gold, grades) if g.arm == Arm.C2]
    result = transitions(c1, c2, on=on)
    result["c1_episodes"] = len(c1)
    result["c2_episodes"] = len(c2)
    return result


def score_degradation(sufficient_rows: list[dict], variant_rows: list[dict],
                      gold: dict[str, Verdict | None], grades: dict) -> dict | None:
    """D_e needs graded rows on both sides; without them it is not computable."""
    if not grades:
        return None
    base = to_graded(sufficient_rows, gold, grades)
    variant = to_graded(variant_rows, gold, grades)
    return degradation(base, variant)


def ungraded_metrics(rows: list[dict], gold: dict[str, Verdict | None]) -> dict:
    """Everything computable from the log alone, with no human in the loop."""
    graded = to_graded(rows, gold)
    return {"accuracy": accuracy(graded), "macro_f1": macro_f1(graded),
            "coverage": coverage(graded), "failure_rate": failure_rate(graded),
            "abstain_rate": abstain_rate(graded),
            "external_search_rate": external_search_rate(graded),
            "episodes": len(graded)}
