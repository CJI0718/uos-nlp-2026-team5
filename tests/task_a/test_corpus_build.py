"""Offline tests for the C1 corpus builder (no network: fetch is injected)."""

from __future__ import annotations

import pytest

from task_a.corpus_build import (Fetched, build_corpus, doc_id_for, extract_html, summarize,
                                 write_outputs)
from task_a.mcp_server import AgentEnvironment, load_agent_corpus
from task_a.schema import write_jsonl

BODY = "Acme announced the Orbit keynote for March 4, 2025 at 10:00 a.m. PST. " * 10
PAGE = f"""<html><head><title>Fallback</title>
<meta property="og:title" content="Acme Orbit keynote">
<meta property="article:published_time" content="2025-02-01T09:00:00Z">
<script>var tracking = "FC001 should never appear";</script></head>
<body><nav>Home | News</nav><article><p>{BODY}</p></article><footer>© Acme</footer></body></html>"""

EVIDENCE = [
    {"evidence_id": "EV_FC900_1", "claim_id": "FC900", "source_url": "https://acme.example/keynote",
     "title": "Acme / 시간대 판정", "content": "판정 문구가 섞인 요약"},
    {"evidence_id": "EV_FC901_1", "claim_id": "FC901", "source_url": "https://acme.example/keynote",
     "title": "x", "content": "y"},
    {"evidence_id": "EV_FC902_1", "claim_id": "FC902", "source_url": "https://dead.example/a",
     "title": "x", "content": "y"},
    {"evidence_id": "EV_FC903_1", "claim_id": "FC903", "source_url": "https://spa.example/app",
     "title": "x", "content": "y"},
]
CLAIMS = [{"claim_id": c, "text": "t", "evidence_cutoff": "2026-10-30T00:00:00+09:00"}
          for c in ("FC900", "FC901", "FC902", "FC903", "FC904")]


def fake_fetch(url: str) -> Fetched:
    pages = {
        "https://acme.example/keynote": Fetched(url, "ok", "text/html; charset=utf-8", PAGE.encode()),
        "https://spa.example/app": Fetched(url, "ok", "text/html", b"<html><body><div id=app></div></body></html>"),
        "https://other.example/rain": Fetched(url, "ok", "text/html", (
            "<html><body><p>" + "Seoul weather report: rain expected over the weekend. " * 10
            + "</p></body></html>").encode()),
        "https://other.example/rates": Fetched(url, "ok", "text/html", (
            "<html><body><p>" + "The central bank held its policy rate unchanged in July. " * 10
            + "</p></body></html>").encode()),
        "https://late.example/x": Fetched(url, "ok", "text/html", PAGE.replace(
            "2025-02-01T09:00:00Z", "2026-11-01T00:00:00Z").replace("Orbit", "Late").encode()),
    }
    return pages.get(url, Fetched(url, "http_error", detail="HTTP 404"))


def test_extract_html_drops_boilerplate_and_reads_metadata():
    ext = extract_html(PAGE)
    assert ext.title == "Acme Orbit keynote"
    assert ext.published_at == "2025-02-01T09:00:00Z"
    assert "10:00 a.m. PST" in ext.text
    assert "Home | News" not in ext.text and "tracking" not in ext.text and "© Acme" not in ext.text


def test_build_fetches_each_url_once_and_never_fills_failures():
    calls = []

    def counting(url):
        calls.append(url)
        return fake_fetch(url)

    res = build_corpus(EVIDENCE, CLAIMS, counting, now="2026-11-19T00:00:00+00:00")

    assert calls.count("https://acme.example/keynote") == 1
    assert [d["evidence_id"] for d in res.corpus] == [doc_id_for("https://acme.example/keynote")]
    status = {r["source_url"]: r["status"] for r in res.report}
    assert status == {"https://acme.example/keynote": "ok",
                      "https://dead.example/a": "http_error",
                      "https://spa.example/app": "too_short"}
    assert res.gold_map[0]["reference_evidence_ids"] == ["EV_FC900_1", "EV_FC901_1"]
    assert res.gold_map[0]["claim_ids"] == ["FC900", "FC901"]

    s = summarize(res, CLAIMS)
    assert s["claims_with_document"] == 2
    assert s["claims_without_document"] == ["FC902", "FC903"]
    assert s["claims_without_reference_url"] == ["FC904"]


def test_corpus_rows_carry_no_reference_content_and_load_in_the_server(tmp_path):
    # BM25 IDF is zero until a term is rarer than half the corpus, so add distractors.
    res = build_corpus(EVIDENCE, CLAIMS, fake_fetch,
                       extra_urls=["https://other.example/rain", "https://other.example/rates"])
    doc = res.corpus[0]
    assert "claim_id" not in doc and "content" not in doc
    assert "판정" not in doc["title"] and "FC9" not in doc["text"]

    paths = write_outputs(res, summarize(res, CLAIMS), tmp_path / "corpus_c1.jsonl")
    units = load_agent_corpus(paths["corpus"])
    assert units[0].text.startswith("Acme announced")

    # The scorer-only map is refused as a corpus by name.
    with pytest.raises(PermissionError):
        load_agent_corpus(paths["gold_map"])

    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [{"claim_id": "FC900", "text": "t"}])
    env = AgentEnvironment(claims_path=claims, corpus_path=paths["corpus"], arm="C1",
                           out_path=tmp_path / "run.jsonl", missions_dir=tmp_path / "m",
                           tokenizer="bigram")
    env.start_episode("FC900")
    hits = env.call_tool("search_evidence", {"query": "Orbit keynote PST"})
    assert doc_id_for("https://acme.example/keynote") in str(hits)


def test_documents_published_after_the_cutoff_are_excluded():
    rows = [{"evidence_id": "EV_FC900_9", "claim_id": "FC900", "source_url": "https://late.example/x"}]
    res = build_corpus(rows, CLAIMS, fake_fetch)
    assert res.corpus == []
    assert res.report[0]["status"] == "after_cutoff"


def test_extra_urls_become_distractors_without_claim_links():
    res = build_corpus([], CLAIMS, fake_fetch, extra_urls=["# comment", "https://acme.example/keynote"])
    assert len(res.corpus) == 1
    assert res.gold_map[0]["claim_ids"] == []


def test_korean_url_paths_are_percent_encoded():
    from task_a.corpus_build import to_ascii_url

    url = to_ascii_url("https://news.samsung.com/kr/삼성전자-갤럭시?q=가격&x=1#frag")
    url.encode("ascii")
    assert url.startswith("https://news.samsung.com/kr/%EC%82%BC%EC%84%B1")
    assert "q=%EA%B0%80%EA%B2%A9&x=1" in url and "#" not in url


def test_lowercase_hex_ids_are_not_mistaken_for_claim_ids(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{"evidence_id": "DOC_fc984ce015", "title": "t", "text": "x"}])
    assert load_agent_corpus(corpus)[0].evidence_id == "DOC_fc984ce015"
