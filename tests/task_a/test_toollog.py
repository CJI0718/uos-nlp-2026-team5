"""Cache determinism and append-only resume, the two cost-control guarantees."""

from __future__ import annotations

import json

import pytest

from task_a.mock import MockBackend
from task_a.retrieve import BigramTokenizer, CorpusBackend
from task_a.schema import (
    AgentResult, EvidenceUnit, ExecutionStatus, ToolStatus, Usage, Verdict,
)
from task_a.toollog import (
    MISSING, CachingBackend, RunConfig, RunLog, ToolCache, cache_key, summarise_usage,
)
from task_a.tools import ToolRegistry

DOC = EvidenceUnit(evidence_id="EV1", title="t", text="본문", source_url="https://example.com/a")


class CountingWeb:
    def __init__(self, results=None, page="원문 본문"):
        self.results = results if results is not None else [
            {"title": "Apple", "url": "https://www.apple.com/x", "snippet": "5:00 a.m. PST"}]
        self.page = page
        self.search_calls = 0
        self.fetch_calls = 0

    def search(self, query, top_k):
        self.search_calls += 1
        return self.results[:top_k]

    def fetch(self, url):
        self.fetch_calls += 1
        return self.page


def make_config(**overrides) -> RunConfig:
    base = dict(run_id="exp-001", condition="C2", policy="react", model_id="m",
                prompt_version="p1", data_version="d1")
    base.update(overrides)
    return RunConfig(**base)


def make_result(claim_id="FC002", verdict=Verdict.REFUTED, **usage) -> AgentResult:
    return AgentResult(
        claim_id=claim_id, verdict=verdict, abstain=False, cited_evidence_ids=["EV1"],
        justification="j", correction=None, stop_reason="evidence_sufficient",
        execution_status=ExecutionStatus.OK, usage=Usage(**usage))


# --- cache key -------------------------------------------------------------

def test_cache_key_ignores_argument_order():
    assert cache_key("search_web", {"a": 1, "b": 2}) == cache_key("search_web", {"b": 2, "a": 1})


def test_cache_key_separates_tools_and_values():
    assert cache_key("search_web", {"q": "x"}) != cache_key("fetch_url", {"q": "x"})
    assert cache_key("search_web", {"q": "x"}) != cache_key("search_web", {"q": "y"})


# --- cache behaviour -------------------------------------------------------

def test_second_identical_call_is_served_from_cache(tmp_path):
    web = CountingWeb()
    cache = ToolCache(tmp_path / "cache.jsonl")
    backend = CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=web), cache)

    first = backend.web_search("Vision Pro", 5)
    second = backend.web_search("Vision Pro", 5)

    assert first == second
    assert web.search_calls == 1
    assert backend.served_from_cache == 1
    assert backend.fetched_live == 1


def test_cached_empty_response_replays_as_empty(tmp_path):
    """A provider returning nothing is a result, not a cache miss.

    Without the MISSING sentinel an empty list would be re-fetched every run and
    the replay would silently become a live call.
    """
    web = CountingWeb(results=[])
    cache = ToolCache(tmp_path / "cache.jsonl")
    backend = CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=web), cache)

    assert backend.web_search("nothing", 5) == []
    assert backend.web_search("nothing", 5) == []
    assert web.search_calls == 1
    assert cache.get(cache_key("search_web", {"query": "nothing", "top_k": 5})) is not MISSING


def test_cache_survives_a_new_process(tmp_path):
    path = tmp_path / "cache.jsonl"
    web = CountingWeb()
    CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=web), ToolCache(path)).fetch(
        "https://www.apple.com/x")

    reloaded = CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=CountingWeb()),
                              ToolCache(path))
    assert reloaded.fetch("https://www.apple.com/x") == "원문 본문"
    assert reloaded.served_from_cache == 1
    assert reloaded.fetched_live == 0


def test_disabled_cache_always_goes_live(tmp_path):
    web = CountingWeb()
    backend = CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=web),
                             ToolCache(tmp_path / "c.jsonl", enabled=False))

    backend.web_search("q", 5)
    backend.web_search("q", 5)

    assert web.search_calls == 2
    assert not (tmp_path / "c.jsonl").exists()


def test_corpus_search_is_not_cached(tmp_path):
    """Retrieval is deterministic given a frozen index; caching it would hide
    index changes between conditions."""
    web = CountingWeb()
    cache = ToolCache(tmp_path / "cache.jsonl")
    backend = CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=web), cache)
    registry = ToolRegistry(backend)

    registry.call("search_evidence", {"query": "본문"})
    registry.call("search_evidence", {"query": "본문"})

    assert cache.stats()["entries"] == 0


def test_cached_and_live_observations_are_identical(tmp_path):
    """Replay must be comparable to live, so the observation text must match."""
    web = CountingWeb()
    live = ToolRegistry(CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=web),
                                       ToolCache(tmp_path / "cache.jsonl")))
    live_result, _ = live.call("search_web", {"query": "Vision Pro"})

    replay = ToolRegistry(CachingBackend(CorpusBackend([DOC], BigramTokenizer(), web=CountingWeb()),
                                         ToolCache(tmp_path / "cache.jsonl")))
    replay_result, _ = replay.call("search_web", {"query": "Vision Pro"})

    assert live_result.status == replay_result.status == ToolStatus.OK
    assert live_result.observation == replay_result.observation
    assert web.search_calls == 1


# --- run log ---------------------------------------------------------------

def test_run_log_is_append_only(tmp_path):
    log = RunLog(tmp_path / "run.jsonl")
    log.append(make_config(), make_result("FC001"))
    log.append(make_config(), make_result("FC002"))

    lines = (tmp_path / "run.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["result"]["claim_id"] == "FC001"
    assert json.loads(lines[1])["config"]["condition"] == "C2"


def test_completed_episodes_are_not_rerun(tmp_path):
    """evaluation.md section 7: a restart must not re-spend budget."""
    path = tmp_path / "run.jsonl"
    log = RunLog(path)
    log.append(make_config(seed=0), make_result("FC001"))

    reloaded = RunLog(path)

    assert reloaded.is_done("FC001", "react", 0)
    assert not reloaded.is_done("FC001", "react", 1)      # another seed is new work
    assert not reloaded.is_done("FC001", "fixed_workflow", 0)  # another policy is new work
    assert not reloaded.is_done("FC002", "react", 0)


def test_run_log_records_which_run_produced_the_result(tmp_path):
    log = RunLog(tmp_path / "run.jsonl")
    log.append(make_config(run_id="exp-002", condition="C1", policy="fixed_workflow",
                           model_id="m2", seed=7, replay=True), make_result("FC003"))

    row = log.load()[0]
    assert row["config"]["run_id"] == "exp-002"
    assert row["config"]["condition"] == "C1"
    assert row["config"]["seed"] == 7
    assert row["config"]["replay"] is True


def test_empty_log_loads_as_empty(tmp_path):
    assert RunLog(tmp_path / "missing.jsonl").load() == []
    assert len(RunLog(tmp_path / "missing.jsonl")) == 0


# --- cost ------------------------------------------------------------------

def test_usage_summary_totals_and_means(tmp_path):
    log = RunLog(tmp_path / "run.jsonl")
    log.append(make_config(), make_result("FC001", input_tokens=1000, output_tokens=50,
                                          tool_calls=3, external_calls=1, cost_usd=0.02))
    log.append(make_config(), make_result("FC002", input_tokens=3000, output_tokens=150,
                                          tool_calls=1, external_calls=0, cost_usd=0.06))

    totals = summarise_usage(log.load())

    assert totals["episodes"] == 2
    assert totals["input_tokens"] == 4000
    assert totals["output_tokens"] == 200
    assert totals["tool_calls"] == 4
    assert totals["external_calls"] == 1
    assert totals["cost_usd"] == pytest.approx(0.08)
    assert totals["mean_cost_usd_per_episode"] == pytest.approx(0.04)
    assert totals["mean_tool_calls_per_episode"] == 2.0


def test_backend_is_a_valid_tool_backend(tmp_path):
    """CachingBackend must be drop-in for MockBackend and CorpusBackend."""
    backend = CachingBackend(MockBackend([DOC]), ToolCache(tmp_path / "c.jsonl"))
    result, _ = ToolRegistry(backend).call("search_evidence", {"query": "본문"})

    assert result.status == ToolStatus.OK
    assert backend.lookup("EV1").evidence_id == "EV1"
