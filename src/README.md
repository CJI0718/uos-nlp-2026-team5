# 실행 코드

Task A(불완전한 근거 아래서의 팩트체크) 에이전트 구현입니다.

```
task_a/
  schema.py     Claim / Gold / EvidenceUnit / ToolEvent / AgentResult / EpisodeState
  dataset.py    evaluation.md §9.8 파서 (원본은 읽기만 함)
  retrieve.py   BM25 + Kiwi/bigram 토크나이저, CorpusBackend
  tools.py      도구 5개 + whitelisted 계산기 + fetch URL 차단
  loop.py       ReAct 루프 — 다음 도구와 종료 시점을 정책이 정함
  policies.py   react / fixed_workflow / closed_book
  llm.py        OpenAI 호환 클라이언트 (자동 재시도 0회)
  toollog.py    append-only 실행 로그, 외부 응답 캐시, 비용 집계
  runner.py     에피소드 실행 — gold를 열 수 없음
  score_run.py  채점 — gold를 여는 유일한 모듈
  mock.py       오프라인 코퍼스 백엔드와 스크립트 LLM
```

## 실행

```bash
uv sync --python 3.12
uv run pytest -q                        # 184개 테스트
uv run python scripts/demo_fc002.py     # FC002·FC004·FC041 오프라인 데모
uv run python scripts/extract_fc_data.py # evaluation.md → data/task_a/*.jsonl
uv run python scripts/run_eval.py --arm C1 --policy react --limit 5 --out /tmp/c1.jsonl
uv run python scripts/score_run.py --run /tmp/c1.jsonl
```

실행 방법은 [experiments/README.md](../experiments/README.md)를 봅니다.

## 현재 상태

구현됐고 테스트로 고정된 것: 루프, 도구, 계산기, BM25 검색, 세 정책, 캐시·로그·예산,
채점 산식, dry-run 실행과 재개.

**아직 없는 것:** 기사 원문 수집(코퍼스 파일), 근거 조건 4변형, 실 LLM 연결, E·T rubric 등급.
모델·provider·예산은 미정이며 **실모델 실험은 수행하지 않았습니다.**

## 설계 제약

- **에이전트는 파일 시스템 도구를 갖지 않습니다.** `evaluation.md`에 gold 50개가 들어 있으므로
  파일 접근은 정답 누출입니다. 도구 목록이 그 경계이며 테스트로 고정했습니다.
- **실행기와 채점기는 분리된 명령입니다.** `runner.py`는 gold 파일을 열지 않으며,
  테스트가 로더를 감시해 이를 확인합니다.
- 도구 실행 상태(`ok/empty/invalid_input/source_unavailable/...`)와 사실 판정을 분리합니다.
  `empty`는 결과 없음이지 주장이 거짓이라는 뜻이 아닙니다.
- 자동 재시도·자동 모델 변경이 없습니다. 실패는 한 번 기록되고 넘어갑니다.
- 계산은 whitelisted 연산만 가능합니다. 임의 수식 평가(`eval`)를 쓰지 않습니다.
- `llm.PRICES`는 비어 있습니다. 단가를 지어넣지 않으며, 미견적 모델의 비용은 0이 아니라
  미확인으로 보고됩니다.
