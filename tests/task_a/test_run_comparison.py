"""Offline tests for scripts/run_comparison.py (no model is called)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _mod():
    spec = importlib.util.spec_from_file_location("run_comparison", ROOT / "scripts/run_comparison.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sample_is_stratified_and_fixed():
    mod = _mod()
    sample = mod.stratified_sample(ROOT / "data/task_a/gold.jsonl")
    gold = {r["claim_id"]: r["label"] for r in map(json.loads, open(ROOT / "data/task_a/gold.jsonl"))}
    labels = [gold[c] for c in sample]
    assert len(sample) == 20
    assert labels.count("refuted") == 11 and labels.count("not_enough_evidence") == 1
    assert sample == mod.stratified_sample(ROOT / "data/task_a/gold.jsonl")
    assert "FC038" not in sample  # 판정 보류


def _cmd(mod, condition, tmp_path):
    claim = {"claim_id": "FC002", "text": "t"}
    paths = mod.job_paths(tmp_path / "raw", tmp_path / "work", "haiku", condition, "FC002")
    return mod.build_command("haiku", condition, claim, paths, "exp-t", "9.9.9")


def _flag(cmd, name):
    return cmd[cmd.index(name) + 1]


def test_every_condition_disables_user_settings_and_other_mcp(tmp_path):
    mod = _mod()
    for cond in mod.CONDITIONS:
        cmd, prompt = _cmd(mod, cond, tmp_path)
        assert {"--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"} <= set(cmd)
        assert _flag(cmd, "--setting-sources") == "project"
        assert prompt and prompt not in cmd  # prompt goes on stdin


def test_tools_per_condition(tmp_path):
    mod = _mod()
    closed, _ = _cmd(mod, "closed_book", tmp_path)
    web, _ = _cmd(mod, "plain_web", tmp_path)
    harness, prompt = _cmd(mod, "harness", tmp_path)

    assert _flag(closed, "--tools") == "" and "--allowedTools" not in closed
    assert _flag(web, "--tools") == "WebSearch,WebFetch"
    assert _flag(harness, "--tools") == ""
    assert _flag(harness, "--allowedTools") == "mcp__factcheck-mission"
    server = json.loads(_flag(harness, "--mcp-config"))["mcpServers"]["factcheck-mission"]["args"]
    assert server[server.index("--arm") + 1] == "C1"
    assert "corpus_c1.jsonl" in server[server.index("--corpus") + 1]
    assert "FC002" in prompt
    skill = _flag(harness, "--append-system-prompt")
    assert "finish_verification" in skill and not skill.startswith("---")
    # Baselines never get the Skill.
    assert "--append-system-prompt" not in closed and "--append-system-prompt" not in web


def test_score_counts_failures_and_uses_gold(tmp_path):
    mod = _mod()
    raw = tmp_path / "raw"
    recs = [("FC002", "refuted", "ok"), ("FC003", "supported", "ok"), ("FC004", None, "timeout")]
    for cid, verdict, status in recs:
        d = raw / "haiku" / "harness"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{cid}.json").write_text(json.dumps({
            "model_alias": "haiku", "condition": "harness", "claim_id": cid, "verdict": verdict,
            "abstain": False, "execution_status": status, "cost_usd": 0.01, "duration_ms": 1000,
            "num_turns": 3, "tool_uses": {"x": 1}, "leak_markers": []}))
    summary = mod.score(raw, tmp_path / "out", ROOT / "data/task_a/gold.jsonl", ["FC002", "FC003", "FC004"])
    row = summary["table"][0]
    assert row["accuracy"]["denominator"] == 3      # the timeout stays in the denominator
    assert row["accuracy"]["numerator"] == 1        # FC002 refuted is right, FC003 is refuted in gold
    assert row["coverage"]["numerator"] == 2
    assert (tmp_path / "out/episodes.jsonl").exists()
