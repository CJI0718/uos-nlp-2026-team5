# 팩트체크 Agent 평가 설계안

2026-10-23 · **아직 팀이 확정하거나 실행하지 않은 제안**. [구상](README.md) · [문헌](literature.md)

## 1. 먼저 분리해야 할 두 평가

**핵심 검증 평가:** 사람이 정규화한 주장 하나를 주고 근거·판정을 받는다. Agent의 retrieval/도구 정책을 주로 평가한다.

**기사 end-to-end 평가:** 기사에서 어떤 주장을 뽑았는지부터 평가한다. 중요 주장 누락률·검증가능성 분류·중복 추출 등을 따로 측정한다. 이 단계의 실패를 근거 검색 성능과 혼동하지 않는다. 한국어 검증가능성/중요성 탐지는 이미 별도 연구 과제다. [FC30](literature.md#fc30), [FC33](literature.md#fc33)

## 2. 50개의 단위와 구성

50은 **독립적인 기본 주장/episode 수**의 계획안이지, 같은 주장을 모델별·표현별로 반복한 실행 수가 아니다. 실제 과목 지침의 데이터 작성 요건은 최종 대조가 필요하다.

### 선택안 A — 직접 작성·검수한 3-class 주장 50개

| 주된 어려움 | 지지 | 반박 | 근거 부족 | 합계 |
| --- | ---: | ---: | ---: | ---: |
| 직접 문장·단일 근거 | 4 | 4 | 2 | 10 |
| 복수 근거·복합 조건 | 4 | 4 | 2 | 10 |
| 게시일·대상 시점·버전 | 4 | 4 | 2 | 10 |
| 수치·단위·분모·비교 기간 | 4 | 4 | 2 | 10 |
| 범위·예외·자료 불일치 검토 | 4 | 4 | 2 | 10 |
| 합계 | 20 | 20 | 10 | 50 |

주된 어려움은 분할용이고 부차적 태그는 중복 가능하다. 자료 충돌을 자동으로 근거 부족으로 지정하지 않는다. 해결 가능한 충돌이면 지지/반박 근거를 작성하고, 해결 불가능한 충돌을 별도 label로 다루고 싶으면 4-class 설계로 변경한다.

### 선택안 B — 공개 benchmark subset 50개

AVeriTeC 원래 4-class를 유지하거나, 공개된 다른 benchmark의 원래 label·split을 유지한다. 추출 규칙·ID·seed·label별 개수·제외 사유·라이선스를 기록한다. native 4-class의 Conflicting Evidence/Cherry-picking을 설명 없이 NEI로 합치지 않는다. 표본을 만들기 전에는 실제 50개를 확보한 것으로 보고하지 않는다. [FC03](literature.md#fc03)

직접 작성과 공개 subset은 같은 평가라고 부르지 않는다. 한국어로 번역하면 숫자·시점·고유명사·label 보존을 사람이 검수하고, 원문과 번역 쌍을 서로 다른 독립 사례처럼 세지 않는다.

### 데이터 누출과 사람 검수

- 개발용 소수 사례는 평가 50개와 분리한다. 표현을 바꾼 같은 사건·숫자 변형·기사 묶음은 같은 split에 둔다.
- 가능하면 두 팀원이 독립 판정한 후 불일치를 조정한다. 조정 전 일치율과 불일치 이유를 남긴다.
- 평가 전에 gold와 채점 규칙을 고정한다. 실행 결과를 보고 정답을 바꾸면 수정 이유·버전과 모든 조건의 재채점 여부를 남긴다.
- gold label·정답 설명·정답 QA·gold 증거 목록은 Agent input에 넣지 않는다. 공정하게 공유한 검색 store 안에 근거 문서가 존재하는 것과 정답을 직접 제공하는 것은 다르다.
- benchmark의 기존 fact-check 기사/평가 해설/label 페이지 검색은 독립 검증 track에서 배제한다. 이미 검증된 답을 찾는 기능은 별도의 ‘기존 판정 검색’ track으로 보고한다.
- 인간 annotator가 알고 있는 다른 출처까지 모델이 반드시 동일 URL로 찾을 필요는 없다. 대체 증거도 충분하면 같은 기준으로 검수한다.

## 3. 시점과 ‘근거 부족’의 의미

각 사례에 `claim_date`(주장이 나온 시각), `target_period`(주장이 말하는 기간), `evidence_cutoff`(허용 정보 공개 시점), `retrieved_at`(가져온 시각), 자료의 `published_at`·`updated_at`을 구분한다.

‘당시 알 수 있었던 정보로 검증’과 ‘오늘 자료로 과거 사건 검증’은 다른 모드다. 전자는 cutoff 이후 정보를 사용하면 누출이고, 후자는 뒤늦게 공개된 정보를 사용할 수 있지만 그 모드 자체를 명시해야 한다. API의 오늘 수정된 과거 통계는 당시 vintage와 다를 수 있다. 접근 시각만 기록한다고 과거 정보 누출이 해결되지는 않는다. [FC03](literature.md#fc03), [FC24](literature.md#fc24), [FC26](literature.md#fc26)

고정 store의 근거 부족은 **해당 corpus·cutoff에서 충분한 지지/반박 근거가 없음**으로 정의한다. open web에서는 무한한 부재를 증명할 수 없으므로 허용한 출처·검색 규칙·시점 아래 사람 검수한 부족 판정으로 한정하고 불확실 사례를 기록한다.

모델이 검색에 실패했다고 정답이 NEI가 되는 것은 아니다. **gold의 근거 부족**, **모델의 보류 행동**, **실행 실패**를 따로 저장한다.

## 4. 최소 비교 조건

| 조건 | 입력·환경 | 목적 |
| --- | --- | --- |
| B0. 검색 없는 LLM | 같은 주장·모델, 외부 도구 없음 | 모델 기억의 진단용. Agent 정책 우월성의 주 baseline은 아님 |
| B1. 강한 고정 workflow | 같은 도구/store와 최대 예산. 정규화·질의·검색·계산·판정의 고정 절차 | 같은 자원에서 적응적 판단이 필요한가 |
| B2. 적응형 Agent | B1과 같은 모델·도구·자료, 관찰에 따라 다음 행동과 종료 선택 | 정책 효과 |

항상 B0~B2 전부 실행할 필요는 없다. 최소 주 비교는 B1/B2이며, 확정 후에만 실행한다. B1을 일부러 단일 허술한 질의로 만들지 않는다. 논문 Fathom·HerO 2를 강한 pipeline 설계 참고로 쓴다. [FC21](literature.md#fc21), [FC22](literature.md#fc22)

고정해야 할 것: 모델 ID/version, sampling·출력 한도, tool schema, 검색 store, 도구 결과 길이, 접근 가능한 정보, 최대 검색/LLM/token 예산, scorer, timeout. Agent의 선택 설명은 비용에 포함한다. 동일한 최대 예산뿐 아니라 **실제 사용한 비용**도 보고한다.

retriever를 비교하려면 먼저 정책·생성 모델을 고정한다. 정책을 비교하려면 retriever를 고정한다. 모든 요인을 동시에 바꾸는 큰 factorial 실험은 첫 단계에서 피한다.

## 5. Metric 정의

| 축 | 제안 metric | 주의 |
| --- | --- | --- |
| 판정 | Accuracy, Macro-F1, label별 precision/recall | 혼합 label·실행 실패 처리 규칙 공개 |
| 근거 회수 | 고정 store의 gold evidence Recall@k, 필요 시 nDCG@k | 열린 웹의 동일 사실은 다른 URL로도 입증 가능 |
| 근거 동반 성공 | `GSR = sum(correct_label AND sufficient_evidence AND correct_time_scope) / N_attempted` | 팀 정의 metric. 공식 FEVER/AVeriTeC score와 이름을 구분 |
| 인용 | 판정을 실제로 뒷받침하는 인용 비율, 검증이 필요한 출력 주장 중 근거 있는 비율 | 단순 링크 유무가 아님; 사람이 blind 검수 가능 |
| 숫자·시간 | 값·단위·기간·분모 정합성, 잘못된 계산/구버전 인용률 | 수치 tolerance를 평가 전에 정함 |
| 보류 | 결정률(지원/반박 출력 비율), 결정한 사례의 오류율, 보류 precision/recall | NEI label과 보류 행동을 동일시하지 않음 |
| 비용 | LLM/search/API 횟수, 입출력 토큰, wall time, 성공 1건당 비용 | index·cache·judge 구축비 별도 병기 |
| 실행 안정성 | timeout·429·파싱 오류·무한 반복·한도 초과율 | fact label이 아니라 execution status |

실행 실패를 통계에서 조용히 제거하지 않는다. 주 결과는 전체 시도 대비 grounded success와 failure rate를 보고하고, label Macro-F1은 응답 완료 subset의 coverage와 함께 보고하거나 사전에 정한 실패 패널티 scorer를 병기한다. 둘을 섞어 유리한 분모를 선택하지 않는다.

50개에서 정확도 한 건은 2%p다. 작은 차이를 일반적 우월성으로 단정하지 않는다. 같은 claim에 대한 paired 결과·오류 사례·claim/group 단위 bootstrap 구간을 보고할 수 있다. 소규모 표본의 subgroup 순위를 확정적 결론으로 쓰지 않는다.

### 기존 benchmark score를 그대로 쓸 때

- FEVER는 판정과 충분한 evidence set을 함께 다룬다. [FC02](literature.md#fc02)
- **AVeriTeC 2024**는 QA의 Hungarian METEOR와 evidence threshold를 이용하는 체계다. 논문·공식 코드 버전을 고정하고 그 버전의 설정을 그대로 기록한다. [FC04](literature.md#fc04)
- **AVeriTeC 2025** 공식 페이지는 Ev2R 기반 score를 제시한다. 2024 점수와 직접 비교하거나 구 scorer를 새 scorer라고 부르지 않는다. [공식 2025 과제](https://fever.ai/2025/task.html), [FC05](literature.md#fc05), [FC29](literature.md#fc29)
- reference와 답이 유사하더라도 원출처가 그 답을 실제로 지지하는지 추가 검수가 필요하다. 자동 evidence scorer도 완전한 진실 판정기가 아니다.
- 영어 기준 scorer를 한국어 번역 자료에 적용하면 언어·형태소·판정 모델의 적합성을 먼저 확인한다. 가능하면 작은 사람 검수 결과와 비교한다.

## 6. 실행 기록과 재현

### 공개 가능한 입력 / 비노출 gold / 결과를 분리

```text
inputs: claim_id, claim_text, language, claim_date, target_period,
        evidence_cutoff, verification_mode, allowed_source_policy
gold:   label, sufficient_evidence_sets, numeric_constraints,
        annotator_agreement, adjudication_note, dataset_version
result: claim_id, method, model_id, run_id, attempt_id,
        verdict, cited_evidence_ids, uncertainty, stop_reason,
        tool_events, request_counts, token_usage, elapsed_time,
        execution_status, scoring_version
```

원문 전체나 비공개 추론을 요구하지 않는다. 재현에는 **행동·인자·관찰 근거·짧은 결정 요약·비용·최종 출력**이 필요하다. provider가 reasoning을 노출하지 않았다고 실패로 세지 않는다. 공개 저장소에는 키·개인정보·권한 없는 기사 본문을 제거한 결과만 올린다.

자료는 허용된 범위에서 snapshot/hash를 보관하고 live demo와 고정 평가를 분리한다. deterministic tool cache는 동일 인자·동일 snapshot에서 공유할 수 있으나 생성 답변을 다른 실험 조건에 재사용하지 않는다. cached run과 cold run의 시간도 구분한다.

## 7. 비용 예시 — 승인이나 실행 계획 확정이 아님

`추론 요청 ≈ 사례 × 조건 × 반복 × episode당 평균 요청`

예를 들어 50개 × 3조건 × 1반복 × 평균 4요청은 600요청이라는 **산식 예시**다. 실제 B0/B1/B2는 요청 수가 다르므로 조건별 합계를 쓴다. retrieval·검색 API·임베딩·reranker·Judge·annotation 비용과 GPU 시간을 별도 계산한다. 특정 모델 가격·무료 한도는 선택 시 다시 확인한다.

개발 예산과 최종 평가 예산을 분리한다. 매 요청/도구 결과를 즉시 append-only 기록하고 재시작 시 완료 사례를 중복 호출하지 않는다. 자동 무한 재시도·자동 모델 변경은 금지하고, 실패 항목 재실행에는 명시적 횟수·범위 승인을 받는다.

## 8. 보고서에서 보여줄 결과 표 — 아직 빈 설계

조건별 `N_attempted / N_completed / Macro-F1 / GSR / 보류 / 평균·p95 시간 / 호출·토큰 / 실패 원인` 표와, 같은 claim의 B1/B2 행동 차이 3~5개를 제시한다. 현재 어떤 칸에도 실험 수치를 채우지 않았다.
