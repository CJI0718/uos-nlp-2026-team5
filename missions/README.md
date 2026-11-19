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

미션은 별도 도구가 아니라 `finish_verification`의 `mission_type`으로 요청합니다.
서버는 그 제출의 **최종 판정**으로 아래 규칙을 확인한 뒤 실행합니다. 규칙에 걸리면 판정은 그대로 기록하고,
미션은 `mission_output.status`에 차단 사유와 함께 남깁니다.

1. **미확인·보류 정보 실행 차단**: 판정이 `not_enough_evidence`이거나 `abstain=true`이면 실행형 미션
   (`event_manager`, `news_to_artifact`, `opportunity_execution`, `app_safe_trial`)을 거부합니다.
   `continuous_tracking`이나 `hold_abstain`만 기록할 수 있습니다.
2. **읽은 근거만 인용**: 실행형 미션은 `cited_evidence_ids`가 하나 이상 있어야 하고, 모두 이번 에피소드에서
   `read_evidence` 또는 `fetch_url`로 본문을 연 문서여야 합니다. 그래서 C0에서는 실행형 미션을 쓸 수 없습니다.
3. **반박 시 정정 강제**: `refuted`이면 `correction`이 있어야 합니다. `event_manager`는 `event_start_kst`의
   `HH:MM`이 `correction`에 그대로 들어 있어야 합니다. 주장의 틀린 시각으로 일정이 만들어지는 것을 막습니다.
4. **불필요한 미션 억제**: 후속 행동이 필요 없는 사실 확인은 `no_op`으로 기록합니다.

### 출처 독립성 규칙 (`--gate provenance`)

같은 원문을 옮긴 기사 5개를 독립 근거 5개로 착각해 일정을 등록하는 실패를 막는 규칙입니다. 기본 게이트(`--gate verdict`)는
이 경우를 통과시킵니다(테스트 `test_default_verdict_gate_does_not_catch_reprints`). `--gate provenance`는 위 1~3에 하나를 더합니다.

5. **독립 근거 요구**: 실행형 미션의 인용 근거에 1차 출처(`source_type`이 `official`·`primary`)가 있거나,
   서로 다른 출처군이 2개 이상이어야 합니다. "○○ 보도에 따르면"처럼 다른 보도를 옮겼다고 밝힌 2차 문서는 출처군 수에 넣지 않습니다.

출처군은 두 방식으로 정합니다(`--provenance-mode`).
- `labeled`(기본): 코퍼스의 `provenance_group`을 쓰고, 표시가 없는 문서(웹에서 연 페이지 등)는 아래 자동 방식으로 묶습니다.
- `auto`: 표시를 무시하고, 이번 에피소드에서 읽은 문서끼리 본문 겹침으로 묶습니다
  ([src/task_a/provenance.py](../src/task_a/provenance.py), 글자 8-gram 포함률 0.4 이상이면 같은 출처군).

자동 방식의 한계:
- 말을 바꿔 다시 쓴 전재 기사는 다른 출처로 잡힙니다. 출처를 밝힌 경우만 2차 문서 규칙으로 걸러집니다.
- 같은 사이트의 메뉴·하단 문구가 겹치면 서로 다른 페이지가 같은 출처로 묶입니다. 게이트가 더 많이 막는 쪽의 오류입니다.
  지금은 페이지에서 본문만 뽑아 비교해서([src/task_a/article.py](../src/task_a/article.py)) 이 오류가 크게 줄었습니다.
  실제 코퍼스 50개 문서에서 0.4 이상 겹친 다른 문서 쌍이 16개에서 1개로 줄었고, 남은 1개는 두 저장소의 같은 MIT 라이선스 전문입니다.
- 웹 문서가 공식 자료인지는 판단하지 않습니다. 웹 근거만 있을 때는 서로 다른 출처군 2개가 있어야 실행됩니다.

채점기(`scripts/score_run.py`)는 `mission_safety`로 요청 수, 차단 수, 판정이 gold와 다른데도 실행된 실행형 미션의 비율을 보고합니다.

이전 버전에는 `execute_mission` 도구가 따로 있었습니다. 에이전트가 신고한 판정만 확인했기 때문에, `supported`로 일정을 만든 뒤
`not_enough_evidence`로 에피소드를 끝낼 수 있었습니다(2026-11-19 재현). 지금 구조는 이 우회를 막기 위한 것입니다.
