"""Runner and scorer: dry-run safety, resume, budget, and the gold boundary."""

from __future__ import annotations

import json

import pytest

import task_a.runner as runner_module
from task_a.runner import RunSpec, execute, load_claims, load_corpus
from task_a.schema import Claim, Verdict, write_jsonl
from task_a.score_run import load_gold, score_run, score_transition, to_graded, ungraded_metrics
from task_a.scorer import Arm

FC002 = {"claim_id": "FC002",
         "text": "미국 비전 프로 사전예약은 2024년 1월 19일 한국시간 오전 5시에 시작한다.",
         "family_id": "solo_FC002", "language": "ko",
         "source_url": "https://v.daum.net/v/2vbOybyj9G", "source_type": "한국어 기사·정보글",
         "claim_date": "2024-01-09", "target_period": "2024-01-19 사전예약 개시",
         "evidence_cutoff": "2026-10-30T01:37:43+09:00", "input_body": None}
FC004 = {**FC002, "claim_id": "FC004", "text": "2024년 노벨문학상 수상자는 한강이다.",
         "family_id": "solo_FC004"}

CORPUS_ROW = {"evidence_id": "EV1", "title": "Apple Newsroom",
              "text": "Pre-orders begin January 19 at 5:00 a.m. PST",
              "source_url": "https://www.apple.com/newsroom/", "document_validity": "valid"}

GOLD = [{"claim_id": "FC002", "label": "refuted", "rationale": "r", "review_status": "draft"},
        {"claim_id": "FC004", "label": "supported", "rationale": "r", "review_status": "draft"},
        {"claim_id": "FC038", "label": None, "rationale": "r", "review_status": "pending"}]


@pytest.fixture
def workspace(tmp_path):
    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [FC002, FC004])
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [CORPUS_ROW])
    gold = tmp_path / "gold.jsonl"
    write_jsonl(gold, GOLD)
    return {"claims": claims, "corpus": corpus, "gold": gold, "out": tmp_path / "run.jsonl",
            "cache": tmp_path / "cache.jsonl"}


def spec(workspace, **overrides) -> RunSpec:
    base = dict(run_id="exp-test", arm="C1", policy="react", out_path=workspace["out"],
                cache_path=workspace["cache"], tokenizer="bigram")
    base.update(overrides)
    return RunSpec(**base)


# --- loading ---------------------------------------------------------------

def test_load_claims_reads_only_agent_visible_fields(workspace):
    claims = load_claims(workspace["claims"], spec(workspace))

    assert [c.claim_id for c in claims] == ["FC002", "FC004"]
    assert isinstance(claims[0], Claim)


def test_limit_and_only_filter_claims(workspace):
    assert len(load_claims(workspace["claims"], spec(workspace, limit=1))) == 1
    only = load_claims(workspace["claims"], spec(workspace, only=["FC004"]))
    assert [c.claim_id for c in only] == ["FC004"]


def test_load_corpus_skips_unknown_fields(workspace):
    units = load_corpus(workspace["corpus"])

    assert units[0].evidence_id == "EV1"
    assert load_corpus(None) == []


# --- dry run ---------------------------------------------------------------

def test_dry_run_executes_and_logs_without_a_provider(workspace):
    outcome = execute(spec(workspace), load_claims(workspace["claims"], spec(workspace)),
                      load_corpus(workspace["corpus"]))

    assert outcome.executed == 2
    assert outcome.cost_usd == 0.0
    assert len(outcome.results) == 2
    rows = [json.loads(line) for line in
            workspace["out"].read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["config"]["arm"] == "C1"
    assert rows[0]["config"]["policy"] == "react"
    assert rows[0]["config"]["model_id"] == "dry-run-scripted"


def test_dry_run_is_labelled_so_it_cannot_be_mistaken_for_a_result(workspace):
    outcome = execute(spec(workspace), load_claims(workspace["claims"], spec(workspace)),
                      load_corpus(workspace["corpus"]))

    assert outcome.results[0].justification == "dry-run: 실모델 미연결"
    assert outcome.results[0].abstain is True


def test_resume_does_not_rerun_completed_episodes(workspace):
    """A restart must not re-spend budget on finished episodes."""
    claims = load_claims(workspace["claims"], spec(workspace))
    execute(spec(workspace), claims, load_corpus(workspace["corpus"]))

    second = execute(spec(workspace), claims, load_corpus(workspace["corpus"]))

    assert second.executed == 0
    assert second.skipped == 2
    lines = workspace["out"].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_a_different_seed_is_new_work(workspace):
    claims = load_claims(workspace["claims"], spec(workspace))
    execute(spec(workspace), claims, load_corpus(workspace["corpus"]))

    other = execute(spec(workspace, seed=1), claims, load_corpus(workspace["corpus"]))

    assert other.executed == 2


def test_budget_cap_stops_the_run(workspace):
    """The cap is checked between episodes, so it can be exceeded by one."""
    claims = load_claims(workspace["claims"], spec(workspace))
    outcome = execute(spec(workspace, budget_usd=0.0), claims, load_corpus(workspace["corpus"]))

    assert outcome.executed == 1
    assert outcome.stopped_reason is not None
    assert "예산 상한" in outcome.stopped_reason


# --- arm construction ------------------------------------------------------

def test_c0_gets_an_empty_corpus(workspace):
    """C0 is closed book: no corpus, so search_evidence cannot return anything."""
    backend = runner_module.build_backend(spec(workspace, arm="C0"),
                                          load_corpus(workspace["corpus"]))

    assert backend.search_corpus("Vision Pro", 5) == []


def test_c1_has_no_external_access(workspace):
    backend = runner_module.build_backend(spec(workspace, arm="C1"),
                                          load_corpus(workspace["corpus"]))

    assert backend.web is None
    with pytest.raises(PermissionError, match="C1 조건"):
        backend.web_search("anything", 5)


def test_c2_accepts_a_provider(workspace):
    class StubWeb:
        def search(self, query, top_k):
            return [{"title": "t", "url": "https://x", "snippet": "s"}]

        def fetch(self, url):
            return "body"

    backend = runner_module.build_backend(spec(workspace, arm="C2"),
                                          load_corpus(workspace["corpus"]), web=StubWeb())

    assert backend.web is not None
    assert backend.web_search("q", 5)


def test_closed_book_policy_makes_no_tool_calls_even_with_a_corpus(workspace):
    claims = load_claims(workspace["claims"], spec(workspace))
    outcome = execute(spec(workspace, arm="C0", policy="closed_book"), claims,
                      load_corpus(workspace["corpus"]))

    assert all(r.events == [] for r in outcome.results)
    assert all(r.abstain for r in outcome.results)


# --- the gold boundary -----------------------------------------------------

def test_runner_never_opens_the_gold_file(workspace, monkeypatch):
    """Structural leakage control: the executing process cannot read the answers.

    Gold lives in this repository, so the boundary has to be which file the
    runner opens, not a promise to be careful. Spying on the loader is stronger
    than grepping the source, which would fail on the word appearing in prose.
    """
    opened: list[str] = []
    real_read = runner_module.read_jsonl

    def spy(path):
        opened.append(str(path))
        return real_read(path)

    monkeypatch.setattr(runner_module, "read_jsonl", spy)

    claims = load_claims(workspace["claims"], spec(workspace))
    corpus = load_corpus(workspace["corpus"])
    execute(spec(workspace), claims, corpus)

    assert opened, "sanity: the spy saw no reads at all"
    assert not any("gold" in path for path in opened), opened
    assert not hasattr(runner_module, "load_gold")


def test_dry_run_output_contains_no_gold_fields(workspace):
    execute(spec(workspace), load_claims(workspace["claims"], spec(workspace)),
            load_corpus(workspace["corpus"]))
    blob = workspace["out"].read_text(encoding="utf-8").lower()

    for forbidden in ("rationale", "evaluation_points", "claim_location", "gold_label"):
        assert forbidden not in blob


# --- scoring ---------------------------------------------------------------

def test_load_gold_keeps_pending_as_none(workspace):
    gold = load_gold(workspace["gold"])

    assert gold["FC002"] == Verdict.REFUTED
    assert gold["FC038"] is None


def run_rows(claim_id, arm, verdict, condition="sufficient", cost=0.0, abstain=False):
    return {"config": {"run_id": "r", "condition": condition, "policy": "react",
                       "model_id": "m", "prompt_version": "p1", "data_version": "d1",
                       "seed": 0, "code_commit": None, "replay": False, "extra": {},
                       "arm": arm},
            "result": {"claim_id": claim_id, "verdict": verdict, "abstain": abstain,
                       "cited_evidence_ids": [], "justification": "j", "correction": None,
                       "stop_reason": "evidence_sufficient", "execution_status": "ok",
                       "steps": 1, "error": None, "events": [],
                       "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0,
                                 "llm_calls": 1, "tool_calls": 0, "external_calls": 0,
                                 "cost_usd": cost, "elapsed_ms": 0}}}


def test_scoring_without_grades_reports_accuracy_but_refuses_gsr(workspace):
    rows = [run_rows("FC002", Arm.C1, "refuted"), run_rows("FC004", Arm.C1, "supported")]

    summary = score_run(rows, load_gold(workspace["gold"]))

    condition = summary["conditions"][0]
    assert condition["accuracy"]["value"] == 1.0
    assert condition["macro_f1"]["macro_f1"] == 1.0
    assert condition["gsr"] is None
    assert "gsr" in condition["requires_grading"]
    assert summary["grading"]["e_t_supplied"] is False


def test_gsr_is_computed_once_grades_are_supplied(workspace):
    rows = [run_rows("FC002", Arm.C1, "refuted"), run_rows("FC004", Arm.C1, "supported")]
    grades = {("FC002", Arm.C1, "sufficient"): {"e": True, "t": True},
              ("FC004", Arm.C1, "sufficient"): {"e": True, "t": False}}

    summary = score_run(rows, load_gold(workspace["gold"]), grades)

    assert summary["conditions"][0]["gsr"] == {"numerator": 1, "denominator": 2, "value": 0.5}
    assert summary["grading"]["e_t_supplied"] is True


def test_a_correct_verdict_with_a_wrong_verdict_still_scores_v(workspace):
    """V comes from gold; E and T come from the rubric. They are independent."""
    rows = [run_rows("FC002", Arm.C1, "refuted")]
    graded = to_graded(rows, {"FC002": Verdict.REFUTED}, {})

    assert graded[0].v is True
    assert graded[0].grounded is False


def test_transition_between_two_arms(workspace):
    c1 = [run_rows("FC002", Arm.C1, "supported"), run_rows("FC004", Arm.C1, "supported")]
    c2 = [run_rows("FC002", Arm.C2, "refuted"), run_rows("FC004", Arm.C2, "refuted")]

    result = score_transition(c1, c2, load_gold(workspace["gold"]))

    assert result["pairs"] == 2
    assert result["recovery"] == {"numerator": 1, "denominator": 1, "value": 1.0}
    assert result["harm"] == {"numerator": 1, "denominator": 1, "value": 1.0}
    assert result["net_accuracy_change"] == 0.0


def test_pending_gold_is_excluded_from_label_metrics(workspace):
    rows = [run_rows("FC002", Arm.C1, "refuted"), run_rows("FC038", Arm.C1, "supported")]

    metrics = ungraded_metrics(rows, load_gold(workspace["gold"]))

    assert metrics["episodes"] == 2
    assert metrics["accuracy"]["denominator"] == 1


def test_dry_run_results_can_be_scored_but_are_marked(workspace):
    """The pipeline is verifiable end to end without a provider.

    Every episode abstains, so accuracy is zero - which is exactly why the model
    id is recorded on every row and the justification names the dry run.
    """
    execute(spec(workspace), load_claims(workspace["claims"], spec(workspace)),
            load_corpus(workspace["corpus"]))
    rows = [json.loads(line) for line in
            workspace["out"].read_text(encoding="utf-8").splitlines() if line.strip()]

    summary = score_run(rows, load_gold(workspace["gold"]))

    assert summary["conditions"][0]["attempts"] == 2
    assert summary["conditions"][0]["abstain_rate"]["value"] == 1.0
    assert all(r["config"]["model_id"] == "dry-run-scripted" for r in rows)
