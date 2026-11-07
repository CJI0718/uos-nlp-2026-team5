"""Episode runner: executes claims and writes the log. It cannot see gold.

This module deliberately never opens gold.jsonl. Scoring lives in score_run.py,
a separate command, so the boundary between what the solver sees and what the
grader sees is enforced by process structure rather than by discipline.

Safety defaults, per AGENTS.md and experiments/README.md:
- dry run unless --live is passed, so an accidental invocation costs nothing
- a hard USD budget that stops the run rather than letting it overshoot
- no retry and no model substitution; a failed episode is logged and skipped
- completed episodes are never re-run, so a restart does not re-spend
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from task_a.llm import OpenAICompatibleClient
from task_a.loop import Budget, LLMClient, ReActAgent
from task_a.mock import ScriptedLLM, finish_response
from task_a.policies import get_policy
from task_a.retrieve import BigramTokenizer, CorpusBackend, KiwiTokenizer
from task_a.schema import AgentResult, Claim, EvidenceUnit, read_jsonl
from task_a.toollog import CachingBackend, RunConfig, RunLog, ToolCache, summarise_usage
from task_a.tools import ToolRegistry

DRY_RUN_MODEL = "dry-run-scripted"


@dataclass
class RunSpec:
    run_id: str
    arm: str                                    # C0 | C1 | C2
    policy: str                                 # react | fixed_workflow | closed_book
    out_path: Path
    condition: str = "sufficient"               # which corpus variant is being served
    model_id: str = DRY_RUN_MODEL
    prompt_version: str = "p1"
    data_version: str = "claims-2026-11-07"
    code_commit: str | None = None
    seed: int = 0
    limit: int | None = None
    only: list[str] = field(default_factory=list)
    budget_usd: float | None = None
    live: bool = False
    base_url: str | None = None
    tokenizer: str = "kiwi"
    cache_path: Path | None = None
    max_steps: int = 8
    max_tool_calls: int = 12
    max_external_calls: int = 4


def load_claims(path: str | Path, spec: RunSpec) -> list[Claim]:
    rows = read_jsonl(path)
    if spec.only:
        rows = [r for r in rows if r["claim_id"] in set(spec.only)]
    if spec.limit:
        rows = rows[:spec.limit]
    return [Claim.from_dict(r) for r in rows]


def load_corpus(path: str | Path | None) -> list[EvidenceUnit]:
    if path is None or not Path(path).exists():
        return []
    rows = read_jsonl(path)
    return [EvidenceUnit(**{k: v for k, v in r.items() if k in EvidenceUnit.__dataclass_fields__})
            for r in rows]


def build_backend(spec: RunSpec, corpus: list[EvidenceUnit], web=None):
    """C0 gets no corpus at all; C1 gets the corpus and no web; C2 adds web."""
    tokenizer = KiwiTokenizer() if spec.tokenizer == "kiwi" else BigramTokenizer()
    if spec.arm == "C0":
        inner = CorpusBackend([], tokenizer, web=None)
    else:
        inner = CorpusBackend(corpus, tokenizer, web=None if spec.arm == "C1" else web)
    if spec.cache_path is None:
        return inner
    return CachingBackend(inner, ToolCache(spec.cache_path, enabled=spec.live))


def dry_run_llm(claims: list[Claim]) -> LLMClient:
    """A scripted model that abstains on everything.

    Exercises the whole pipeline - tools, budget, logging, resume - without a
    provider. It produces no meaningful verdicts and must never be scored as a
    result.
    """
    return ScriptedLLM([
        finish_response("not_enough_evidence", [], "dry-run: 실모델 미연결",
                        "no_further_tools_helpful", abstain=True)
        for _ in claims
    ])


def build_llm(spec: RunSpec, claims: list[Claim]) -> LLMClient:
    if not spec.live:
        return dry_run_llm(claims)
    return OpenAICompatibleClient(spec.model_id, base_url=spec.base_url,
                                  temperature=0.0, seed=spec.seed)


def make_config(spec: RunSpec, replay: bool = False) -> RunConfig:
    return RunConfig(run_id=spec.run_id, arm=spec.arm, condition=spec.condition,
                     policy=spec.policy, model_id=spec.model_id,
                     prompt_version=spec.prompt_version, data_version=spec.data_version,
                     seed=spec.seed, code_commit=spec.code_commit, replay=replay)


@dataclass
class RunOutcome:
    executed: int = 0
    skipped: int = 0
    stopped_reason: str | None = None
    cost_usd: float = 0.0
    results: list[AgentResult] = field(default_factory=list)
    cache_stats: dict | None = None
    pricing_note: dict | None = None

    def as_dict(self, log: RunLog) -> dict:
        return {"executed": self.executed, "skipped": self.skipped,
                "stopped_reason": self.stopped_reason, "cost_usd": self.cost_usd,
                "logged_episodes": len(log), "cache": self.cache_stats,
                "pricing": self.pricing_note, "usage": summarise_usage(log.load())}


def execute(spec: RunSpec, claims: list[Claim], corpus: list[EvidenceUnit],
            llm: LLMClient | None = None, web=None) -> RunOutcome:
    """Run every requested episode, honouring the budget and the resume set."""
    log = RunLog(spec.out_path)
    config = make_config(spec)
    backend = build_backend(spec, corpus, web=web)
    llm = llm or build_llm(spec, claims)
    agent = ReActAgent(llm, ToolRegistry(backend),
                       Budget(spec.max_steps, spec.max_tool_calls, spec.max_external_calls),
                       policy=get_policy(spec.policy))

    outcome = RunOutcome()
    for claim in claims:
        if log.is_done(claim.claim_id, spec.policy, spec.seed):
            outcome.skipped += 1
            continue

        started = time.monotonic()
        result = agent.run(claim)
        result.usage.elapsed_ms = int((time.monotonic() - started) * 1000)
        log.append(config, result)
        outcome.executed += 1
        outcome.results.append(result)
        outcome.cost_usd += result.usage.cost_usd

        if spec.budget_usd is not None and outcome.cost_usd >= spec.budget_usd:
            outcome.stopped_reason = (f"예산 상한 도달: {outcome.cost_usd:.4f} USD "
                                      f">= {spec.budget_usd:.4f} USD")
            break

    outcome.cache_stats = backend.cache.stats() if isinstance(backend, CachingBackend) else None
    outcome.pricing_note = llm.pricing_note() if hasattr(llm, "pricing_note") else None
    return outcome
