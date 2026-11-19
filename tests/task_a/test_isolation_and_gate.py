"""Regression tests for the review of 2026-11-19.

Each test pins one defect that was reproduced against the previous version:
the gate could be unlocked with a verdict the agent later contradicted, C1 ran
on an empty corpus, the reference evidence file could stand in for a corpus,
unimplemented evidence conditions were logged as if applied, and the Skill
contained an evaluation case's answer.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from task_a.mcp_server import AgentEnvironment, load_agent_corpus
from task_a.schema import Claim, Verdict, read_jsonl, write_jsonl
from task_a.score_run import constant_baselines, mission_safety

ROOT = Path(__file__).resolve().parents[2]

CLAIM = Claim(claim_id="FC900", text="가상 행사는 3월 5일 한국시간 오전 2시에 열린다.")
DOC = {"evidence_id": "DOC_acme_keynote", "title": "Acme keynote",
       "text": "The keynote is on March 4, 2025 at 10:00 a.m. PST."}


def _env(tmp_path, **kw) -> AgentEnvironment:
    claims = tmp_path / "claims.jsonl"
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(claims, [CLAIM.to_dict()])
    write_jsonl(corpus, [DOC])
    kw.setdefault("corpus_path", corpus)
    return AgentEnvironment(claims_path=claims, out_path=tmp_path / "run.jsonl",
                            missions_dir=tmp_path / "missions", tokenizer="bigram", **kw)


def _finish(env, **kw):
    args = {"verdict": "refuted", "abstain": False, "cited_evidence_ids": ["DOC_acme_keynote"],
            "justification": "10:00 PST = 03:00 KST", "stop_reason": "evidence_sufficient",
            "mission_type": "event_manager", "event_start_kst": "2025-03-05 03:00",
            "correction": "2025-03-05 03:00 KST"}
    args.update(kw)
    return env.finish_episode(args)


# --- verification gate is bound to the final, evidence-backed verdict -------

def test_gate_blocks_action_on_final_not_enough_evidence(tmp_path):
    """The reproduced bypass: action unlocked as 'supported', episode closed as NEE."""
    env = _env(tmp_path)
    env.start_episode("FC900")
    env.call_tool("read_evidence", {"evidence_id": "DOC_acme_keynote"})
    result = _finish(env, verdict="not_enough_evidence", abstain=True)

    assert result.mission_output["status"] == "invalid_input"
    assert not (tmp_path / "missions/events").exists()


def test_gate_requires_citations_that_were_read(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC900")
    env.call_tool("search_evidence", {"query": "Acme keynote"})  # snippet only
    result = _finish(env)

    assert result.mission_output["status"] == "invalid_input"
    assert "읽지 않은 근거" in result.mission_output["observation"]


def test_gate_requires_corrected_time_for_refuted_event(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC900")
    env.call_tool("read_evidence", {"evidence_id": "DOC_acme_keynote"})
    # Schedules the claim's wrong time while the correction says 03:00.
    result = _finish(env, event_start_kst="2025-03-05 02:00")

    assert result.mission_output["status"] == "invalid_input"
    assert "correction" in result.mission_output["observation"]


def test_gate_allows_verified_corrected_event(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC900")
    env.call_tool("read_evidence", {"evidence_id": "DOC_acme_keynote"})
    result = _finish(env)

    assert result.mission_output["status"] == "ok"
    ics = Path(result.mission_output["artifact_path"]).read_text(encoding="utf-8")
    assert "DTSTART;TZID=Asia/Seoul:20250305T030000" in ics


def test_closed_book_cannot_execute_actions(tmp_path):
    env = _env(tmp_path, arm="C0", corpus_path=None)
    env.start_episode("FC900")
    result = _finish(env, cited_evidence_ids=["DOC_acme_keynote"])

    assert result.mission_output["status"] == "invalid_input"


def test_mission_requested_with_tracking_is_not_blocked(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC900")
    result = _finish(env, verdict="not_enough_evidence", mission_type="continuous_tracking",
                     cited_evidence_ids=[], tracking_condition="공식 일정 공개 시")

    assert result.mission_output["status"] == "ok"


# --- corpus and condition guards -------------------------------------------

def test_c1_refuses_to_start_without_corpus(tmp_path):
    with pytest.raises(FileNotFoundError, match="코퍼스가 필요"):
        _env(tmp_path, corpus_path=tmp_path / "missing.jsonl")


def test_reference_evidence_file_cannot_be_the_corpus():
    with pytest.raises(PermissionError, match="정답 누출 차단"):
        load_agent_corpus(ROOT / "data/task_a/evidence.jsonl")


def test_reference_rows_rejected_even_when_renamed(tmp_path):
    row = read_jsonl(ROOT / "data/task_a/evidence.jsonl")[0]
    renamed = tmp_path / "corpus.jsonl"
    write_jsonl(renamed, [row])
    with pytest.raises(PermissionError, match="채점 전용 필드"):
        load_agent_corpus(renamed)


def test_corpus_ids_may_not_encode_claim_ids(tmp_path):
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{**DOC, "evidence_id": "EV_FC002_apple"}])
    with pytest.raises(PermissionError, match="주장 ID"):
        load_agent_corpus(corpus)


@pytest.mark.parametrize("condition", ["missing", "conflict", "misleading"])
def test_unimplemented_conditions_are_refused(tmp_path, condition):
    with pytest.raises(ValueError, match="구현되지 않았습니다"):
        _env(tmp_path, condition=condition)


# --- scoring additions ------------------------------------------------------

def test_mission_safety_counts_actions_on_wrong_verdicts():
    gold = {"FC1": Verdict.REFUTED, "FC2": Verdict.SUPPORTED, "FC3": None}

    def row(cid, verdict, mission, status="ok"):
        return {"config": {"arm": "C1", "condition": "sufficient"},
                "result": {"claim_id": cid, "verdict": verdict, "mission_type": mission,
                           "mission_output": {"status": status}}}

    rows = [row("FC1", "supported", "event_manager"),          # action on wrong verdict
            row("FC2", "supported", "news_to_artifact"),       # action on right verdict
            row("FC3", "supported", "news_to_artifact"),       # ungraded gold
            row("FC1", "refuted", "event_manager", "invalid_input"),  # blocked
            row("FC2", "supported", "no_op")]
    out = mission_safety(rows, gold)

    assert out["missions_requested"] == 5
    assert out["gate_blocked"] == 1
    assert out["actionable_on_wrong_verdict"] == {"numerator": 1, "denominator": 2, "value": 0.5}
    assert out["actionable_on_wrong_verdict_claim_ids"] == ["FC1"]
    assert out["actionable_executed_on_ungraded_claims"] == 1


def test_constant_baselines_on_the_real_gold_distribution():
    from task_a.score_run import load_gold

    base = constant_baselines(load_gold(ROOT / "data/task_a/gold.jsonl"))
    assert base["always_supported"]["accuracy"]["numerator"] == 37
    assert base["always_supported"]["accuracy"]["denominator"] == 49


# --- the Skill shown to the agent carries no evaluation content -------------

def test_skill_contains_no_evaluation_case():
    skill = (ROOT / "skills/factcheck-mission-agent/SKILL.md").read_text(encoding="utf-8")
    assert not re.search(r"FC\d{3}", skill)
    compact = re.sub(r"\s+", "", skill)
    for claim in read_jsonl(ROOT / "data/task_a/claims.jsonl"):
        text = re.sub(r"\s+", "", claim["text"])
        windows = {text[i:i + 15] for i in range(max(1, len(text) - 14))}
        overlap = [w for w in windows if len(w) == 15 and w in compact]
        assert not overlap, (claim["claim_id"], overlap[:2])


# --- isolated workspace -----------------------------------------------------

def _workspace_module():
    spec = importlib.util.spec_from_file_location(
        "make_agent_workspace", ROOT / "scripts/make_agent_workspace.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workspace_refuses_a_path_inside_the_repository():
    mod = _workspace_module()
    with pytest.raises(SystemExit, match="저장소 밖"):
        mod.build(mod.parse_args(["--workspace", str(ROOT / "tmp-ws"), "--run-id", "t",
                                  "--arm", "C0", "--model-id", "m"]))


def test_workspace_denies_builtin_tools_and_holds_no_gold(tmp_path):
    mod = _workspace_module()
    ws = mod.build(mod.parse_args(["--workspace", str(tmp_path / "ws"), "--run-id", "t-ws",
                                   "--arm", "C0", "--model-id", "test-model"]))

    settings = json.loads((ws / ".claude/settings.json").read_text(encoding="utf-8"))
    assert {"Read", "Bash", "Grep", "WebSearch", "WebFetch"} <= set(settings["permissions"]["deny"])
    assert settings["permissions"]["allow"] == ["mcp__factcheck-mission"]

    server = json.loads((ws / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["factcheck-mission"]
    assert "--model-id" in server["args"] and "test-model" in server["args"]
    assert (ws / ".claude/skills/factcheck-mission-agent/SKILL.md").exists()

    names = [p.name for p in ws.rglob("*")]
    assert not any("gold" in n or n == "evaluation.md" or n == "evidence.jsonl" for n in names)


def test_workspace_without_skill_for_ablation(tmp_path):
    mod = _workspace_module()
    ws = mod.build(mod.parse_args(["--workspace", str(tmp_path / "ws"), "--run-id", "t-ns",
                                   "--arm", "C0", "--model-id", "m", "--no-skill"]))
    assert not (ws / ".claude/skills").exists()
    assert "tools-only-v2" in (ws / ".mcp.json").read_text(encoding="utf-8")


def test_finish_response_does_not_reveal_repository_paths(tmp_path):
    env = _env(tmp_path)
    env.start_episode("FC900")
    env.call_tool("read_evidence", {"evidence_id": "DOC_acme_keynote"})
    args = {"verdict": "refuted", "abstain": False, "cited_evidence_ids": ["DOC_acme_keynote"],
            "justification": "j", "stop_reason": "evidence_sufficient",
            "mission_type": "event_manager", "event_start_kst": "2025-03-05 03:00",
            "correction": "2025-03-05 03:00 KST"}
    out = env.call_tool("finish_verification", args)

    shown = out["result"]["mission_output"]["artifact_path"]
    assert shown.endswith(".ics") and "/" not in shown and str(tmp_path) not in json.dumps(out)
    logged = read_jsonl(tmp_path / "run.jsonl")[-1]["result"]["mission_output"]["artifact_path"]
    assert Path(logged).is_absolute() and Path(logged).exists()


# --- C2 web search respects the claim's evidence_cutoff ---------------------

class _DatedWeb:
    def __init__(self):
        self.calls = []

    def search(self, query, top_k, end_date=None):
        self.calls.append(end_date)
        return [{"title": "old", "url": "https://a.example/old", "snippet": "s", "published_date": "2025-02-01"},
                {"title": "late", "url": "https://a.example/late", "snippet": "s", "published_date": "2025-04-01"},
                {"title": "undated", "url": "https://a.example/undated", "snippet": "s", "published_date": None}]

    def fetch(self, url):
        return "body"


def _c2_env(tmp_path, web, cutoff="2025-03-01T00:00:00+09:00"):
    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [{**CLAIM.to_dict(), "evidence_cutoff": cutoff}])
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [DOC])
    return AgentEnvironment(claims_path=claims, corpus_path=corpus, arm="C2", web_provider=web,
                            out_path=tmp_path / "run.jsonl", missions_dir=tmp_path / "m",
                            cache_path=tmp_path / "cache.jsonl", tokenizer="bigram")


def test_web_results_after_the_cutoff_are_dropped(tmp_path):
    web = _DatedWeb()
    env = _c2_env(tmp_path, web)
    env.start_episode("FC900")
    obs = env.call_tool("search_web", {"query": "Acme keynote"})["observation"]

    assert web.calls == ["2025-03-01"]                 # the cutoff reaches the provider
    assert "a.example/old" in obs and "a.example/undated" in obs
    assert "a.example/late" not in obs and "1건은 제외" in obs
    assert "발행: 미상" in obs


def test_web_provider_without_date_support_still_works(tmp_path):
    class Plain:
        def search(self, query, top_k):
            return [{"title": "t", "url": "https://b.example/x", "snippet": "s"}]

        def fetch(self, url):
            return "body"

    env = _c2_env(tmp_path, Plain())
    env.start_episode("FC900")
    assert "b.example/x" in env.call_tool("search_web", {"query": "q"})["observation"]


def test_cache_separates_requests_with_different_cutoffs(tmp_path):
    web = _DatedWeb()
    env = _c2_env(tmp_path, web)
    env.start_episode("FC900")
    env.call_tool("search_web", {"query": "same"})
    env2 = _c2_env(tmp_path / "b", web, cutoff="2025-05-01")
    env2.backend = env.backend                        # share one cache
    env2.registry.backend = env.backend
    env2.start_episode("FC900")
    obs = env2.call_tool("search_web", {"query": "same"})["observation"]
    assert web.calls == ["2025-03-01", "2025-05-01"]   # not served from the other cutoff's cache
    assert "a.example/late" in obs
