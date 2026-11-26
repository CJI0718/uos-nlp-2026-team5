"""Harness v3: changes taken from the exp-011 error analysis.

- claim_gate: a supported/refuted verdict needs a verbatim quote from a read,
  cited document; a forecast claim is never settled by a forecast report or
  refuted for stating a forecast as fact (exp-011 FC017, FC026).
- find_in_page: locate a value inside a long document without paging
  (exp-011 FC040, a 422k-character README).
- A repeated search or a re-fetch of an opened page costs no external call
  (ten exp-011 episodes used 22-25 of 25 external calls).
All fictional claims; no evaluation case appears here.
"""

from __future__ import annotations

import pytest

from task_a.claim_gate import check_verdict, detect_claim_kind, quote_found
from task_a.mcp_server import AgentEnvironment
from task_a.schema import write_jsonl
from task_a.tools import find_passages

FORECAST = {"claim_id": "FC901", "text": "Acme Phone 2의 미국 출시 가격은 999달러가 될 것이다."}
FACT = {"claim_id": "FC902", "text": "Acme Phone 2의 미국 출시 가격은 999달러다."}
LONG = ("Release notes. " + "Older version listed 74 tools. " * 2000
        + "As of v2.0 the server exposes 81 MCP tools in total. " + "Filler text. " * 500)


class _Web:
    def __init__(self):
        self.searches = 0
        self.fetches = 0

    def search(self, query, top_k, end_date=None):
        self.searches += 1
        return [{"title": "Acme", "url": "https://acme.example/news", "snippet": "s",
                 "published_date": "2025-01-01"}]

    def fetch(self, url):
        self.fetches += 1
        if "long" in url:
            return {"text": LONG, "title": "README"}
        return {"text": ("Acme Phone 2 will reportedly cost $999, according to people familiar "
                         "with the plan. Acme announced Acme Phone 2 costs $999 in the US."),
                "title": "Acme news"}


def _env(tmp_path, v3=True, web=None):
    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [FORECAST, FACT])
    return AgentEnvironment(claims_path=claims, arm="C2", web_provider=web or _Web(), web_only=True,
                            out_path=tmp_path / "run.jsonl", missions_dir=tmp_path / "m",
                            tokenizer="bigram", max_external_calls=3, harness_v3=v3)


def _finish(env, **kw):
    args = {"verdict": "supported", "abstain": False,
            "cited_evidence_ids": ["https://acme.example/news"], "justification": "j",
            "stop_reason": "evidence_sufficient"}
    args.update(kw)
    return env.call_tool("finish_verification", args)


# --- claim kind and quote checks ---------------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("Acme 폰은 999달러가 될 것이다.", "forecast"),
    ("Acme Phone will cost $999.", "forecast"),
    ("Acme 증권은 가격이 999달러일 것으로 전망했다.", "attribution"),
    ("Acme는 두 모델을 공개했다고 발표했다.", "attribution"),
    ("Acme 폰은 999달러다.", None),
    ("성적 통지는 12월 11일로 예정됐다.", None),
])
def test_claim_kind_from_wording(text, kind):
    assert detect_claim_kind(text) == kind


def test_quote_matches_across_spacing_and_ellipsis():
    body = "Acme   announced\nAcme Phone 2 costs $999 in the US. More text here."
    assert quote_found("Acme announced Acme Phone 2 costs $999", [body])
    assert quote_found("“Acme announced Acme Phone 2 … in the US.”", [body])
    assert not quote_found("Acme announced Acme Phone 2 costs $899", [body])
    assert not quote_found("Acme", [body])                 # too short to prove anything


@pytest.mark.parametrize("quote,ok", [
    ("국내 제품의 판매 가격은 … 99만 원", True),
    ("국내 제품의 판매 가격은 … 89만 원", False),     # a short fragment that is not there
    ("국내 제품의 판매 가격은 … 9만 원", False),      # cut out of '99만 원'
    ("국내 제품의 판매 가격은 … 1,99", False),        # cut out of '1,999원'
    ("오늘 판매 가격을 공지했다 … 국내 제품의 판매 가격은", True),   # order is free
    ("국내제품의 판매가격은 정가 기준", True),          # spacing is free
])
def test_every_fragment_is_checked_and_numbers_are_not_cut(quote, ok):
    body = "국내 제품의 판매 가격은 정가 기준 99만 원이다. 교육용은 1,999원. 오늘 판매 가격을 공지했다."
    assert quote_found(quote, [body]) is ok


def test_forecast_quote_cannot_leave_out_the_hedge():
    _, refusal = check_verdict(claim_text="Acme will cost $999.", verdict="supported", declared_kind=None,
                               quote="The new phone will … cost $999.", distortion_type=None,
                               cited_texts=["The new phone will reportedly cost $999."])
    assert refusal and "reportedly" in refusal


def test_declaring_attribution_cannot_bypass_forecast_rule():
    kind, refusal = check_verdict(
        claim_text=FORECAST["text"], verdict="supported", declared_kind="attribution",
        quote="Acme Phone 2 will reportedly cost $999", distortion_type="none",
        cited_texts=["Acme Phone 2 will reportedly cost $999, according to people."])
    assert kind == "forecast" and refusal and "reportedly" in refusal


def test_not_enough_evidence_needs_no_quote():
    assert check_verdict(claim_text=FORECAST["text"], verdict="not_enough_evidence", declared_kind=None,
                         quote=None, distortion_type="forecast_as_fact", cited_texts=[]) == ("forecast", None)


# --- the checks at finish_verification -----------------------------------------

def test_forecast_supported_by_a_report_is_sent_back(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC901")
    env.call_tool("fetch_url", {"url": "https://acme.example/news"})
    with pytest.raises(ValueError, match="예측"):
        _finish(env, evidence_quote="Acme Phone 2 will reportedly cost $999")
    # The episode stays open; a settled-fact quote is accepted and both are logged.
    out = _finish(env, evidence_quote="Acme announced Acme Phone 2 costs $999 in the US.")["result"]
    assert out["claim_kind"] == "forecast" and len(out["gate_refusals"]) == 1


def test_forecast_refuted_as_forecast_as_fact_is_sent_back(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC901")
    env.call_tool("fetch_url", {"url": "https://acme.example/news"})
    with pytest.raises(ValueError, match="not_enough_evidence"):
        _finish(env, verdict="refuted", distortion_type="forecast_as_fact", correction="c",
                evidence_quote="Acme Phone 2 will reportedly cost $999")
    out = _finish(env, verdict="not_enough_evidence", distortion_type="forecast_as_fact")
    assert out["result"]["verdict"] == "not_enough_evidence"


def test_quote_must_come_from_a_read_cited_document(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC902")
    with pytest.raises(ValueError, match="evidence_quote"):          # missing
        _finish(env)
    with pytest.raises(ValueError, match="본문에 없습니다"):          # cited but never read
        _finish(env, evidence_quote="Acme announced Acme Phone 2 costs $999 in the US.")
    env.call_tool("fetch_url", {"url": "https://acme.example/news"})
    with pytest.raises(ValueError, match="본문에 없습니다"):          # paraphrased
        _finish(env, evidence_quote="Acme said the phone is $999")
    out = _finish(env, evidence_quote="Acme announced Acme Phone 2 costs $999 in the US.")["result"]
    assert out["claim_kind"] == "fact" and out["evidence_quote"].startswith("Acme announced")


def test_without_v3_nothing_changes(tmp_path):
    env = _env(tmp_path, v3=False)
    env.start_episode("FC901")
    names = {t["name"] for t in env.mcp_tools()}
    finish = next(t for t in env.mcp_tools() if t["name"] == "finish_verification")
    assert "find_in_page" not in names and "evidence_quote" not in finish["inputSchema"]["properties"]
    out = _finish(env)["result"]                 # no quote needed, nothing extra logged
    assert "claim_kind" not in out and "gate_refusals" not in out
    assert env.config.extra["harness_v3"] is False


def test_v3_lists_new_fields(tmp_path):
    env = _env(tmp_path)
    finish = next(t for t in env.mcp_tools() if t["name"] == "finish_verification")
    assert {"evidence_quote", "claim_kind"} <= set(finish["inputSchema"]["properties"])
    assert "find_in_page" in {t["name"] for t in env.mcp_tools()}


# --- find_in_page --------------------------------------------------------------

def test_find_passages_prefers_the_exact_phrase():
    hits = find_passages(LONG, "81 MCP tools")
    assert any("81 MCP tools" in LONG[s:e] for s, e in hits)
    assert LONG[hits[0][0]:hits[0][1]].count("81 MCP tools") == 1


def test_find_in_page_reaches_deep_text_and_counts_as_read(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC902")
    env.call_tool("fetch_url", {"url": "https://acme.example/long"})
    res = env.call_tool("find_in_page", {"evidence_id": "https://acme.example/long", "query": "MCP tools"})
    assert res["status"] == "ok" and "81 MCP tools" in res["observation"]
    assert "[offset" in res["observation"] and len(res["observation"]) < 4000
    assert env.active.external_calls == 1                     # only the fetch
    assert env.call_tool("find_in_page", {"evidence_id": "https://acme.example/long",
                                          "query": "no such words"})["status"] == "empty"


def test_find_in_page_needs_an_opened_document(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC902")
    res = env.call_tool("find_in_page", {"evidence_id": "https://acme.example/x", "query": "q"})
    assert res["status"] == "invalid_input"


# --- reuse without external calls ------------------------------------------------

def test_repeated_search_and_refetch_are_free(tmp_path):
    web = _Web()
    env = _env(tmp_path, web=web)
    env.start_episode("FC902")
    env.call_tool("search_web", {"query": "Acme  Phone 2 price"})
    again = env.call_tool("search_web", {"query": "acme phone 2 PRICE"})
    assert "이미 검색했다" in again["observation"] and "acme.example/news" in again["observation"]
    env.call_tool("fetch_url", {"url": "https://acme.example/news"})
    refetch = env.call_tool("fetch_url", {"url": "https://acme.example/news"})
    assert "다시 내려받지 않았다" in refetch["observation"] and "Acme announced" in refetch["observation"]
    assert (web.searches, web.fetches, env.active.external_calls) == (1, 1, 2)


def test_reuse_still_works_after_the_external_budget_is_spent(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC902")
    env.call_tool("search_web", {"query": "a"})
    env.call_tool("fetch_url", {"url": "https://acme.example/news"})
    env.call_tool("search_web", {"query": "b"})                      # 3 of 3
    assert env.call_tool("search_web", {"query": "c"})["status"] == "blocked"
    assert env.call_tool("search_web", {"query": "a"})["status"] == "ok"
    assert env.call_tool("fetch_url", {"url": "https://acme.example/news"})["status"] == "ok"
