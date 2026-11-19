"""Build an isolated Claude Code workspace for one Task A run.

The MCP server keeps gold out of its own tools, but a host agent such as Claude
Code also has file, shell and web tools of its own. Run from this repository,
it can open data/task_a/gold.jsonl or evaluation.md directly. This script
builds a directory OUTSIDE the repository that holds only:

    .mcp.json                     the factcheck-mission server, fixed arm/corpus/log
    .claude/settings.json         built-in file/shell/web tools denied, MCP allowed
    .claude/skills/factcheck-mission-agent/SKILL.md
    RUN.md                        the per-claim headless command and fixed prompt

The server process itself runs from the repository (it needs the code), but
the agent never gets a tool that reads files. Nothing here calls a model.

    uv run python scripts/make_agent_workspace.py \\
        --workspace ~/agent-runs/exp-001-c1 --run-id exp-001-c1 --arm C1 \\
        --model-id claude-code-<version>+<model-id>

Other agents (Codex, Cursor, ...) need the equivalent settings in their own
config format; only the Claude Code layout is generated here.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_NAME = "factcheck-mission"
SKILL_SRC = ROOT / "skills/factcheck-mission-agent/SKILL.md"

#: Claude Code built-in tools that could read the repository, run commands or
#: reach the web outside the arm's control. Deny rules win over allow rules.
DENIED_TOOLS = ("Bash", "Read", "Edit", "Write", "Glob", "Grep", "NotebookEdit",
                "WebFetch", "WebSearch", "Agent", "Task")

PROMPT_TEMPLATE = (
    "factcheck-mission-agent 스킬의 절차를 따라 주장 {claim_id}를 검증하세요. "
    "start_episode로 {claim_id}를 시작하고, 제공된 MCP 도구만 사용하며, "
    "finish_verification을 한 번 호출해 끝내세요."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", type=Path, required=True,
                        help="생성할 작업공간. 저장소 밖이어야 한다")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--arm", choices=["C0", "C1", "C2"], required=True)
    parser.add_argument("--model-id", required=True,
                        help="에이전트와 모델 버전. 로그의 config.model_id로 기록된다")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/raw/task_a/corpus_c1.jsonl")
    parser.add_argument("--live-web", action="store_true", help="C2에서 실제 웹 검색 사용")
    parser.add_argument("--no-skill", action="store_true",
                        help="Skill 없이 도구만 연결 (Skill 효과 비교용)")
    parser.add_argument("--force", action="store_true", help="기존 작업공간 덮어쓰기")
    return parser.parse_args(argv)


def build(args: argparse.Namespace) -> Path:
    workspace = args.workspace.expanduser().resolve()
    if workspace == ROOT or ROOT in workspace.parents:
        raise SystemExit(f"작업공간은 저장소 밖이어야 합니다: {workspace}")
    if workspace.exists() and any(workspace.iterdir()):
        if not args.force:
            raise SystemExit(f"비어 있지 않은 작업공간입니다(--force로 덮어쓰기): {workspace}")
        shutil.rmtree(workspace)
    if args.arm != "C0" and not args.corpus.exists():
        raise SystemExit(f"{args.arm}에는 코퍼스가 필요합니다: {args.corpus} (data/README.md 참고)")
    if args.live_web and args.arm != "C2":
        raise SystemExit("--live-web은 C2에서만 쓸 수 있습니다.")

    run_dir = ROOT / "results" / args.run_id
    private_dir = ROOT / "results/raw" / args.run_id   # git-ignored: missions, cache
    prompt_version = "tools-only-v2" if args.no_skill else "skill-v2"
    server_args = [
        "run", "--project", str(ROOT), "python", str(ROOT / "scripts/mcp_stdio.py"),
        "--arm", args.arm,
        "--run-id", args.run_id,
        "--model-id", args.model_id,
        "--prompt-version", prompt_version,
        "--out", str(run_dir / "run.jsonl"),
        "--missions-dir", str(private_dir / "missions"),
        "--cache", str(private_dir / "tools-cache.jsonl"),
    ]
    if args.arm != "C0":
        server_args += ["--corpus", str(args.corpus.resolve())]
    if args.live_web:
        server_args.append("--live-web")

    (workspace / ".claude").mkdir(parents=True)
    (workspace / ".mcp.json").write_text(json.dumps(
        {"mcpServers": {SERVER_NAME: {"command": "uv", "args": server_args}}},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    settings = {
        "permissions": {"allow": [f"mcp__{SERVER_NAME}"], "deny": list(DENIED_TOOLS)},
        "enabledMcpjsonServers": [SERVER_NAME],
    }
    (workspace / ".claude/settings.json").write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.no_skill:
        skill_dir = workspace / ".claude/skills/factcheck-mission-agent"
        skill_dir.mkdir(parents=True)
        shutil.copyfile(SKILL_SRC, skill_dir / "SKILL.md")

    deny = ",".join(DENIED_TOOLS)
    prompt = PROMPT_TEMPLATE.format(claim_id="<CLAIM_ID>")
    (workspace / "RUN.md").write_text(f"""# {args.run_id}

arm `{args.arm}` · model_id `{args.model_id}` · prompt_version `{prompt_version}`
log `{run_dir / 'run.jsonl'}`

주장마다 새 세션으로 한 번씩 실행합니다. 한 세션에서 여러 주장을 풀면 앞 주장의
근거가 다음 주장의 컨텍스트에 남습니다. 실행은 팀이 승인한 호출 예산 안에서만 합니다.

```bash
cd {workspace}
claude -p "{prompt}" \\
  --mcp-config .mcp.json --strict-mcp-config \\
  --allowedTools "mcp__{SERVER_NAME}" \\
  --disallowedTools "{deny}"
```

`--strict-mcp-config`는 사용자 계정에 연결된 다른 MCP 서버(파일·git 도구 포함)를 막습니다.
사용자 전역 Skill·플러그인은 이 설정으로 꺼지지 않으므로 실행 환경 기록에 남깁니다.
""", encoding="utf-8")
    return workspace


def main(argv: list[str] | None = None) -> int:
    workspace = build(parse_args(argv))
    print(f"작업공간 생성: {workspace}\n실행 방법: {workspace / 'RUN.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
