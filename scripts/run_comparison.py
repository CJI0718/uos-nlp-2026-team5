"""Compare plain Claude Code against the Task A harness, per model.

Three conditions, each a fresh headless `claude -p` session per claim:

    closed_book  no tools at all; the model answers from what it knows
    plain_web    Claude Code's own WebSearch + WebFetch, no MCP, no Skill
                 ("why not just use Claude Code?")
    harness      only the factcheck-mission MCP server on the C1 source corpus,
                 the Skill appended to the system prompt, verdict and missions
                 through finish_verification

Every condition sees the same claim fields the MCP server exposes in
start_episode. User-level settings, plugins, hooks, skills and other MCP
servers are switched off in all three (--setting-sources project,
--disable-slash-commands, --strict-mcp-config), and each session runs in its
own empty directory outside the repository, so no condition can open gold.

THIS SCRIPT CALLS MODELS. Run it only within an agreed budget. Failed sessions
are recorded as failures and never retried automatically; `--only-missing`
re-runs sessions that have no record at all, on explicit request.

    uv run python scripts/run_comparison.py run --dry-run
    uv run python scripts/run_comparison.py run --workers 4
    uv run python scripts/run_comparison.py score

Raw stream transcripts go to results/raw/<exp-id>/ (git-ignored). `score`
writes results/<exp-id>/summary.json and episodes.jsonl (verdicts, counts,
cost; no transcript text).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from make_agent_workspace import PROMPT_TEMPLATE  # noqa: E402
from task_a.schema import ExecutionStatus, Verdict, read_jsonl  # noqa: E402
from task_a.scorer import Graded, abstain_rate, accuracy, coverage, macro_f1  # noqa: E402
from task_a.skill import skill_body  # noqa: E402

CONDITIONS = ("closed_book", "plain_web", "harness")
MODELS = ("opus", "sonnet", "haiku")
SERVER = "factcheck-mission"
SAMPLE_SEED = 20261119
N_SUPPORTED = 8
LEAK_MARKERS = ("uos-nlp-2026-team5", "CJI0718", "gold.jsonl", "evaluation.md")

BASELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": [v.value for v in Verdict]},
        "abstain": {"type": "boolean"},
        "justification": {"type": "string"},
        "cited_sources": {"type": "array", "items": {"type": "string"}},
        "correction": {"type": ["string", "null"]},
    },
    "required": ["verdict", "abstain", "justification", "cited_sources"],
    "additionalProperties": False,
}

BASELINE_PROMPT = """다음 주장을 사실 검증하세요.

판정은 셋 중 하나입니다.
- supported: 신뢰할 수 있는 근거가 주장을 지지한다
- refuted: 근거가 주장의 일부라도 틀렸음을 보여 준다 (수치·날짜·시간대·주체·범위 포함)
- not_enough_evidence: 판정할 근거가 부족하다

{tool_rule}
evidence_cutoff 이후에 나온 정보는 판정 근거로 쓰지 마세요.
판정 근거(justification)와 참고한 출처(cited_sources, URL 또는 문서명)를 함께 내세요. 주장이 틀렸다면 correction에 정정 문장을 쓰세요.

주장 정보(JSON):
{claim}
"""
TOOL_RULES = {
    "closed_book": "도구는 쓸 수 없습니다. 알고 있는 지식으로만 판단하세요.",
    "plain_web": "필요하면 웹 검색(WebSearch)과 웹 페이지 열기(WebFetch)를 사용하세요.",
}


# --------------------------------------------------------------------------
# Sample and commands
# --------------------------------------------------------------------------

def stratified_sample(gold_path: Path) -> list[str]:
    """All refuted and NEE claims plus a seeded draw of supported ones."""
    rows = read_jsonl(gold_path)
    by: dict[str | None, list[str]] = {}
    for r in rows:
        by.setdefault(r.get("label"), []).append(r["claim_id"])
    supported = sorted(by.get("supported", []))
    picked = random.Random(SAMPLE_SEED).sample(supported, N_SUPPORTED)
    return sorted(by.get("refuted", []) + by.get("not_enough_evidence", []) + picked)


def _skill_body() -> str:
    return skill_body(ROOT / "skills/factcheck-mission-agent/SKILL.md")


def _claim_view(claim: dict) -> str:
    return json.dumps(claim, ensure_ascii=False, indent=2)


def build_command(model: str, condition: str, claim: dict, paths: dict, exp_id: str,
                  cli_version: str) -> tuple[list[str], str]:
    """Return argv and the prompt. The prompt goes on stdin: variadic flags such
    as --allowedTools would otherwise swallow a trailing positional prompt."""
    common = ["claude", "-p", "--model", model, "--output-format", "stream-json", "--verbose",
              "--no-session-persistence", "--setting-sources", "project",
              "--disable-slash-commands", "--strict-mcp-config"]
    if condition in TOOL_RULES:
        prompt = BASELINE_PROMPT.format(tool_rule=TOOL_RULES[condition], claim=_claim_view(claim))
        tools = "" if condition == "closed_book" else "WebSearch,WebFetch"
        cmd = common + ["--tools", tools, "--mcp-config", '{"mcpServers":{}}',
                        "--json-schema", json.dumps(BASELINE_SCHEMA, ensure_ascii=False)]
        if tools:
            cmd += ["--allowedTools", tools]
        return cmd, prompt

    server_args = [
        "run", "--project", str(ROOT), "python", str(ROOT / "scripts/mcp_stdio.py"),
        "--arm", "C1", "--run-id", f"{exp_id}-{model}-harness",
        "--model-id", f"claude-code-{cli_version}+{model}",
        "--prompt-version", "skill-v2-sysprompt",
        "--corpus", str(ROOT / "data/raw/task_a/corpus_c1.jsonl"),
        "--out", str(paths["server_log"]),
        "--missions-dir", str(paths["missions"]),
        "--cache", str(paths["cache"]),
    ]
    mcp = {"mcpServers": {SERVER: {"command": "uv", "args": server_args}}}
    prompt = PROMPT_TEMPLATE.format(claim_id=claim["claim_id"])
    return common + ["--tools", "", "--mcp-config", json.dumps(mcp, ensure_ascii=False),
                     "--allowedTools", f"mcp__{SERVER}",
                     "--append-system-prompt", _skill_body()], prompt


def job_paths(raw_dir: Path, work_root: Path, model: str, condition: str, claim_id: str) -> dict:
    base = raw_dir / model / condition
    return {
        "stream": base / f"{claim_id}.stream.jsonl",
        "stderr": base / f"{claim_id}.stderr.txt",
        "record": base / f"{claim_id}.json",
        "server_log": base / f"{claim_id}.run.jsonl",
        "missions": base / "missions" / claim_id,
        "cache": base / f"{claim_id}.cache.jsonl",
        "cwd": work_root / model / condition / claim_id,
    }


# --------------------------------------------------------------------------
# Running one session
# --------------------------------------------------------------------------

def parse_stream(lines: list[str]) -> dict:
    init, final, tool_uses = {}, {}, {}
    for line in lines:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "system" and msg.get("subtype") == "init":
            init = msg
        elif msg.get("type") == "result":
            final = msg
        elif msg.get("type") == "assistant":
            for block in (msg.get("message") or {}).get("content") or []:
                if block.get("type") == "tool_use":
                    tool_uses[block["name"]] = tool_uses.get(block["name"], 0) + 1
    return {"init": init, "final": final, "tool_uses": tool_uses}


def verdict_from_server_log(path: Path) -> dict | None:
    if not path.exists():
        return None
    rows = read_jsonl(path)
    return rows[-1]["result"] if rows else None


def run_job(model, condition, claim, paths, exp_id, cli_version, timeout) -> dict:
    for key in ("stream", "missions", "cwd"):
        (paths[key] if key != "stream" else paths[key].parent).mkdir(parents=True, exist_ok=True)
    cmd, prompt = build_command(model, condition, claim, paths, exp_id, cli_version)
    env = {**os.environ, "ENABLE_TOOL_SEARCH": "false"}
    started = time.time()
    status = ExecutionStatus.OK.value
    try:
        proc = subprocess.run(cmd, cwd=paths["cwd"], env=env, capture_output=True, text=True,
                              timeout=timeout, input=prompt)
        stdout, stderr, rc = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr, rc, status = "timeout", None, ExecutionStatus.TIMEOUT.value
    paths["stream"].write_text(stdout, encoding="utf-8")
    paths["stderr"].write_text(stderr or "", encoding="utf-8")
    parsed = parse_stream(stdout.splitlines())
    final, init = parsed["final"], parsed["init"]

    verdict = abstain = None
    if condition == "harness":
        result = verdict_from_server_log(paths["server_log"])
        if result:
            verdict, abstain = result.get("verdict"), bool(result.get("abstain"))
            mission = {"mission_type": result.get("mission_type"),
                       "mission_status": (result.get("mission_output") or {}).get("status")}
        else:
            mission = {}
    else:
        out = final.get("structured_output") or {}
        verdict, abstain = out.get("verdict"), out.get("abstain")
        mission = {}
    if status == ExecutionStatus.OK.value and (rc not in (0, None) or final.get("is_error")):
        status = ExecutionStatus.PROVIDER_ERROR.value
    if status == ExecutionStatus.OK.value and verdict not in [v.value for v in Verdict]:
        status = ExecutionStatus.PARSE_ERROR.value
        verdict = None

    # The init message echoes the working directory; scan only what the model saw or wrote.
    text = "\n".join(l for l in stdout.splitlines() if '"subtype":"init"' not in l.replace(" ", "")).lower()
    record = {
        "exp_id": exp_id, "model_alias": model, "condition": condition,
        "claim_id": claim["claim_id"], "verdict": verdict, "abstain": bool(abstain),
        "execution_status": status, "return_code": rc,
        "model": init.get("model"), "cli_version": cli_version,
        "tools_available": sorted(init.get("tools") or []),
        "mcp_servers": [s.get("name") for s in init.get("mcp_servers") or []],
        "tool_uses": parsed["tool_uses"],
        "num_turns": final.get("num_turns"),
        "duration_ms": final.get("duration_ms") or int((time.time() - started) * 1000),
        "cost_usd": final.get("total_cost_usd"),
        "usage": final.get("usage"),
        "leak_markers": [m for m in LEAK_MARKERS if m.lower() in text],
        **mission,
    }
    paths["record"].write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _graded(rec: dict, gold: dict[str, str | None]) -> Graded:
    label = gold.get(rec["claim_id"])
    verdict = Verdict(rec["verdict"]) if rec.get("verdict") else None
    gl = Verdict(label) if label else None
    return Graded(claim_id=rec["claim_id"], arm=rec["condition"], condition=rec["model_alias"],
                  gold_label=gl, verdict=verdict, v=bool(gl and verdict == gl),
                  abstain=bool(rec.get("abstain")),
                  execution_status=ExecutionStatus(rec["execution_status"]),
                  cost_usd=rec.get("cost_usd") or 0.0, graded_for_label=gl is not None)


def score(raw_dir: Path, out_dir: Path, gold_path: Path, claims: list[str]) -> dict:
    gold = {r["claim_id"]: r.get("label") for r in read_jsonl(gold_path)}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(raw_dir.glob("*/*/*.json"))]
    records = [r for r in records if r["claim_id"] in claims]
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        groups.setdefault((r["model_alias"], r["condition"]), []).append(r)

    table = []
    for (model, cond), recs in sorted(groups.items()):
        graded = [_graded(r, gold) for r in recs]
        refuted = [g for g in graded if g.gold_label == Verdict.REFUTED]
        supported = [g for g in graded if g.gold_label == Verdict.SUPPORTED]
        costs = [r["cost_usd"] for r in recs if r.get("cost_usd") is not None]
        durations = [r["duration_ms"] for r in recs if r.get("duration_ms")]
        table.append({
            "model": model, "condition": cond, "episodes": len(recs),
            "models_seen": sorted({r["model"] for r in recs if r.get("model")}),
            "accuracy": accuracy(graded), "macro_f1": macro_f1(graded),
            "coverage": coverage(graded), "abstain_rate": abstain_rate(graded),
            "refuted_recall": accuracy(refuted), "supported_recall": accuracy(supported),
            "execution_status": {s: sum(1 for r in recs if r["execution_status"] == s)
                                 for s in sorted({r["execution_status"] for r in recs})},
            "cost_usd_total": round(sum(costs), 4) if costs else None,
            "cost_usd_reported_for": len(costs),
            "duration_s_median": (sorted(durations)[len(durations) // 2] / 1000) if durations else None,
            "mean_turns": (round(sum(r["num_turns"] or 0 for r in recs) / len(recs), 2)) if recs else None,
            "sessions_with_leak_markers": [r["claim_id"] for r in recs if r.get("leak_markers")],
            "tool_use_totals": _sum_counts(r.get("tool_uses") or {} for r in recs),
        })
        if cond == "harness":
            table[-1]["missions"] = _sum_counts(
                {f"{r.get('mission_type')}:{r.get('mission_status')}": 1} for r in recs if r.get("mission_type"))

    out_dir.mkdir(parents=True, exist_ok=True)
    episodes = [{k: r.get(k) for k in ("model_alias", "model", "condition", "claim_id", "verdict",
                                        "abstain", "execution_status", "num_turns", "duration_ms",
                                        "cost_usd", "tool_uses", "mission_type", "mission_status",
                                        "leak_markers")}
                | {"gold": gold.get(r["claim_id"]),
                   "correct": bool(r.get("verdict") and r.get("verdict") == gold.get(r["claim_id"]))}
                for r in records]
    with (out_dir / "episodes.jsonl").open("w", encoding="utf-8") as fh:
        for row in sorted(episodes, key=lambda e: (e["model_alias"], e["condition"], e["claim_id"])):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {"claims": claims, "n_claims": len(claims),
               "gold_distribution": _sum_counts({str(gold.get(c)): 1} for c in claims),
               "always_supported_accuracy": sum(gold.get(c) == "supported" for c in claims) / len(claims),
               "table": table}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    return summary


def _sum_counts(dicts) -> dict:
    out: dict[str, int] = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return dict(sorted(out.items()))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["run", "score"])
    parser.add_argument("--exp-id", default="exp-001-compare")
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--claims", help="쉼표 구분 claim_id. 기본값은 층화 표본 20건")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=900, help="세션당 제한 시간(초)")
    parser.add_argument("--work-root", type=Path, default=Path.home() / "agent-runs",
                        help="세션별 빈 작업 디렉터리를 만들 곳. 저장소 밖이어야 한다")
    parser.add_argument("--only-missing", action="store_true",
                        help="기록이 없는 세션만 실행 (명시적으로 요청할 때만)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    gold_path = ROOT / "data/task_a/gold.jsonl"
    claim_ids = args.claims.split(",") if args.claims else stratified_sample(gold_path)
    raw_dir = ROOT / "results/raw" / args.exp_id
    out_dir = ROOT / "results" / args.exp_id

    if args.action == "score":
        print(json.dumps(score(raw_dir, out_dir, gold_path, claim_ids), ensure_ascii=False, indent=2))
        return 0

    work_root = (args.work_root / args.exp_id).expanduser().resolve()
    if work_root == ROOT or ROOT in work_root.parents:
        raise SystemExit(f"작업 디렉터리는 저장소 밖이어야 합니다: {work_root}")
    claims = {c["claim_id"]: c for c in read_jsonl(ROOT / "data/task_a/claims.jsonl")}
    cli_version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.split()[0]
    jobs = []
    for model in args.models.split(","):
        for cond in args.conditions.split(","):
            if cond not in CONDITIONS:
                raise SystemExit(f"알 수 없는 조건: {cond}")
            for cid in claim_ids:
                paths = job_paths(raw_dir, work_root, model, cond, cid)
                if paths["record"].exists():
                    if args.only_missing:
                        continue
                    raise SystemExit(f"이미 기록이 있습니다(덮어쓰지 않음): {paths['record']}")
                jobs.append((model, cond, claims[cid], paths))
    print(f"세션 {len(jobs)}개: models={args.models} conditions={args.conditions} claims={len(claim_ids)}",
          file=sys.stderr)
    if args.dry_run:
        m, c, cl, p = jobs[0] if jobs else (None,) * 4
        if jobs:
            print(json.dumps(build_command(m, c, cl, p, args.exp_id, cli_version), ensure_ascii=False)[:3000])
        return 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_job, m, c, cl, p, args.exp_id, cli_version, args.timeout): (m, c, cl["claim_id"])
                   for m, c, cl, p in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            m, c, cid = futures[fut]
            try:
                rec = fut.result()
                print(f"[{i}/{len(jobs)}] {m} {c} {cid} -> {rec['verdict']} ({rec['execution_status']}, "
                      f"${rec['cost_usd']}, {rec['duration_ms']} ms)", file=sys.stderr, flush=True)
            except Exception as exc:  # recorded, not retried
                print(f"[{i}/{len(jobs)}] {m} {c} {cid} -> 실행기 오류 {exc!r}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
