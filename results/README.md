# 결과 요약

| 실험 | 날짜 | 내용 |
| :--- | :--- | :--- |
| [exp-001-compare](exp-001-compare/summary.md) | 2026-11-19 | 도구 없음 vs 그냥 Claude Code(웹) vs 하네스(C1), Opus·Sonnet·Haiku, 주장 20건, 180세션 |
| [exp-002-action-safety](exp-002-action-safety/summary.md) | 2026-11-19~20 | NP01/Pilot 4 재구성: 합성 6건 × 조건 5개(Skill·출처 정보·서버 게이트) × 모델 3개, 90세션 |
| [exp-003-real-web](exp-003-real-web/summary.md) | 2026-11-20 | 같은 설계를 실제 웹 사례 7건으로: 조건 3개(base, Skill, Skill+게이트) × Haiku·Sonnet, 42세션 |

실험 ID별로 공개 가능한 metrics.json 또는 summary.md 등을 기록합니다.
전체 사례 수·성공·실패·미실행 분모, 지표, 비용·token·시간, 오류 유형, 한계와 개선 제안을 남깁니다.
같은 결과를 다른 조건의 결과인 것처럼 덮어쓰지 않습니다. 실패한 시도도 집계합니다.
민감정보 제거를 검토하지 않은 원본 로그·trajectory는 올리지 않습니다.
