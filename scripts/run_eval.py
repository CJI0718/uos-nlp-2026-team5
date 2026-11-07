"""Run Task A episodes and append them to a run log.

Dry run by default: no provider is contacted and nothing is spent. Real calls
need --live plus an explicit model id, and read the key from the environment
only, never from argv or a file in the repository.

    uv run python scripts/run_eval.py --arm C1 --policy react --limit 5 \
        --out results/exp-001/c1-react.jsonl

    TASK_A_API_KEY=... uv run python scripts/run_eval.py --live \
        --model-id <id> --arm C2 --policy react --budget-usd 2.00 \
        --out results/exp-001/c2-react.jsonl

This command cannot read gold.jsonl. Scoring is scripts/score_run.py.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.runner import RunSpec, execute, load_claims, load_corpus  # noqa: E402
from task_a.toollog import RunLog  # noqa: E402


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="코퍼스 JSONL. 없으면 빈 코퍼스로 실행한다.")
    parser.add_argument("--arm", choices=["C0", "C1", "C2"], required=True)
    parser.add_argument("--policy", choices=["react", "fixed_workflow", "closed_book"],
                        required=True)
    parser.add_argument("--condition", default="sufficient",
                        choices=["sufficient", "missing", "conflict", "misleading"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run-id", default="exp-001")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", nargs="*", default=[], help="FC001 FC002 형태로 제한")
    parser.add_argument("--tokenizer", choices=["kiwi", "bigram"], default="kiwi")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-tool-calls", type=int, default=12)
    parser.add_argument("--max-external-calls", type=int, default=4)
    parser.add_argument("--cache", type=Path, default=ROOT / "data/cache/tools.jsonl")

    live = parser.add_argument_group("실호출 (승인 필요)")
    live.add_argument("--live", action="store_true",
                      help="없으면 dry-run이다. dry-run 결과는 성과로 인용하지 않는다.")
    live.add_argument("--model-id", default=None)
    live.add_argument("--base-url", default=None)
    live.add_argument("--budget-usd", type=float, default=None,
                      help="누적 비용이 이 값을 넘으면 실행을 중단한다.")
    return parser.parse_args(argv)


def build_spec(args: argparse.Namespace) -> RunSpec:
    if args.live:
        if not args.model_id:
            raise SystemExit("--live에는 --model-id가 필요합니다. 모델을 암묵적으로 정하지 않습니다.")
        if not os.environ.get("TASK_A_API_KEY"):
            raise SystemExit("TASK_A_API_KEY 환경변수가 없습니다. 키를 argv나 파일로 받지 않습니다.")
        if args.budget_usd is None:
            print("경고: --budget-usd 미설정. experiments/README.md는 금액 상한 기록을 요구합니다.",
                  file=sys.stderr)
    return RunSpec(
        run_id=args.run_id, arm=args.arm, policy=args.policy, out_path=args.out,
        condition=args.condition,
        model_id=args.model_id or "dry-run-scripted",
        code_commit=git_commit(), seed=args.seed, limit=args.limit, only=args.only,
        budget_usd=args.budget_usd, live=args.live, base_url=args.base_url,
        tokenizer=args.tokenizer, cache_path=args.cache, max_steps=args.max_steps,
        max_tool_calls=args.max_tool_calls, max_external_calls=args.max_external_calls)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec = build_spec(args)

    claims = load_claims(args.claims, spec)
    corpus = load_corpus(args.corpus)
    if not claims:
        raise SystemExit(f"주장이 없습니다: {args.claims}")

    mode = "LIVE" if spec.live else "DRY-RUN"
    print(f"[{mode}] run_id={spec.run_id} arm={spec.arm} policy={spec.policy} "
          f"condition={spec.condition} model={spec.model_id} seed={spec.seed}")
    print(f"주장 {len(claims)}건 · 코퍼스 문서 {len(corpus)}건 · "
          f"예산 상한 {spec.budget_usd if spec.budget_usd is not None else '미설정'} USD")
    if not spec.live:
        print("dry-run: 스크립트된 모형이 모든 주장에 보류로 답합니다. "
              "파이프라인 검증용이며 결과가 아닙니다.")

    outcome = execute(spec, claims, corpus)
    log = RunLog(spec.out_path)

    print(f"\n실행 {outcome.executed}건 · 건너뜀(이미 완료) {outcome.skipped}건")
    if outcome.stopped_reason:
        print(f"중단: {outcome.stopped_reason}")
    if outcome.pricing_note and not outcome.pricing_note["pricing_available"]:
        print(f"경고: {spec.model_id} 단가가 llm.PRICES에 없어 비용을 계산하지 못했습니다. "
              f"0 USD는 '무료'가 아니라 '미확인'입니다.")
    print(json.dumps(outcome.as_dict(log), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
