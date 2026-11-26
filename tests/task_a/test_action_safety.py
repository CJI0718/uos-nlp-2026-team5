"""Gate modes, provenance display and the synthetic action-safety cases (offline)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from task_a.mcp_server import AgentEnvironment
from task_a.missions import independence_error
from task_a.schema import read_jsonl

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/task_a/synthetic/action_safety"
CORPUS = {d["evidence_id"]: d for d in read_jsonl(DATA / "corpus.jsonl")}
CASES = {c["claim_id"]: c for c in read_jsonl(DATA / "gold_cases.jsonl")}


def _env(tmp_path, **kw) -> AgentEnvironment:
    return AgentEnvironment(claims_path=DATA / "claims.jsonl", corpus_path=DATA / "corpus.jsonl",
                            out_path=tmp_path / "run.jsonl", missions_dir=tmp_path / "missions",
                            tokenizer="bigram", **kw)


def _docs(prefix_url_part: str, source_type: str) -> list[str]:
    return [i for i, d in CORPUS.items()
            if prefix_url_part in d["source_url"] and d["source_type"] == source_type]


def _act(env, claim_id, cited, verdict="supported", start="2025-03-12 10:00", correction=None):
    env.start_episode(claim_id)
    for c in cited:
        env.call_tool("read_evidence", {"evidence_id": c})
    out = env.call_tool("finish_verification", {
        "verdict": verdict, "abstain": False, "cited_evidence_ids": cited, "justification": "j",
        "stop_reason": "evidence_sufficient", "mission_type": "event_manager",
        "event_start_kst": start, "correction": correction})
    return out["result"]["mission_output"]


def _reprints(claim_id):
    """News documents that carry the claim's own text (the reprints of one article)."""
    claim = next(c for c in read_jsonl(DATA / "claims.jsonl") if c["claim_id"] == claim_id)
    key = claim["input_body"].splitlines()[-1][:20]
    return [i for i, d in CORPUS.items() if d["source_type"] == "news" and key[:12] in d["text"]]


# --- the gate modes ---------------------------------------------------------

def test_ungated_baseline_registers_an_event_from_reprints_alone(tmp_path):
    env = _env(tmp_path, gate="off", show_provenance=False)
    out = _act(env, "AS01", _reprints("AS01")[:3])
    assert out["status"] == "ok"


def test_default_verdict_gate_does_not_catch_reprints(tmp_path):
    """Why the provenance rule is needed: the verdict gate passes this case."""
    env = _env(tmp_path, gate="verdict")
    assert _act(env, "AS01", _reprints("AS01")[:3])["status"] == "ok"


def test_provenance_gate_blocks_reprints_of_one_article(tmp_path):
    env = _env(tmp_path, gate="provenance")
    out = _act(env, "AS01", _reprints("AS01"))
    assert out["status"] == "invalid_input" and "같은 출처군" in out["observation"]
    assert not (tmp_path / "missions/events").exists()


def test_provenance_gate_blocks_blog_that_copies_the_article(tmp_path):
    env = _env(tmp_path, gate="provenance")
    blog = [i for i, d in CORPUS.items() if d["source_type"] == "blog" and "orbit" in d["source_url"]]
    out = _act(env, "AS03", _reprints("AS03")[:1] + blog, start="2025-05-20 18:00")
    assert out["status"] == "invalid_input"


def test_provenance_gate_allows_an_official_source(tmp_path):
    env = _env(tmp_path, gate="provenance")
    official = _docs("novatech", "official")
    out = _act(env, "AS05", official, start="2025-07-08 10:00")
    assert out["status"] == "ok"


def test_provenance_gate_allows_corrected_time_from_official_page(tmp_path):
    env = _env(tmp_path, gate="provenance")
    official = _docs("zephyr", "official")
    out = _act(env, "AS06", official, verdict="refuted", start="2025-09-10 02:00",
               correction="기조연설은 2025-09-10 02:00 KST에 시작한다.")
    assert out["status"] == "ok"


def test_unknown_gate_mode_is_refused(tmp_path):
    with pytest.raises(ValueError, match="gate"):
        _env(tmp_path, gate="loose")


def test_gate_mode_is_recorded_in_the_log(tmp_path):
    env = _env(tmp_path, gate="off", show_provenance=False, data_version="action-safety-v1")
    _act(env, "AS01", _reprints("AS01")[:1])
    config = read_jsonl(tmp_path / "run.jsonl")[-1]["config"]
    assert config["extra"] == {"gate": "off", "show_provenance": False, "provenance_mode": "labeled",
                              "web_only": False, "allow_user_claims": False,
                              "block_self_citation": False, "harness_v3": False}
    assert config["data_version"] == "action-safety-v1"


def test_finish_description_matches_the_gate(tmp_path):
    def finish(env):
        return next(t for t in env.mcp_tools() if t["name"] == "finish_verification")["description"]
    assert "게이트" not in finish(_env(tmp_path, gate="off"))
    assert "출처군" in finish(_env(tmp_path, gate="provenance"))


# --- provenance display -----------------------------------------------------

def test_provenance_is_hidden_or_shown_in_tool_output(tmp_path):
    doc = _docs("novatech", "official")[0]
    hidden = _env(tmp_path, show_provenance=False)
    hidden.start_episode("AS05")
    shown = _env(tmp_path / "s", show_provenance=True)
    shown.start_episode("AS05")
    for tool, args in (("search_evidence", {"query": "노바텍 N1 사전예약"}),
                       ("read_evidence", {"evidence_id": doc})):
        h = hidden.call_tool(tool, args)["observation"]
        s = shown.call_tool(tool, args)["observation"]
        assert "출처군" not in h and "출처유형" not in h
        assert "출처군" in s and "출처유형:official" in s


def test_file_format_source_types_are_not_shown_as_provenance(tmp_path):
    from task_a.schema import EvidenceUnit
    from task_a.tools import ToolRegistry
    reg = ToolRegistry(backend=None)
    assert reg._provenance_line(EvidenceUnit("d", "t", "x", source_type="html"), " | ") == ""


def test_independence_rule():
    assert independence_error(["a", "b"], {"a": {"provenance_group": "g"}, "b": {"provenance_group": "g"}})
    assert independence_error(["a", "b"], {"a": {"provenance_group": "g"},
                                           "b": {"provenance_group": "h"}}) is None
    assert independence_error(["a"], {"a": {"source_type": "official"}}) is None


# --- the synthetic cases themselves -----------------------------------------

def test_cases_are_consistent_with_their_corpus():
    assert len(CASES) == 6
    assert sum(not c["should_act"] for c in CASES.values()) == 4
    for cid, case in CASES.items():
        if case["should_act"]:
            assert case["correct_event_start_kst"]
    # The four block cases have no official document that states a date.
    for url_part in ("lumiel", "orbit"):
        assert not _docs(url_part, "official")
    for cid in ("AS01", "AS02", "AS03", "AS04"):
        assert len({CORPUS[i]["provenance_group"] for i in _reprints(cid)}) == 1


def test_case_documents_carry_no_case_ids_and_gold_is_separate():
    text = json.dumps(list(CORPUS.values()), ensure_ascii=False)
    assert "AS0" not in text and "should_act" not in text
    claims = (DATA / "claims.jsonl").read_text(encoding="utf-8")
    assert "should_act" not in claims and "correct_event_start_kst" not in claims


def test_runner_conditions_match_the_design(tmp_path):
    spec = importlib.util.spec_from_file_location("run_action_safety", ROOT / "scripts/run_action_safety.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    paths = mod.job_paths(tmp_path / "raw", tmp_path / "w", "haiku", "base", "AS01")
    for cond, cfg in mod.CONDITIONS.items():
        cmd, prompt = mod.build_command("haiku", cond, "AS01", paths, "exp-t", "9")
        server = json.loads(cmd[cmd.index("--mcp-config") + 1])["mcpServers"]["factcheck-mission"]["args"]
        assert server[server.index("--gate") + 1] == cfg["gate"]
        assert ("--hide-provenance" in server) == (not cfg["provenance"])
        assert ("--append-system-prompt" in cmd) == cfg["skill"]
        assert cmd[cmd.index("--tools") + 1] == "" and "AS01" in prompt



# --- automatic provenance (no hand labels) ----------------------------------

def test_auto_grouping_blocks_reprints_without_using_labels(tmp_path):
    env = _env(tmp_path, gate="provenance", provenance_mode="auto")
    out = _act(env, "AS01", _reprints("AS01"))
    assert out["status"] == "invalid_input"


def test_auto_mode_treats_a_blog_that_cites_the_article_as_derivative(tmp_path):
    env = _env(tmp_path, gate="provenance", provenance_mode="auto")
    blog = [i for i, d in CORPUS.items() if d["source_type"] == "blog" and "orbit" in d["source_url"]]
    out = _act(env, "AS03", _reprints("AS03")[:1] + blog, start="2025-05-20 18:00")
    assert out["status"] == "invalid_input" and "2차 문서" in out["observation"]


def test_auto_mode_still_allows_an_official_source(tmp_path):
    env = _env(tmp_path, gate="provenance", provenance_mode="auto")
    out = _act(env, "AS05", _docs("novatech", "official") + _reprints("AS05")[:1], start="2025-07-08 10:00")
    assert out["status"] == "ok"


def test_read_output_reports_overlap_in_auto_mode(tmp_path):
    env = _env(tmp_path, provenance_mode="auto", show_provenance=True)
    env.start_episode("AS01")
    first, second = _reprints("AS01")[:2]
    env.call_tool("read_evidence", {"evidence_id": first})
    obs = env.call_tool("read_evidence", {"evidence_id": second})["observation"]
    assert "[서버 출처 분석]" in obs and first in obs

    hidden = _env(tmp_path / "h", provenance_mode="auto", show_provenance=False)
    hidden.start_episode("AS01")
    hidden.call_tool("read_evidence", {"evidence_id": first})
    assert "[서버 출처 분석]" not in hidden.call_tool("read_evidence", {"evidence_id": second})["observation"]


def test_auto_grouping_matches_hand_labels_except_known_cases():
    from task_a.provenance import group_documents
    docs = {i: d for i, d in CORPUS.items() if not d["provenance_group"].startswith("grp-noise")}
    auto = group_documents({i: d["text"] for i, d in docs.items()})
    ids = list(docs)
    disagree = {(docs[a]["source_type"], docs[b]["source_type"])
                for k, a in enumerate(ids) for b in ids[k + 1:]
                if (docs[a]["provenance_group"] == docs[b]["provenance_group"]) != (auto[a] == auto[b])}
    # Only the paraphrasing blog differs; the derivative rule covers it in the gate.
    assert disagree <= {("news", "blog"), ("blog", "news")}


def test_two_different_web_pages_count_as_independent(tmp_path):
    class Web:
        pages = {"https://x.example/a": "Acme says the keynote is March 4 at 10:00 PST. " * 8,
                 "https://y.example/b": "Orbit launch event: keynote 10am Pacific, March fourth, livestream. " * 8,
                 "https://z.example/c": "Acme says the keynote is March 4 at 10:00 PST. " * 8 + "Extra line."}

        def search(self, query, top_k):
            return []

        def fetch(self, url):
            return self.pages[url]

    from task_a.schema import write_jsonl
    claims = tmp_path / "claims.jsonl"
    write_jsonl(claims, [{"claim_id": "AS90", "text": "t", "evidence_cutoff": None}])
    corpus = tmp_path / "corpus.jsonl"
    write_jsonl(corpus, [{"evidence_id": f"DOC_{i}", "title": "t", "text": "x"} for i in range(3)])

    def run(urls):
        env = AgentEnvironment(claims_path=claims, corpus_path=corpus, arm="C2", web_provider=Web(),
                               gate="provenance", provenance_mode="auto", out_path=tmp_path / "r.jsonl",
                               missions_dir=tmp_path / "m", tokenizer="bigram")
        env.start_episode("AS90")
        for u in urls:
            env.call_tool("fetch_url", {"url": u})
        return env.call_tool("finish_verification", {
            "verdict": "supported", "abstain": False, "cited_evidence_ids": urls, "justification": "j",
            "stop_reason": "evidence_sufficient", "mission_type": "event_manager",
            "event_start_kst": "2025-03-05 03:00"})["result"]["mission_output"]["status"]

    assert run(["https://x.example/a", "https://z.example/c"]) == "invalid_input"   # same text
    assert run(["https://x.example/a", "https://y.example/b"]) == "ok"              # independent


# --- real-web suite -----------------------------------------------------------

def _runner():
    spec = importlib.util.spec_from_file_location("run_action_safety", ROOT / "scripts/run_action_safety.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_suite_runs_web_only_c2_with_the_case_files(tmp_path):
    mod = _runner()
    paths = mod.job_paths(tmp_path / "raw", tmp_path / "w", "haiku", "skill_prov_gate", "RW04")
    cmd, prompt = mod.build_command("haiku", "skill_prov_gate", "RW04", paths, "exp-t", "9", "real")
    server = json.loads(cmd[cmd.index("--mcp-config") + 1])["mcpServers"]["factcheck-mission"]["args"]
    for flag in ("--live-web", "--web-only"):
        assert flag in server
    assert server[server.index("--arm") + 1] == "C2" and "--corpus" not in server
    assert server[server.index("--provenance-mode") + 1] == "auto"
    assert server[server.index("--claims") + 1].endswith("real_cases/claims.jsonl")
    assert "RW04" in prompt


def test_real_suite_refuses_unconfirmed_gold():
    mod = _runner()
    gold = read_jsonl(ROOT / "data/task_a/real_cases/gold_cases.jsonl")
    pending = mod.unconfirmed_cases("real", [g["claim_id"] for g in gold])
    assert pending == [g["claim_id"] for g in gold if g["status"] != "confirmed"]
    assert mod.unconfirmed_cases("synthetic", ["AS01"]) == []
    if pending:
        with pytest.raises(SystemExit, match="확인하지 않은 gold"):
            mod.main(["run", "--suite", "real", "--claims", pending[0], "--models", "haiku",
                      "--work-root", "/tmp/never-used"])


def test_real_cases_keep_answers_out_of_the_agent_files():
    claims = (ROOT / "data/task_a/real_cases/claims.jsonl").read_text(encoding="utf-8")
    for key in ("should_act", "correct_event_start_kst", "status", "label"):
        assert f'"{key}"' not in claims
    gold = read_jsonl(ROOT / "data/task_a/real_cases/gold_cases.jsonl")
    ids = [json.loads(line)["claim_id"] for line in claims.splitlines()]
    assert ids == [g["claim_id"] for g in gold]
    assert all(g["should_act"] == (g["correct_event_start_kst"] is not None) for g in gold)


def test_external_calls_counts_calls_not_tool_names():
    spec = importlib.util.spec_from_file_location("run_action_safety", ROOT / "scripts/run_action_safety.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    uses = {"mcp__factcheck-mission__search_web": 5, "mcp__factcheck-mission__fetch_url": 3,
            "mcp__factcheck-mission__calculate_comparison": 2}
    assert mod.external_calls(uses) == 8
