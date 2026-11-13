---
name: factcheck-mission-agent
description: Evidence-grounded fact verification, distortion localization, and verification-gated mission/tracking execution under imperfect retrieved evidence. Use when verifying claims from articles/SNS posts, identifying exact distortion spans/types, and executing or gating follow-up missions.
---

# Fact-Check & Verification-Gated Mission Agent Skill

이 스킬은 **불완전·오염된 정보 환경에서 주장의 원출처를 역추적해 왜곡 지점과 원인을 정밀 교정하고, 검증 결과에 따라 후속 실무 행동(Mission 실행 / 장기 추적 등록 / 행동 보류)까지 자율 결정·수행**하도록 설계된 표준 에이전트 지침입니다.

## 1. 절대 보안 규칙 (정답 누출 금지)

- 에이전트는 어떤 경우에도 저장소 내의 `data/task_a/gold.jsonl`, `data/task_a/evidence.jsonl`, `docs/research/fact_checking/evaluation.md`를 직접 열람(`read_file`, `grep`, `cat` 등)해서는 안 됩니다.
- 모든 문제 조회, 근거 검색, 수치 계산, 후속 미션 실행, 최종 판정 제출은 반드시 제공된 **MCP 도구(`mcp_stdio.py`)** 또는 **전용 CLI(`scripts/agent_cli.py`)**를 통해서만 수행합니다.

## 2. 4단계 수행 프로토콜

### Step 1. 주장 분해 및 출처 독립성 기반 근거 탐색
1. `start_episode(claim_id)`(또는 `agent_cli.py start <CLAIM_ID>`)로 검증할 주장과 대상 기간(`target_period`), 근거 허용 시점(`evidence_cutoff`), 원문 발췌(`input_body`)를 확인합니다.
2. 주장을 **주체 · 관계 · 수치/조건 · 대상 시점**으로 분해합니다.
3. `search_evidence`와 `read_evidence`로 코퍼스를 탐색합니다.
   - **다수결 착시 주의**: 여러 한국어 기사가 동일한 수치·시각을 반복하더라도 같은 보도자료의 단순 전재(`provenance_group`)일 수 있습니다.
   - **한→영 교차 질의(Cross-lingual Query)**: 원출처가 해외 기업/기관/논문(Apple, OpenAI, NASA, Nobel, CERN, Mistral 등)인 경우, 한국어 질의로 1차 원문이 나오지 않으면 반드시 **영어 질의**로 재검색합니다.
4. C2 조건에서 코퍼스 근거가 누락(`missing`)·충돌(`conflict`)·오도(`misleading`) 상태라면 `search_web` 및 `fetch_url`로 독립된 1차 원출처를 확보합니다.

### Step 2. 결정론적 검산 및 왜곡 지점·원인 특정 (Distortion Localization)
1. **암산 금지**: 가격 차액(`diff`), 증감률(`pct_change`), 퍼센트포인트 차이(`percentage_point_gap`), 시간대 변환(`tz_convert`), 단위 변환(`scale_unit`), 곱셈/환산(`multiply`, `ratio`)은 반드시 `calculate_comparison` 도구를 호출해 검증합니다.
2. 주장이 반박(`refuted`)되거나 맥락 왜곡이 있을 때 다음 세 가지를 특정합니다:
   - `problematic_span`: 원문/주장에서 틀리거나 과장된 구체적 구절
   - `distortion_type`:
     - `timezone_or_date_error`: 시간대(PST↔KST 등) 미변환 또는 발표일·시행일·종료일 착오
     - `numeric_error`: 수치·비율·차액 계산 오류
     - `unit_or_scale_error`: 단위(`%` vs `%p`, `억` vs `만`, `billion` vs `million`, `GB` vs `B`) 혼동
     - `missing_condition_or_scope`: 적용 조건·지역·용량·대상 범위 누락
     - `overgeneralization`: 특정 조건/일부 실험 결과를 전체 성능이나 보편 사실로 과장
     - `forecast_as_fact`: 시장 전망·예측·계획 발표를 이미 확정·실현된 사실로 서술
     - `source_misattribution`: 개발 주체·발표 기관 오기
     - `unverified_claim`: 재현·검증 가능한 공식 자료가 없는 일방적 주장
     - `none`: 왜곡 없음 (`supported`)
   - `correction`: 원출처와 계산 결과로 입증된 정확한 정정 문장

### Step 3. 검증 게이팅 기반 후속 행동 결정 (Verification-Gated Mission Discovery)
검증 판정(`verdict`)과 정정 사실(`correction`)이 확보되면 `execute_mission` 도구로 후속 행동을 결정·실행합니다:

| 검증 결과 및 정보 성격 | 선택할 `mission_type` | 게이팅 규칙 및 실행 내용 |
| :--- | :--- | :--- |
| 출시일·사전예약·지원종료·행사 등 **구체적 일정**이 확인됨 | `event_manager` | `supported`면 원문 시각, `refuted`면 반드시 **정정된 KST 시각(`correction`)**으로 `.ics` 일정 파일 생성 (`Garbage In, Action Out` 방지) |
| 가격 비교·통계 수치·모델 제원 등 **구조화할 가치가 있는 검증 데이터** | `news_to_artifact` | 검증된 수치와 계산 근거를 정리한 비교 분석 리포트(`missions/artifacts/*.md`) 생성 |
| 무료 교육·행사·지원사업 등 **참가/활용 기회** | `opportunity_execution` | 신청 조건·제한 사항을 검증한 준비 아티팩트 생성 |
| 오픈소스·신규 AI 도구 등 **신뢰성/보안 점검 대상** | `app_safe_trial` | 주장된 성능/기능과 실제 공개 코드·문서의 정합성 점검 리포트 생성 |
| **미래 시점 전망**(예: 2026~2027년 예측) 또는 **근거 부족(`not_enough_evidence`)** | `continuous_tracking` | 실행형 미션을 **차단**하고, 향후 재검증 조건과 검색 질의를 `missions/tracking/tracking_registry.jsonl`에 등록 |
| 판정 보류(`abstain=true`) 상태 | `hold_abstain` | 어떠한 후속 미션도 실행하지 않고 보류 사유 기록 |
| 후속 실무 행동이 필요 없는 **단순 사실·역사·과학 상식 확인** | `no_op` | 불필요한 아티팩트를 생성하지 않음 |

### Step 4. 최종 검증 제출 (`finish_verification`)
- `finish_verification`을 호출하여 `verdict`, `abstain`, `cited_evidence_ids`, `justification`, `correction`, `stop_reason`, `distortion_type`, `problematic_span`, `mission_type`을 제출합니다.

## 3. 도구 호출 방법 (CLI 모드 예시)

MCP 서버가 연결되지 않은 터미널 환경에서는 `scripts/agent_cli.py`를 순서대로 호출합니다:

```bash
# 1. 에피소드 시작
uv run python scripts/agent_cli.py start FC002 --arm C1 --corpus data/task_a/corpus_c1.jsonl --out results/exp-001/c1.jsonl

# 2. 코퍼스 검색 (한국어 → 필요시 영어 교차 검색)
uv run python scripts/agent_cli.py search "Vision Pro 사전예약 2024년 1월 19일"
uv run python scripts/agent_cli.py search "Apple Vision Pro pre-order January 19 PST"

# 3. 근거 본문 확인
uv run python scripts/agent_cli.py read EV_FC002_1

# 4. 결정론적 계산기 호출
uv run python scripts/agent_cli.py calc tz_convert --time "2024-01-19 05:00" --from-tz PST --to-tz KST

# 5. 검증 게이팅 기반 후속 미션 실행
uv run python scripts/agent_cli.py mission event_manager \
  --verdict refuted \
  --title "Apple Vision Pro 미국 사전예약 개시 (KST 정정)" \
  --summary "기사 원문은 오전 5시(KST)로 오기했으나 Apple 공식 발표(05:00 PST) 기준 한국시간 22:00로 정정하여 일정 등록" \
  --cited EV_FC002_1 \
  --correction "2024-01-19 22:00 KST" \
  --distortion-type timezone_or_date_error \
  --event-start-kst "2024-01-19 22:00"

# 6. 최종 판정 제출
uv run python scripts/agent_cli.py finish \
  --verdict refuted \
  --cited EV_FC002_1 \
  --justification "Apple 공식 발표는 2024-01-19 05:00 PST이며, KST 변환 시 같은 날 22:00이다." \
  --correction "사전예약 시작은 2024-01-19 22:00 KST" \
  --distortion-type timezone_or_date_error \
  --problematic-span "오전 5시(한국시간)" \
  --mission-type event_manager
```
