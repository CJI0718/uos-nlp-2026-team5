"""Launch the Task A + Mission Verification MCP Server over stdio.

Connect any MCP-compatible AI agent (Antigravity, Claude Code, Cursor, Codex):

    uv run python scripts/mcp_stdio.py --arm C1 --model-id <agent+model> --out results/exp-001/c1.jsonl
    uv run python scripts/mcp_stdio.py --arm C2 --live-web --model-id <agent+model> --out results/exp-001/c2.jsonl

Verify any claim a user brings (no preset claims, live web, results in ./missions):

    uv run python scripts/mcp_stdio.py --arm C2 --live-web --web-only --allow-user-claims \
        --no-preset-claims --model-id <agent+model> --out results/user/run.jsonl

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
    GATE_MODES, IMPLEMENTED_CONDITIONS, PROVENANCE_MODES, AgentEnvironment, MCPStdioServer, current_commit,
)
from task_a.web import LiveWebProvider, load_env_file  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/raw/task_a/corpus_c1.jsonl",
                        help="에이전트용 코퍼스(JSONL). C1·C2에서 필수(--web-only 제외). 형식은 data/README.md")
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
    parser.add_argument("--gate", choices=list(GATE_MODES), default="verdict",
                        help="미션 통제: verdict(기본) / provenance(출처 독립성 추가) / off(실험 기준선 전용)")
    parser.add_argument("--data-version", default="claims-2026-11-07")
    parser.add_argument("--provenance-mode", choices=list(PROVENANCE_MODES), default="labeled",
                        help="labeled: 코퍼스 출처군 사용, 없으면 본문 겹침으로 묶음 / auto: 항상 본문 겹침으로 묶음")
    parser.add_argument("--web-only", action="store_true",
                        help="C2에서 고정 코퍼스 없이 웹 검색·열람만 쓴다 (실제 웹 사례 실험용)")
    parser.add_argument("--max-tool-calls", type=int, default=12)
    parser.add_argument("--max-external-calls", type=int, default=4,
                        help="search_web·fetch_url 호출 상한 (Tavily 크레딧 상한이기도 함)")
    parser.add_argument("--allow-user-claims", action="store_true",
                        help="submit_claim 도구를 켠다: 미리 등록하지 않은 주장 텍스트를 바로 검증")
    parser.add_argument("--no-preset-claims", action="store_true",
                        help="--claims 파일을 읽지 않는다(--allow-user-claims와 함께)")
    parser.add_argument("--hide-provenance", action="store_true",
                        help="검색·열람 결과에서 출처유형·출처군 표시를 뺀다 (실험 조건용)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_env_file(ROOT / ".env")  # TAVILY_API_KEY only; the shell environment wins
    web = LiveWebProvider(provider=args.web_provider) if (args.arm == "C2" and args.live_web) else None
    env = AgentEnvironment(
        claims_path=None if args.no_preset_claims else args.claims,
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
        gate=args.gate,
        show_provenance=not args.hide_provenance,
        data_version=args.data_version,
        provenance_mode=args.provenance_mode,
        web_only=args.web_only,
        max_tool_calls=args.max_tool_calls,
        max_external_calls=args.max_external_calls,
        allow_user_claims=args.allow_user_claims,
    )
    MCPStdioServer(env).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
