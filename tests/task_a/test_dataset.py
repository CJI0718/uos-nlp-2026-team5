"""The parser is checked against counts evaluation.md itself documents.

If a number here changes, either the parser broke or the team edited the
source document - both need a human look, not a silent re-baseline.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from task_a.dataset import DOCUMENTED_GROUPS, extract

SOURCE = Path(__file__).resolve().parents[2] / "docs/research/fact_checking/evaluation.md"


@pytest.fixture(scope="module")
def parsed():
    return extract(SOURCE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def by_id(parsed):
    return {c["claim_id"]: c for c in parsed["claims"]}


@pytest.fixture(scope="module")
def gold_by_id(parsed):
    return {g["claim_id"]: g for g in parsed["gold"]}


def test_extracts_exactly_fifty_cases(parsed):
    assert len(parsed["claims"]) == 50
    assert len(parsed["gold"]) == 50
    assert [c["claim_id"] for c in parsed["claims"]] == [f"FC{i:03d}" for i in range(1, 51)]


def test_label_distribution_matches_section_9_2_2(parsed):
    """evaluation.md 9.2.2: 지지 37, 반박 11, 근거 부족 1, 판정 보류 1."""
    labels = Counter(g["label_text"] for g in parsed["gold"])

    assert labels == {"지지": 37, "반박": 11, "근거 부족": 1, "판정 보류": 1}


def test_source_kind_distribution_matches_section_9_2_1(parsed):
    """evaluation.md 9.2.1: 기사·정보글 37 (한국어 29 + 영어 8), Threads 9, X 4."""
    kinds = Counter(c["source_type"] for c in parsed["claims"])

    assert kinds["한국어 기사·정보글"] == 29
    assert kinds["영어 기사"] == 8
    assert kinds["Threads"] == 9
    assert kinds["X"] == 4


def test_pending_case_is_not_relabelled_as_nei(gold_by_id):
    """판정 보류 (FC038) is a review state. It must not become a label."""
    pending = [cid for cid, g in gold_by_id.items() if g["review_status"] == "pending"]

    assert pending == ["FC038"]
    assert gold_by_id["FC038"]["label"] is None


def test_the_single_nei_case(gold_by_id):
    assert gold_by_id["FC041"]["label"] == "not_enough_evidence"
    assert gold_by_id["FC041"]["nei_investigation"]


def test_fc002_fields(by_id):
    claim = by_id["FC002"]

    assert claim["text"].startswith("미국 비전 프로 사전예약은 2024년 1월 19일")
    assert claim["source_url"] == "https://v.daum.net/v/2vbOybyj9G"
    assert claim["claim_date"] == "2024-01-09T00:38:00+09:00"
    assert claim["target_period"] == "2024-01-19 사전예약 개시"
    assert "오전 5시(한국시간)" in claim["input_body"]
    assert claim["language"] == "ko"


def test_fc002_gold_and_reference_evidence(gold_by_id, parsed):
    gold = gold_by_id["FC002"]

    assert gold["label"] == "refuted"
    assert "17시간" in gold["rationale"]
    assert gold["evaluation_points"]
    assert gold["scope_notes"]

    rows = [e for e in parsed["evidence"] if e["claim_id"] == "FC002"]
    assert len(rows) == 1
    assert rows[0]["source_url"].startswith("https://www.apple.com/newsroom/")
    assert rows[0]["check_status"] == "본문 확인"
    assert gold["sufficient_evidence_ids"] == ["EV_FC002_1"]


def test_sns_case_uses_transcript_as_input(by_id):
    """FC031 is a Threads post: the input is the transcribed author text."""
    claim = by_id["FC031"]

    assert claim["source_type"] == "Threads"
    assert claim["source_url"].startswith("https://www.threads.com/")
    assert "CVE-2026-98432" in claim["input_body"]
    assert "9.8" in claim["input_body"]


def test_english_case_language(by_id):
    assert by_id["FC026"]["language"] == "en"
    assert by_id["FC026"]["source_type"] == "영어 기사"


def test_documented_split_groups_are_shared(by_id):
    """evaluation.md 9.6: FC032/FC034 and FC015/FC019/FC020 are one group each."""
    assert by_id["FC032"]["family_id"] == by_id["FC034"]["family_id"]
    assert by_id["FC032"]["family_id"] == DOCUMENTED_GROUPS["FC032"]

    size_group = {by_id[c]["family_id"] for c in ("FC015", "FC019", "FC020")}
    assert len(size_group) == 1

    # Grouping must not collapse unrelated cases.
    assert by_id["FC001"]["family_id"] != by_id["FC002"]["family_id"]
    assert len({c["family_id"] for c in by_id.values()}) == 47


def test_gold_sections_never_leak_into_claims(parsed):
    """평가 포인트 and 판정 이유 state the answer, so they belong to gold only.

    Only prose is compared. A bare token like FC026's evaluation point
    '2023-08-23' legitimately also appears in the claim's own date field, and
    counting that as a leak would hide real ones.
    """
    claims = {c["claim_id"]: c for c in parsed["claims"]}
    leaked = []
    for gold in parsed["gold"]:
        claim = claims[gold["claim_id"]]
        blob = f"{claim['text']} {claim['input_body'] or ''}"
        for point in gold["evaluation_points"] + gold["scope_notes"]:
            if len(point) >= 12 and point in blob:
                leaked.append((claim["claim_id"], point))
        if len(gold["rationale"]) >= 12 and gold["rationale"] in blob:
            leaked.append((claim["claim_id"], "rationale"))

    assert leaked == []


def test_claim_location_is_gold_only(by_id, gold_by_id):
    """주장 위치 can state the answer outright.

    FC044's reads '기사 제목의 10월 24일; 본문의 10월 14일과 비교' - the title/body
    discrepancy is exactly what makes that case refuted.
    """
    assert "claim_location" not in by_id["FC044"]
    assert "10월 14일" in gold_by_id["FC044"]["claim_location"]


def test_agent_visible_fields_are_a_closed_set(by_id):
    """The claim record is the agent's whole input, so its shape is pinned."""
    allowed = {"claim_id", "text", "family_id", "language", "source_url",
               "source_type", "claim_date", "target_period", "evidence_cutoff",
               "input_body"}

    assert set(next(iter(by_id.values()))) == allowed


def test_every_case_has_a_claim_and_a_source_url(parsed):
    assert all(c["text"] for c in parsed["claims"])
    assert all(c["source_url"] for c in parsed["claims"])
    assert all(c["evidence_cutoff"] for c in parsed["claims"])


def test_multi_evidence_cases_get_distinct_ids(parsed):
    rows = [e for e in parsed["evidence"] if e["claim_id"] == "FC001"]

    assert len(rows) == 2
    assert [r["evidence_id"] for r in rows] == ["EV_FC001_1", "EV_FC001_2"]
    assert all(r["content"] and r["locator"] for r in rows)


def test_background_only_evidence_is_flagged(parsed):
    """FC041's reference is background, explicitly not proof for or against."""
    rows = [e for e in parsed["evidence"] if e["claim_id"] == "FC041"]

    assert len(rows) == 1
    assert rows[0]["note"] == "배경·추가 확인용"


def test_title_containing_a_colon_is_not_read_as_a_section(by_id, gold_by_id):
    """Regression: FC044's title has a colon, so it used to be parsed as a
    section header and every top-level field fell into that section."""
    claim = by_id["FC044"]

    assert claim["text"] == "일반 Windows 10 지원은 2025년 10월 24일 종료된다."
    assert claim["source_url"] == "https://zdnet.co.kr/view/?no=20250423093406"
    assert claim["claim_date"] == "2025-04-23"
    assert gold_by_id["FC044"]["label"] == "refuted"
    assert "10월 14일" in gold_by_id["FC044"]["rationale"]


def test_every_sns_case_has_a_transcript(by_id):
    """13 SNS inputs (Threads 9 + X 4) are transcribed from the screen."""
    sns = [c for c in by_id.values() if c["source_type"] in ("Threads", "X")]

    assert len(sns) == 13
    assert all(c["input_body"] for c in sns), [c["claim_id"] for c in sns if not c["input_body"]]


def test_translated_posts_record_the_translation_heading(by_id):
    """FC040/FC042 are Spanish posts; the input is the platform's Korean
    translation, and that provenance must survive into the agent's input."""
    for case_id in ("FC040", "FC042"):
        body = by_id[case_id]["input_body"]
        assert "플랫폼에 표시된 한국어 번역 전사" in body


def test_cases_without_an_excerpt_are_left_empty_not_invented(by_id):
    """37 article inputs are URLs only; full text is a separate collection step.

    The parser must not fabricate a body for them.
    """
    missing = [cid for cid, c in by_id.items() if not c["input_body"]]

    assert len(missing) == 21
    assert all(by_id[cid]["source_type"] in ("한국어 기사·정보글", "영어 기사")
               for cid in missing)
    assert all(by_id[cid]["source_url"] for cid in missing)
