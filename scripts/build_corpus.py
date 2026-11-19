"""Fetch the original source pages into the agent-visible C1 corpus.

Reads the source URLs in data/task_a/evidence.jsonl (scorer-only; this script
is run by a person, never by the solving agent) and writes, under the
git-ignored data/raw/task_a/:

    corpus_c1.jsonl            what search_evidence / read_evidence serve
    corpus_c1.gold_map.jsonl   scorer-only map from document id to reference ids
    corpus_c1.report.json      per-URL outcome; failed pages are listed, not filled

This makes live HTTP requests to the source sites (no model calls). Article
text is copyrighted: keep the output local and do not commit it.

    uv run python scripts/build_corpus.py
    uv run python scripts/build_corpus.py --extra-urls distractors.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from task_a.corpus_build import build_corpus, http_fetch, summarize, write_outputs  # noqa: E402
from task_a.schema import read_jsonl  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--evidence", type=Path, default=ROOT / "data/task_a/evidence.jsonl")
    parser.add_argument("--claims", type=Path, default=ROOT / "data/task_a/claims.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "data/raw/task_a/corpus_c1.jsonl")
    parser.add_argument("--extra-urls", type=Path,
                        help="방해 문서 URL 목록 (한 줄에 하나, #은 주석). 어느 주장과도 연결되지 않는다")
    parser.add_argument("--delay", type=float, default=1.0, help="요청 사이 대기(초)")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)

    out = args.out.resolve()
    if ROOT in out.parents and (ROOT / "data/raw") not in out.parents:
        raise SystemExit(f"원문이 들어가므로 Git 제외 위치(data/raw/) 아래에 써야 합니다: {out}")

    claims = read_jsonl(args.claims)
    extra = args.extra_urls.read_text(encoding="utf-8").splitlines() if args.extra_urls else ()
    result = build_corpus(read_jsonl(args.evidence), claims,
                          partial(http_fetch, timeout=args.timeout),
                          extra_urls=extra, delay=args.delay)
    summary = summarize(result, claims)
    paths = write_outputs(result, summary, out)
    print(json.dumps({"summary": summary, "files": paths}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
