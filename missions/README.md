# 후속 미션(Mission) 및 장기 추적(Tracking) 결과물 폴더

이 폴더는 에이전트가 주장을 검증(`Supported` / `Refuted` / `Not Enough Evidence`)한 뒤, **검증 게이팅(Verification Gate)** 규칙에 따라 생성한 후속 결과물을 저장합니다.

## 구조

```text
missions/
├── events/       # Event & Change Manager 결과물 (검증·정정된 시각이 반영된 .ics 캘린더 파일)
├── artifacts/    # News-to-Artifact / Opportunity / Safe Trial 결과물 (검증 리포트 및 데이터 요약 .md)
└── tracking/     # Continuous Claim Tracking 레지스트리 (tracking_registry.jsonl)
```

## 검증 게이팅(Verification Gate) 원칙

1. **미확인·보류 정보 실행 차단 (`Garbage In, Action Out` 방지)**:
   - 판정이 `not_enough_evidence`이거나 `abstain=true`인 경우, `event_manager`나 `news_to_artifact` 같은 실행형 미션은 코드 레벨에서 거부되며 장기 추적(`continuous_tracking`) 또는 보류(`hold_abstain`)로만 기록할 수 있습니다.
2. **반박(`refuted`) 시 정정 사실(`correction`) 강제 적용**:
   - 기사의 날짜·시간대·수치가 틀린 경우(`refuted`), 원문의 잘못된 값이 아니라 검증을 통해 도출한 `correction` 값이 일정(`.ics`)과 아티팩트(`.md`)에 반영됩니다.
3. **불필요한 미션 생성 억제 (`no_op`)**:
   - 후속 행동이 필요 없는 단순 사실 확인 사례는 불필요한 파일을 생성하지 않고 `no_op`으로 기록합니다.
