# 실행 코드

Task A(불완전한 근거 아래서의 팩트체크) 에이전트 구현입니다.

```
task_a/
  schema.py   Claim / Gold / EvidenceUnit / ToolEvent / AgentResult
  tools.py    도구 5개 + whitelisted 계산기 + fetch URL 차단
  loop.py     ReAct 루프 — 다음 도구와 종료 시점을 모델이 선택
  mock.py     오프라인 코퍼스 백엔드와 스크립트 LLM (API 호출 0)
```

## 실행

```bash
uv sync --python 3.12
uv run pytest -q                      # 46개 테스트
uv run python scripts/demo_fc002.py   # FC002·FC004·FC041 오프라인 데모
```

데모와 테스트는 모의 도구·스크립트 LLM으로 돌므로 비용이 들지 않습니다.
실제 모델 호출은 예산 합의와 실행 승인이 있어야 하며, 자동 재시도와 자동 모델 변경은 하지 않습니다.

## 설계 제약

- **에이전트는 파일 시스템 도구를 갖지 않습니다.** `evaluation.md`에 gold 50개가 들어 있으므로
  파일 접근은 정답 누출입니다. 도구 목록이 그 경계이며 테스트로 고정했습니다.
- 도구 실행 상태(`ok/empty/invalid_input/source_unavailable/...`)와 사실 판정을 분리합니다.
  `empty`는 결과 없음이지 주장이 거짓이라는 뜻이 아닙니다.
- gold는 scorer만 읽고 에이전트 입력·도구 응답에 들어가지 않습니다.

아직 없는 것: 고정 코퍼스 수집, BM25 인덱스, 실 LLM 클라이언트, scorer, 4개 근거 조건 변형.
