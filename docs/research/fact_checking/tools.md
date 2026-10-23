# 자료원과 ReAct 도구 설계 후보

2026-10-23 · 공식 안내 페이지를 확인한 **후보**. 키 발급·사용·실제 통계/API 요청·RSS 수집은 하지 않았다. 아래 함수명은 우리가 만들 수 있는 인터페이스 제안이지 서비스의 실제 endpoint 이름이 아니다.

[구상](README.md) · [평가](evaluation.md) · [문헌](literature.md)

## 1. 자료원 확인 표

| 자료원 | 이번 확인 | 프로젝트에서의 역할 | 사용 전 남은 확인 |
| --- | --- | --- | --- |
| [한국은행 ECOS Open API](https://ecos.bok.or.kr/api/) | 경제통계 API와 인증키 신청 절차 | 환율·금리 등 선택한 통계의 원자료 조회 | 지표 코드·단위·빈도·수정/vintage·키·요청 제한·자료별 이용조건 |
| [KOSIS 공유서비스](https://kosis.kr/serviceInfo/openAPIGuide.do) | 통계목록·수치·설명·통계표 metadata, JSON/SDMX 등 제공 | 지표 발견과 수치·정의 대조 | 정확한 표/분류 코드·키·자료 이용조건·수정 이력 |
| [KOSIS 통계목록 명세](https://www.kosis.kr/openapi/devGuide/devGuide_0101List.do) | apiKey·서비스뷰·parentId, 기관/표 ID·갱신일 등 명세 | 이름만 비슷한 지표를 잘못 고르지 않기 위한 탐색 | 통계자료 endpoint 명세·실제 오류와 pagination 확인 |
| [한국은행 RSS 안내](https://www.bok.or.kr/static/view/popup/rss_popup.html) | 경제통계 보도자료·해명자료·의결사항 등의 RSS 주소 | 발표/정정 발견, 원문으로 이동 | 각 feed 실제 응답·본문 접근·갱신 주기·재사용 범위 |
| [정책브리핑 정책뉴스 API](https://www.data.go.kr/data/15095335/openapi.do) | REST/XML, 제목·내용·승인일 등, 포털에 무료·출처표시 이용조건 기재 | 정책 발표와 관련 문서 수집 | 활용신청·계정 한도·실제 schema·외부 첨부물 권리 |
| [정책브리핑 보도자료 API](https://www.data.go.kr/data/15095295/openapi.do?recommendDataYn=Y) | startDate/endDate, 수정·승인일·원문 URL 등의 명세 | 주장과 원발표·수정문 연결 | 키 발급, transport·응답 형태·누락 필드·권리 검수 |
| [경향신문 RSS 안내](https://www.khan.co.kr/help/help_rss.html) | RSS 제공 및 개인 구독 목적, 다수 공유에 허락 필요하다는 안내 | 기사 발견 후보 | **공개 repo에 feed·기사 본문을 그대로 재배포하지 않음**. 연구 이용·수집 범위 확인 |
| [동아일보 RSS 안내](https://rss.donga.com/) | 분야별 RSS 구독 안내 | 기사 발견 후보 | 이용약관·저장/재배포 권한·실제 feed 주소 확인 |
| [Google Fact Check Tools claims.search](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search) | 이미 fact-check된 주장 검색, 언어·발행처·최신성 필터 | 기존 판정 발견/annotation 보조의 별도 track | 독립 검증 실험에 그대로 주면 정답 누출. 인증·quota·비용·범위 확인 |

정책뉴스/보도자료 포털의 무료·개발 트래픽 표시는 조회일의 안내이며 우리 계정 사용 가능성을 확인한 것은 아니다. 공개 이용조건을 모든 첨부 이미지·기사·외부 원문으로 확장하지 않는다. 이 문서는 법률적 이용허락 판단을 대신하지 않는다.

**핵심 구분:** 공식 API는 모든 주장의 정답을 알려주는 API가 아니다. 예를 들어 정의가 다른 두 통계는 모두 공식 자료여도 직접 비교할 수 없다. 공식 해명자료도 특정 기관의 주장이라는 성격을 기록하고, 필요하면 독립적인 근거와 함께 검토한다.

## 2. 처음부터 모두 만들지 않을 도구 메뉴

| 제안 함수 | 입력 | 출력에 반드시 남길 것 | deterministic / model 판단 |
| --- | --- | --- | --- |
| `discover_updates` | 허용 feed ID, 기간 | 제목/URL/발표시각/원출처 ID | 파싱은 코드, 사실 여부 판정 아님 |
| `search_evidence` | 질의, source filter, cutoff, top_k | 문서 ID·URL·snippet·순위·시점·retriever version | BM25/dense/혼합 검색; 정책은 어떤 질의를 할지 선택 |
| `read_evidence` | 허용 문서/URL ID, 필요한 구간 | 인용 가능한 문장/표, hash, provenance | 읽기 전용 parser; 평가 gold 파일 접근 금지 |
| `search_stat_series` | 주제·지역·빈도 등 | 후보 지표 ID·정의·단위·범위 | 목록/metadata 검색; Agent가 의미를 대조 |
| `fetch_stat_series` | 공급자·지표·기간·분류 ID | 값·단위·기간·잠정 여부·수정정보·누락 상태 | 코드로 검증된 요청·파싱 |
| `calculate_comparison` | 원자료 evidence ID와 허용 연산 | 값·공식·입력 ID·검증 결과 | whitelist 계산; 임의 eval/Python 실행 없음 |
| `finish_verification` | verdict, evidence IDs, 기준 시점, 한계 | 구조화 결과·종료 사유 | schema 검사와 제출; 인터넷 게시 아님 |

최소 구현은 task에 맞는 검색/읽기/계산 정도로 줄인다. 외부 도구 결과를 확인한 뒤 무엇이 부족한지에 따라 Agent가 다음 행동을 선택하도록 한다. ‘모든 도구를 반드시 한 번씩 사용’하는 prompt나 정답 도구 순서 채점은 피한다.

## 3. 근거 객체와 계산 경계

권장 evidence 필드:

```text
evidence_id, source_url, publisher, source_type, original_source_id,
published_at, updated_at, retrieved_at, effective_or_target_period,
content_hash, document_version, excerpt_or_cell_locator,
unit, population_scope, value_status, reuse_policy, retrieval_query
```

본문이 없거나 날짜를 모르면 빈칸을 채워 추정하지 않고 unknown으로 남긴다. 기사 A와 B가 같은 보도자료를 전재했다면 두 독립 증거로 세지 않는다. 문장과 표 셀의 실제 위치를 기록한다.

계산 도구는 `%`와 `%p`, 절대 변화와 상대 변화, 전년 동기와 직전 기간, 명목과 실질, 단위·분모를 입력 계약으로 구분한다. missing·0 분모·NaN·불일치 기간은 계산 실패로 반환한다. **정확하게 계산했다는 사실은 지표를 올바르게 선택했다는 증거가 아니다.**

## 4. 상태·오류·최소 안전장치

- 도구 결과는 `ok / empty / invalid_input / source_unavailable / rate_limited / timed_out` 등 실행 상태와 관찰 자료를 분리한다.
- `empty`는 검색 결과 없음이지 claim이 거짓이라는 뜻이 아니다. 도구 실패를 NEI 정답으로 바꾸지 않는다.
- 읽기 전용 도구, 허용 scheme/host·리디렉션 검사, 사설망/로컬 파일 차단, 파일 크기·본문 길이·시간 상한을 둔다. 운영 프레임워크 전체를 새로 만들 필요는 없다.
- 외부 기사·도구 결과는 비신뢰 자료다. 그 안의 명령은 시스템 지시로 실행하지 않는다. 저장·전송·키 접근 권한을 주지 않는다.
- API 키는 runtime 환경에서만 읽고 URL query·로그·오류·Git에 남기지 않는다. 공식 예제에 나온 키 문자열도 복사하지 않는다.
- 요청 시작/종료·error·최종 결과를 즉시 기록한다. 같은 호출의 시간 초과 후 무제한 중복 실행을 하지 않는다.
- timeout, 최대 step·검색·토큰 예산, 재시도 정책은 파일럿 승인 전에 정한다. 재시도할 때는 새로운 attempt와 실패 이유를 보존한다.
- HTTP 200과 JSON parse 성공을 fact-check 성공으로 세지 않는다. 판정 schema와 근거의 실제 존재를 별도로 확인한다.

## 5. 재현 가능한 평가와 live 데모의 관계

처음에는 허용된 문서·통계 snapshot을 고정하고, 같은 tool interface가 그 store를 조회하도록 할 수 있다. 모델은 자료를 미리 전부 받지 않고 도구로 필요한 근거를 찾는다. 이때도 관찰에 따른 도구 선택은 Agent 실험이지만 **live web 실험이라고 부르면 안 된다**.

live RSS/API 데모는 별도 실행으로 추가하고 네트워크·검색순위·자료 갱신 문제를 따로 보고한다. 고정 store에 사례별 정답 근거만 딱 넣으면 검색이 지나치게 쉬워지므로 관련 distractor·구버전·유사 지표를 설계하고 gold 목록은 숨긴다.

## 6. GPU·학습을 활용하는 선택지

- 고정 공개 encoder의 embedding cache, 작은 reranker, 로컬 LLM 반복 평가에 GPU를 활용할 수 있다.
- Kiwi+BM25와 고정 dense/hybrid 비교는 LLM 추가 학습 없이도 가능하다.
- RL을 연결한다면 후속으로 검색/계산/종료의 작은 정책을 학습하는 선택지를 생각할 수 있다. 50개 test는 학습 자료가 아니며 별도 학습·검증·보상이 필요하다.
- HerO 2의 공개 README는 32B 모델 fine-tuning과 AWQ를 설명한다. 그 구현 전체를 복제하는 것과 설계 아이디어만 참고하는 것을 구분한다. 코드 라이선스도 별도로 확인한다. [저자 코드](https://github.com/ssu-humane/HerO2)

현재 GPU 작업·학습·가중치 다운로드는 하지 않았다. 남은 Colab 자원과 실제 VRAM 적재 가능성도 확인 전이다.
