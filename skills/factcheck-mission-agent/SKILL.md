---
name: factcheck-mission-agent
description: Evidence-grounded fact verification, distortion localization, and verification-gated mission/tracking execution under imperfect retrieved evidence. Use when verifying claims from articles/SNS posts, identifying exact distortion spans/types, and executing or gating follow-up missions.
---

# Fact-Check & Verification-Gated Mission Agent Skill

이 스킬은 주장 하나를 근거로 검증하고, 틀렸다면 왜곡 지점과 유형을 특정한 뒤, 검증 결과가 허용할 때만 후속 행동(일정·아티팩트 생성, 장기 추적 등록, 보류)을 실행하도록 하는 지침입니다.

## 1. 도구 사용 규칙

- 문제 조회, 근거 검색·열람, 계산, 최종 제출은 제공된 MCP 도구(`factcheck-mission` 서버)로만 합니다.
- 근거로 인용할 수 있는 것은 이번 에피소드에서 `read_evidence`(코퍼스) 또는 `fetch_url`(C2 웹)로 **본문을 직접 읽은** 문서뿐입니다. 검색 결과 스니펫만 본 문서는 인용하지 않습니다.
- 도구 호출 예산은 `start_episode` 응답의 `budget`에 있습니다. 예산을 다 쓰면 확보한 근거로 `finish_verification`을 호출합니다.

## 2. 4단계 수행 프로토콜

### Step 1. 주장 분해와 출처 독립성 기반 근거 탐색
1. `start_episode(claim_id)`로 주장, 대상 기간(`target_period`), 근거 허용 시점(`evidence_cutoff`), 원문 발췌(`input_body`)를 확인합니다.
2. 주장을 **주체 · 관계 · 수치/조건 · 대상 시점**으로 분해합니다.
3. `search_evidence`로 코퍼스를 찾고, 판단에 쓸 문서는 `read_evidence`로 본문을 읽습니다.
   - **긴 문서는 끝까지 확인**: 한 번에 4,000자까지만 보입니다. 응답 끝에 `(전체 N자 중 …자. 이어 읽기: …offset=…)`가 있고 찾는 내용이 아직 없으면, 그 `offset`으로 이어 읽거나 `section`에 찾는 문구를 넣습니다. 앞부분에 없다고 "근거 부족"으로 판단하지 않습니다.
   - **다수결 착시 주의**: 여러 문서가 같은 수치·시각을 반복해도 같은 보도자료의 전재일 수 있습니다. 검색 결과의 `출처군`이 같으면 독립 출처로 세지 않습니다.
   - **교차 언어 질의**: 원출처가 해외 기업·기관·논문이면, 한국어 질의로 1차 원문이 나오지 않을 때 영어 질의로 다시 검색합니다.
   - `evidence_cutoff` 이후에 발행된 문서는 근거로 쓰지 않습니다.
4. C2 조건에서 코퍼스 근거가 없거나, 서로 충돌하거나, 1차 출처가 아니라면 `search_web`과 `fetch_url`로 독립된 1차 출처를 확보합니다.
   - `fetch_url`로 연 페이지는 `read_evidence(evidence_id=URL, offset=…)`로 이어 읽습니다. 다시 `fetch_url`을 부르면 외부 호출 예산만 씁니다.

### Step 2. 결정론적 검산과 왜곡 지점·원인 특정
1. **암산 금지**: 차액(`diff`), 증감률(`pct_change`), 퍼센트포인트 차이(`percentage_point_gap`), 시간대 변환(`tz_convert`), 단위 변환(`scale_unit`), 곱셈·비율(`multiply`, `ratio`)은 `calculate_comparison`으로 계산합니다.
2. 주장이 반박(`refuted`)되거나 맥락 왜곡이 있으면 다음 세 가지를 특정합니다.
   - `problematic_span`: 주장 또는 입력 글에서 틀리거나 과장된 구체적 구절
   - `distortion_type`:
     - `timezone_or_date_error`: 시간대 미변환, 발표일·시행일·종료일 착오
     - `numeric_error`: 수치·비율·차액 계산 오류
     - `unit_or_scale_error`: `%`와 `%p`, `억`과 `만`, `billion`과 `million` 같은 단위·자릿수 혼동
     - `missing_condition_or_scope`: 적용 조건·지역·용량·대상 범위 누락
     - `overgeneralization`: 일부 조건·실험 결과를 전체 성능이나 보편 사실로 과장
     - `forecast_as_fact`: 전망·예측·계획을 확정된 사실로 서술
     - `source_misattribution`: 개발 주체·발표 기관 오기
     - `unverified_claim`: 재현·검증 가능한 공식 자료가 없는 일방적 주장
     - `none`: 왜곡 없음 (`supported`)
   - `correction`: 원출처와 계산 결과로 입증한 정정 문장. 시각을 정정할 때는 `22:00`처럼 `HH:MM` 형식을 포함합니다.

### Step 3. 후속 행동 선택 (검증 게이팅)
후속 행동은 별도 도구가 아니라 `finish_verification`의 `mission_type`으로 요청합니다. 서버는 **제출한 최종 판정**으로 게이트를 적용한 뒤 실행하고, 차단되면 사유를 기록합니다.

| 검증 결과와 정보 성격 | `mission_type` | 게이트 규칙과 실행 내용 |
| :--- | :--- | :--- |
| 출시·예약·종료·행사 등 **구체적 일정**이 확인됨 | `event_manager` | `event_start_kst`로 `.ics` 생성. `refuted`면 `correction`에 같은 `HH:MM`이 있어야 함 |
| 가격·통계·제원 등 **구조화할 가치가 있는 검증 데이터** | `news_to_artifact` | 검증된 수치와 계산 근거를 정리한 `.md` 생성 |
| 교육·행사·지원사업 등 **참가·활용 기회** | `opportunity_execution` | 신청 조건·제한을 검증한 준비 문서 생성 |
| 공개 소프트웨어·신규 도구 등 **신뢰성 점검 대상** | `app_safe_trial` | 주장된 기능과 공개 코드·문서의 정합성 점검 문서 생성 |
| **미래 시점 전망**, 또는 `not_enough_evidence` | `continuous_tracking` | 실행형 미션 없이 재검증 조건(`tracking_condition`)과 질의(`tracking_queries`)를 등록 |
| 판정 보류(`abstain=true`) | `hold_abstain` | 아무것도 실행하지 않고 보류 사유만 기록 |
| 후속 행동이 필요 없는 단순 사실 확인 | `no_op` | 결과물 없음 |

실행형 미션(`event_manager`, `news_to_artifact`, `opportunity_execution`, `app_safe_trial`)의 공통 조건:
- `not_enough_evidence`나 `abstain=true`이면 차단됩니다.
- `cited_evidence_ids`가 하나 이상 있어야 하고, 모두 이번 에피소드에서 읽은 문서여야 합니다.
- `refuted`이면 `correction`이 있어야 합니다.

### Step 4. 최종 제출 (`finish_verification`)
`verdict`, `abstain`, `cited_evidence_ids`, `justification`, `stop_reason`을 반드시 제출합니다. 해당하면 `correction`, `distortion_type`, `problematic_span`, `mission_type`, `mission_title`, `mission_summary`, `event_start_kst`, `tracking_condition`, `tracking_queries`를 함께 제출합니다. `finish_verification`은 에피소드마다 한 번만 호출합니다.

## 3. 예시 (가상 사례, 평가 데이터와 무관)

주장: "Acme Orbit 공개 행사는 2025년 3월 5일 한국시간 오전 2시에 열린다."

1. `start_episode` → `search_evidence("Acme Orbit keynote time")` → `read_evidence("DOC_acme_keynote")`. 본문에는 "March 4, 2025 at 10:00 a.m. PST"라고 적혀 있습니다.
2. `calculate_comparison(op="tz_convert", time="2025-03-04 10:00", from_tz="PST", to_tz="KST")` → `2025-03-05 03:00 KST`.
3. `finish_verification`:

```json
{
  "verdict": "refuted",
  "abstain": false,
  "cited_evidence_ids": ["DOC_acme_keynote"],
  "justification": "공식 발표는 10:00 PST이고, KST로는 다음 날 03:00이다.",
  "correction": "공개 행사는 2025-03-05 03:00 KST에 열린다.",
  "stop_reason": "evidence_sufficient",
  "distortion_type": "timezone_or_date_error",
  "problematic_span": "한국시간 오전 2시",
  "mission_type": "event_manager",
  "mission_title": "Acme Orbit 공개 행사 (KST 정정)",
  "event_start_kst": "2025-03-05 03:00"
}
```
