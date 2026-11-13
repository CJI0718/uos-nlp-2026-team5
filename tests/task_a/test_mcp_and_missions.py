"""Tests for MCP server, AgentEnvironment budget/arm isolation, extended calculator, verification-gated missions, and run scoring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from task_a.mcp_server import AgentEnvironment, MCPStdioServer
from task_a.missions import MissionExecutor
from task_a.mock import MockBackend
from task_a.schema import Claim, EvidenceUnit, ToolStatus, Verdict, write_jsonl
from task_a.score_run import load_gold, score_run, score_transition, to_graded, ungraded_metrics
from task_a.scorer import Arm
from task_a.tools import FINISH_TOOL, ToolRegistry, calculate_comparison

FC002 = Claim(
    claim_id="FC002",
    text="미국 비전 프로 사전예약은 2024년 1월 19일 한국시간 오전 5시에 시작한다.",
    target_period="2024-01-19 사전예약 개시",
    input_body="사전예약은 이달 19일 오전 5시(한국시간)부터 받는다.",
)

APPLE = EvidenceUnit(
    evidence_id="EV_FC002_apple",
    title="Apple Vision Pro available in the US on February 2",
    text="Pre-orders begin on January 19, 2024 at 5:00 a.m. PST.",
    publisher="Apple",
    source_type="official_announcement",
)


# --- 1. Extended calculator & URL SSRF guard -------------------------------

def test_fc006_minimum_wage_multiplication():
    """FC006: 10,030 KRW * 209 hours = 2,096,270 KRW."""
    res = calculate_comparison("multiply", a=10_030, b=209)

    assert res.status == ToolStatus.OK
    assert res.payload["value"] == 2_096_270


def test_ratio_calculation_and_zero_guard():
    res = calculate_comparison("ratio", a=165_000, b=1_962_400)
    assert res.status == ToolStatus.OK
    assert res.payload["percentage"] == pytest.approx(8.40807, abs=0.001)

    zero = calculate_comparison("ratio", a=10, b=0)
    assert zero.status == ToolStatus.INVALID_INPUT


@pytest.mark.parametrize("url,expected", [
    ("https://www.apple.com/newsroom/x", ToolStatus.OK),
    ("file:///etc/passwd", ToolStatus.BLOCKED),
    ("http://localhost:8000/gold", ToolStatus.BLOCKED),
    ("http://127.0.0.1/gold", ToolStatus.BLOCKED),
    ("http://192.168.1.5/gold", ToolStatus.BLOCKED),
    ("http://169.254.169.254/latest/meta-data", ToolStatus.BLOCKED),
    ("ftp://example.com/x", ToolStatus.BLOCKED),
])
def test_fetch_url_guard(url, expected):
    backend = MockBackend([APPLE], pages={"https://www.apple.com/newsroom/x": "본문"})
    registry = ToolRegistry(backend)

    result, is_external = registry.call("fetch_url", {"url": url})

    assert result.status == expected
    assert is_external is True


# --- 2. Verification-Gated Missions ----------------------------------------

def test_verification_gate_blocks_unverified_or_uncorrected_action(tmp_path):
    executor = MissionExecutor(tmp_path / "missions")

    # 1) NEI cannot run an actionable mission (must use continuous_tracking or hold_abstain)
    nei_res = executor.execute_mission(
        claim_id="FC041",
        mission_type="news_to_artifact",
        verdict="not_enough_evidence",
        title="40B 코어 리포트",
        summary="미검증 성능 리포트",
    )
    assert nei_res.status == ToolStatus.INVALID_INPUT
    assert "검증 게이팅 차단" in nei_res.observation

    # 2) Refuted claim WITHOUT correction cannot run event_manager ('Garbage In, Action Out' block)
    uncorrected = executor.execute_mission(
        claim_id="FC002",
        mission_type="event_manager",
        verdict="refuted",
        title="비전 프로 사전예약",
        summary="시간대 오보",
        event_start_kst="2024-01-19 05:00",
    )
    assert uncorrected.status == ToolStatus.INVALID_INPUT
    assert "correction" in uncorrected.observation

    # 3) Refuted claim WITH correction succeeds and writes .ics
    corrected = executor.execute_mission(
        claim_id="FC002",
        mission_type="event_manager",
        verdict="refuted",
        title="비전 프로 사전예약 (정정)",
        summary="05:00 PST를 22:00 KST로 정정 반영",
        cited_evidence_ids=["EV_FC002_apple"],
        correction="2024-01-19 22:00 KST",
        distortion_type="timezone_or_date_error",
        event_start_kst="2024-01-19 22:00",
    )
    assert corrected.status == ToolStatus.OK
    ics_path = Path(corrected.payload["artifact_path"])
    assert ics_path.exists()
    assert "DTSTART;TZID=Asia/Seoul:20240119T220000" in ics_path.read_text(encoding="utf-8")


def test_continuous_tracking_and_artifact_generation(tmp_path):
    executor = MissionExecutor(tmp_path / "missions")

    track = executor.execute_mission(
        claim_id="FC007",
        mission_type="continuous_tracking",
        verdict="supported",
        title="2026 폴더블 시장 30% 성장 전망 추적",
        summary="전망 발표는 사실이나 2026년 실제 성장률 실현 여부는 후속 추적 필요",
        tracking_condition="2026년 연간 폴더블 출하량 확정 통계 발표 시",
        tracking_queries=["DSCC foldable market 2026 actual growth"],
    )
    assert track.status == ToolStatus.OK
    reg_file = Path(track.payload["artifact_path"])
    assert reg_file.exists()
    row = json.loads(reg_file.read_text(encoding="utf-8").strip())
    assert row["claim_id"] == "FC007"

    art = executor.execute_mission(
        claim_id="FC001",
        mission_type="news_to_artifact",
        verdict="supported",
        title="갤럭시 S24 vs S23 1TB 출고가 비교",
        summary="2,127,400원 vs 1,962,400원 (+165,000원, +8.4%)",
        cited_evidence_ids=["EV_FC001_1", "EV_FC001_2"],
    )
    assert art.status == ToolStatus.OK
    assert Path(art.payload["artifact_path"]).exists()


# --- 3. MCP Server & External Agent Bridge ---------------------------------

def test_agent_environment_blocks_gold_leakage(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    write_jsonl(gold_path, [{"claim_id": "FC002", "label": "refuted"}])

    with pytest.raises(PermissionError, match="정답 누출 차단"):
        AgentEnvironment(claims_path=gold_path, out_path=tmp_path / "out.jsonl")


def test_mcp_exposes_no_filesystem_tools(tmp_path):
    claims_path = tmp_path / "claims.jsonl"
    write_jsonl(claims_path, [FC002.to_dict()])
    env = AgentEnvironment(claims_path=claims_path, out_path=tmp_path / "out.jsonl", tokenizer="bigram")
    server = MCPStdioServer(env)

    tools_resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {t["name"] for t in tools_resp["result"]["tools"]}
    assert not any(n in names for n in {"read_file", "list_dir", "run_shell", "execute_code"})


def test_agent_environment_enforces_budget_but_allows_finish(tmp_path):
    claims_path = tmp_path / "claims.jsonl"
    corpus_path = tmp_path / "corpus.jsonl"
    write_jsonl(claims_path, [FC002.to_dict()])
    write_jsonl(corpus_path, [{
        "evidence_id": APPLE.evidence_id,
        "title": APPLE.title,
        "text": APPLE.text,
        "publisher": APPLE.publisher,
    }])

    env = AgentEnvironment(
        claims_path=claims_path,
        corpus_path=corpus_path,
        out_path=tmp_path / "out.jsonl",
        tokenizer="bigram",
        max_tool_calls=1,
    )
    env.start_episode("FC002")

    # 1st tool call succeeds
    first = env.call_tool("read_evidence", {"evidence_id": "EV_FC002_apple"})
    assert first["status"] == "ok"

    # 2nd tool call is blocked by budget
    second = env.call_tool("search_evidence", {"query": "another query"})
    assert second["status"] == "blocked"
    assert "도구 호출 예산" in second["observation"]

    # finish_verification is still allowed so the agent can submit its verdict
    fin = env.finish_episode({
        "verdict": "refuted",
        "abstain": False,
        "cited_evidence_ids": ["EV_FC002_apple"],
        "justification": "05:00 PST = 22:00 KST",
        "stop_reason": "budget_exhausted",
    })
    assert fin.verdict == Verdict.REFUTED
    assert fin.usage.tool_calls == 1


def test_mcp_server_end_to_end_and_scoring_compatibility(tmp_path):
    claims_path = tmp_path / "claims.jsonl"
    corpus_path = tmp_path / "corpus.jsonl"
    gold_path = tmp_path / "gold.jsonl"
    out_path = tmp_path / "run.jsonl"

    write_jsonl(claims_path, [FC002.to_dict()])
    write_jsonl(corpus_path, [{
        "evidence_id": "EV_FC002_apple",
        "title": APPLE.title,
        "text": APPLE.text,
        "publisher": "Apple",
        "document_validity": "valid",
    }])
    write_jsonl(gold_path, [{"claim_id": "FC002", "label": "refuted", "review_status": "draft"}])

    env = AgentEnvironment(
        claims_path=claims_path,
        corpus_path=corpus_path,
        out_path=out_path,
        missions_dir=tmp_path / "missions",
        arm="C1",
        condition="sufficient",
        tokenizer="bigram",
    )
    server = MCPStdioServer(env)

    # 1. initialize & tools/list
    init_resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_resp["result"]["serverInfo"]["name"] == "uos-nlp-team5-factcheck-mcp"

    tools_resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
    assert {"start_episode", "search_evidence", "calculate_comparison",
            "execute_mission", FINISH_TOOL} <= tool_names

    # 2. start_episode -> search -> calc -> mission -> finish
    server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "start_episode", "arguments": {"claim_id": "FC002"}},
    })
    server.handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "search_evidence", "arguments": {"query": "Pre-orders January 19 PST"}},
    })
    server.handle_request({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {
            "name": "calculate_comparison",
            "arguments": {"op": "tz_convert", "time": "2024-01-19 05:00", "from_tz": "PST", "to_tz": "KST"},
        },
    })
    server.handle_request({
        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
        "params": {
            "name": "execute_mission",
            "arguments": {
                "mission_type": "event_manager",
                "verdict": "refuted",
                "title": "Vision Pro 사전예약",
                "summary": "22:00 KST로 시간대 정정",
                "cited_evidence_ids": ["EV_FC002_apple"],
                "correction": "2024-01-19 22:00 KST",
                "distortion_type": "timezone_or_date_error",
                "event_start_kst": "2024-01-19 22:00",
            },
        },
    })
    finish_resp = server.handle_request({
        "jsonrpc": "2.0", "id": 7, "method": "tools/call",
        "params": {
            "name": FINISH_TOOL,
            "arguments": {
                "verdict": "refuted",
                "abstain": False,
                "cited_evidence_ids": ["EV_FC002_apple"],
                "justification": "05:00 PST는 22:00 KST이므로 오전 5시 한국시간 주장은 반박됨",
                "correction": "2024-01-19 22:00 KST",
                "stop_reason": "evidence_sufficient",
                "distortion_type": "timezone_or_date_error",
                "problematic_span": "오전 5시(한국시간)",
                "mission_type": "event_manager",
            },
        },
    })
    payload = json.loads(finish_resp["result"]["content"][0]["text"])
    assert payload["status"] == "finished"
    assert payload["result"]["distortion_type"] == "timezone_or_date_error"
    assert payload["result"]["mission_type"] == "event_manager"

    # 3. Score with the existing scorer!
    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = score_run(rows, load_gold(gold_path))
    assert summary["conditions"][0]["accuracy"]["value"] == 1.0


# --- 4. Run Scoring & Gold Boundary ----------------------------------------

def _run_row(claim_id, arm, verdict, condition="sufficient", cost=0.0, abstain=False):
    return {
        "config": {
            "run_id": "r", "condition": condition, "policy": "mcp_skill_agent",
            "model_id": "external-agent", "prompt_version": "skill-v1", "data_version": "d1",
            "seed": 0, "code_commit": None, "replay": False, "extra": {}, "arm": arm,
        },
        "result": {
            "claim_id": claim_id, "verdict": verdict, "abstain": abstain,
            "cited_evidence_ids": [], "justification": "j", "correction": None,
            "stop_reason": "evidence_sufficient", "execution_status": "ok",
            "steps": 1, "error": None, "events": [],
            "usage": {
                "input_tokens": 0, "output_tokens": 0, "cached_tokens": 0,
                "llm_calls": 0, "tool_calls": 1, "external_calls": 0,
                "cost_usd": cost, "elapsed_ms": 0,
            },
        },
    }


def test_score_run_and_transitions(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    write_jsonl(gold_path, [
        {"claim_id": "FC002", "label": "refuted", "rationale": "r", "review_status": "draft"},
        {"claim_id": "FC004", "label": "supported", "rationale": "r", "review_status": "draft"},
        {"claim_id": "FC038", "label": None, "rationale": "r", "review_status": "pending"},
    ])
    gold = load_gold(gold_path)
    assert gold["FC002"] == Verdict.REFUTED
    assert gold["FC038"] is None

    c1 = [_run_row("FC002", Arm.C1, "supported"), _run_row("FC004", Arm.C1, "supported")]
    c2 = [_run_row("FC002", Arm.C2, "refuted"), _run_row("FC004", Arm.C2, "refuted")]

    summary_no_grades = score_run(c2, gold)
    assert summary_no_grades["conditions"][0]["gsr"] is None

    grades = {
        ("FC002", Arm.C2, "sufficient"): {"e": True, "t": True},
        ("FC004", Arm.C2, "sufficient"): {"e": False, "t": False},
    }
    summary_with_grades = score_run(c2, gold, grades)
    assert summary_with_grades["conditions"][0]["gsr"] == {"numerator": 1, "denominator": 2, "value": 0.5}

    trans = score_transition(c1, c2, gold)
    assert trans["pairs"] == 2
    assert trans["recovery"]["value"] == 1.0
    assert trans["harm"]["value"] == 1.0

    metrics = ungraded_metrics([_run_row("FC002", Arm.C1, "refuted"), _run_row("FC038", Arm.C1, "supported")], gold)
    assert metrics["episodes"] == 2
    assert metrics["accuracy"]["denominator"] == 1

    graded = to_graded([_run_row("FC002", Arm.C1, "refuted")], {"FC002": Verdict.REFUTED}, {})
    assert graded[0].v is True
    assert graded[0].grounded is False
