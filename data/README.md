# 평가 데이터

최종 태스크가 정해진 뒤 직접 작성할 평가 사례를 관리합니다.

## task_a/ — Task A 평가 사례 50개

`docs/research/fact_checking/evaluation.md` §9.8에서 `scripts/extract_fc_data.py`로 추출합니다.
원본 Markdown이 기준이며 스크립트는 원본을 읽기만 하고 수정하지 않습니다.

```bash
uv run python scripts/extract_fc_data.py
```

| 파일 | 받는 사람 | 내용 |
| --- | --- | --- |
| `task_a/claims.jsonl` | **해결 에이전트** | 주장 50개, 시점, 출처, 입력 본문 |
| `task_a/gold.jsonl` | **채점기 전용** | 참조 판정·이유·평가 포인트·주장 위치 |
| `task_a/evidence.jsonl` | **채점기 전용** | 참조 근거 64건과 확인 상태 |

구성(§9.2.2·§9.2.1과 일치): 지지 37·반박 11·근거 부족 1·판정 보류 1, 한국어 기사 29·영어 기사 8·Threads 9·X 4.
분할 그룹은 47개이며 `family_id`로 관리합니다(FC032·FC034, FC015·FC019·FC020).

`주장 위치`는 gold에만 있습니다. FC044의 값은 "기사 제목의 10월 24일; 본문의 10월 14일과 비교"로
그 자체가 정답을 밝히기 때문입니다. 에이전트 입력 필드 집합은 테스트로 고정했습니다.

**아직 없는 것:** 기사 37건의 원문 본문(21건은 발췌도 없음). URL만 있고 본문 수집은 별도 단계이며,
수집한 원문은 저작권 때문에 `data/raw/`(Git 제외)에 두고 manifest만 커밋합니다.
참조 판정은 독립 검수 전 초안이고 FC038은 판정 보류 상태입니다.

## 사례 작성 원칙

사례별 권장 필드:
- case_id, category, user_request
- initial_state / available_evidence
- gold_answer_or_state / required_constraints
- evaluation_rule / tolerance
- source / authoring_note / review_status

정답은 평가기에만 제공하고 해결 Agent의 입력에서 제외합니다.
개발용 사례와 고정 평가본을 구분합니다. 같은 기본 사례에서 만든 변형을 독립 사례로 중복 계산하지 않습니다.
공개 전 개인정보·저작권·공유 권한을 확인합니다. 원본 대용량 자료는 raw/ 등에 두고 Git에 올리지 않습니다.
