"""Fixed-corpus retrieval behaviour, including a known cross-lingual gap."""

from __future__ import annotations

import pytest

from task_a.loop import ReActAgent
from task_a.mock import ScriptedLLM, finish_response, tool_call_response
from task_a.retrieve import (
    BM25Index, BigramTokenizer, CorpusBackend, KiwiTokenizer, load_corpus, make_tokenizer,
)
from task_a.schema import Claim, EvidenceUnit, ToolStatus, Verdict
from task_a.tools import ToolRegistry

FC002 = Claim(
    claim_id="FC002",
    text="미국 비전 프로 사전예약은 2024년 1월 19일 한국시간 오전 5시에 시작한다.",
    target_period="2024-01-19 사전예약 개시")

APPLE = EvidenceUnit(
    evidence_id="EV_apple",
    title="Apple Vision Pro available in the US on February 2",
    text=("Apple Vision Pro will be available in the US on Friday, February 2, 2024. "
          "Pre-orders begin on January 19, 2024 at 5:00 a.m. PST."),
    publisher="Apple", provenance_group="pg_apple_launch", document_validity="valid")
KOREAN_ANNOUNCE = EvidenceUnit(
    evidence_id="EV_ko",
    title="애플 비전 프로 사전예약 안내",
    text="애플 비전 프로의 사전예약은 2024년 1월 19일 오전 5시에 시작된다. 미국 출시일은 2월 2일이다.",
    publisher="example", provenance_group="pg_apple_launch", document_validity="valid")
KOREAN_DISTRACTOR = EvidenceUnit(
    evidence_id="EV_dist",
    title="애플 비전 프로 체험기",
    text="애플의 혼합현실 헤드셋을 미리 사용해 봤다. 무게와 착용감이 인상적이다.",
    publisher="example", document_validity="valid")
MISLEADING = EvidenceUnit(
    evidence_id="EV_bad",
    title="비전 프로 예약 일정 정리",
    text="비전 프로 사전예약은 2024년 1월 19일 오전 5시 한국시간에 시작된다.",
    publisher="example", document_validity="misleading")

CORPUS = [APPLE, KOREAN_ANNOUNCE, KOREAN_DISTRACTOR, MISLEADING]
KO_QUERY = "비전 프로 사전예약 2024년 1월 19일 시작 시각"
EN_QUERY = "Vision Pro pre-order January 19 2024 PST"


def test_kiwi_segments_korean_morphologically():
    tokens = KiwiTokenizer().tokenize("사전예약은 한국시간 오전 5시에 시작한다")

    assert "사전" in tokens and "예약" in tokens
    assert "사전예약은" not in tokens


def test_bigram_tokenizer_keeps_latin_words_whole():
    tokens = BigramTokenizer().tokenize("Vision Pro 2024년 사전예약")

    assert "vision" in tokens and "pro" in tokens and "2024" in tokens
    assert "사전" in tokens and "전예" in tokens


def test_make_tokenizer_rejects_unknown_name():
    with pytest.raises(ValueError, match="unknown tokenizer"):
        make_tokenizer("mecab")


@pytest.mark.parametrize("tokenizer", [BigramTokenizer(), KiwiTokenizer()])
def test_relevant_document_outranks_distractor_in_the_same_language(tokenizer):
    index = BM25Index(CORPUS, tokenizer)
    ranked = [u.evidence_id for u, _ in index.search(EN_QUERY, 4)]

    assert ranked[0] == "EV_apple"


def test_documents_matching_no_query_term_are_dropped():
    """BM25 scores term-disjoint documents negative; they must not be returned."""
    index = BM25Index(CORPUS, BigramTokenizer())

    assert index.search("zzz qqq xyz", 4) == []


def test_top_k_limits_the_returned_set():
    index = BM25Index(CORPUS, BigramTokenizer())

    assert len(index.search(KO_QUERY, 2)) == 2
    assert len(index.search(KO_QUERY, 99)) <= len(CORPUS)


def test_backend_caps_top_k_at_its_own_limit():
    backend = CorpusBackend(CORPUS, BigramTokenizer(), top_k=3)

    assert len(backend.search_corpus(KO_QUERY, 50)) <= 3


def test_empty_corpus_returns_no_hits():
    assert BM25Index([], BigramTokenizer()).search(KO_QUERY, 5) == []


def test_misleading_document_wins_korean_retrieval():
    """The contamination mechanism, observed rather than assumed.

    EV_bad restates the claim almost word for word ('사전예약은 2024년 1월 19일
    오전 5시 한국시간'), so BM25 ranks it first - above both the true Korean
    announcement and Apple's decisive English source. Lexical closeness to the
    claim is not evidence of validity, and the planted document is closer to the
    claim than the truth is.

    Pinned so that a retriever change which moves this ranking is a deliberate
    decision, not a silent shift in the experiment's difficulty.
    """
    backend = CorpusBackend(CORPUS, KiwiTokenizer())
    ranked = [u.evidence_id for u, _ in backend.search_corpus(KO_QUERY, 4)]

    assert ranked[0] == "EV_bad"
    assert ranked.index("EV_apple") > ranked.index("EV_bad")


def test_cross_lingual_gap_is_pinned():
    """KNOWN GAP: the decisive source is often the English original.

    FC002's is Apple's newsroom; FC004 (NobelPrize), FC026-FC030 and
    FC048-FC050 have the same shape - Korean claim, English decisive evidence.
    A Korean query ranks Apple last, below an unrelated Korean hands-on piece.
    BM25 cannot bridge languages, so the agent must re-query in the source
    language. The system prompt instructs that and the loop permits it.
    """
    backend = CorpusBackend(CORPUS, KiwiTokenizer())

    korean_ranked = [u.evidence_id for u, _ in backend.search_corpus(KO_QUERY, 4)]
    english_ranked = [u.evidence_id for u, _ in backend.search_corpus(EN_QUERY, 4)]

    assert english_ranked[0] == "EV_apple"
    assert korean_ranked.index("EV_apple") > english_ranked.index("EV_apple")
    assert korean_ranked[-1] == "EV_apple"


def test_agent_can_recover_by_requerying_in_english():
    """The two-query path the prompt asks for, end to end."""
    backend = CorpusBackend(CORPUS, KiwiTokenizer())
    llm = ScriptedLLM([
        tool_call_response("search_evidence", {"query": KO_QUERY}),
        tool_call_response("search_evidence", {"query": EN_QUERY}),
        tool_call_response("read_evidence", {"evidence_id": "EV_apple"}),
        tool_call_response("calculate_comparison", {"op": "tz_convert", "time": "2024-01-19 05:00",
                                                    "from_tz": "PST", "to_tz": "KST"}),
        finish_response("refuted", ["EV_apple"],
                        "공식 발표는 05:00 PST다. 한국어 질의에서 1위였던 문서는 독립 확인이 없다.",
                        "evidence_sufficient", correction="2024-01-19 22:00 KST"),
    ])
    agent = ReActAgent(llm, ToolRegistry(backend))

    result = agent.run(FC002)

    assert result.verdict == Verdict.REFUTED
    # The first query surfaced the planted document; the second found the source.
    assert result.events[0].evidence_ids[0] == "EV_bad"
    assert "EV_apple" in result.events[1].evidence_ids
    assert result.cited_evidence_ids == ["EV_apple"]


def test_c1_backend_has_no_external_access():
    """A backend built without a provider IS the C1 condition."""
    registry = ToolRegistry(CorpusBackend(CORPUS, BigramTokenizer()))

    web, _ = registry.call("search_web", {"query": "anything"})
    fetch, _ = registry.call("fetch_url", {"url": "https://www.apple.com/newsroom/"})

    assert web.status == ToolStatus.SOURCE_UNAVAILABLE
    assert fetch.status == ToolStatus.SOURCE_UNAVAILABLE
    assert "C1 조건" in web.observation


def test_c2_backend_routes_to_the_provider():
    class StubWeb:
        def __init__(self):
            self.queries = []

        def search(self, query, top_k):
            self.queries.append(query)
            return [{"title": "Apple Newsroom", "url": "https://www.apple.com/x", "snippet": "5:00 a.m. PST"}]

        def fetch(self, url):
            return "Pre-orders begin January 19 at 5:00 a.m. PST"

    web = StubWeb()
    registry = ToolRegistry(CorpusBackend(CORPUS, BigramTokenizer(), web=web))

    result, is_external = registry.call("search_web", {"query": EN_QUERY})

    assert result.status == ToolStatus.OK
    assert is_external is True
    assert web.queries == [EN_QUERY]


def test_misleading_documents_are_flagged_for_exposure_tracking():
    """Exposure and false-adoption rates need to know which docs were planted."""
    registry = ToolRegistry(CorpusBackend(CORPUS, BigramTokenizer()))

    result, _ = registry.call("search_evidence", {"query": "비전 프로 사전예약 한국시간 오전 5시"})

    assert "EV_bad" in result.evidence_ids


def test_load_corpus_ignores_unknown_fields():
    rows = [{"evidence_id": "E1", "title": "t", "text": "b", "not_a_field": 1}]

    units = load_corpus(rows)

    assert units[0].evidence_id == "E1"
    assert not hasattr(units[0], "not_a_field")
