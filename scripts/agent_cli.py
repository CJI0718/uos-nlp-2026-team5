"""CLI interface for existing AI agents to execute Task A + Mission episodes.

Provides the exact same tools and leakage boundaries as `mcp_stdio.py`, while
persisting active episode state in a local state file so CLI/bash-based agents
can invoke one tool per command and automatically log to `RunLog`.

Examples:
    uv run python scripts/agent_cli.py list --limit 5
    uv run python scripts/agent_cli.py start FC002 --arm C1 --out results/exp-cli/c1.jsonl
    uv run python scripts/agent_cli.py search "Vision Pro 사전예약 2024년 1월 19일"
    uv run python scripts/agent_cli.py calc tz_convert --time "2024-01-19 05:00" --from-tz PST --to-tz KST
    uv run python scripts/agent_cli.py mission event_manager --verdict refuted \
        --title "비전 프로 사전예약" --summary "시간대 오보 정정 반영" \
        --correction "2024-01-19 22:00 KST" --event-start-kst "2024-01-19 22:00"
    uv run python scripts/agent_cli.py finish --verdict refuted --cited EV_FC002_apple \
        --justification "공식 발표는 05:00 PST로 한국시간 22:00이다." \
        --correction "2024-01-19 22:00 KST" --distortion-type timezone_or_date_error \
        --problematic-span "오전 5시(한국시간)" --mission-type event_manager
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.mcp_server import ActiveEpisode, AgentEnvironment  # noqa: E402
from task_a.schema import ToolEvent, ToolStatus  # noqa: E402
from task_a.web import LiveWebProvider  # noqa: E402

DEFAULT_STATE = ROOT / "data/cache/active_cli_session.json"


def _save_state(path: Path, env: AgentEnvironment, extra: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ep = env.active
    data = {
        **extra,
        "active": None if ep is None else {
            "claim_id": ep.claim.claim_id,
            "started_at": ep.started_at,
            "step": ep.step,
            "tool_calls": ep.tool_calls,
            "external_calls": ep.external_calls,
            "events": [e.to_dict() for e in ep.events],
            "last_mission": ep.last_mission,
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_env(state_path: Path) -> tuple[AgentEnvironment, dict]:
    if not state_path.exists():
        raise SystemExit("활성 CLI 세션이 없습니다. 먼저 `start <CLAIM_ID>`를 실행하세요.")
    meta = json.loads(state_path.read_text(encoding="utf-8"))
    web = LiveWebProvider(provider=meta.get("web_provider", "auto")) if (
        meta["arm"] == "C2" and meta.get("live_web")
    ) else None
    env = AgentEnvironment(
        claims_path=meta["claims"],
        out_path=meta["out"],
        arm=meta["arm"],
        condition=meta["condition"],
        model_id=meta["model_id"],
        run_id=meta["run_id"],
        corpus_path=meta.get("corpus"),
        cache_path=meta.get("cache"),
        missions_dir=meta.get("missions_dir"),
        tokenizer=meta.get("tokenizer", "kiwi"),
        web_provider=web,
    )
    active = meta.get("active")
    if active:
        claim = env.claims[active["claim_id"]]
        events = [
            ToolEvent(
                step=e["step"],
                tool=e["tool"],
                args=e["args"],
                status=ToolStatus(e["status"]),
                observation_chars=e["observation_chars"],
                elapsed_ms=e["elapsed_ms"],
                evidence_ids=e.get("evidence_ids", []),
                ranks=e.get("ranks", []),
                rendered_snippet_ids=e.get("rendered_snippet_ids", []),
                corruption_flags=e.get("corruption_flags", []),
                external=e.get("external", False),
                error=e.get("error"),
            )
            for e in active.get("events", [])
        ]
        env.active = ActiveEpisode(
            claim=claim,
            started_at=active["started_at"],
            step=active["step"],
            tool_calls=active["tool_calls"],
            external_calls=active["external_calls"],
            events=events,
            last_mission=active.get("last_mission"),
        )
    return env, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="검증할 주장 목록 조회")
    p_list.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    p_list.add_argument("--out", type=Path, default=ROOT / "results/exp-cli/run.jsonl")
    p_list.add_argument("--limit", type=int, default=10)
    p_list.add_argument("--only-pending", action="store_true")

    p_start = sub.add_parser("start", help="에피소드 시작")
    p_start.add_argument("claim_id")
    p_start.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    p_start.add_argument("--corpus", type=Path, default=None)
    p_start.add_argument("--arm", choices=["C0", "C1", "C2"], default="C1")
    p_start.add_argument("--condition", default="sufficient",
                         choices=["sufficient", "missing", "conflict", "misleading"])
    p_start.add_argument("--out", type=Path, default=ROOT / "results/exp-cli/run.jsonl")
    p_start.add_argument("--run-id", default="exp-cli")
    p_start.add_argument("--model-id", default="external-cli-agent")
    p_start.add_argument("--tokenizer", choices=["kiwi", "bigram"], default="kiwi")
    p_start.add_argument("--cache", type=Path, default=ROOT / "data/cache/tools.jsonl")
    p_start.add_argument("--missions-dir", type=Path, default=ROOT / "missions")
    p_start.add_argument("--live-web", action="store_true")
    p_start.add_argument("--web-provider", choices=["auto", "tavily", "ddg"], default="auto")

    p_search = sub.add_parser("search", help="고정 코퍼스 검색 (search_evidence)")
    p_search.add_argument("query")
    p_search.add_argument("--top-k", type=int, default=5)

    p_read = sub.add_parser("read", help="코퍼스 문서 본문 열람 (read_evidence)")
    p_read.add_argument("evidence_id")
    p_read.add_argument("--section", default=None)

    p_calc = sub.add_parser("calc", help="결정론적 계산기 (calculate_comparison)")
    p_calc.add_argument("op", choices=[
        "diff", "pct_change", "percentage_point_gap", "tz_convert", "scale_unit", "multiply", "ratio"
    ])
    p_calc.add_argument("--a", type=float)
    p_calc.add_argument("--b", type=float)
    p_calc.add_argument("--old", type=float)
    p_calc.add_argument("--new", type=float)
    p_calc.add_argument("--value", type=float)
    p_calc.add_argument("--time")
    p_calc.add_argument("--from-tz")
    p_calc.add_argument("--to-tz")
    p_calc.add_argument("--from-unit")
    p_calc.add_argument("--to-unit")

    p_web = sub.add_parser("web", help="외부 웹 검색 (search_web, C2 전용)")
    p_web.add_argument("query")
    p_web.add_argument("--top-k", type=int, default=5)

    p_fetch = sub.add_parser("fetch", help="외부 URL 원문 읽기 (fetch_url, C2 전용)")
    p_fetch.add_argument("url")

    p_mission = sub.add_parser("mission", help="검증 게이팅 기반 후속 Mission / Tracking 실행")
    p_mission.add_argument("mission_type", choices=[
        "no_op", "event_manager", "news_to_artifact", "opportunity_execution",
        "app_safe_trial", "continuous_tracking", "hold_abstain",
    ])
    p_mission.add_argument("--verdict", required=True,
                           choices=["supported", "refuted", "not_enough_evidence"])
    p_mission.add_argument("--abstain", action="store_true")
    p_mission.add_argument("--title", required=True)
    p_mission.add_argument("--summary", required=True)
    p_mission.add_argument("--cited", nargs="*", default=[])
    p_mission.add_argument("--correction", default=None)
    p_mission.add_argument("--distortion-type", default=None)
    p_mission.add_argument("--event-start-kst", default=None)
    p_mission.add_argument("--tracking-condition", default=None)
    p_mission.add_argument("--tracking-queries", nargs="*", default=[])

    p_finish = sub.add_parser("finish", help="최종 판정 및 왜곡/미션 결과 제출 (finish_verification)")
    p_finish.add_argument("--verdict", required=True,
                          choices=["supported", "refuted", "not_enough_evidence"])
    p_finish.add_argument("--abstain", action="store_true")
    p_finish.add_argument("--cited", nargs="*", default=[])
    p_finish.add_argument("--justification", required=True)
    p_finish.add_argument("--correction", default=None)
    p_finish.add_argument("--stop-reason", default="evidence_sufficient",
                          choices=["evidence_sufficient", "budget_exhausted",
                                   "no_further_tools_helpful", "conflict_unresolved"])
    p_finish.add_argument("--distortion-type", default=None)
    p_finish.add_argument("--problematic-span", default=None)
    p_finish.add_argument("--mission-type", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "list":
        env = AgentEnvironment(claims_path=args.claims, out_path=args.out, tokenizer="bigram")
        print(json.dumps(env.list_claims(args.limit, args.only_pending), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "start":
        meta = {
            "claims": str(args.claims),
            "corpus": str(args.corpus) if args.corpus else None,
            "arm": args.arm,
            "condition": args.condition,
            "out": str(args.out),
            "run_id": args.run_id,
            "model_id": args.model_id,
            "tokenizer": args.tokenizer,
            "cache": str(args.cache) if args.cache else None,
            "missions_dir": str(args.missions_dir),
            "live_web": args.live_web,
            "web_provider": args.web_provider,
        }
        web = LiveWebProvider(provider=args.web_provider) if (args.arm == "C2" and args.live_web) else None
        env = AgentEnvironment(
            claims_path=args.claims,
            out_path=args.out,
            arm=args.arm,
            condition=args.condition,
            model_id=args.model_id,
            run_id=args.run_id,
            corpus_path=args.corpus,
            cache_path=args.cache,
            missions_dir=args.missions_dir,
            tokenizer=args.tokenizer,
            web_provider=web,
        )
        out = env.start_episode(args.claim_id)
        _save_state(args.state, env, meta)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    env, meta = _load_env(args.state)

    if args.cmd == "search":
        out = env.call_tool("search_evidence", {"query": args.query, "top_k": args.top_k})
    elif args.cmd == "read":
        out = env.call_tool("read_evidence", {"evidence_id": args.evidence_id, "section": args.section})
    elif args.cmd == "calc":
        calc_args = {"op": args.op}
        for k in ("a", "b", "old", "new", "value", "time", "from_tz", "to_tz", "from_unit", "to_unit"):
            val = getattr(args, k)
            if val is not None:
                calc_args[k] = val
        out = env.call_tool("calculate_comparison", calc_args)
    elif args.cmd == "web":
        out = env.call_tool("search_web", {"query": args.query, "top_k": args.top_k})
    elif args.cmd == "fetch":
        out = env.call_tool("fetch_url", {"url": args.url})
    elif args.cmd == "mission":
        out = env.call_tool("execute_mission", {
            "mission_type": args.mission_type,
            "verdict": args.verdict,
            "abstain": args.abstain,
            "title": args.title,
            "summary": args.summary,
            "cited_evidence_ids": args.cited,
            "correction": args.correction,
            "distortion_type": args.distortion_type,
            "event_start_kst": args.event_start_kst,
            "tracking_condition": args.tracking_condition,
            "tracking_queries": args.tracking_queries,
        })
    elif args.cmd == "finish":
        out = env.call_tool("finish_verification", {
            "verdict": args.verdict,
            "abstain": args.abstain,
            "cited_evidence_ids": args.cited,
            "justification": args.justification,
            "correction": args.correction,
            "stop_reason": args.stop_reason,
            "distortion_type": args.distortion_type,
            "problematic_span": args.problematic_span,
            "mission_type": args.mission_type,
        })
    else:
        raise SystemExit(f"Unknown command: {args.cmd}")

    _save_state(args.state, env, meta)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
