"""Launch the Task A + Mission Verification MCP Server over stdio.

Connect any MCP-compatible AI agent (Antigravity, Claude Code, Cursor, Codex):

    uv run python scripts/mcp_stdio.py --arm C1 --model-id <agent+model> --out results/exp-001/c1.jsonl
    uv run python scripts/mcp_stdio.py --arm C2 --live-web --model-id <agent+model> --out results/exp-001/c2.jsonl

For experiments, do not point an agent at this repository directly: build an
isolated workspace with scripts/make_agent_workspace.py so the agent cannot
open gold files with its own tools.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.mcp_server import (  # noqa: E402
    IMPLEMENTED_CONDITIONS, AgentEnvironment, MCPStdioServer, current_commit,
)
from task_a.web import LiveWebProvider  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/raw/task_a/corpus_c1.jsonl",
                        help="에이전트용 코퍼스(JSONL). C1·C2에서 필수. 형식은 data/README.md")
    parser.add_argument("--arm", choices=["C0", "C1", "C2"], default="C1")
    parser.add_argument("--condition", default="sufficient", choices=list(IMPLEMENTED_CONDITIONS),
                        help="missing/conflict/misleading은 코퍼스 변형이 아직 없어 거부됩니다")
    parser.add_argument("--out", type=Path, default=ROOT / "results/exp-mcp/run.jsonl")
    parser.add_argument("--run-id", default="exp-mcp")
    parser.add_argument("--model-id", default="unrecorded",
                        help="에이전트와 모델 버전, 예: claude-code-2.x+claude-opus-5-5")
    parser.add_argument("--prompt-version", default="skill-v2")
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
        code_commit=current_commit(ROOT),
        prompt_version=args.prompt_version,
    )
    MCPStdioServer(env).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
