"""Metrics for Task A.

Every formula here is the one written down in TaskA_지표정의와_평가예시.md and
평가지표_질의응답_산식과근거.md. Three rules are load-bearing and easy to get
wrong, so they are enforced in code and pinned by tests:

1. A zero denominator returns None (reported as N/A), never 0.
2. Recovery and Harm have different denominators and are computed only over
   pairs where both arms produced a valid verdict.
3. Macro-F1 comes from one confusion matrix per condition. Per-claim F1 values
   are not averaged - Macro-F1 is not linear, so averaging it is wrong (Q04).

V, E and T are rubric grades produced by a human or a judge model; this module
only aggregates them. It never grades semantic sufficiency itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from task_a.schema import AgentResult, ExecutionStatus, Verdict

LABELS = (Verdict.SUPPORTED, Verdict.REFUTED, Verdict.NOT_ENOUGH_EVIDENCE)


class Condition:
    """The four initial-evidence conditions from 발표대본 slide 16.

    충분함 / 결정적 정보 누락 / 문서 간 충돌 / 일관되지만 잘못됨.
    """

    SUFFICIENT = "sufficient"
    MISSING = "missing"
    CONFLICT = "conflict"
    MISLEADING = "misleading"
    ALL = (SUFFICIENT, MISSING, CONFLICT, MISLEADING)


class Arm:
    """C0 closed book, C1 fixed corpus, C2 same start plus external fetch."""

    C0 = "C0"
    C1 = "C1"
    C2 = "C2"


@dataclass(frozen=True)
class Graded:
    """One scored episode. `condition` is the evidence condition, `arm` is C0/C1/C2."""

    claim_id: str
    arm: str
    condition: str
    gold_label: Verdict | None
    verdict: Verdict | None
    v: bool = False          # verdict matches gold
    e: bool = False          # cited evidence is valid and sufficient
    t: bool = False          # time and scope match the claim
    abstain: bool = False
    searched_externally: bool = False
    execution_status: ExecutionStatus = ExecutionStatus.OK
    misleading_exposed: bool = False
    misleading_adopted: bool = False
    cost_usd: float = 0.0
    graded_for_label: bool = True   # False for 판정 보류 and other unreviewed gold

    @property
    def grounded(self) -> bool:
        return self.v and self.e and self.t

    @property
    def failed(self) -> bool:
        return self.execution_status != ExecutionStatus.OK

    @property
    def has_valid_verdict(self) -> bool:
        return self.verdict is not None and self.execution_status == ExecutionStatus.OK


def grade(result: AgentResult, gold_label: Verdict | None, *, condition: str, arm: str,
          e: bool = False, t: bool = False, misleading_exposed: bool = False,
          misleading_adopted: bool = False, graded_for_label: bool | None = None) -> Graded:
    """Combine an episode with its rubric grades.

    V is derived from the gold label. E and T must be supplied: a citation
    existing in the log is not evidence of sufficiency (Q36), so this module
    refuses to guess them.
    """
    if graded_for_label is None:
        graded_for_label = gold_label is not None
    v = bool(graded_for_label and result.verdict is not None
             and result.verdict == gold_label)
    return Graded(
        claim_id=result.claim_id, arm=arm, condition=condition, gold_label=gold_label,
        verdict=result.verdict, v=v,
        # A failed or abstaining episode cannot have grounded success.
        e=e and v and not result.abstain, t=t and v and not result.abstain,
        abstain=result.abstain, searched_externally=result.searched_externally,
        execution_status=result.execution_status, misleading_exposed=misleading_exposed,
        misleading_adopted=misleading_adopted, cost_usd=result.usage.cost_usd,
        graded_for_label=graded_for_label)


def _ratio(numerator: int, denominator: int) -> dict | None:
    """Every published ratio carries its counts. N=50 means one case is 2%p."""
    if denominator == 0:
        return None
    return {"numerator": numerator, "denominator": denominator,
            "value": round(numerator / denominator, 6)}


# --- verdict quality -------------------------------------------------------

def grounded_success(rows: Iterable[Graded]) -> dict | None:
    """GSR(c,e) = mean of 1[V and E and T] over every designated attempt.

    Execution failures stay in the denominator and contribute zero, so a system
    cannot improve its score by crashing (TaskA_지표정의와_평가예시.md).
    """
    rows = list(rows)
    return _ratio(sum(1 for r in rows if r.grounded), len(rows))


def accuracy(rows: Iterable[Graded]) -> dict | None:
    rows = [r for r in rows if r.graded_for_label]
    return _ratio(sum(1 for r in rows if r.v), len(rows))


def macro_f1(rows: Iterable[Graded]) -> dict | None:
    """One confusion matrix, then the mean of per-class F1.

    Only episodes with a valid verdict enter the matrix. Abstentions and
    execution failures are therefore excluded from label metrics - report
    `coverage` next to this so the excluded share is visible (Q11).
    """
    rows = [r for r in rows if r.graded_for_label and r.has_valid_verdict]
    if not rows:
        return None
    present = [label for label in LABELS if any(r.gold_label == label for r in rows)]
    per_class = {}
    for label in present:
        tp = sum(1 for r in rows if r.gold_label == label and r.verdict == label)
        fp = sum(1 for r in rows if r.gold_label != label and r.verdict == label)
        fn = sum(1 for r in rows if r.gold_label == label and r.verdict != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class[label.value] = {"precision": round(precision, 6), "recall": round(recall, 6),
                                  "f1": round(f1, 6), "support": tp + fn}
    macro = sum(c["f1"] for c in per_class.values()) / len(per_class)
    return {"macro_f1": round(macro, 6), "per_class": per_class,
            "graded": len(rows), "labels_included": [label.value for label in present]}


def coverage(rows: Iterable[Graded]) -> dict | None:
    """Share of attempts that produced a usable verdict. Pairs with macro_f1."""
    rows = list(rows)
    return _ratio(sum(1 for r in rows if r.has_valid_verdict), len(rows))


def failure_rate(rows: Iterable[Graded]) -> dict | None:
    rows = list(rows)
    return _ratio(sum(1 for r in rows if r.failed), len(rows))


def abstain_rate(rows: Iterable[Graded]) -> dict | None:
    rows = list(rows)
    return _ratio(sum(1 for r in rows if r.abstain), len(rows))


# --- robustness across evidence conditions ---------------------------------

def degradation(baseline: Iterable[Graded], variant: Iterable[Graded]) -> dict | None:
    """D_e = GSR(C1, sufficient) - GSR(C1, e), in percentage points.

    Negative means the variant scored higher than the sufficient condition.
    """
    base = grounded_success(baseline)
    var = grounded_success(variant)
    if base is None or var is None:
        return None
    gap = base["value"] - var["value"]
    return {"baseline_gsr": base["value"], "variant_gsr": var["value"],
            "drop_percentage_points": round(gap * 100, 4),
            "relative_drop": round(gap / base["value"], 6) if base["value"] else None,
            "baseline": base, "variant": var}


# --- C1 -> C2 transitions --------------------------------------------------

def transitions(c1: Sequence[Graded], c2: Sequence[Graded], *,
                on: str = "v") -> dict:
    """Recovery and Harm. The denominators differ; that is the point (Q24).

    Only claims where both arms produced a valid verdict are paired. Unpaired
    counts are reported so the pair loss is never hidden. `on='v'` grades the
    transition by verdict correctness, `on='grounded'` by grounded success.
    """
    def ok(row: Graded) -> bool:
        return row.v if on == "v" else row.grounded

    first = {r.claim_id: r for r in c1}
    second = {r.claim_id: r for r in c2}
    shared = [cid for cid in first if cid in second]
    pairs = [cid for cid in shared
             if first[cid].has_valid_verdict and second[cid].has_valid_verdict]

    wrong_then_right = [cid for cid in pairs if not ok(first[cid]) and ok(second[cid])]
    right_then_wrong = [cid for cid in pairs if ok(first[cid]) and not ok(second[cid])]
    initially_wrong = [cid for cid in pairs if not ok(first[cid])]
    initially_right = [cid for cid in pairs if ok(first[cid])]

    recovery = _ratio(len(wrong_then_right), len(initially_wrong))
    harm = _ratio(len(right_then_wrong), len(initially_right))
    net = None
    if pairs:
        net = round((len(wrong_then_right) - len(right_then_wrong)) / len(pairs), 6)

    extra_cost = sum(second[cid].cost_usd for cid in pairs) - sum(first[cid].cost_usd for cid in pairs)
    return {
        "basis": on,
        "pairs": len(pairs),
        "claims_in_both_arms": len(shared),
        "unpaired_dropped": len(shared) - len(pairs),
        "recovery": recovery,
        "harm": harm,
        "net_accuracy_change": net,
        "recovered_claim_ids": wrong_then_right,
        "harmed_claim_ids": right_then_wrong,
        "extra_cost_usd": round(extra_cost, 6),
        "cost_per_recovery": (round(extra_cost / len(wrong_then_right), 6)
                              if wrong_then_right else None),
    }


# --- verification behaviour ------------------------------------------------

def external_search_rate(rows: Iterable[Graded]) -> dict | None:
    """S_e. A case counts once however many searches it made."""
    rows = list(rows)
    return _ratio(sum(1 for r in rows if r.searched_externally), len(rows))


def exposure_rate(rows: Iterable[Graded]) -> dict | None:
    """Exposure = misleading content reached the model input / cases where it was planted.

    The denominator is the planted cases only. A document sitting in the corpus
    but never rendered into the prompt is not exposure (Q22), and counting it as
    such would credit the retriever with a defence the model never had to make.
    """
    planted = [r for r in rows if r.condition == Condition.MISLEADING]
    return _ratio(sum(1 for r in planted if r.misleading_exposed), len(planted))


def false_adoption_rate(rows: Iterable[Graded]) -> dict | None:
    """Conditional on exposure. Citing a false document to refute it is not
    adoption, and that distinction is made upstream when setting the flag."""
    exposed = [r for r in rows if r.misleading_exposed]
    return _ratio(sum(1 for r in exposed if r.misleading_adopted), len(exposed))


# --- evidence quality ------------------------------------------------------

def recall_at_k(retrieved_ids: Sequence[str], gold_ids: Sequence[str]) -> dict | None:
    """Recall@k = |R@k ∩ G| / |G|. Empty gold is N/A, not a perfect score.

    `retrieved_ids` is the ranked top-k list itself, so k is its length. A
    misleading document that is topically relevant is still not valid gold (Q20).
    """
    gold = set(gold_ids)
    if not gold:
        return None
    return _ratio(len(set(retrieved_ids) & gold), len(gold))


def precision_at_k(retrieved_ids: Sequence[str], gold_ids: Sequence[str], k: int) -> dict | None:
    """Precision@k keeps k in the denominator; short result sets are penalised.

    Dividing by the number actually returned is a different metric and must be
    labelled as such (Q20).
    """
    if k <= 0:
        return None
    hits = len(set(retrieved_ids[:k]) & set(gold_ids))
    return {"numerator": hits, "denominator": k, "value": round(hits / k, 6),
            "returned": len(retrieved_ids),
            "returned_set_precision": (round(hits / len(retrieved_ids), 6)
                                       if retrieved_ids else None)}


def complete_set_hit_at_k(retrieved_ids: Sequence[str],
                          sufficient_sets: Sequence[Sequence[str]], k: int) -> int | None:
    """1 if any single sufficient set is fully inside the top-k."""
    if not sufficient_sets:
        return None
    top = set(retrieved_ids[:k])
    return int(any(set(s) <= top for s in sufficient_sets))


# --- reporting -------------------------------------------------------------

@dataclass
class ConditionReport:
    arm: str
    condition: str
    rows: list[Graded] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "arm": self.arm,
            "condition": self.condition,
            "attempts": len(self.rows),
            "unreviewed_gold_excluded": sum(1 for r in self.rows if not r.graded_for_label),
            "gsr": grounded_success(self.rows),
            "accuracy": accuracy(self.rows),
            "macro_f1": macro_f1(self.rows),
            "coverage": coverage(self.rows),
            "failure_rate": failure_rate(self.rows),
            "abstain_rate": abstain_rate(self.rows),
            "external_search_rate": external_search_rate(self.rows),
            "exposure_rate": exposure_rate(self.rows),
            "false_adoption_rate": false_adoption_rate(self.rows),
            "cost_usd": round(sum(r.cost_usd for r in self.rows), 6),
        }


def report(rows: Iterable[Graded]) -> dict:
    """The per-condition table results/exp-NNN/summary.md is written from."""
    rows = list(rows)
    grouped: dict[tuple[str, str], list[Graded]] = {}
    for row in rows:
        grouped.setdefault((row.arm, row.condition), []).append(row)
    return {
        "conditions": [ConditionReport(arm, condition, grouped[(arm, condition)]).as_dict()
                       for arm, condition in sorted(grouped)],
        "total_episodes": len(rows),
    }
