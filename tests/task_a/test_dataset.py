"""The parser is checked against counts evaluation_cases.md §0 itself documents.

If a number here changes, either the parser broke or the team edited the
source document - both need a human look, not a silent re-baseline.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from task_a.dataset import DOCUMENTED_GROUPS, extract

SOURCE = Path(__file__).resolve().parents[2] / "data/task_a/evaluation_cases.md"


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


def test_label_distribution_matches_section_0(parsed):
    """evaluation_cases.md §0 (2026-11-25): 지지 30, 반박 14, 근거 부족 6."""
    labels = Counter(g["label_text"] for g in parsed["gold"])

    assert labels == {"지지": 30, "반박": 14, "근거 부족": 6}


def test_source_kind_distribution_matches_section_0(parsed):
    """§0: Korean articles 28 (4 re-written), English 10 (2 re-written),
    Threads 5, X 3, Bluesky 4 (2 re-written)."""
    kinds = Counter(g["source_kind"] for g in parsed["gold"])

    assert kinds == {
        "한국어 기사·정보글": 24,
        "재가공 게시물 · 한국어 기사 기반": 4,
        "영어 기사": 8,
        "재가공 게시물 · 영어 기사 기반": 2,
        "Threads": 5,
        "X": 3,
        "Bluesky": 2,
        "재가공 게시물 · Bluesky 기반": 2,
    }


def test_no_case_is_left_pending(gold_by_id):
    """The old 판정 보류 case (Starlink, FC038) was replaced; every case has a label."""
    assert [cid for cid, g in gold_by_id.items() if g["review_status"] == "pending"] == []
    assert all(g["label"] for g in gold_by_id.values())


def test_nei_cases_record_their_investigation_and_cutoff(by_id, gold_by_id):
    """All six NEE cases are predictions judged as of their posting time."""
    nei = sorted(cid for cid, g in gold_by_id.items() if g["label"] == "not_enough_evidence")

    assert nei == ["FC003", "FC010", "FC017", "FC026", "FC038", "FC041"]
    assert all(gold_by_id[cid]["nei_investigation"] for cid in nei)
    for cid in nei:
        assert by_id[cid]["evidence_cutoff"] == by_id[cid]["claim_date"], cid


def test_fc002_fields(by_id):
    """FC002 is a re-written post: the altered time is in the input, no URL."""
    claim = by_id["FC002"]

    assert claim["text"] == "WWDC26 키노트는 한국시간 6월 9일 오전 3시에 시작하도록 공지됐다."
    assert claim["source_url"] is None
    assert claim["source_type"] == "게시물 전사"
    assert claim["claim_date"] == "2026-05-19T09:13:12+09:00"
    assert "한국시간 9일 오전 3시" in claim["input_body"]
    assert claim["language"] == "ko"


def test_fc002_gold_and_reference_evidence(gold_by_id, parsed):
    gold = gold_by_id["FC002"]

    assert gold["label"] == "refuted"
    assert "02:00 KST" in gold["rationale"]
    assert gold["evaluation_points"]
    assert gold["scope_notes"]

    rows = [e for e in parsed["evidence"] if e["claim_id"] == "FC002"]
    assert len(rows) == 2
    assert rows[0]["source_url"].startswith("https://www.apple.com/newsroom/")
    assert rows[0]["check_status"] == "본문 확인"
    assert rows[1]["title"].startswith("원 보도")
    assert gold["sufficient_evidence_ids"] == ["EV_FC002_1", "EV_FC002_2"]


ALTERED = ("FC002", "FC005", "FC018", "FC029", "FC030", "FC035", "FC039", "FC046")


def test_altered_cases_hide_the_original_report(by_id, gold_by_id, parsed):
    """The original report holds the correct value, so it may only be evidence.

    Each re-written post has no URL, carries its transcript as input, and
    lists the original report ('원 보도 · ...') among the scorer's evidence.
    """
    altered = sorted(cid for cid, g in gold_by_id.items() if g["altered_input"])
    assert tuple(altered) == ALTERED

    for cid in ALTERED:
        claim = by_id[cid]
        assert claim["source_url"] is None, cid
        assert claim["input_body"].startswith("[입력 본문 — 게시물 전사]"), cid
        originals = [e for e in parsed["evidence"]
                     if e["claim_id"] == cid and e["title"].startswith("원 보도")]
        assert len(originals) == 1, cid
        assert originals[0]["source_url"] not in claim["input_body"], cid


def test_agent_never_sees_the_word_for_an_altered_post(parsed):
    """Every altered case is refuted, so '재가공' in the input would leak the label."""
    blob = json.dumps(parsed["claims"], ensure_ascii=False)

    assert "재가공" not in blob
    assert "연구자" not in blob


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
    # Re-written posts keep the language of the report they copy.
    assert by_id["FC029"]["language"] == "en"
    assert by_id["FC018"]["language"] == "ko"


def test_bluesky_posts_are_english(by_id, gold_by_id):
    bluesky = [by_id[g["claim_id"]] for g in gold_by_id.values() if "Bluesky" in g["source_kind"]]

    assert sorted(c["claim_id"] for c in bluesky) == ["FC035", "FC036", "FC038", "FC039"]
    assert all(c["language"] == "en" for c in bluesky)


def test_documented_split_groups_are_shared(by_id):
    """evaluation.md 9.6: FC032/FC034 and FC015/FC020 are one group each.

    FC019 was replaced on 2026-11-25 and is its own group now.
    """
    assert by_id["FC032"]["family_id"] == by_id["FC034"]["family_id"]
    assert by_id["FC032"]["family_id"] == DOCUMENTED_GROUPS["FC032"]

    assert by_id["FC015"]["family_id"] == by_id["FC020"]["family_id"]
    assert by_id["FC019"]["family_id"] == "solo_FC019"

    # Grouping must not collapse unrelated cases.
    assert by_id["FC001"]["family_id"] != by_id["FC002"]["family_id"]
    assert len({c["family_id"] for c in by_id.values()}) == 48


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
    """Only re-written posts lack a URL; every other input links its source."""
    assert all(c["text"] for c in parsed["claims"])
    assert all(c["source_url"] for c in parsed["claims"] if c["claim_id"] not in ALTERED)
    assert all(c["evidence_cutoff"] for c in parsed["claims"])


def test_multi_evidence_cases_get_distinct_ids(parsed):
    rows = [e for e in parsed["evidence"] if e["claim_id"] == "FC029"]

    assert len(rows) == 4
    assert [r["evidence_id"] for r in rows] == [f"EV_FC029_{i}" for i in range(1, 5)]
    assert all(r["content"] and r["locator"] for r in rows)


def test_background_only_evidence_is_flagged(parsed):
    """FC041's second reference postdates its cutoff, so it is background only."""
    rows = [e for e in parsed["evidence"] if e["claim_id"] == "FC041"]

    assert len(rows) == 2
    assert rows[0]["note"] is None
    assert rows[1]["note"] == "배경·추가 확인용"


def test_title_containing_a_colon_is_not_read_as_a_section(by_id, gold_by_id):
    """Regression: FC044's title has a colon, so it used to be parsed as a
    section header and every top-level field fell into that section."""
    claim = by_id["FC044"]

    assert claim["text"] == "일반 Windows 10 지원은 2025년 10월 24일 종료된다."
    assert claim["source_url"] == "https://zdnet.co.kr/view/?no=20250423093406"
    assert claim["claim_date"] == "2025-04-23T12:00:00+09:00"
    assert gold_by_id["FC044"]["label"] == "refuted"
    assert "10월 14일" in gold_by_id["FC044"]["rationale"]


def test_every_sns_case_has_a_transcript(by_id):
    """10 SNS inputs (Threads 5 + X 3 + Bluesky 2) carry the author's text."""
    sns = [c for c in by_id.values() if c["source_type"] in ("Threads", "X", "Bluesky")]

    assert len(sns) == 10
    assert all(c["input_body"] for c in sns), [c["claim_id"] for c in sns if not c["input_body"]]


def test_sns_posting_times_are_absolute(by_id):
    """X status IDs and Threads post codes encode the posting time; the screen
    showed only a clock time or a relative one ('21분')."""
    assert by_id["FC040"]["claim_date"] == "2026-10-29T04:47:54+09:00"
    assert by_id["FC043"]["claim_date"] == "2026-10-29T13:23:20+09:00"
    assert by_id["FC031"]["claim_date"] == "2026-10-30T00:30:03+09:00"
    assert by_id["FC037"]["claim_date"] == "2026-10-29T08:01:14+09:00"
    threads = [c for c in by_id.values() if c["source_type"] == "Threads"]
    assert all(c["claim_date"][:4] == "2026" for c in threads)


def test_translated_posts_record_the_translation_heading(by_id):
    """FC040/FC042 are Spanish posts; the input is the platform's Korean
    translation, and that provenance must survive into the agent's input."""
    for case_id in ("FC040", "FC042"):
        body = by_id[case_id]["input_body"]
        assert "플랫폼에 표시된 한국어 번역 전사" in body


def test_cases_without_an_excerpt_are_left_empty_not_invented(by_id):
    """Some article inputs are URLs only; full text is a separate collection step.

    The parser must not fabricate a body for them.
    """
    missing = [cid for cid, c in by_id.items() if not c["input_body"]]

    # Since the 2026-11-25 review every case carries an excerpt or transcript.
    assert missing == []
    assert all(by_id[cid]["source_type"] in ("한국어 기사·정보글", "영어 기사")
               for cid in missing)
    assert all(by_id[cid]["source_url"] for cid in missing)


# --- re-written (altered) posts and per-case cutoff ---------------------------
_ALTERED = """#### FC999

**시험 사례**

- **입력 글**: 재가공 게시물 (연구자 작성, 원 보도 URL은 에이전트에 주지 않음)
- **게시 시점**: 2026-05-19T09:13:12+09:00
- **근거 기준 시점**: 2026-05-19T09:13:12+09:00
- **선정 주장**: 키노트는 한국시간 6월 9일 오전 3시에 시작한다.
- **참조 판정**: 반박
- **판정 이유**: 공식 공지는 02:00 KST다.

**입력 본문 — 게시물 전사**

> 키노트는 한국시간 9일 오전 3시에 진행된다.
"""


def test_altered_post_has_no_source_url_and_no_annotator_note():
    from task_a.dataset import parse_case, to_records
    claim = to_records(parse_case("FC999", _ALTERED.split("\n", 1)[1]))["claim"]
    assert claim["source_url"] is None
    assert "연구자" not in json.dumps(claim, ensure_ascii=False)
    assert "오전 3시" in claim["input_body"]


def test_per_case_evidence_cutoff_overrides_default():
    from task_a.dataset import DEFAULT_EVIDENCE_CUTOFF, parse_case, to_records
    claim = to_records(parse_case("FC999", _ALTERED.split("\n", 1)[1]))["claim"]
    assert claim["evidence_cutoff"] == "2026-05-19T09:13:12+09:00"
    assert DEFAULT_EVIDENCE_CUTOFF == "2026-10-30T01:37:43+09:00"


def test_every_case_records_its_review(gold_by_id):
    """The '검수' line goes to gold only; FC041 was replaced after review."""
    assert all(g["review_note"] for g in gold_by_id.values())
    drafts = sorted(cid for cid, g in gold_by_id.items() if g["review_status"] == "draft")
    assert drafts == ["FC041"]


def test_review_record_is_not_agent_visible(parsed):
    blob = json.dumps(parsed["claims"], ensure_ascii=False)
    assert "정헌수" not in blob and "검수" not in blob
