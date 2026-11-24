"""Auto-add policy: the Task A gate plus the two rules learned in exp-004."""

from __future__ import annotations

import pytest

from assistant.dedupe import event_key, find_match
from assistant.policy import Verified, decide, identity_ok, literal_match

OFFICIAL = "https://acme.example/news/keynote"
BLOG = "https://blog.example/acme"
OTHER = "https://other.example/acme"
DOMAINS = ["acme.example"]
TODAY = "2026-11-24"


def _v(**kw) -> Verified:
    base = dict(verdict="supported", abstain=False, event_start="2026-12-10 03:00", correction=None,
                distortion_type="none", cited=[OFFICIAL], observed=[OFFICIAL],
                texts={OFFICIAL: "Acme Orbit keynote streams December 9, 2026 at 10 a.m. PST."},
                docs={OFFICIAL: {"title": "Acme Orbit keynote"}},
                meta={OFFICIAL: {"provenance_group": "auto-1", "derivative": False}})
    base.update(kw)
    return Verified(**base)


def _decide(v, **kw):
    args = dict(name="Acme Orbit Keynote", claimed_start="2026-12-10 03:00", local_tz=None,
                official_domains=DOMAINS, today=TODAY)
    args.update(kw)
    return decide(v, **args)


def test_official_source_with_the_time_is_added():
    d = _decide(_v())
    assert d.status == "auto_added" and d.reasons == [] and d.official_url == OFFICIAL
    assert any(e["quote"] and "december 9" in e["quote"] for e in d.evidence)


def test_time_only_in_a_snippet_goes_to_approval():
    """exp-004 RW10: the cited page was read but did not contain the time."""
    v = _v(texts={OFFICIAL: "Acme Orbit keynote is coming on December 9, 2026."})
    d = _decide(v)
    assert d.status == "pending_approval" and "TIME_NOT_IN_CITED_TEXT" in d.reasons


def test_unread_citation_is_blocked_by_the_gate():
    d = _decide(_v(observed=[]))
    assert d.status == "pending_approval" and "GATE_BLOCKED" in d.reasons


def test_a_different_event_is_not_added():
    """exp-004 RW11: the correction pointed at another event of the same company."""
    v = _v(texts={OFFICIAL: "Acme Home event streams December 9, 2026 at 10 a.m. PST."},
           docs={OFFICIAL: {"title": "Acme Home event"}})
    d = _decide(v, name="Acme Orbit Keynote")
    assert d.status == "pending_approval" and "IDENTITY_MISMATCH" in d.reasons


def test_a_correction_that_moves_the_date_far_needs_review():
    v = _v(verdict="refuted", correction="한국시간 2026-12-10 03:00", distortion_type="timezone_or_date_error")
    d = _decide(v, claimed_start="2026-12-20 03:00")
    assert "LARGE_DATE_CHANGE" in d.reasons


def test_timezone_correction_is_added_when_written_in_the_correction():
    v = _v(verdict="refuted", correction="한국시간 2026-12-10 03:00", distortion_type="timezone_or_date_error")
    assert _decide(v, claimed_start="2026-12-09 10:00").status == "auto_added"
    # Without the corrected HH:MM in the correction the gate refuses it.
    bad = _v(verdict="refuted", correction="한국시간 새벽", distortion_type="timezone_or_date_error")
    assert "GATE_BLOCKED" in _decide(bad, claimed_start="2026-12-09 10:00").reasons


def test_two_copies_of_one_article_are_one_source():
    text = "Acme Orbit keynote streams December 9, 2026 at 10 a.m. PST. " * 3
    v = _v(cited=[BLOG, OTHER], observed=[BLOG, OTHER], texts={BLOG: text, OTHER: text},
           docs={BLOG: {"title": "Acme Orbit"}, OTHER: {"title": "Acme Orbit"}},
           meta={BLOG: {"provenance_group": "auto-1"}, OTHER: {"provenance_group": "auto-1"}})
    d = _decide(v)
    assert d.status == "pending_approval" and "GATE_BLOCKED" in d.reasons


def test_two_independent_sources_pass_but_are_marked():
    t1 = "Acme Orbit keynote streams December 9, 2026 at 10 a.m. PST."
    t2 = "아크미 오르빗 키노트(Acme Orbit)는 한국시간 12월 10일 오전 3시에 시작한다."
    v = _v(cited=[BLOG, OTHER], observed=[BLOG, OTHER], texts={BLOG: t1, OTHER: t2},
           docs={BLOG: {"title": "Acme Orbit"}, OTHER: {"title": "Acme Orbit"}},
           meta={BLOG: {"provenance_group": "auto-1"}, OTHER: {"provenance_group": "auto-2"}})
    d = _decide(v)
    assert d.status == "auto_added" and d.reasons == ["NO_OFFICIAL_SOURCE"]


def test_not_enough_evidence_is_tracked_until_the_date_passes():
    v = _v(verdict="not_enough_evidence", abstain=True, event_start=None)
    assert _decide(v).status == "tracking"
    assert _decide(v, claimed_start="2026-11-01").status == "rejected"


def test_refuted_without_correction_is_dropped():
    assert _decide(_v(verdict="refuted", correction=None)).status == "rejected"


def test_date_only_release_needs_only_the_date():
    v = _v(event_start="2027-02-26", texts={OFFICIAL: "Acme Orbit launches February 26, 2027."})
    assert _decide(v, claimed_start="2027-02-26").status == "auto_added"


def test_conflicting_entry_goes_to_approval():
    assert "CONFLICT" in _decide(_v(), conflict=True).reasons


@pytest.mark.parametrize("text, start, zone, ok", [
    ("Streams June 8, 2026 at 10 a.m. PDT", "2026-06-09 02:00", None, True),
    ("Streams June 8, 2026 at 10:00 AM PDT", "2026-06-09 02:00", None, True),
    ("한국시간 6월 9일 오전 2시 시작", "2026-06-09 02:00", None, True),
    ("2026년 6월 9일 02:00 KST", "2026-06-09 02:00", None, True),
    ("Le 9 septembre 2026, 16h CEST", "2026-09-09 23:00", None, False),   # French month: not handled
    ("9 September 2026 at 4 p.m. CEST", "2026-09-09 23:00", None, True),
    ("Streams June 8, 2026", "2026-06-09 02:00", None, False),            # date without time
    ("Streams June 8, 2026 at 11 a.m. PDT", "2026-06-09 02:00", None, False),
    ("Out February 26, 2027", "2027-02-26", None, True),
])
def test_literal_match(text, start, zone, ok):
    assert bool(literal_match(text, start, zone)) is ok


def test_identity_needs_most_name_words():
    assert identity_ok("Nintendo Direct", "Nintendo Direct airs Sept 9")
    assert not identity_ok("Apple Mac event", "Apple Welcome home smart home event")


def test_event_key_keeps_years_apart_and_matches_similar_names():
    assert event_key("tech", "WWDC 2021", "2021-06-08") != event_key("tech", "WWDC 2026", "2026-06-08")
    existing = [{"event_key": event_key("game", "Nintendo Direct", "2026-09-09"), "interest": "game",
                 "title": "Nintendo Direct", "start_kst": "2026-09-09 23:00"}]
    assert find_match(existing, "game", "Nintendo Direct Showcase", "2026-09-10") is not None
    assert find_match(existing, "game", "Nintendo Direct", "2026-12-01") is None
