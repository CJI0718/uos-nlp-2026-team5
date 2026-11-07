"""The scorer is checked against the worked example the team already computed.

TaskA_지표정의와_평가예시.md walks through ten virtual cases by hand:
C1 under a variant condition gets 6 verdicts right and 4 wrong, 5 of the
correct ones also have sufficient evidence; C2 recovers 2 and harms 1.
Every number below is that document's number. If the implementation disagrees,
the implementation is wrong - Q39 asks for exactly this comparison before any
real result is produced.
"""

from __future__ import annotations

import pytest

from task_a.schema import (
    AgentResult, ExecutionStatus, ToolEvent, ToolStatus, Usage, Verdict,
)
from task_a.scorer import (
    Arm, Condition, Graded, abstain_rate, accuracy, complete_set_hit_at_k, coverage,
    degradation, external_search_rate, exposure_rate, failure_rate, false_adoption_rate,
    grade, grounded_success, macro_f1, precision_at_k, recall_at_k, report, transitions,
)

SUP = Verdict.SUPPORTED
REF = Verdict.REFUTED
NEI = Verdict.NOT_ENOUGH_EVIDENCE

# scorer._ratio rounds to 6 decimals, which can exceed approx's default
# relative tolerance on small values (round(1/6, 6) differs by 3.3e-7).
close = lambda value: pytest.approx(value, abs=1e-6)  # noqa: E731


def row(claim_id, *, arm=Arm.C1, condition=Condition.MISLEADING, gold=REF, verdict=REF,
        v=None, e=False, t=False, external=False, exposed=False, adopted=False,
        cost=0.0, status=ExecutionStatus.OK, graded_for_label=True, abstain=False):
    return Graded(claim_id=claim_id, arm=arm, condition=condition, gold_label=gold,
                  verdict=verdict, v=(verdict == gold) if v is None else v, e=e, t=t,
                  abstain=abstain, searched_externally=external, execution_status=status,
                  misleading_exposed=exposed, misleading_adopted=adopted, cost_usd=cost,
                  graded_for_label=graded_for_label)


def c1_variant():
    """Ten cases: 6 correct verdicts, 4 wrong; 5 of the correct ones are grounded.

    Exposure 7/10 and adoption 3/7 follow the same document's numbers.
    """
    rows = [row(f"C{i:02d}", e=True, t=True, exposed=True, adopted=i <= 3)
            for i in range(1, 6)]                       # grounded and correct
    rows.append(row("C06", exposed=True))                # correct verdict, evidence fails
    rows.append(row("C07", verdict=SUP, exposed=True))   # wrong, and exposed
    rows += [row(f"C{i:02d}", verdict=SUP) for i in range(8, 11)]   # wrong, not exposed
    return rows


def c2_variant():
    """C1's four wrong cases with C07 and C08 recovered, and C01 harmed.

    Accuracy becomes 6 + 2 - 1 = 7 of 10. Each episode costs 0.10 more than C1,
    so the extra spend over the pair is 1.00 and cost per recovery is 0.50.
    """
    rows = []
    for i in range(1, 11):
        claim_id = f"C{i:02d}"
        if claim_id == "C01":                            # harmed
            rows.append(row(claim_id, arm=Arm.C2, verdict=SUP, external=True,
                            exposed=True, adopted=True, cost=0.1))
        elif claim_id in ("C07", "C08"):                 # recovered
            rows.append(row(claim_id, arm=Arm.C2, e=True, t=True, external=True,
                            exposed=True, cost=0.1))
        elif claim_id in ("C02", "C03", "C04", "C05"):
            rows.append(row(claim_id, arm=Arm.C2, e=True, t=True, cost=0.1))
        elif claim_id == "C06":
            rows.append(row(claim_id, arm=Arm.C2, external=True, cost=0.1))
        else:                                            # C09, C10 still wrong
            rows.append(row(claim_id, arm=Arm.C2, verdict=SUP, external=True, cost=0.1))
    return rows


def c1_sufficient():
    """The same ten claims with valid, sufficient evidence: 8 grounded."""
    return [row(f"C{i:02d}", condition=Condition.SUFFICIENT, e=True, t=True)
            for i in range(1, 9)] + [
        row("C09", condition=Condition.SUFFICIENT),
        row("C10", condition=Condition.SUFFICIENT, verdict=SUP)]


# --- the worked example ----------------------------------------------------

def test_gsr_is_five_of_ten():
    result = grounded_success(c1_variant())

    assert result == {"numerator": 5, "denominator": 10, "value": 0.5}


def test_accuracy_is_six_of_ten_before_verification():
    assert accuracy(c1_variant())["value"] == 0.6


def test_accuracy_is_seven_of_ten_after_verification():
    assert accuracy(c2_variant())["value"] == 0.7


def test_degradation_is_thirty_percentage_points():
    """D_e = GSR(C1, sufficient) - GSR(C1, e) = 80% - 50%."""
    result = degradation(c1_sufficient(), c1_variant())

    assert result["baseline_gsr"] == 0.8
    assert result["variant_gsr"] == 0.5
    assert result["drop_percentage_points"] == 30.0
    assert result["relative_drop"] == pytest.approx(0.375)


def test_recovery_is_two_of_four():
    assert transitions(c1_variant(), c2_variant())["recovery"] == {
        "numerator": 2, "denominator": 4, "value": 0.5}


def test_harm_is_one_of_six():
    """The harm denominator is the initially-correct cases, not all cases."""
    assert transitions(c1_variant(), c2_variant())["harm"] == {
        "numerator": 1, "denominator": 6, "value": close(1 / 6)}


def test_net_change_is_ten_percentage_points():
    assert transitions(c1_variant(), c2_variant())["net_accuracy_change"] == 0.1


def test_cost_per_recovery_is_fifty_cents():
    result = transitions(c1_variant(), c2_variant())

    assert result["extra_cost_usd"] == pytest.approx(1.0)
    assert result["cost_per_recovery"] == pytest.approx(0.5)


def test_transition_basis_can_be_grounded_success():
    """The same transitions on the grounded basis give different numbers."""
    result = transitions(c1_variant(), c2_variant(), on="grounded")

    assert result["basis"] == "grounded"
    assert result["recovery"]["denominator"] == 5


def test_external_search_rate_is_six_of_ten():
    assert external_search_rate(c2_variant()) == {
        "numerator": 6, "denominator": 10, "value": 0.6}


def test_exposure_is_seven_of_ten_planted():
    assert exposure_rate(c1_variant()) == {"numerator": 7, "denominator": 10, "value": 0.7}


def test_false_adoption_is_conditional_on_exposure():
    """3 of the 7 exposed, not 3 of all 10."""
    assert false_adoption_rate(c1_variant()) == {
        "numerator": 3, "denominator": 7, "value": close(3 / 7)}


def test_exposure_ignores_unplanted_conditions():
    rows = c1_variant() + c1_sufficient()

    assert exposure_rate(rows)["denominator"] == 10


# --- zero denominators are N/A, never zero ---------------------------------

@pytest.mark.parametrize("fn", [grounded_success, accuracy, macro_f1, coverage,
                                failure_rate, abstain_rate, external_search_rate,
                                exposure_rate, false_adoption_rate])
def test_empty_input_is_none_not_zero(fn):
    assert fn([]) is None


def test_harm_with_no_initially_correct_cases_is_na():
    wrong = [row("C01", verdict=SUP)]
    still_wrong = [row("C01", arm=Arm.C2, verdict=SUP)]

    assert transitions(wrong, still_wrong)["harm"] is None


def test_cost_per_recovery_with_no_recovery_is_na():
    same = [row("C01", e=True, t=True)]
    assert transitions(same, [row("C01", arm=Arm.C2, e=True, t=True)])["cost_per_recovery"] is None


def test_recall_with_empty_gold_is_na():
    """No gold evidence is not a perfect recall."""
    assert recall_at_k(["EV1"], []) is None


# --- failures stay in the denominator --------------------------------------

def test_execution_failure_counts_as_zero_success_not_as_missing():
    rows = [row("C01", e=True, t=True),
            row("C02", verdict=None, v=False, status=ExecutionStatus.TIMEOUT)]

    assert grounded_success(rows) == {"numerator": 1, "denominator": 2, "value": 0.5}
    assert failure_rate(rows)["value"] == 0.5


def test_unpaired_episodes_are_reported_not_silently_dropped():
    c1 = [row("C01", e=True, t=True), row("C02", verdict=SUP)]
    c2 = [row("C01", arm=Arm.C2, e=True, t=True)]

    result = transitions(c1, c2)

    assert result["claims_in_both_arms"] == 1
    assert result["pairs"] == 1
    assert result["unpaired_dropped"] == 0


def test_episodes_without_a_valid_verdict_are_excluded_from_pairs():
    c1 = [row("C01", verdict=SUP), row("C02", verdict=None, status=ExecutionStatus.PARSE_ERROR)]
    c2 = [row("C01", arm=Arm.C2), row("C02", arm=Arm.C2)]

    result = transitions(c1, c2)

    assert result["claims_in_both_arms"] == 2
    assert result["pairs"] == 1
    assert result["unpaired_dropped"] == 1


def test_abstention_is_not_counted_as_recovery():
    c1 = [row("C01", verdict=SUP)]
    c2 = [row("C01", arm=Arm.C2, verdict=None, abstain=True)]

    result = transitions(c1, c2)

    assert result["pairs"] == 0
    assert result["recovery"] is None


# --- macro F1 --------------------------------------------------------------

def test_macro_f1_uses_one_confusion_matrix():
    rows = [row("C01", gold=SUP, verdict=SUP), row("C02", gold=SUP, verdict=SUP),
            row("C03", gold=REF, verdict=REF), row("C04", gold=REF, verdict=SUP)]

    result = macro_f1(rows)

    assert result["per_class"]["supported"]["support"] == 2
    assert result["per_class"]["refuted"]["support"] == 2
    assert result["per_class"]["supported"]["recall"] == 1.0
    assert result["per_class"]["supported"]["precision"] == pytest.approx(2 / 3)
    assert result["per_class"]["refuted"]["recall"] == 0.5
    # supported F1 = 2*(2/3)*1 / (2/3 + 1) = 0.8; refuted F1 = 2*1*0.5 / 1.5 = 2/3
    assert result["per_class"]["supported"]["f1"] == pytest.approx(0.8)
    assert result["per_class"]["refuted"]["f1"] == pytest.approx(2 / 3)
    assert result["macro_f1"] == pytest.approx((0.8 + 2 / 3) / 2)


def test_macro_f1_averages_classes_not_claims():
    """Averaging per-claim F1 is wrong because Macro-F1 is not linear (Q04)."""
    imbalanced = ([row(f"S{i}", gold=SUP, verdict=SUP) for i in range(9)]
                  + [row("R0", gold=REF, verdict=SUP)])

    result = macro_f1(imbalanced)

    assert result["macro_f1"] < accuracy(imbalanced)["value"]
    assert result["per_class"]["refuted"]["f1"] == 0.0


def test_absent_class_is_not_averaged_in():
    rows = [row("C01", gold=SUP, verdict=SUP), row("C02", gold=REF, verdict=REF)]

    assert macro_f1(rows)["labels_included"] == ["supported", "refuted"]


def test_coverage_reports_what_label_metrics_excluded():
    rows = [row("C01"), row("C02", verdict=None, status=ExecutionStatus.TIMEOUT)]

    assert coverage(rows)["value"] == 0.5
    assert accuracy(rows)["denominator"] == 2


def test_unreviewed_gold_is_excluded_from_label_metrics():
    """FC038 is 판정 보류. It is a review state, not a fourth label."""
    rows = [row("C01"), row("FC038", gold=None, verdict=SUP, graded_for_label=False)]

    assert accuracy(rows)["denominator"] == 1
    assert macro_f1(rows)["graded"] == 1
    assert grounded_success(rows)["denominator"] == 2


def test_abstain_rate_is_tracked_separately_from_nei():
    rows = [row("C01", gold=NEI, verdict=NEI),
            row("C02", gold=SUP, verdict=None, abstain=True)]

    assert abstain_rate(rows)["value"] == 0.5


# --- retrieval metrics -----------------------------------------------------

def test_recall_and_precision_denominators():
    """gold 3, top-5 returns 2 relevant: recall 2/3, precision 2/5."""
    gold = ["G1", "G2", "G3"]
    retrieved = ["G1", "X1", "G2", "X2", "X3"]

    assert recall_at_k(retrieved, gold) == {"numerator": 2, "denominator": 3,
                                            "value": pytest.approx(2 / 3)}
    precision = precision_at_k(retrieved, gold, k=5)
    assert precision["value"] == 0.4
    assert precision["denominator"] == 5


def test_precision_keeps_k_in_the_denominator_when_fewer_are_returned():
    """Standard P@k penalises a short result set; returned-set precision does not.

    Both are reported, under different names, so they cannot be confused (Q20).
    """
    precision = precision_at_k(["G1", "G2"], ["G1", "G2", "G3"], k=5)

    assert precision["value"] == 0.4
    assert precision["returned_set_precision"] == 1.0


def test_complete_set_hit_accepts_any_one_sufficient_set():
    retrieved = ["A1", "B1", "X"]
    sets = [["A1", "A2"], ["B1"]]

    assert complete_set_hit_at_k(retrieved, sets, k=3) == 1
    assert complete_set_hit_at_k(retrieved, [["A1", "A2"]], k=3) == 0
    assert complete_set_hit_at_k(retrieved, [], k=3) is None


# --- grade() ---------------------------------------------------------------

def result(verdict=REF, abstain=False, status=ExecutionStatus.OK, external=False,
           cost=0.0, claim_id="FC002"):
    events = [ToolEvent(step=1, tool="search_web", args={}, status=ToolStatus.OK,
                        observation_chars=10, elapsed_ms=1, external=external)] if external else []
    return AgentResult(claim_id=claim_id, verdict=verdict, abstain=abstain,
                       cited_evidence_ids=["EV1"], justification="j", correction=None,
                       stop_reason="evidence_sufficient", execution_status=status,
                       events=events, usage=Usage(cost_usd=cost))


def test_grade_derives_v_from_gold():
    assert grade(result(REF), REF, condition=Condition.SUFFICIENT, arm=Arm.C1).v is True
    assert grade(result(SUP), REF, condition=Condition.SUFFICIENT, arm=Arm.C1).v is False


def test_grade_refuses_to_infer_e_and_t():
    """A citation in the log is not evidence of sufficiency (Q36)."""
    graded = grade(result(REF), REF, condition=Condition.SUFFICIENT, arm=Arm.C1)

    assert graded.v is True
    assert graded.e is False and graded.t is False
    assert graded.grounded is False


def test_grounded_success_requires_all_three():
    graded = grade(result(REF), REF, condition=Condition.SUFFICIENT, arm=Arm.C1, e=True, t=True)

    assert graded.grounded is True


def test_abstention_cannot_be_grounded_success():
    graded = grade(result(None, abstain=True), REF, condition=Condition.SUFFICIENT,
                   arm=Arm.C1, e=True, t=True)

    assert graded.v is False
    assert graded.grounded is False
    assert graded.abstain is True


def test_grade_marks_unreviewed_gold():
    graded = grade(result(SUP), None, condition=Condition.SUFFICIENT, arm=Arm.C1)

    assert graded.graded_for_label is False
    assert graded.v is False


# --- report ----------------------------------------------------------------

def test_report_groups_by_arm_and_condition():
    rows = c1_variant() + c2_variant() + c1_sufficient()

    summary = report(rows)

    assert summary["total_episodes"] == 30
    keys = {(c["arm"], c["condition"]) for c in summary["conditions"]}
    assert keys == {(Arm.C1, Condition.MISLEADING), (Arm.C2, Condition.MISLEADING),
                    (Arm.C1, Condition.SUFFICIENT)}

    c1_row = next(c for c in summary["conditions"]
                  if c["arm"] == Arm.C1 and c["condition"] == Condition.MISLEADING)
    assert c1_row["gsr"]["value"] == 0.5
    assert c1_row["attempts"] == 10
    assert c1_row["exposure_rate"]["value"] == 0.7
    assert c1_row["cost_usd"] == 0.0
