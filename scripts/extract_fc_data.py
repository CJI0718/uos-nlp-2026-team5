"""Extract the 50 annotated cases from evaluation.md into data/task_a/.

Reads docs/research/fact_checking/evaluation.md (never writes to it) and emits
three JSONL files. Gold stays out of claims.jsonl.

    uv run python scripts/extract_fc_data.py
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.dataset import extract  # noqa: E402
from task_a.schema import write_jsonl  # noqa: E402

SOURCE = ROOT / "docs/research/fact_checking/evaluation.md"
OUT_DIR = ROOT / "data/task_a"


def main() -> int:
    parsed = extract(SOURCE.read_text(encoding="utf-8"))

    counts = {
        "claims": write_jsonl(OUT_DIR / "claims.jsonl", parsed["claims"]),
        "gold": write_jsonl(OUT_DIR / "gold.jsonl", parsed["gold"]),
        "evidence": write_jsonl(OUT_DIR / "evidence.jsonl", parsed["evidence"]),
    }

    labels = Counter(g["label_text"] for g in parsed["gold"])
    kinds = Counter(c["source_type"] for c in parsed["claims"])
    missing_text = [c["claim_id"] for c in parsed["claims"] if not c["text"]]
    missing_body = [c["claim_id"] for c in parsed["claims"] if not c["input_body"]]
    no_evidence = [g["claim_id"] for g in parsed["gold"] if not g["sufficient_evidence_ids"]]

    print(f"claims   {counts['claims']}")
    print(f"gold     {counts['gold']}")
    print(f"evidence {counts['evidence']}")
    print(f"\n참조 판정: {dict(labels)}")
    print(f"자료 유형: {dict(kinds)}")
    if missing_text:
        print(f"\n경고: 선정 주장 비어 있음 {missing_text}")
    if missing_body:
        print(f"경고: 입력 본문 없음 {missing_body}")
    if no_evidence:
        print(f"참고: 참조 근거 없음 {no_evidence}")
    return 1 if missing_text else 0


if __name__ == "__main__":
    raise SystemExit(main())
