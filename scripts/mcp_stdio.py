"""Launch the Task A + Mission Verification MCP Server over stdio.

Connect any MCP-compatible AI agent (Antigravity, Claude Code, Cursor, Codex):

    uv run python scripts/mcp_stdio.py --arm C1 --out results/exp-mcp/c1.jsonl
    uv run python scripts/mcp_stdio.py --arm C2 --live-web --out results/exp-mcp/c2.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.mcp_server import AgentEnvironment, MCPStdioServer  # noqa: E402
from task_a.web import LiveWebProvider  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    parser.add_argument("--corpus", type=Path, default=None)
    parser.add_argument("--arm", choices=["C0", "C1", "C2"], default="C1")
    parser.add_argument("--condition", default="sufficient",
                        choices=["sufficient", "missing", "conflict", "misleading"])
    parser.add_argument("--out", type=Path, default=ROOT / "results/exp-mcp/run.jsonl")
    parser.add_argument("--run-id", default="exp-mcp")
    parser.add_argument("--model-id", default="external-mcp-agent")
    parser.add_argument("--tokenizer", choices=["kiwi", "bigram"], default="kiwi")
    parser.add_argument("--cache", type=Path, default=ROOT / "data/cache/tools.jsonl")
    parser.add_argument("--missions-dir", type=Path, default=ROOT / "missions")
    parser.add_argument("--live-web", action="store_true",
                        help="C2에서 실제 웹 검색(Tavily 또는 DuckDuckGo 폴백)을 활성화합니다.")
    parser.add_argument("--web-provider", choices=["auto", "tavily", "ddg"], default="auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
    MCPStdioServer(env).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
