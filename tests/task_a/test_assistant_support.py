"""Opt-in task_a features used by the schedule assistant; defaults must not change."""

from __future__ import annotations

import pytest

from task_a.mcp_server import AgentEnvironment
from task_a.missions import is_date_only, validate_mission_gate
from task_a.schema import EvidenceUnit, ToolStatus, write_jsonl
from task_a.skill import skill_body
from task_a.tools import calculate_comparison


@pytest.mark.parametrize("value", ["2026-07-22T14:00:00", "2026-07-22 14:00:00"])
def test_tz_convert_accepts_seconds(value):
    res = calculate_comparison("tz_convert", time=value, from_tz="Europe/London", to_tz="KST")
    assert res.status == ToolStatus.OK and "2026-07-22 22:00" in res.observation


def _gate(event_start, correction, **kw):
    return validate_mission_gate("event_manager", "refuted", correction=correction,
                                 cited_evidence_ids=["u"], observed_evidence_ids={"u"},
                                 event_start_kst=event_start, **kw)


def test_date_only_events_are_opt_in():
    assert is_date_only("2027-02-26") and not is_date_only("2027-02-26 10:00")
    # Default (experiments): unchanged, a date-only refutation has no HH:MM and is blocked.
    assert _gate("2027-02-26", "출시일은 2027-02-26이다") is not None
    assert _gate("2027-02-26", "출시일은 2027-02-26이다", allow_date_only=True) is None
    assert _gate("2027-02-26", "출시일은 2월 26일이다", allow_date_only=True) is None
    assert "날짜" in _gate("2027-02-26", "출시일은 3월이다", allow_date_only=True)
    # A timed event still needs its HH:MM even with the option on.
    assert _gate("2027-02-26 22:00", "2027-02-26", allow_date_only=True) is not None


def test_episode_snapshot_reports_reads_without_ending_the_episode(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{"evidence_id": "DOC1", "title": "t", "text": "Starts June 9 at 10 a.m."}])
    env = AgentEnvironment(claims_path=None, allow_user_claims=True, corpus_path=corpus,
                           out_path=tmp_path / "run.jsonl", tokenizer="bigram")
    env.submit_claim({"text": "행사는 6월 9일 오전 10시에 열린다."})
    env.call_tool("read_evidence", {"evidence_id": "DOC1"})
    snap = env.episode_snapshot(["DOC1"])
    assert snap["observed"] == ["DOC1"] and "June 9" in snap["texts"]["DOC1"]
    assert "provenance_group" in snap["meta"]["DOC1"]
    assert env.active is not None


def test_skill_body_has_no_frontmatter():
    body = skill_body()
    assert not body.startswith("---") and "finish_verification" in body
