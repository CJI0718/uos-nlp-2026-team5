"""Run and score Task A on the 50 claims, C0/C1/C2, with Claude or an API model.

Two backends drive the same factcheck-mission server, the same Skill and the
same claims; only the transport differs.

    openai  any OpenAI-compatible chat API (Mistral, DeepSeek, OpenRouter...).
            Tools are called in-process on AgentEnvironment.
    claude  a fresh headless `claude -p` session per claim, the server attached
            over MCP (as in exp-001), now for C0, C1 and C2.

Arms
    C0  no evidence tools; finish_verification only
    C1  search_evidence / read_evidence on data/raw/task_a/corpus_c1.jsonl
    C2  C1 plus search_web (Tavily) / fetch_url

THIS SCRIPT CALLS MODELS AND TAVILY. Run it only within an agreed budget.
One ledger (results/raw/task_a_budget_ledger.jsonl) holds money and Tavily
use across every run, so the caps cover the pilot, the baseline and the rerun
together. A run stops as soon as either cap would be crossed. Nothing is
retried: failures are logged and scored as failures. Claims that already
have a record for an arm are skipped, never re-run.

    uv run python scripts/run_task_a.py run --exp-id exp-005-pilot --claims FC001,FC002 --dry-run
    uv run python scripts/run_task_a.py run --exp-id exp-005-baseline --arms C0,C1,C2
    uv run python scripts/run_task_a.py score --exp-id exp-005-baseline
    uv run python scripts/run_task_a.py ledger

Raw logs and transcripts go to results/raw/<exp-id>/ (git-ignored: they hold
page text). `score` writes results/<exp-id>/summary.json, summary.md and
episodes.jsonl with verdicts, counts and costs only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from task_a.agent_loop import (  # noqa: E402
    Budget, BudgetExceeded, Price, run_episode, run_plain_episode, system_prompt,
)
from task_a.mcp_server import AgentEnvironment, current_commit  # noqa: E402
from task_a.schema import Verdict, read_jsonl  # noqa: E402
from task_a.score_run import load_gold, to_graded  # noqa: E402
from task_a.scorer import abstain_rate, accuracy, coverage, macro_f1, transitions  # noqa: E402
from task_a.tools import same_page  # noqa: E402
from task_a.web import LiveWebProvider, load_env_file  # noqa: E402

ARMS = ("C0", "C1", "C2", "C2W", "C2P")
# C2W: C2 without the fixed corpus. The agent has to find its evidence on the
# web itself (search_web / fetch_url); C1 and C2 always contain the reference
# documents, so they measure judgement given evidence, not finding it.
# C2P: the same model, web and protocol as C2W without the harness (no Skill,
# no calculator, no paged reading, no distortion fields or missions).
SERVER_ARM = {"C0": "C0", "C1": "C1", "C2": "C2", "C2W": "C2", "C2P": "C2"}
LEDGER = ROOT / "results/raw/task_a_budget_ledger.jsonl"
CORPUS = ROOT / "data/raw/task_a/corpus_c1.jsonl"
GOLD_MAP = ROOT / "data/raw/task_a/corpus_c1.gold_map.jsonl"
CLAIMS = ROOT / "data/task_a/claims.jsonl"
GOLD = ROOT / "data/task_a/gold.jsonl"
EVIDENCE = ROOT / "data/task_a/evidence.jsonl"
CLAIM_TYPES = ROOT / "data/task_a/claim_types.json"
DATA_VERSION = "claims-2026-11-25"
SERVER = "factcheck-mission"
# A C2 episode may use up to max_external_calls searches; never start one that
# could cross the Tavily cap.
_LEDGER_LOCK = threading.Lock()


# --------------------------------------------------------------------------
# Ledger: one file for money and Tavily across all runs
# --------------------------------------------------------------------------

def ledger_totals(path: Path = LEDGER) -> dict:
    cost = tavily = 0.0
    episodes = 0
    for row in (read_jsonl(path) if path.exists() else []):
        cost += row.get("cost_usd") or 0.0
        tavily += row.get("tavily_searches") or 0
        episodes += 1
    return {"cost_usd": round(cost, 6), "tavily_searches": int(tavily), "episodes": episodes}


def tavily_used_all() -> int:
    """Tavily searches across every ledger: one key, one approved cap."""
    return sum(ledger_totals(p)["tavily_searches"] for p in sorted(LEDGER.parent.glob("task_a_budget_ledger*.jsonl")))


def ledger_append(row: dict, path: Path = LEDGER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LEDGER_LOCK, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class TavilyCounter:
    def __init__(self, cap: int, used_before: int) -> None:
        self.cap = cap
        self.used = used_before
        self._lock = threading.Lock()

    def take(self) -> None:
        with self._lock:
            if self.used >= self.cap:
                raise RuntimeError(f"Tavily 검색 상한({self.cap}회)에 도달했습니다.")
            self.used += 1

    def remaining(self) -> int:
        with self._lock:
            return self.cap - self.used


class CountingWeb:
    """LiveWebProvider with every live search counted against the Tavily cap.

    Cached searches never reach the provider, so they are not counted.
    The explicit signature matters: the corpus backend passes `end_date` only
    when the provider's `search` declares it.
    """

    def __init__(self, inner: LiveWebProvider, counter: TavilyCounter) -> None:
        self.inner = inner
        self.counter = counter
        self.searches = 0
        self._lock = threading.Lock()

    def search(self, query: str, top_k: int = 5, end_date: str | None = None,
               start_date: str | None = None) -> list[dict]:
        self.counter.take()
        with self._lock:
            self.searches += 1
        return self.inner.search(query, top_k, end_date=end_date, start_date=start_date)

    def fetch(self, url: str) -> dict:
        return self.inner.fetch(url)


class LockedCache:
    """One ToolCache shared by every worker thread of an arm."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            return self.inner.get(key)

    def put(self, *args, **kwargs):
        with self._lock:
            return self.inner.put(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.inner, name)


# --------------------------------------------------------------------------
# Paths and records
# --------------------------------------------------------------------------

def arm_dir(exp_id: str, arm: str) -> Path:
    return ROOT / "results/raw" / exp_id / arm


def done_claims(exp_id: str, arm: str) -> set[str]:
    path = arm_dir(exp_id, arm) / "records.jsonl"
    return {r["claim_id"] for r in read_jsonl(path)} if path.exists() else set()


def append_record(exp_id: str, arm: str, record: dict) -> None:
    path = arm_dir(exp_id, arm) / "records.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LEDGER_LOCK, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# openai backend
# --------------------------------------------------------------------------

def make_env(args, arm: str, worker: int, web, shared_cache) -> AgentEnvironment:
    base = arm_dir(args.exp_id, arm)
    web_arm = arm in ("C2", "C2W", "C2P")
    env = AgentEnvironment(
        claims_path=CLAIMS, out_path=base / f"server.w{worker}.run.jsonl", arm=SERVER_ARM[arm],
        model_id=f"{args.backend}:{args.model}", run_id=f"{args.exp_id}-{arm}",
        corpus_path=CORPUS if arm in ("C1", "C2") else None,
        cache_path=base / "tool_cache.jsonl" if web_arm else None,
        missions_dir=base / "missions", tokenizer=args.tokenizer,
        web_provider=web if web_arm else None, web_only=arm in ("C2W", "C2P"),
        max_tool_calls=args.max_tool_calls, max_external_calls=args.max_external_calls,
        code_commit=current_commit(ROOT), prompt_version=args.prompt_version,
        gate=args.gate, data_version=args.data_version,
        block_self_citation=args.block_self_citation and arm != "C2P",
        harness_v3=args.harness_v3 and arm != "C2P")
    if web_arm and shared_cache is not None:
        env.backend.cache = shared_cache
    return env


def run_openai(args, arm: str, claim_ids: list[str], budget: Budget, tavily: TavilyCounter) -> list[dict]:
    sys.path.insert(0, str(ROOT / "src"))
    from assistant.llm import OpenAICompatClient
    from task_a.toollog import ToolCache

    client = OpenAICompatClient(args.base_url, args.model, args.api_key_env, timeout_s=args.timeout,
                                max_tokens=args.max_tokens, temperature=args.temperature)
    price = Price(args.price_input, args.price_output, args.price_cached)
    system = system_prompt(args.skill)
    web_arm = arm in ("C2", "C2W", "C2P")
    web = CountingWeb(LiveWebProvider(provider="tavily"), tavily) if web_arm else None
    shared_cache = (LockedCache(ToolCache(arm_dir(args.exp_id, arm) / "tool_cache.jsonl"))
                    if web_arm else None)
    local = threading.local()
    stop = threading.Event()
    records: list[dict] = []
    worker_ids = iter(range(10_000))
    ids_lock = threading.Lock()

    def env_for_thread() -> AgentEnvironment:
        if not hasattr(local, "env"):
            with ids_lock:
                wid = next(worker_ids)
            local.env = make_env(args, arm, wid, web, shared_cache)
        return local.env

    def one(cid: str) -> dict | None:
        if stop.is_set():
            return None
        if web_arm and tavily.remaining() < args.max_external_calls:
            stop.set()
            print(f"  Tavily 잔여 {tavily.remaining()}회: 새 웹 에피소드를 시작하지 않습니다.", file=sys.stderr)
            return None
        if budget.remaining() < args.min_episode_budget:
            stop.set()
            print(f"  남은 예산 ${budget.remaining():.4f}: 새 에피소드를 시작하지 않습니다.", file=sys.stderr)
            return None
        env = env_for_thread()
        tdir = arm_dir(args.exp_id, arm) / "transcripts"
        tdir.mkdir(parents=True, exist_ok=True)

        def save(messages):
            (tdir / f"{cid}.json").write_text(json.dumps(messages, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
        try:
            if arm == "C2P":
                out = run_plain_episode(env, client, cid, price=price, budget=budget,
                                        max_turns=args.max_turns, transcript=save)
            else:
                out = run_episode(env, client, cid, price=price, budget=budget,
                                  max_turns=args.max_turns, system=system, transcript=save)
        except BudgetExceeded as exc:
            stop.set()
            print(f"  {exc}", file=sys.stderr)
            out = None
        if out is None:
            return None
        # This episode's own search_web calls. A shared counter would also count
        # other workers' searches (exp-008 logged 765 for 155 real searches).
        # Cached repeats are included, so this can only overcount.
        searches = out.tool_counts.get("search_web", 0) if web else 0
        rec = {"exp_id": args.exp_id, "backend": args.backend, "model": args.model,
               **out.to_dict(), "arm": arm, "tavily_searches": searches, "finished_at": _now()}
        append_record(args.exp_id, arm, rec)
        ledger_append({"ts": _now(), "exp_id": args.exp_id, "backend": args.backend,
                       "model": args.model, "arm": arm, "claim_id": cid,
                       "cost_usd": round(out.cost_usd, 6), "tavily_searches": searches}, args.ledger)
        return rec

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, cid): cid for cid in claim_ids}
        for i, fut in enumerate(as_completed(futures), 1):
            cid = futures[fut]
            try:
                rec = fut.result()
            except Exception as exc:   # runner bug: shown, not retried
                print(f"[{arm} {i}/{len(claim_ids)}] {cid} 실행기 오류 {exc!r}", file=sys.stderr, flush=True)
                continue
            if rec:
                records.append(rec)
                print(f"[{arm} {i}/{len(claim_ids)}] {cid} -> {rec['verdict']} ({rec['execution_status']}, "
                      f"{rec['turns']}턴, ${rec['cost_usd']:.4f}, 누적 ${budget.spent:.4f}, "
                      f"Tavily {tavily.used})", file=sys.stderr, flush=True)
    return records


# --------------------------------------------------------------------------
# claude backend
# --------------------------------------------------------------------------

def claude_command(args, arm: str, claim_id: str, base: Path, cli_version: str) -> tuple[list[str], str]:
    from make_agent_workspace import PROMPT_TEMPLATE
    from task_a.skill import skill_body

    server_args = [
        "run", "--project", str(ROOT), "python", str(ROOT / "scripts/mcp_stdio.py"),
        "--arm", SERVER_ARM[arm], "--run-id", f"{args.exp_id}-{arm}",
        "--model-id", f"claude-code-{cli_version}+{args.model}",
        "--prompt-version", args.prompt_version, "--data-version", args.data_version,
        "--gate", args.gate,
        *(["--block-self-citation"] if args.block_self_citation else []),
        *(["--harness-v3"] if args.harness_v3 else []),
        "--out", str(base / "server" / f"{claim_id}.run.jsonl"),
        "--missions-dir", str(base / "missions" / claim_id),
        "--max-tool-calls", str(args.max_tool_calls),
        "--max-external-calls", str(args.max_external_calls),
    ]
    if arm in ("C1", "C2"):
        server_args += ["--corpus", str(CORPUS)]
    if arm in ("C2", "C2W"):
        server_args += ["--live-web", "--web-provider", "tavily",
                        "--cache", str(base / "tool_cache.jsonl")]
    if arm == "C2W":
        server_args += ["--web-only"]
    mcp = {"mcpServers": {SERVER: {"command": "uv", "args": server_args}}}
    skill = skill_body(args.skill) if args.skill else skill_body()
    cmd = ["claude", "-p", "--model", args.model, "--output-format", "stream-json", "--verbose",
           "--no-session-persistence", "--setting-sources", "project", "--disable-slash-commands",
           "--strict-mcp-config", "--tools", "", "--mcp-config", json.dumps(mcp, ensure_ascii=False),
           "--allowedTools", f"mcp__{SERVER}", "--append-system-prompt", skill]
    return cmd, PROMPT_TEMPLATE.format(claim_id=claim_id)


def usage_limited(final: dict) -> bool:
    """A Claude Code result that hit the account's usage or rate limit (HTTP 429)."""
    return (final.get("api_error_status") == 429 or final.get("api_error_type") == "rate_limit_error"
            or final.get("api_error") == "usage_limit_reached")


def run_claude(args, arm: str, claim_ids: list[str], budget: Budget, tavily: TavilyCounter) -> list[dict]:
    from run_comparison import parse_stream

    cli_version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.split()[0]
    base = arm_dir(args.exp_id, arm)
    work_root = (Path(args.work_root).expanduser() / args.exp_id / arm).resolve()
    if work_root == ROOT or ROOT in work_root.parents:
        raise SystemExit(f"작업 디렉터리는 저장소 밖이어야 합니다: {work_root}")
    stop = threading.Event()
    records = []

    def one(cid: str) -> dict | None:
        if stop.is_set():
            return None
        if arm in ("C2", "C2W") and tavily.remaining() < args.max_external_calls:
            stop.set()
            return None
        if budget.remaining() < args.min_episode_budget:
            stop.set()
            return None
        for sub in ("server", "streams", f"missions/{cid}"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        cwd = work_root / cid
        cwd.mkdir(parents=True, exist_ok=True)
        cmd, prompt = claude_command(args, arm, cid, base, cli_version)
        started = time.time()
        status = "ok"
        try:
            proc = subprocess.run(cmd, cwd=cwd, env={**os.environ, "ENABLE_TOOL_SEARCH": "false"},
                                  capture_output=True, text=True, timeout=args.timeout, input=prompt)
            stdout, rc = proc.stdout, proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            rc, status = None, "timeout"
        (base / "streams" / f"{cid}.stream.jsonl").write_text(stdout, encoding="utf-8")
        parsed = parse_stream(stdout.splitlines())
        final = parsed["final"]
        cost = float(final.get("total_cost_usd") or 0.0)
        budget.add(cost)
        server_rows = read_jsonl(base / "server" / f"{cid}.run.jsonl") if (base / "server" / f"{cid}.run.jsonl").exists() else []
        result = server_rows[-1]["result"] if server_rows else {}
        searches = sum(1 for ev in result.get("events", []) if ev.get("tool") == "search_web")
        for _ in range(searches):
            try:
                tavily.take()
            except RuntimeError:
                break
        verdict = result.get("verdict")
        if usage_limited(final):
            # The account's usage window is exhausted: this session never ran.
            # Keep the spend in the ledger but leave the claim unrecorded so the
            # same command resumes it once the limit resets, and stop starting more.
            ledger_append({"ts": _now(), "exp_id": args.exp_id, "backend": "claude", "model": args.model,
                           "arm": arm, "claim_id": cid, "cost_usd": round(cost, 6),
                           "tavily_searches": searches, "note": "usage_limit_not_recorded"}, args.ledger)
            (base / "server" / f"{cid}.run.jsonl").unlink(missing_ok=True)
            if not stop.is_set():
                print(f"  사용 한도에 걸려 멈춥니다: {final.get('result')}", file=sys.stderr, flush=True)
            stop.set()
            return None
        if status == "ok" and (rc not in (0, None) or final.get("is_error")):
            status = "provider_error"
        if status == "ok" and not server_rows:
            status = "parse_error"
        rec = {"exp_id": args.exp_id, "backend": "claude", "model": args.model, "arm": arm,
               "claim_id": cid, "execution_status": status, "verdict": verdict,
               "finished": bool(server_rows), "turns": final.get("num_turns") or 0,
               "cost_usd": cost, "tool_counts": parsed["tool_uses"],
               "duration_ms": final.get("duration_ms") or int((time.time() - started) * 1000),
               "tavily_searches": searches, "finished_at": _now()}
        append_record(args.exp_id, arm, rec)
        ledger_append({"ts": _now(), "exp_id": args.exp_id, "backend": "claude", "model": args.model,
                       "arm": arm, "claim_id": cid, "cost_usd": round(cost, 6), "tavily_searches": searches},
                      args.ledger)
        if budget.remaining() <= 0:
            stop.set()
        return rec

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, cid): cid for cid in claim_ids}
        for i, fut in enumerate(as_completed(futures), 1):
            rec = fut.result()
            if rec:
                records.append(rec)
                print(f"[{arm} {i}/{len(claim_ids)}] {rec['claim_id']} -> {rec['verdict']} "
                      f"({rec['execution_status']}, ${rec['cost_usd']:.4f}, 누적 ${budget.spent:.4f})",
                      file=sys.stderr, flush=True)
    return records


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _norm_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.").removeprefix("m.")
    path = parts.path.rstrip("/")
    return f"{host}{path}" + (f"?{parts.query}" if parts.query else "")


def reference_sources() -> dict[str, dict]:
    """Per claim: corpus doc ids and URLs of its reference evidence (scorer-only)."""
    refs: dict[str, dict] = {}
    for row in read_jsonl(EVIDENCE):
        r = refs.setdefault(row["claim_id"], {"docs": set(), "urls": set()})
        if row.get("source_url"):
            r["urls"].add(_norm_url(row["source_url"]))
    if GOLD_MAP.exists():
        for row in read_jsonl(GOLD_MAP):
            for cid in row.get("claim_ids") or []:
                refs.setdefault(cid, {"docs": set(), "urls": set()})["docs"].add(row["evidence_id"])
    return refs


def cites_reference(result: dict, ref: dict) -> bool:
    for cited in result.get("cited_evidence_ids") or []:
        if cited in ref["docs"]:
            return True
        if cited.startswith(("http://", "https://")) and _norm_url(cited) in ref["urls"]:
            return True
    return False


def unread_citations(result: dict) -> list[str]:
    read = set()
    for ev in result.get("events") or []:
        if ev.get("tool") in ("read_evidence", "fetch_url") and ev.get("status") == "ok":
            read.update(ev.get("evidence_ids") or [])
    return [c for c in result.get("cited_evidence_ids") or [] if c not in read]


def score(exp_id: str) -> dict:
    gold = load_gold(GOLD)
    gold_rows = {r["claim_id"]: r for r in read_jsonl(GOLD)}
    refs = reference_sources()
    altered = {cid for cid, g in gold_rows.items() if g.get("altered_input")}
    claims_src = {c["claim_id"]: c.get("source_url") for c in read_jsonl(CLAIMS)}
    types = json.loads(CLAIM_TYPES.read_text(encoding="utf-8"))["types"] if CLAIM_TYPES.exists() else {}
    out_dir = ROOT / "results" / exp_id
    arms_rows: dict[str, list[dict]] = {}
    table, episodes = [], []

    for arm in ARMS:
        base = arm_dir(exp_id, arm)
        if not base.exists():
            continue
        rows = []
        for path in sorted(base.rglob("*.run.jsonl")):
            rows.extend(read_jsonl(path))
        # One row per claim: the last logged attempt (there is only one unless a run was repeated).
        latest = {}
        for row in rows:
            latest[row["result"]["claim_id"]] = row
        rows = list(latest.values())
        arms_rows[arm] = rows
        recs = {r["claim_id"]: r for r in read_jsonl(base / "records.jsonl")} if (base / "records.jsonl").exists() else {}
        graded = to_graded(rows, gold)

        grounded = []
        for row, g in zip(rows, graded):
            res = row["result"]
            cid = res["claim_id"]
            label = gold.get(cid)
            e = cites_reference(res, refs.get(cid, {"docs": set(), "urls": set()}))
            own = claims_src.get(cid)
            independent = any(not same_page(c, own) for c in res.get("cited_evidence_ids") or [])
            self_only = bool(own) and bool(res.get("cited_evidence_ids")) and not independent
            if label == Verdict.NOT_ENOUGH_EVIDENCE:
                ve = g.v
            else:
                ve = g.v and e
            grounded.append(ve)
            rec = recs.get(cid, {})
            mission = res.get("mission_output") or {}
            episodes.append({
                "arm": arm, "claim_id": cid, "gold": label.value if label else None,
                "verdict": res.get("verdict"), "correct": g.v, "cites_reference": e,
                "grounded_auto": ve, "altered_input": cid in altered, "claim_type": types.get(cid),
                "cites_independent": independent, "cites_only_own_post": self_only,
                "correct_independent": g.v and (independent or label == Verdict.NOT_ENOUGH_EVIDENCE),
                "execution_status": res.get("execution_status"),
                "distortion_type": res.get("distortion_type"),
                "cited_evidence_ids": res.get("cited_evidence_ids"),
                "unread_citations": unread_citations(res),
                "tool_calls": (res.get("usage") or {}).get("tool_calls"),
                "external_calls": (res.get("usage") or {}).get("external_calls"),
                "mission_type": res.get("mission_type"), "mission_status": mission.get("status"),
                "turns": rec.get("turns"), "cost_usd": rec.get("cost_usd"),
                "prompt_tokens": rec.get("prompt_tokens"), "completion_tokens": rec.get("completion_tokens"),
                "tavily_searches": sum(1 for ev in res.get("events") or [] if ev.get("tool") == "search_web"),
                "duration_ms": rec.get("duration_ms"),
            })

        def acc_of(pred) -> dict | None:
            sub = [g for g in graded if pred(g)]
            return accuracy(sub) if sub else None

        arm_eps = [e for e in episodes if e["arm"] == arm]
        costs = [r.get("cost_usd") or 0.0 for r in recs.values()]
        table.append({
            "arm": arm, "episodes": len(rows),
            "execution_status": dict(Counter(r["result"]["execution_status"] for r in rows)),
            "accuracy": accuracy(graded), "macro_f1": macro_f1(graded),
            "coverage": coverage(graded), "abstain_rate": abstain_rate(graded),
            "recall_supported": acc_of(lambda g: g.gold_label == Verdict.SUPPORTED),
            "recall_refuted": acc_of(lambda g: g.gold_label == Verdict.REFUTED),
            "recall_nee": acc_of(lambda g: g.gold_label == Verdict.NOT_ENOUGH_EVIDENCE),
            "refuted_altered": acc_of(lambda g: g.gold_label == Verdict.REFUTED and g.claim_id in altered),
            "refuted_real": acc_of(lambda g: g.gold_label == Verdict.REFUTED and g.claim_id not in altered),
            "grounded_auto": {"numerator": sum(grounded), "denominator": len(grounded),
                              "value": round(sum(grounded) / len(grounded), 4) if grounded else None},
            "cites_reference": sum(1 for e in arm_eps if e["cites_reference"]),
            "correct_with_independent_source": {
                "numerator": sum(1 for e in arm_eps if e["correct_independent"]), "denominator": len(arm_eps),
                "value": round(sum(1 for e in arm_eps if e["correct_independent"]) / len(arm_eps), 4) if arm_eps else None},
            "episodes_citing_only_own_post": sum(1 for e in arm_eps if e["cites_only_own_post"]),
            "episodes_with_unread_citations": sum(1 for e in arm_eps if e["unread_citations"]),
            "verdicts": dict(Counter(e["verdict"] for e in arm_eps)),
            "mean_tool_calls": _mean(e["tool_calls"] for e in arm_eps),
            "tavily_searches": sum(e["tavily_searches"] or 0 for e in arm_eps),
            "mean_turns": _mean(e["turns"] for e in arm_eps),
            "cost_usd_total": round(sum(costs), 4),
            "prompt_tokens_total": sum(e["prompt_tokens"] or 0 for e in arm_eps),
            "completion_tokens_total": sum(e["completion_tokens"] or 0 for e in arm_eps),
            "missions": dict(Counter(f"{e['mission_type']}:{e['mission_status']}"
                                     for e in arm_eps if e["mission_type"])),
            "accuracy_by_claim_type": {
                t: acc_of(lambda g, t=t: types.get(g.claim_id) == t)
                for t in sorted(set(types.values()))},
            "confusion": dict(Counter(f"{e['gold']}->{e['verdict']}" for e in arm_eps)),
        })

    trans = {}
    for a, b in (("C0", "C1"), ("C1", "C2"), ("C0", "C2"), ("C0", "C2W"), ("C2", "C2W"), ("C2P", "C2W")):
        if a in arms_rows and b in arms_rows:
            trans[f"{a}->{b}"] = transitions(to_graded(arms_rows[a], gold), to_graded(arms_rows[b], gold))

    summary = {
        "exp_id": exp_id, "scored_at": _now(), "data_version": DATA_VERSION,
        "gold_distribution": dict(Counter(g.value if g else None for g in gold.values())),
        "always_supported_accuracy": round(sum(1 for g in gold.values() if g == Verdict.SUPPORTED) / len(gold), 4),
        "notes": {
            "accuracy": "분모는 시도한 에피소드 전체다. 실행 실패와 보류는 오답으로 센다.",
            "grounded_auto": ("자동 근사치. 지지·반박은 판정이 맞고 인용 근거에 참조 근거(코퍼스 문서 또는 같은 URL)가 "
                              "있어야 하고, 근거 부족은 판정만 본다. 시점·범위(T)는 사람이 채점해야 한다."),
            "refuted_altered": "변형 주장 8개(재가공 게시물)와 실제 반박 사례 6개를 나눈 정확도.",
        },
        "table": table, "transitions": trans,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (out_dir / "episodes.jsonl").open("w", encoding="utf-8") as fh:
        for e in sorted(episodes, key=lambda x: (x["arm"], x["claim_id"])):
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    (out_dir / "summary.md").write_text(render_md(summary), encoding="utf-8")
    return summary


def _mean(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _fmt(r: dict | None) -> str:
    if not r:
        return "-"
    return f"{r['numerator']}/{r['denominator']} ({r['value']:.0%})" if r.get("value") is not None else "-"


def render_md(summary: dict) -> str:
    lines = [f"# {summary['exp_id']} 결과 요약", "",
             f"채점 {summary['scored_at']} · 데이터 `{summary['data_version']}` · "
             f"항상 '지지'라고 답할 때 정확도 {summary['always_supported_accuracy']:.0%}", "",
             "| 조건 | 에피소드 | 정확도 | Macro-F1 | 근거 동반 정답(자동) | 지지 재현율 | 반박 재현율 | 근거 부족 재현율 | 반박: 변형 | 반박: 실제 | 실행 실패 | 비용 |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for t in summary["table"]:
        f1 = t["macro_f1"]
        failed = sum(v for k, v in t["execution_status"].items() if k != "ok")
        f1_text = f"{f1['macro_f1']:.3f}" if f1 else "-"
        lines.append(
            f"| {t['arm']} | {t['episodes']} | {_fmt(t['accuracy'])} | {f1_text} | "
            f"{_fmt(t['grounded_auto'])} | {_fmt(t['recall_supported'])} | {_fmt(t['recall_refuted'])} | "
            f"{_fmt(t['recall_nee'])} | {_fmt(t['refuted_altered'])} | {_fmt(t['refuted_real'])} | "
            f"{failed} | ${t['cost_usd_total']:.4f} |")
    lines += ["", "정의는 `summary.json`의 `notes`에 있습니다. 세션별 판정은 `episodes.jsonl`에 있습니다.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=["run", "score", "ledger"])
    p.add_argument("--exp-id", default="exp-005-baseline")
    p.add_argument("--backend", choices=["openai", "claude"], default="openai")
    p.add_argument("--model", default="deepseek-v4-1-flash-1017")
    p.add_argument("--base-url", default="https://api.mistral.ai/v1")
    p.add_argument("--api-key-env", default="MISTRAL_API_KEY", help="키 값이 아니라 환경변수 이름")
    p.add_argument("--price-input", type=float, default=0.3, help="USD / 1M 입력 토큰")
    p.add_argument("--price-output", type=float, default=1.2, help="USD / 1M 출력 토큰")
    p.add_argument("--price-cached", type=float, default=None,
                   help="USD / 1M 캐시 입력 토큰. 기본은 입력 가격(보수적)")
    p.add_argument("--arms", default="C0,C1,C2")
    p.add_argument("--claims", default="all", help="all 또는 쉼표 구분 claim_id")
    p.add_argument("--limit", type=int, default=None, help="앞에서 N개만")
    p.add_argument("--max-cost-usd", type=float, default=5.0, help="이 장부에 기록된 모든 실행을 합친 모델 비용 상한")
    p.add_argument("--ledger", type=Path, default=LEDGER,
                   help="비용 장부. 예산을 따로 승인받은 실행(예: Claude)은 다른 파일을 쓴다. Tavily는 모든 장부를 합쳐 센다")
    p.add_argument("--tavily-cap", type=int, default=600, help="모든 실행을 합친 Tavily 검색 상한")
    p.add_argument("--min-episode-budget", type=float, default=0.03,
                   help="남은 예산이 이보다 적으면 새 에피소드를 시작하지 않는다")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--max-turns", type=int, default=20)
    p.add_argument("--max-tool-calls", type=int, default=12)
    p.add_argument("--max-external-calls", type=int, default=4)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=int, default=180, help="API 요청 하나(또는 claude 세션 하나)의 제한 시간(초)")
    p.add_argument("--tokenizer", choices=["kiwi", "bigram"], default="kiwi")
    p.add_argument("--gate", default="verdict")
    p.add_argument("--skill", type=Path, default=None, help="다른 SKILL.md로 실험할 때")
    p.add_argument("--prompt-version", default="skill-v2")
    p.add_argument("--data-version", default=DATA_VERSION)
    p.add_argument("--work-root", default=str(Path.home() / "agent-runs"))
    p.add_argument("--block-self-citation", action="store_true",
                   help="하네스 조건에서 주장이 나온 글을 근거로 인용하지 못하게 함(C2P에는 적용하지 않음)")
    p.add_argument("--harness-v3", action="store_true",
                   help="exp-011 분석으로 넣은 개선: find_in_page, 반복 검색·열람 재사용, "
                        "인용문 대조·예측 주장 게이트(C2P에는 적용하지 않음)")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.action == "ledger":
        print(json.dumps({"ledger": str(args.ledger), **ledger_totals(args.ledger),
                          "tavily_searches_all_ledgers": tavily_used_all()}, ensure_ascii=False, indent=2))
        return 0
    if args.action == "score":
        summary = score(args.exp_id)
        print(render_md(summary))
        return 0

    load_env_file(ROOT / ".env", keys=("TAVILY_API_KEY", args.api_key_env))
    claims_all = [c["claim_id"] for c in read_jsonl(CLAIMS)]
    claim_ids = claims_all if args.claims == "all" else args.claims.split(",")
    unknown = set(claim_ids) - set(claims_all)
    if unknown:
        raise SystemExit(f"없는 claim_id: {sorted(unknown)}")
    if args.limit:
        claim_ids = claim_ids[: args.limit]
    arms = args.arms.split(",")
    if any(a not in ARMS for a in arms):
        raise SystemExit(f"arm은 {ARMS} 중에서 고릅니다.")
    if any(a in ("C1", "C2") for a in arms) and not CORPUS.exists():
        raise SystemExit(f"C1·C2에는 코퍼스가 필요합니다: {CORPUS} (scripts/build_corpus.py)")

    spent = ledger_totals(args.ledger)
    budget = Budget(args.max_cost_usd, spent_before=spent["cost_usd"])
    tavily = TavilyCounter(args.tavily_cap, used_before=tavily_used_all())
    plan = {a: [c for c in claim_ids if c not in done_claims(args.exp_id, a)] for a in arms}
    print(f"계획: {args.backend}:{args.model} exp={args.exp_id} "
          + ", ".join(f"{a} {len(v)}개" for a, v in plan.items())
          + f" | 장부 {args.ledger.name}: ${spent['cost_usd']:.4f}/${args.max_cost_usd}, "
            f"Tavily(전체) {tavily.used}/{args.tavily_cap}", file=sys.stderr)
    skipped = {a: len(claim_ids) - len(v) for a, v in plan.items() if len(claim_ids) - len(v)}
    if skipped:
        print(f"이미 기록이 있어 건너뜀: {skipped}", file=sys.stderr)
    if args.dry_run:
        if args.backend == "claude":
            cmd, prompt = claude_command(args, arms[0], claim_ids[0], arm_dir(args.exp_id, arms[0]), "x.y.z")
            print(json.dumps({"cmd": cmd[:20], "prompt": prompt}, ensure_ascii=False)[:2000])
        else:
            print(f"key {args.api_key_env} 설정됨: {bool(os.environ.get(args.api_key_env))}, "
                  f"TAVILY 설정됨: {bool(os.environ.get('TAVILY_API_KEY'))}", file=sys.stderr)
        return 0

    if "C2P" in arms and args.backend != "openai":
        raise SystemExit("C2P(하네스 없는 기본 웹 에이전트)는 --backend openai에서만 돌립니다.")
    runner = run_openai if args.backend == "openai" else run_claude
    for arm in arms:
        if not plan[arm]:
            continue
        runner(args, arm, plan[arm], budget, tavily)
        left = [c for c in plan[arm] if c not in done_claims(args.exp_id, arm)]
        if left:
            print(f"{arm}에 남은 사례 {len(left)}개가 있어 다음 조건으로 넘어가지 않습니다. "
                  f"같은 명령을 다시 실행하면 이어서 돌아요.", file=sys.stderr)
            break
        if budget.remaining() < args.min_episode_budget:
            print("예산 상한에 가까워 남은 조건을 실행하지 않습니다.", file=sys.stderr)
            break
    print(json.dumps(ledger_totals(args.ledger), ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
