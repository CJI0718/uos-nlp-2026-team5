"""Score a run log against gold. This is the only command that reads gold.

    uv run python scripts/score_run.py \
        --gold data/task_a/gold.jsonl \
        --run results/exp-001/c1-react.jsonl

    # with a second arm, recovery and harm become available
    uv run python scripts/score_run.py --gold data/task_a/gold.jsonl \
        --run results/exp-001/c1-react.jsonl \
        --c2 results/exp-001/c2-react.jsonl

    # with rubric grades, GSR / exposure / adoption become available
    uv run python scripts/score_run.py --gold data/task_a/gold.jsonl \
        --run results/exp-001/c1-react.jsonl --grades data/task_a/grades.jsonl

Metrics that need E and T grades are reported as unavailable when no grade file
is supplied. They are not defaulted to zero, because a GSR of zero from missing
grades looks identical to a GSR of zero from a failing system.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.schema import read_jsonl  # noqa: E402
from task_a.score_run import load_gold, load_grades, score_run, score_transition  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold", type=Path, default=ROOT / "data/task_a/gold.jsonl")
    parser.add_argument("--run", type=Path, required=True, help="C1(또는 단일 arm) 실행 로그")
    parser.add_argument("--c2", type=Path, default=None, help="C2 로그. 주면 회복·손상을 계산한다")
    parser.add_argument("--grades", type=Path, default=None, help="E·T rubric 등급 JSONL")
    parser.add_argument("--basis", choices=["v", "grounded"], default="v",
                        help="회복·손상을 판정 기준(v) 또는 근거 동반 성공 기준으로")
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    gold = load_gold(args.gold)
    grades = load_grades(args.grades)
    rows = read_jsonl(args.run)

    summary = {"run": str(args.run), "episodes": len(rows),
               "gold_cases": len(gold),
               "unreviewed_gold": sum(1 for label in gold.values() if label is None),
               "c1": score_run(rows, gold, grades)}

    if args.c2 is not None:
        c2_rows = read_jsonl(args.c2)
        summary["c2"] = score_run(c2_rows, gold, grades)
        summary["c2_run"] = str(args.c2)
        summary["transition"] = score_transition(rows, c2_rows, gold, grades, on=args.basis)

    if not grades:
        summary["warning"] = (
            "E·T 등급 파일이 없습니다. GSR·노출률·채택률은 계산 불가로 표시되며 0이 아닙니다. "
            "Accuracy·Macro-F1·회복·손상·비용은 로그만으로 계산됩니다.")

    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"기록: {args.out}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
