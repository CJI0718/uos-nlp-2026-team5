"""Harness v3 value check: an artifact may only write values the episode read
or calculated from what it read. All fictional; no evaluation case appears here."""

from __future__ import annotations

import pytest

from task_a.mcp_server import AgentEnvironment
from task_a.schema import write_jsonl
from task_a.value_check import (
    check_action_values,
    datetime_in,
    numbers,
    ungrounded_numbers,
)

PRICE_DOC = "Acme Book 256GB의 국내 가격은 99만원, 교육용 가격은 85만원이다. 미국 가격은 599달러다."


def _check(summary, *, sources=(PRICE_DOC,), calls=(), mission="news_to_artifact", verdict="supported",
           correction=None, start=None, claim="Acme Book 교육가는 85만원이다."):
    return check_action_values(mission_type=mission, verdict=verdict, title="", summary=summary,
                               correction=correction, event_start_kst=start, claim=claim,
                               sources=list(sources), calls=list(calls))


@pytest.mark.parametrize("text,value", [
    ("35만9000원", 359_000), ("107조4천405억원", 107_440_500_000_000), ("195조 2,532억원", 195_253_200_000_000),
    ("23만 8300명", 238_300), ("2,600만 개", 26_000_000), ("26 million", 26_000_000), ("1 200 TWh", 1200),
])
def test_numbers_read_korean_and_english_units(text, value):
    assert any(abs(v - value) < 1e-6 for n in numbers(text) for v in n.values)


def test_values_from_the_source_pass_in_any_spelling():
    assert _check("국내가 990,000원, 교육가 85만 원, 미국가 599달러.") is None


@pytest.mark.parametrize("summary", [
    "교육가 89만원.",          # not in the source
    "교육가 5만원.",           # cut out of '85만원'
    "교육가 85억원.",          # same digits, other unit
])
def test_a_value_not_in_the_source_blocks_the_artifact(summary):
    assert "값 대조 차단" in _check(summary)


def test_calculations_count_only_when_their_inputs_were_read():
    good = [{"op": "diff", "a": 990000, "b": 850000}, {"op": "pct_change", "old": 990000, "new": 850000}]
    assert _check("차액 140,000원(14만 원), 할인율 14.1%.", calls=good) is None
    # A wrong input cannot launder a wrong output through the calculator.
    bad = [{"op": "diff", "a": 1990000, "b": 850000}]
    assert "1,140,000" in _check("차액 1,140,000원.", calls=bad)


def test_a_refuted_claim_may_be_restated():
    claim = "Acme Book 교육가는 75만원이다."
    assert _check("주장의 75만원은 틀렸고 교육가는 85만원이다.", verdict="refuted",
                  correction="교육가는 85만원이다.", claim=claim) is None
    assert _check("교육가는 75만원이다.", claim=claim) is not None   # supported: not from the claim


def test_single_digit_integers_are_not_checked():
    assert ungrounded_numbers("근거 2건, 1차 출처.", [PRICE_DOC], []) == []


EVENT_DOC = "Acme Summit keynote: June 8, 2027 at 10 a.m. PDT in San Jose."


@pytest.mark.parametrize("text,stamp,found", [
    (EVENT_DOC, "2027-06-08 10:00", True),
    (EVENT_DOC, "2027-06-08 11:00", False),
    (EVENT_DOC, "2027-06-09 10:00", False),
    ("행사는 6월 9일 새벽 2시(한국 시간)에 시작한다.", "2027-06-09 02:00", True),
    ("행사는 6월 9일 오후 2시에 시작한다.", "2027-06-09 14:00", True),
    ("행사는 6월 9일 오후 2시에 시작한다.", "2027-06-09 02:00", False),
    ("성적은 12월 11일 통지된다.", "2027-12-11", True),
    ("성적은 12월 11일 통지된다.", "2027-12-11 09:00", False),   # a time the source never gave
])
def test_dates_and_times_in_prose(text, stamp, found):
    assert datetime_in(stamp, [text]) is found


def test_event_time_from_a_conversion_of_the_source_time():
    tz = {"op": "tz_convert", "time": "2027-06-08 10:00", "from_tz": "PDT", "to_tz": "KST"}
    ok = _check("키노트는 한국 시간 6월 9일 02:00.", sources=[EVENT_DOC], calls=[tz],
                mission="event_manager", start="2027-06-09 02:00", claim="Acme Summit")
    assert ok is None
    # Converting a time the source does not give is not evidence.
    wrong = dict(tz, time="2027-06-08 11:00")
    assert "event_start_kst" in _check("키노트", sources=[EVENT_DOC], calls=[wrong],
                                       mission="event_manager", start="2027-06-09 03:00", claim="Acme Summit")


def test_refuted_event_needs_the_same_day_and_time_in_the_correction():
    tz = {"op": "tz_convert", "time": "2027-06-08 10:00", "from_tz": "PDT", "to_tz": "KST"}
    args = {"sources": [EVENT_DOC], "calls": [tz], "mission": "event_manager", "verdict": "refuted",
                "start": "2027-06-09 02:00", "claim": "Acme Summit은 6월 9일 03:00에 시작한다."}
    assert _check("정정", correction="한국 시간 2027-06-09 02:00 시작", **args) is None
    assert "correction" in _check("정정", correction="한국 시간 2027-06-10 02:00 시작", **args)


# --- through the server -------------------------------------------------------

def _server(tmp_path, v3):
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{"evidence_id": "doc", "title": "공지", "text": PRICE_DOC}])
    env = AgentEnvironment(claims_path=None, allow_user_claims=True, corpus_path=corpus,
                           out_path=tmp_path / "run.jsonl", missions_dir=tmp_path / "missions",
                           tokenizer="bigram", harness_v3=v3)
    env.submit_claim({"text": "Acme Book 256GB 교육가는 85만원이다."})
    env.call_tool("read_evidence", {"evidence_id": "doc"})
    return env


@pytest.mark.parametrize("v3", [True, False])
def test_server_blocks_a_wrong_value_only_with_v3(tmp_path, v3):
    env = _server(tmp_path, v3)
    result = env.call_tool("finish_verification", {
        "verdict": "supported", "cited_evidence_ids": ["doc"], "justification": "j",
        "evidence_quote": "교육용 가격은 85만원이다", "mission_type": "news_to_artifact",
        "mission_summary": "교육가 75만원 확인"})["result"]
    assert result["verdict"] == "supported" and result["mission_type"] == "news_to_artifact"
    status = result["mission_output"]["status"]
    assert status == ("invalid_input" if v3 else "ok")
    assert not list((tmp_path / "missions").rglob("*.md")) if v3 else True


def test_server_writes_a_grounded_artifact(tmp_path):
    env = _server(tmp_path, True)
    env.call_tool("calculate_comparison", {"op": "diff", "a": 990000, "b": 850000})
    result = env.call_tool("finish_verification", {
        "verdict": "supported", "cited_evidence_ids": ["doc"], "justification": "j",
        "evidence_quote": "교육용 가격은 85만원이다", "mission_type": "news_to_artifact",
        "mission_summary": "일반가 99만원, 교육가 85만원, 차액 140,000원"})["result"]
    assert result["mission_output"]["status"] == "ok"
    assert list((tmp_path / "missions").rglob("*.md"))
