# 결과 요약

| 실험 | 날짜 | 내용 |
| :--- | :--- | :--- |
| [exp-001-compare](exp-001-compare/summary.md) | 2026-11-19 | 도구 없음 vs 그냥 Claude Code(웹) vs 하네스(C1), Opus·Sonnet·Haiku, 주장 20건, 180세션 |
| [exp-002-action-safety](exp-002-action-safety/summary.md) | 2026-11-19~20 | NP01/Pilot 4 재구성: 합성 6건 × 조건 5개(Skill·출처 정보·서버 게이트) × 모델 3개, 90세션 |
| [exp-003-real-web](exp-003-real-web/summary.md) | 2026-11-20 | 같은 설계를 실제 웹 사례 7건으로: 조건 3개(base, Skill, Skill+게이트) × Haiku·Sonnet, 42세션 |
| [exp-004-real-web-fixed](exp-004-real-web-fixed/summary.md) | 2026-11-20~21 | exp-003의 하네스 문제 3개를 고친 뒤 다시 실행, Skill+기본 검증 게이트 조건 추가: 조건 4개 × Haiku·Sonnet, 56세션 |
| [exp-005-pilot](exp-005-pilot/summary.md) | 2026-11-25 | 개정 평가데이터·새 실행기 시험: 3건 × C0/C1/C2, DeepSeek V4.1 Flash, 9세션 |
| [exp-005-baseline](exp-005-baseline/summary.md) | 2026-11-25 | 기말 baseline: 평가데이터 50건 × C0/C1/C2, DeepSeek V4.1 Flash(Mistral API), 150세션 |
| [exp-006-improved](exp-006-improved/summary.md) | 2026-11-25 | 오류 분석에서 나온 Action Item 3개(예측 주장 규칙, 본문 추출, 조건별 도구) 적용 후 재실행, 150세션 |
| [exp-006-repeat](exp-006-repeat/summary.md) | 2026-11-25 | 개선 대상 8건 × C1/C2 반복 확인, 16세션 |
| [exp-007-claude-haiku](exp-007-claude-haiku/summary.md) | 2026-11-26 | 개선 후 하네스를 Claude Haiku 5.5로: 50건 × C0/C1/C2, 150세션 |
| [exp-007-claude-sonnet](exp-007-claude-sonnet/summary.md) | 2026-11-26 | 같은 설계를 Claude Sonnet 5.5로: 148세션(C2 2건은 비용 상한으로 미실행) |
| [exp-008-webonly](exp-008-webonly/summary.md) | 2026-11-26 | 코퍼스 없이 웹 검색만(C2W): 50건, DeepSeek V4.1 Flash, 외부 호출 한도 8 |
| [exp-009-plainweb](exp-009-plainweb/summary.md) | 2026-11-26 | 같은 모델·웹에서 하네스를 뺀 기본 웹 에이전트(C2P): 50건 |
| [exp-010-webonly-noself](exp-010-webonly-noself/summary.md) | 2026-11-26 | C2W + 주장이 나온 글 인용 금지, 외부 호출 한도 8: 50건 |
| [exp-011-webonly-noself-b25](exp-011-webonly-noself-b25/summary.md) | 2026-11-26 | 같은 조건, 외부 호출 한도 25: 50건(FC025는 Tavily 432로 재실행) |
| [exp-012-harness-v3](exp-012-harness-v3/summary.md) | 2026-11-26 | exp-011 조건 + 하네스 v3(인용문 대조, find_in_page, 재사용): 50건(FC026은 HTTP 502로 재실행) |
| [exp-013-plainweb-b25](exp-013-plainweb-b25/summary.md) | 2026-11-26 | 하네스 없는 웹 에이전트(C2P), 외부 호출 한도 25: exp-012와 예산을 맞춘 비교, 50건 |

exp-005~006의 분석과 해석은 [docs/research/fact_checking/final-20261125/](../docs/research/fact_checking/final-20261125/README.md)에 있습니다.

실험 ID별로 공개 가능한 metrics.json 또는 summary.md 등을 기록합니다.
전체 사례 수·성공·실패·미실행 분모, 지표, 비용·token·시간, 오류 유형, 한계와 개선 제안을 남깁니다.
같은 결과를 다른 조건의 결과인 것처럼 덮어쓰지 않습니다. 실패한 시도도 집계합니다.
민감정보 제거를 검토하지 않은 원본 로그·trajectory는 올리지 않습니다.
