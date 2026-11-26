"""exp-005 Action Item 2/3: page text the extractor used to miss, and arm-aware tool lists."""

from __future__ import annotations

import json

from task_a.article import extract_article
from task_a.mcp_server import AgentEnvironment
from task_a.schema import Claim, write_jsonl
from task_a.web import readable_url

MENU = "<nav>" + " ".join(f"<a>메뉴{i}</a>" for i in range(30)) + "</nav>"
BODY = ("<p>한국닌텐도주식회사가 새로운 게임기를 희망소비자가격 648,000원으로 "
        "2025년 6월 5일(목)에 발매한다고 발표했다.</p>")


def test_github_file_pages_are_read_from_the_raw_file():
    assert readable_url("https://github.com/HKUDS/Vibe-Trading/blob/dccb17c/README.md") == \
        "https://raw.githubusercontent.com/HKUDS/Vibe-Trading/dccb17c/README.md"
    assert readable_url("https://github.com/o/r/blob/main/docs/a b.md") == \
        "https://raw.githubusercontent.com/o/r/main/docs/a b.md"
    # Repository front pages render server-side and stay as they are.
    assert readable_url("https://github.com/browser-use/video-use") == "https://github.com/browser-use/video-use"


def test_app_router_page_data_supplies_the_missing_body():
    payload = json.dumps(json.dumps({"tinyMce": BODY, "id": "5ynPEAZG5jwqIEBOclQ09G",
                                     "url": "https://images.example/banner.jpg?w=1400"}))
    raw = (f"<html><head><title>발매</title></head><body>{MENU}"
           f"<script>self.__next_f.push([1,{payload}])</script></body></html>")
    art = extract_article(raw, "https://www.nintendo.com/kr/news/article/x")
    assert art.method == "page_data"
    assert "648,000원" in art.text and "5ynPEAZG" not in art.text and "<p>" not in art.text


def test_pages_router_next_data_is_read_too():
    data = json.dumps({"props": {"pageProps": {"body": BODY}}})
    raw = f'<html><body>{MENU}<script id="__NEXT_DATA__" type="application/json">{data}</script></body></html>'
    assert "648,000원" in extract_article(raw).text


def test_a_normal_article_keeps_its_extracted_body():
    para = "<p>" + "기준금리를 연 2.75%에서 연 2.50%로 낮췄다. " * 40 + "</p>"
    payload = json.dumps(json.dumps({"x": "<p>다른 추천 기사 제목이 여기에 들어갑니다 길게 길게</p>"}))
    raw = f"<html><body><article>{para}</article><script>self.__next_f.push([1,{payload}])</script></body></html>"
    art = extract_article(raw)
    assert art.method != "page_data" and "2.50%" in art.text


def _env(tmp_path, arm):
    claims = tmp_path / "claims.jsonl"
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(claims, [Claim(claim_id="FC901", text="t").to_dict()])
    write_jsonl(corpus, [{"evidence_id": "DOC_x", "title": "x", "text": "본문"}])
    return AgentEnvironment(claims_path=claims, out_path=tmp_path / "run.jsonl", arm=arm,
                            corpus_path=corpus if arm != "C0" else None, tokenizer="bigram",
                            web_provider=object() if arm == "C2" else None)


def test_tool_list_matches_what_the_arm_allows(tmp_path):
    names = {arm: {t["name"] for t in _env(tmp_path / arm, arm).mcp_tools()} for arm in ("C0", "C1", "C2")}
    control = {"list_claims", "start_episode", "finish_verification"}
    assert names["C0"] == control
    assert names["C1"] == control | {"search_evidence", "read_evidence", "calculate_comparison"}
    assert names["C2"] == names["C1"] | {"search_web", "fetch_url"}


# --- web-only arm and the public answer key ------------------------------------

def test_the_team_repository_is_never_served_to_the_agent():
    from task_a.tools import check_url, is_leak_url
    assert is_leak_url("https://github.com/CJI0718/uos-nlp-2026-team5/blob/main/data/task_a/gold.jsonl")
    assert is_leak_url("https://raw.githubusercontent.com/cji0718/UOS-NLP-2026-TEAM5/main/x.md")
    assert check_url("https://github.com/CJI0718/uos-nlp-2026-team5", None)
    assert check_url("https://github.com/HKUDS/Vibe-Trading/blob/main/README.md", None) is None


def test_search_results_from_the_repository_are_dropped(tmp_path):
    class Web:
        def search(self, query, top_k=5, end_date=None, start_date=None):
            return [{"url": "https://github.com/CJI0718/uos-nlp-2026-team5/blob/main/gold.jsonl",
                     "title": "gold", "snippet": "refuted"},
                    {"url": "https://www.bok.or.kr/x", "title": "기준금리", "snippet": "2.50"}]

        def fetch(self, url):
            return {"text": "본문", "fetched_url": url}

    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [Claim(claim_id="FC902", text="t").to_dict()])
    env = AgentEnvironment(claims_path=claims, out_path=tmp_path / "run.jsonl", arm="C2",
                           web_provider=Web(), web_only=True, tokenizer="bigram")
    env.start_episode("FC902")
    obs = env.call_tool("search_web", {"query": "기준금리"})["observation"]
    assert "bok.or.kr" in obs and "uos-nlp-2026-team5" not in obs and "저장소 결과 1건" in obs
    blocked = env.call_tool("fetch_url", {"url": "https://github.com/CJI0718/uos-nlp-2026-team5"})
    assert blocked["status"] == "blocked"
    names = {t["name"] for t in env.mcp_tools()}
    assert "search_evidence" not in names and {"search_web", "fetch_url", "read_evidence"} <= names


def test_the_post_a_claim_came_from_cannot_be_its_proof(tmp_path):
    from task_a.tools import same_page

    class Web:
        def search(self, query, top_k=5, end_date=None, start_date=None):
            return []

        def fetch(self, url):
            return {"text": "기사 본문 " * 50, "fetched_url": url}

    src = "https://www.news.example/view/1"
    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [Claim(claim_id="FC903", text="t", source_url=src).to_dict()])
    env = AgentEnvironment(claims_path=claims, out_path=tmp_path / "run.jsonl", arm="C2",
                           web_provider=Web(), web_only=True, tokenizer="bigram",
                           block_self_citation=True)
    env.start_episode("FC903")
    assert env.call_tool("fetch_url", {"url": src})["status"] == "ok"   # reading it is fine
    finish = {"verdict": "supported", "justification": "기사에 그렇게 나옴",
              "cited_evidence_ids": ["http://news.example/view/1/"]}
    try:
        env.call_tool("finish_verification", finish)
        raised = False
    except ValueError as exc:
        raised = "인용할 수 없습니다" in str(exc)
    assert raised and env.active is not None
    assert same_page("https://m.news.example/view/1", src)
