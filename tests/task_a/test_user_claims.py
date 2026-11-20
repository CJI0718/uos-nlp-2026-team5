"""submit_claim: verify a claim the user types, without a preset claims file."""

from __future__ import annotations

import pytest

from task_a.mcp_server import AgentEnvironment, MCPStdioServer
from task_a.schema import Claim, EvidenceUnit, write_jsonl

FC002 = Claim(claim_id="FC002", text="비전 프로 사전예약은 1월 19일 오전 5시(한국시간)에 시작한다.")
APPLE = EvidenceUnit(evidence_id="DOC_apple_vp", title="Apple Vision Pro available in the US",
                     text="Pre-orders begin on January 19, 2024 at 5:00 a.m. PST.", publisher="Apple")


def _env(tmp_path, **kw):
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{"evidence_id": APPLE.evidence_id, "title": APPLE.title,
                          "text": APPLE.text, "publisher": APPLE.publisher}])
    kw.setdefault("claims_path", None)
    kw.setdefault("allow_user_claims", True)
    return AgentEnvironment(out_path=tmp_path / "run.jsonl", corpus_path=corpus, tokenizer="bigram",
                            missions_dir=tmp_path / "missions", **kw)


def _call(server, name, args, req_id=1):
    return server.handle_request({"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                                  "params": {"name": name, "arguments": args}})


def _tools(server):
    resp = server.handle_request({"jsonrpc": "2.0", "id": 0, "method": "tools/list"})
    return {t["name"] for t in resp["result"]["tools"]}


def test_submit_claim_is_hidden_unless_enabled(tmp_path):
    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [FC002.to_dict()])
    server = MCPStdioServer(_env(tmp_path, claims_path=claims, allow_user_claims=False))
    assert "submit_claim" not in _tools(server)
    assert "error" in _call(server, "submit_claim", {"text": "x"})


def test_needs_claims_or_user_claims(tmp_path):
    with pytest.raises(ValueError, match="allow_user_claims"):
        _env(tmp_path, allow_user_claims=False)


def test_user_claim_runs_a_full_gated_episode(tmp_path):
    env = _env(tmp_path)
    server = MCPStdioServer(env)
    assert "submit_claim" in _tools(server)

    text = "미국 비전 프로 사전예약은 2024년 1월 19일 한국시간 오전 5시에 시작한다."
    started = env.submit_claim({"text": text, "input_body": "사전예약은 19일 오전 5시부터."})
    cid = started["claim"]["claim_id"]
    assert started["status"] == "started" and cid.startswith("USER-")
    assert started["claim"]["evidence_cutoff"] is None and "note" in started
    assert started["claim"]["claim_date"]  # filled with the submission time
    # Same text and source -> same id (re-verification, not a copy).
    assert env.submit_claim({"text": text})["claim"]["claim_id"] == cid
    assert [c["claim_id"] for c in env.list_claims()] == [cid]

    # Gate still applies: citing an unread document is refused.
    blocked = env.finish_episode({
        "verdict": "refuted", "abstain": False, "cited_evidence_ids": [APPLE.evidence_id],
        "justification": "05:00 PST = 22:00 KST", "stop_reason": "evidence_sufficient",
        "correction": "2024-01-19 22:00 KST", "mission_type": "event_manager",
        "event_start_kst": "2024-01-19 22:00"})
    assert blocked.mission_output["status"] == "invalid_input"

    env.submit_claim({"text": text})
    assert env.call_tool("read_evidence", {"evidence_id": APPLE.evidence_id})["status"] == "ok"
    done = env.finish_episode({
        "verdict": "refuted", "abstain": False, "cited_evidence_ids": [APPLE.evidence_id],
        "justification": "05:00 PST = 22:00 KST", "stop_reason": "evidence_sufficient",
        "correction": "2024-01-19 22:00 KST", "mission_type": "event_manager",
        "event_start_kst": "2024-01-19 22:00"})
    assert done.mission_output["status"] == "ok"
    assert done.claim_id == cid


@pytest.mark.parametrize("args, message", [
    ({}, "text"),
    ({"text": "가" * 1001}, "1000자"),
    ({"text": "주장", "evidence_cutoff": "어제"}, "evidence_cutoff"),
])
def test_bad_user_claims_are_rejected(tmp_path, args, message):
    with pytest.raises(ValueError, match=message):
        _env(tmp_path).submit_claim(args)
