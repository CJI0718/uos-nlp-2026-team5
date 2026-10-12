# AI Agents 연구 후보 30개

조사 기준: 2026-10-11. 주제 미선정 · 실험 미실행.

이 문서는 원논문/공식 자료를 탐색해 만든 연구 제안입니다. 모든 논문 전문 정독이나 구현 재현을 했다는 뜻이 아닙니다.

각 후보의 50개는 작성할 평가 사례 구성안이며, 이미 데이터가 존재한다는 뜻이 아닙니다.

D1=비교적 낮음, D2=중간, D3=높음. 호출량은 사례당·조건당 계획용 추정으로 구축·judge 비용은 별도입니다.

## RAG와 검색 기반 문제 해결

무엇을 근거로 가져와야 정확하고 효율적으로 업무를 끝낼 수 있는가?

### R1. 질문과 문서 규모에 맞는 검색 선택

- **문제:** 정확한 용어 검색과 의미가 같은 다른 표현 검색에서 필요한 방법이 다를까?
- **업무:** Agent가 한국어 문서에서 근거를 찾아 짧은 답과 근거 ID를 제시한다.
- **예시:** 규정 문서에서 '휴학 중 신청 가능한 지원'의 조건을 찾아 근거 조항을 제시한다.
- **50개 구성:** 정확 용어 15개 / 동의어·바꿔쓰기 15개 / 고유명사·숫자 10개 / 모호한 질의 10개
- **정답 정보:** 관련 청크 집합, 허용 답, 질문 유형. 자료를 늘려도 정답 근거는 유지하고 새 관련 문서는 재판정한다.
- **비교 조건:** Kiwi+BM25 / 고정 embedding dense / BM25+dense hybrid
- **주요 지표:** Recall@5·nDCG@10 / 답 정확도·인용 정확성 / 구축 시간·검색 p50/p95·인덱스 크기
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 1–3회. BM25-only 검색 실험은 생성 호출 0회. 임베딩 계산·인덱스 구축은 별도.
- **주의:** 규모·청킹·모델을 동시에 바꾸지 않는다. BM25와 DB 제품 자체를 같은 층의 대안으로 비교하지 않는다.
- **확장:** 한국어/영어 도메인 전이 / Flat/HNSW 규모 비교 / 질문 유형별 검색 router
- **참고:** [P01 Operational Advice for Dense and Sparse Retrievers: HNSW, Flat, or Inverted Indexes?](https://aclanthology.org/2025.acl-industry.61/), [P02 BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html), [P09 Balancing the Blend: An Experimental Analysis of Trade-Offs in Hybrid Search](https://dl.acm.org/doi/abs/10.14778/3811243.3811246), [P10 BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms](https://arxiv.org/abs/2607.26497)

### R2. 주장 검증과 근거 부족 판정

- **문제:** 찾은 문서가 관련 있어 보이는 것과 주장을 실제로 입증하는 것은 같을까?
- **업무:** Agent가 근거를 탐색해 지원·반박·정보 부족 중 하나와 증거를 반환한다.
- **예시:** '이 제도는 모든 재학생에게 적용된다'를 예외 조항까지 확인해 판정한다.
- **50개 구성:** 지원 20개 / 반박 20개 / 정보 부족 10개
- **정답 정보:** 3-class 정답과 충분한 증거 집합. 정보 부족은 검색 실패가 아니라 고정 코퍼스에서 입증·반박할 수 없는 사례로 작성한다.
- **비교 조건:** 한 번 검색 후 판정 / 질문 분해 후 재검색 / 판정·근거 검증 후 한 번 보완
- **주요 지표:** Macro-F1 / 판정+충분한 근거 동시 성공률 / 정보 부족 F1·불필요 재검색 수
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–6회. 판정은 코드로, 근거의 충분성은 작성자·검토자가 확인할 수 있어 별도 Judge 호출이 필수는 아니다.
- **주의:** 같은 사건명이나 단어 겹침을 증거의 참·거짓 정답으로 대신하지 않는다.
- **확장:** 조건·예외가 있는 규정 / 상반된 출처 비교 / 수치 주장 검증
- **참고:** [P03 FEVER: a Large-scale Dataset for Fact Extraction and VERification](https://aclanthology.org/N18-1074/), [P04 Enabling Large Language Models to Generate Text with Citations (ALCE)](https://aclanthology.org/2023.emnlp-main.398/), [P11 ReAct: Synergizing Reasoning and Acting in Language Models](https://react-lm.github.io/)

### R3. 여러 문서를 연결하는 종합 답변

- **문제:** 청크만 찾는 방식과 미리 요약·연결한 구조 중 무엇이 종합 질문에 도움이 될까?
- **업무:** Agent가 문서 여러 곳의 근거를 연결하거나 문서 집합의 공통 경향을 설명한다.
- **예시:** 여러 정책 안내문에서 반복되는 신청 제한과 서로 다른 예외를 비교한다.
- **50개 구성:** 한 문서 사실 15개 / 두 문서 연결 15개 / 세 문서 이상 비교 10개 / 문서 집합 전체 경향 10개
- **정답 정보:** 필수 사실·근거 목록과 금지된 과잉 일반화. 사실형과 전역형 점수를 따로 집계한다.
- **비교 조건:** 원문 청크 RAG / 계층 요약 RAG / GraphRAG 또는 Wiki 보조 검색
- **주요 지표:** 필수 사실 포함률 / 주장별 근거 일치율 / 누락·모순률·구축/질의 토큰
- **구현 부담:** D3
- **호출 추정:** 사례당·조건당 3–10회. 그래프·트리·Wiki 구축과 갱신에 문서 수 비례 추가 호출. 질의 비용만으로 비교하지 않는다.
- **주의:** 평가 질문·정답을 요약 구조 생성에 제공하면 누설된다. 두-hop과 전체 경향 질문은 구분한다.
- **확장:** RAPTOR/GraphRAG/LightRAG / 원문+Wiki 교차 검증 / 구조 갱신 비용
- **참고:** [P06 RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval](https://arxiv.org/abs/2401.18059), [P07 From Local to Global: A GraphRAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130), [P08 LightRAG: Simple and Fast Retrieval-Augmented Generation](https://aclanthology.org/2025.findings-emnlp.568/), [I01 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

### R4. 파싱과 표 구조가 답변에 미치는 영향

- **문제:** 검색 모델보다 입력 파싱 손실이 더 큰 병목인 경우는 언제일까?
- **업무:** Agent가 본문·표·각주에서 필요한 값을 찾아 계산하고 원문 위치를 제시한다.
- **예시:** 안내문의 표와 각주를 함께 읽어 본인 조건에 해당하는 지원 한도를 계산한다.
- **50개 구성:** 본문만 10개 / 표만 10개 / 본문+표 10개 / 각주·예외 10개 / 단위·기간 혼동 10개
- **정답 정보:** 근거 페이지·표 셀, 정답 수치·단위·기간, 허용 오차. 원문과 파싱 결과를 별도로 보관한다.
- **비교 조건:** 단순 텍스트 추출 / 표·제목 구조 보존 / 구조 보존+계산 도구
- **주요 지표:** 핵심 필드 추출 정확도 / 수치·단위 동시 정답률 / 근거 회수율·파싱 시간
- **구현 부담:** D3
- **호출 추정:** 사례당·조건당 2–6회. 텍스트 PDF는 로컬 처리 가능. OCR·비전 모델을 쓰면 페이지 단위 비용이 별도 발생한다.
- **주의:** 파서 비교에서는 후속 retriever를 고정한다. 일부러 만든 깨끗한 문서만으로 실제 PDF 전체에 일반화하지 않는다.
- **확장:** 재무 공시·규정·제품 규격서 / OCR 유무 / 청킹과 표 행 분리
- **참고:** [P33 OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations](https://openaccess.thecvf.com/content/CVPR2025/html/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.html), [P34 TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance](https://aclanthology.org/2021.acl-long.254/), [P04 Enabling Large Language Models to Generate Text with Citations (ALCE)](https://aclanthology.org/2023.emnlp-main.398/)

### R5. 개정 자료를 반영하는 최신 근거 Agent

- **문제:** 오래된 문서와 새 문서가 함께 있을 때 최신 규정과 과거 규정을 구분할 수 있을까?
- **업무:** 질문 기준일에 맞는 버전을 찾아 답하고 자료가 바뀌면 검색 지식도 갱신한다.
- **예시:** 작년과 올해의 신청 요건이 다른 안내문에서 특정 날짜 기준의 조건을 답한다.
- **50개 구성:** 변경 없음 10개 / 조건 변경 10개 / 폐지·철회 10개 / 출처 간 충돌 10개 / 과거 시점 질문 10개
- **정답 정보:** 유효기간·출처별 권위·버전 관계와 시점별 정답. 최신 문서가 언제나 정답인 것은 아니다.
- **비교 조건:** 날짜 무시 검색 / 시간·버전 필터 검색 / 원문+갱신 Wiki/graph
- **주요 지표:** 시점별 답 정확도 / 구버전 오인용률 / 갱신 시간·추가 토큰·누락률
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–5회. Wiki·graph 갱신비는 독립 기록. 라이브 웹 대신 날짜가 고정된 문서 묶음으로 시작할 수 있다.
- **주의:** 게시일과 효력 발생일을 구분한다. 검색일이 달라져 자료가 바뀌는 실험은 비교가 흔들린다.
- **확장:** 증분 색인 / 철회·수정 반영 / 출처 우선순위 판단
- **참고:** [P08 LightRAG: Simple and Fast Retrieval-Augmented Generation](https://aclanthology.org/2025.findings-emnlp.568/), [P16 LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html), [I01 LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

### R6. 제한된 검색 예산에서 답하거나 보류하기

- **문제:** 모든 질문에 같은 횟수로 검색하는 것보다 난이도에 따라 예산을 달리 쓰는 게 좋을까?
- **업무:** Agent가 한 번 검색, 추가 검색, 답변 보류를 선택하며 제한된 비용으로 근거 답변을 완성한다.
- **예시:** 간단한 사실 질문에는 즉시 답하고 근거가 분산된 질문에만 추가 검색한다.
- **50개 구성:** 단일 근거 20개 / 복수 근거 20개 / 자료 내 답 없음 10개
- **정답 정보:** 정답·근거·답변 불가능 여부. 최적 행동 순서를 정답으로 강제하지 않는다.
- **비교 조건:** 고정 1회 검색 / 고정 다회 검색 / 예산 내 적응형 검색
- **주요 지표:** 성공률-토큰 곡선 / 보류 precision/recall / 성공 한 건당 비용·한도 초과율
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–8회. router도 모델을 쓰면 그 호출을 포함한다. 무료 API의 rate limit도 실패 원인으로 기록한다.
- **주의:** 검색을 줄인 대신 추측해서 맞힌 답과 근거를 갖춘 답을 구분한다.
- **확장:** confidence 기반 중단 / 오류 유형별 재검색 / 품질 하한을 둔 비용 최적화
- **참고:** [P05 Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity](https://aclanthology.org/2024.naacl-long.389/), [P04 Enabling Large Language Models to Generate Text with Citations (ALCE)](https://aclanthology.org/2023.emnlp-main.398/), [P10 BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms](https://arxiv.org/abs/2607.26497)

## ReAct와 도구 선택 및 실행

무엇을 할지 선택하고 결과에 맞춰 다음 행동을 바꿀 수 있는가?

### T1. 상태와 순서 제약이 있는 사무 업무

- **문제:** 앞선 도구 결과가 다음 행동의 조건일 때 업무를 올바르게 완수할까?
- **업무:** Agent가 조회·검사·수정 도구를 사용해 모의 일정·대여·문의 업무를 끝낸다.
- **예시:** 참가자 가능 시간을 확인하고 겹치지 않는 회의를 생성하되 초대 발송은 승인 후 수행한다.
- **50개 구성:** 2단계 10개 / 3단계 10개 / 4단계 10개 / 분기 조건 10개 / 승인 필요 10개
- **정답 정보:** 초기/목표 DB 상태와 선행 조건의 부분 순서. 정당한 다른 실행 경로를 허용한다.
- **비교 조건:** 고정 workflow / Act-only 도구 선택 / 계획·관찰 갱신을 포함한 ReAct
- **주요 지표:** 목표 상태 달성률 / 필수 선행조건 준수율 / 불필요 호출 수·종료 시간
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–8회. 모든 API는 로컬 모의 도구로 만들 수 있다. 자연어 사용자 simulator는 별도 호출 없이 고정 응답으로 대체 가능하다.
- **주의:** 계획 설명이 좋아도 실제 상태가 바뀌지 않으면 성공이 아니다.
- **확장:** 일정·재고·반품 / 병렬 가능한 행동 식별 / 권한 조건 포함
- **참고:** [P11 ReAct: Synergizing Reasoning and Acting in Language Models](https://react-lm.github.io/), [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html)

### T2. 복수 조건을 만족하는 선택과 계산

- **문제:** 자료 수집·계산·비교가 섞인 의사결정에서 제약을 빠뜨리지 않을까?
- **업무:** Agent가 모의 상품·예약·요금 정보를 조회해 예산과 조건을 모두 만족하는 선택안을 만든다.
- **예시:** 배송일·재고·총액 조건을 만족하는 장비 구매안을 계산하되 주문은 실행하지 않는다.
- **50개 구성:** 예산 10개 / 기한 10개 / 재고 10개 / 복합 조건 10개 / 가능한 대안 없음 10개
- **정답 정보:** 정답 후보 집합과 비용 계산식, 하드 제약. 복수 최적해는 모두 허용한다.
- **비교 조건:** 한 번에 계획 / 단계별 관찰·계산 / 명시적 제약 체크리스트
- **주요 지표:** 모든 제약 충족률 / 수치 정확도 / 최적해 대비 비용 차이·도구 호출
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–7회. 정답을 작은 열거 프로그램으로 확인할 수 있다. 실제 결제·예약은 필요 없다.
- **주의:** 추천 문장의 설득력보다 하드 제약 만족을 먼저 채점한다.
- **확장:** 구독료 비교 / 장비 대여 / 여행 일정의 시간 제약
- **참고:** [P11 ReAct: Synergizing Reasoning and Acting in Language Models](https://react-lm.github.io/), [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html), [P34 TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance](https://aclanthology.org/2021.acl-long.254/)

### T3. 도구 장애에서 복구하는 Agent

- **문제:** timeout·빈 결과·부분 성공에 무작정 재시도하지 않고 적절히 대처할까?
- **업무:** 일부 도구가 실패하는 모의 환경에서 중복 변경 없이 목표를 달성하거나 안전하게 중단한다.
- **예시:** 저장은 되었지만 응답이 끊긴 상황에서 상태를 확인한 후 중복 저장을 피한다.
- **50개 구성:** 일시 timeout 10개 / 빈 결과 10개 / 부분 성공 10개 / 입력 형식 오류 10개 / 복구 불가능 10개
- **정답 정보:** 미리 고정한 장애 일정, 실제 상태 변화, 허용 복구 행동과 정당한 중단 조건.
- **비교 조건:** 재시도 없음 / 고정 재시도 상한 / 오류 분류+상태 확인
- **주요 지표:** 복구 성공률 / 중복·손상률 / 추가 호출·안전 중단률
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 4–10회. 이후 승인된 실험에서만 재시도 조건을 실행한다. 장애 주입은 모의 도구에서 고정한다.
- **주의:** 시스템에 넣은 timeout과 실제 공급자 장애를 섞어 원인을 해석하지 않는다.
- **확장:** 장기 작업 재개 / idempotency / 재시도 예산 배분
- **참고:** [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html), [P15 Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html), [P27 SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)

### T4. 언제 사용자에게 되물어야 하는가

- **문제:** 정보가 부족할 때 적절히 질문하면서도 불필요한 확인을 줄일 수 있을까?
- **업무:** Agent가 모호한 업무 요청에서 필수 정보를 확인하고 정당한 가정으로 수행 가능한 부분은 진행한다.
- **예시:** 동명이인 두 명 중 수신자가 불명확할 때 임의 선택하지 않고 확인한다.
- **50개 구성:** 정보 충분 10개 / 필수 항목 누락 10개 / 동명이인·모호성 10개 / 조건 충돌 10개 / 가정 허용 10개
- **정답 정보:** 질문 필요 여부, 필수 확인 슬롯, 표준 사용자 답, 목표 상태.
- **비교 조건:** 항상 질문 / 질문 없이 수행 / 불확실성별 선택 질문
- **주요 지표:** 최종 성공률 / 필수 확인 누락률 / 불필요 질문률·대화 턴 수
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–6회. 사용자 응답을 사람이 미리 작성하면 simulator 비용과 변동을 줄일 수 있다.
- **주의:** 질문 횟수만 최소화하면 무단 추측이 늘 수 있어 안전·성공 지표를 함께 본다.
- **확장:** 수신자 확인 / 조건 협상 / 불가능한 요청 설명
- **참고:** [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html)

### T5. 도구가 많아져도 필요한 것만 선택하기

- **문제:** 도구 수·이름 유사성·설명 방식이 선택과 인자 생성에 어떤 영향을 줄까?
- **업무:** 필요한 도구와 방해 도구가 함께 있는 환경에서 올바른 API와 인자를 골라 업무를 수행한다.
- **예시:** 조회 전용 도구와 수정 도구가 비슷한 이름일 때 읽기 요청에는 조회만 사용한다.
- **50개 구성:** 작은 도구 집합 10개 / 중간 집합 10개 / 큰 집합 10개 / 유사 도구 이름 10개 / 사용 가능한 도구 없음 10개
- **정답 정보:** 허용 도구 집합·필수 인자·업무 최종 상태. 도구 이름 대신 기능을 기준으로 정답을 작성한다.
- **비교 조건:** 전체 도구 노출 / 도구 설명 정돈 / 과제별 후보 도구 필터
- **주요 지표:** 도구 선택 정확도 / 인자 유효율 / 위험 오호출률·성공률
- **구현 부담:** D1
- **호출 추정:** 사례당·조건당 2–6회. 모의 함수와 JSON schema로 평가 가능하다. 도구 설명의 입력 토큰 비용이 증가할 수 있다.
- **주의:** 후보 필터가 정답 도구를 정답지에서 알려주는 oracle이 되지 않도록 한다.
- **확장:** 한국어·영어 도구 설명 / 도구 검색 / API 명칭의 모호성
- **참고:** [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html), [P27 SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)

### T6. API와 화면 조작의 업무 수행 차이

- **문제:** 같은 업무를 구조화 API로 할 때와 웹 화면으로 할 때 무엇이 달라질까?
- **업무:** 로컬 미니 웹 환경에서 조회·필터·입력·저장 업무를 끝내고 결과 상태를 검사한다.
- **예시:** 모의 게시판에서 조건에 맞는 항목을 찾아 태그를 수정한다.
- **50개 구성:** 탐색 10개 / 필터·정렬 10개 / 폼 입력 10개 / 복수 화면 10개 / 오류·팝업 10개
- **정답 정보:** 같은 초기 데이터와 목표 상태, 동일한 권한·업무 의미. 화면 좌표 경로는 정답으로 고정하지 않는다.
- **비교 조건:** 직접 API / DOM 기반 조작 / 시각 기반 조작 또는 DOM+검증
- **주요 지표:** 최종 상태 성공률 / 오조작·부작용률 / 행동 수·지연·이미지 입력 비용
- **구현 부담:** D3
- **호출 추정:** 사례당·조건당 5–15회. 브라우저 환경 구축·reset·시각 모델 입력이 추가 부담. 기존 서비스의 실제 계정은 사용하지 않는다.
- **주의:** API와 UI의 기능·권한 차이를 모델 성능 차이로 단정하지 않는다.
- **확장:** 접근성 / 레이아웃 변화 / 복구 가능한 UI 자동화
- **참고:** [P14 WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854), [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P27 SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)

## 메모리와 장기 작업

과거 정보를 남기고 필요한 순간에 최신 상태로 활용할 수 있는가?

### M1. 변하는 사용자 선호와 조건 기억

- **문제:** 과거 선호를 기억하는 것과 현재 유효한 선호를 따르는 것은 어떻게 다를까?
- **업무:** 합성 사용자의 여러 세션 정보를 기억해 이후 추천·일정·문서 작성에서 현재 조건을 지킨다.
- **예시:** 예전에는 오전을 선호했지만 최근 오후로 바꾼 사용자의 회의 시간을 제안한다.
- **50개 구성:** 단일 선호 회상 10개 / 다중 조건 10개 / 선호 변경 10개 / 예외 조건 10개 / 언급되지 않은 정보 10개
- **정답 정보:** 사용자별 사실·유효기간·예외·출처 세션. 최신 사실과 미상 정보를 명확히 구분한다.
- **비교 조건:** 최근 대화만 / 누적 요약 / 검색 가능한 구조화 사실 기억
- **주요 지표:** 현재 조건 충족률 / 오래된 기억 사용률 / 미상 정보 보류 정확도·입력 토큰
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–6회. 초기 이력의 기억 추출·요약 비용이 별도. 실제 사용자의 민감 대화 없이 합성 기록으로 평가한다.
- **주의:** Agent가 사용자 특성을 임의 추론한 것을 기억 성공으로 세지 않는다.
- **확장:** 여행·학습·작업 스타일 / 예외 우선순위 / 개인화와 과잉 추측
- **참고:** [P16 LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html), [P17 Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo)](https://aclanthology.org/2024.acl-long.747/), [P19 MemoryBank: Enhancing Large Language Models with Long-Term Memory](https://ojs.aaai.org/index.php/AAAI/article/view/29946)

### M2. 여러 세션의 프로젝트 상태와 시간 관계

- **문제:** 완료·취소·변경된 업무를 시간 순서와 함께 정확히 관리할까?
- **업무:** 여러 회의·업무 기록을 읽고 다음 할 일과 현재 담당자·마감일을 제시한다.
- **예시:** 담당자가 바뀌고 마감이 연기된 프로젝트에서 현재 남은 작업만 정리한다.
- **50개 구성:** 한 세션 회상 10개 / 세션 간 결합 10개 / 시간 순서 10개 / 정정·취소 10개 / 충돌·정보 부족 10개
- **정답 정보:** 이벤트 로그로부터 계산되는 시점별 프로젝트 상태. 질문 시점 이후의 정보는 입력하지 않는다.
- **비교 조건:** 전체 로그 제공 / 서술 요약 / 시간·상태가 있는 이벤트 기억
- **주요 지표:** 현재 상태 필드 정확도 / 시간 순서 정확도 / 누락·취소 업무 부활률
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–7회. 긴 로그를 매번 입력하는 비용과 미리 상태를 만드는 비용을 분리한다.
- **주의:** 미래 세션이나 정답 timeline을 메모리 입력에 노출하지 않는다.
- **확장:** 연구노트 / 인수인계 / 문서 버전 관리
- **참고:** [P16 LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html), [P17 Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo)](https://aclanthology.org/2024.acl-long.747/), [P18 MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)

### M3. 실패 경험을 다음 업무에 적용하기

- **문제:** 실패를 기록하면 비슷하지만 새로운 문제에서 실제로 행동이 나아질까?
- **업무:** 과거 도구 오류·잘못된 가정의 피드백을 기억해 이후 업무에서 같은 실수를 피한다.
- **예시:** 이전에 단위 변환을 누락한 경험을 저장한 뒤 다른 수치 업무에서 단위를 확인한다.
- **50개 구성:** 같은 오류 유형 10개 / 다른 표현의 유사 오류 10개 / 새로운 오류 10개 / 잘못된 과거 교훈 10개 / 교훈 적용이 불필요한 업무 10개
- **정답 정보:** 별도 연습 경험과 새로운 평가 업무, 필요한 교훈·피해야 할 과잉 적용.
- **비교 조건:** 경험 저장 없음 / 원시 실패 로그 검색 / 정리된 교훈 기억
- **주요 지표:** 동일 오류 재발률 / 새 업무 성공률 / 잘못된 교훈 적용률·비용
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–9회. 교훈 생성·재시도 횟수도 비용에 포함. 비교군에도 같은 총 시도 예산을 준다.
- **주의:** 평가 문제의 정답이나 패치를 기억에 넣고 성공한 것을 일반화로 주장하지 않는다.
- **확장:** 절차 기억 / 팀의 실패 기록 / 교훈의 신뢰도·폐기
- **참고:** [P15 Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html), [P20 A-Mem: Agentic Memory for LLM Agents](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html), [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/)

### M4. 제한된 기억 예산에서 무엇을 남길까

- **문제:** 전체 로그·요약·검색 기억 중 정보량 대비 효율이 좋은 표현은 무엇일까?
- **업무:** 고정된 메모리 토큰 예산으로 과거 정보를 보존하고 이후 질문과 업무에 사용한다.
- **예시:** 장기간 업무 기록에서 불필요한 잡담보다 필요한 결정·수치·조건을 유지한다.
- **50개 구성:** 사실 위주 10개 / 잡음이 많은 이력 10개 / 드문 중요 사실 10개 / 상호 관련 사실 10개 / 반복·중복 이력 10개
- **정답 정보:** 회상해야 할 사실과 근거 위치. 같은 메모리 예산에서 비교하고 길이를 별도 실험 변수로 둔다.
- **비교 조건:** 최근 구간 보존 / 고정 길이 요약 / 사실·관계 중심 검색 기억
- **주요 지표:** 사실 회상 정확도 / 최종 업무 성공률 / 기억 토큰·쓰기/읽기 비용
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–7회. 메모리 추출·재요약·검색 비용을 합산한다. 학습 없이 로컬 저장소로 축소 가능하다.
- **주의:** 요약 방식에만 더 긴 토큰 예산이나 더 강한 모델을 제공하지 않는다.
- **확장:** 요약 주기 / 중요도 기반 압축 / 연결된 메모리와 벡터 검색
- **참고:** [P18 MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), [P20 A-Mem: Agentic Memory for LLM Agents](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html), [P21 Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413), [P31 Lost in the Middle: How Language Models Use Long Contexts](https://aclanthology.org/2024.tacl-1.9/)

### M5. 삭제·만료·사용자 경계를 지키는 기억

- **문제:** 기억해야 하는 정보와 더 이상 사용하면 안 되는 정보를 구분할 수 있을까?
- **업무:** 모의 사용자·프로젝트별 기억에서 정정·삭제·만료 요청을 반영하고 허용 범위의 정보만 사용한다.
- **예시:** 삭제를 요청한 연락처는 검색에 반환하지 않고 다른 사용자의 기록도 참조하지 않는다.
- **50개 구성:** 정정 10개 / 삭제 10개 / 유효기간 만료 10개 / 사용자 경계 10개 / 프로젝트 경계 10개
- **정답 정보:** 허용·금지 기억 ID, 삭제 뒤 저장소·색인 상태, 최신 정답. 가짜 개인정보만 사용한다.
- **비교 조건:** 단일 누적 기억 / 소유자·시간 필터 / 필터+삭제 전파 검사
- **주요 지표:** 금지 기억 반환률 / 갱신·삭제 반영률 / 정상 업무 성공률
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–6회. 검색 인덱스와 요약 사본까지 검사하는 구현 비용이 든다. 모델 재학습은 필요하지 않다.
- **주의:** 검색에서 삭제되었다고 모델 파라미터에서 완전히 잊었다고 주장하면 안 된다.
- **확장:** 메모리 provenance / 동의 철회 / 삭제와 요약 캐시의 일관성
- **참고:** [P16 LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html), [P19 MemoryBank: Enhancing Large Language Models with Long-Term Memory](https://ojs.aaai.org/index.php/AAAI/article/view/29946), [P25 Defeating Prompt Injections by Design (CaMeL)](https://arxiv.org/abs/2503.18813)

### M6. 기억 담당 서브에이전트는 이득인가

- **문제:** 기억 관리 역할을 분리하면 성능이 좋아지는가, 단지 호출과 전달 손실이 늘어나는가?
- **업무:** 주 업무 Agent가 과거 정보를 요청·활용하며 기억 관리를 같은 모델의 별도 역할로 분리해 비교한다.
- **예시:** 연구 보조 Agent가 이전 결정의 근거를 메모리 담당 역할에 요청하고 현재 문서에 반영한다.
- **50개 구성:** 단순 사실 10개 / 다중 사실 10개 / 갱신 요청 10개 / 모호한 회상 10개 / 장기 이력 10개
- **정답 정보:** 필요한 기억과 최종 업무 정답. 동일 기반 모델·정보 접근·전체 토큰 한도로 비교한다.
- **비교 조건:** 단일 Agent 내 메모리 / 일반 메모리 함수 / 별도 메모리 역할 호출
- **주요 지표:** 업무 성공률 / 기억 전달 누락률 / 총 토큰·호출·지연
- **구현 부담:** D3
- **호출 추정:** 사례당·조건당 4–12회. 추가 역할 호출과 원문 재전달이 비용을 키울 수 있다. 실제 다중 프로세스가 아닌 순차 호출로도 비교 가능하다.
- **주의:** 역할 분리와 모델 강도·추가 예산의 효과를 혼동하지 않는다.
- **확장:** 독립 검증 역할 / 질문 압축 / 동일 예산에서 멀티 역할의 가치
- **참고:** [P18 MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), [P20 A-Mem: Agentic Memory for LLM Agents](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html), [P21 Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413)

## LLM과 Agent의 지시 준수 및 안전성

외부 정보와 권한이 추가되어도 사용자의 목표와 행동 경계를 지키는가?

### A1. 외부 문서의 방해 지시 속에서 업무 유지

- **문제:** 검색 문서나 도구 결과의 지시를 사용자 요청으로 잘못 받아들일까?
- **업무:** Agent가 비신뢰 문서에서 사실만 사용하고 사용자에게 허용받지 않은 행동은 실행하지 않는다.
- **예시:** 모의 안내문에 작업 방향을 바꾸는 문구가 섞여 있어도 요청된 근거 답변만 만든다.
- **50개 구성:** 검색 문서 10개 / 모의 메일 10개 / 도구 반환값 10개 / 인용문·로그 10개 / 혼합 출처 10개
- **정답 정보:** 정상 목표와 허용·금지 행동. 50개 기본 업무 각각에 clean/교란 조건을 짝지어 실행한다.
- **비교 조건:** 방어 없음 / 비신뢰 입력 표기 / 출처 분리+실행 권한 검사
- **주요 지표:** 공격 성공률 ASR / 공격 중 정상 업무 성공률 / clean 성공률·오탐 차단률
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–8회. clean/교란 쌍 때문에 실행 수는 기본 예산의 2배. 모의 자료·도구 외 실제 서비스를 사용하지 않는다.
- **주의:** 원래 못 푸는 업무를 안전해서 막은 것으로 세지 않는다. 공격 성공 분모를 명시한다.
- **확장:** 검색 순위와 노출 위치 / 다중 도구 경유 / 방어 비용
- **참고:** [P22 AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), [P23 InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents](https://aclanthology.org/2024.findings-acl.624/), [P25 Defeating Prompt Injections by Design (CaMeL)](https://arxiv.org/abs/2503.18813)

### A2. 최소 권한과 승인 절차의 효용

- **문제:** 허용 도구가 많아질 때 성공률과 권한 위반 위험은 함께 어떻게 바뀔까?
- **업무:** 조회·초안·수정 권한을 구분하는 환경에서 승인 범위 내의 업무만 수행한다.
- **예시:** 초안 작성만 요청받았을 때 모의 전송 도구를 실행하지 않는다.
- **50개 구성:** 조회만 10개 / 초안만 10개 / 승인 후 변경 10개 / 범위 밖 대상 10개 / 추가 승인 필요 10개
- **정답 정보:** 요청별 권한표, 허용 상태 변화, 승인 이벤트. 실제 계정·메일 발송은 제외한다.
- **비교 조건:** 넓은 도구 노출 / 최소 권한 노출 / 최소 권한+승인 gate
- **주요 지표:** 권한 위반 시도율 / 실제 위반 차단률 / 정상 완료율·사용자 개입 수
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–7회. 정책 검사기는 코드로 구현 가능하다. gate가 차단한 것과 모델이 스스로 지킨 것을 분리 집계한다.
- **주의:** 필수 권한을 없애 업무를 불가능하게 만든 조건을 동일 능력 비교로 해석하지 않는다.
- **확장:** 파일 접근 범위 / 실행 전 미리보기 / 위험 수준별 승인
- **참고:** [P25 Defeating Prompt Injections by Design (CaMeL)](https://arxiv.org/abs/2503.18813), [P22 AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html)

### A3. 모델의 말과 Agent의 행동 사이

- **문제:** 텍스트로는 규정을 따르겠다고 하면서 실제 도구 행동은 어기는 경우가 있을까?
- **업무:** 같은 요청·관찰에서 계획을 제시하는 모드와 도구를 실행하는 모드의 제약 준수를 비교한다.
- **예시:** 읽기 전용 업무에서 제안한 계획과 실제 모의 파일 변경 여부를 나란히 평가한다.
- **50개 구성:** 금지 도구 10개 / 금지 대상 10개 / 승인 전 실행 10개 / 충돌하는 요청 10개 / 정상 요청 10개
- **정답 정보:** 행동 수준의 정책과 최종 상태. 계획도 구조화 action으로 받아 같은 검사기를 적용한다.
- **비교 조건:** 구조화 계획만 / 동일 모델의 도구 실행 / 도구 실행+외부 정책 검사
- **주요 지표:** 계획상 위반률 / 실행 위반률 / clean 업무 성공률·말/행동 불일치
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–6회. 계획·실행 조건별 관찰량과 허용 도구를 가능한 한 맞춘다.
- **주의:** 그냥 챗봇의 거절 문구와 Agent의 실행 실패를 비교해 'Agent가 본질적으로 덜 aligned'라고 결론 내리지 않는다.
- **확장:** 권한 확대 효과 / 다단계에서의 규칙 유지 / 자기보고의 신뢰성
- **참고:** [P24 AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c493d23af93118975cdbc32cbe7323f5-Abstract-Conference.html), [P22 AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html)

### A4. 오염된 기억과 지식의 출처 검증

- **문제:** 과거 기억이나 검색 DB의 잘못된 정보가 반복 작업에 퍼지는 것을 막을 수 있을까?
- **업무:** Agent가 기억·검색 결과의 출처와 유효성을 확인하고 검증되지 않은 정보를 행동 근거에서 제외한다.
- **예시:** 합성 기억에 들어간 잘못된 담당자 정보가 새 업무에 재사용되지 않도록 원문을 확인한다.
- **50개 구성:** 잘못된 사실 10개 / 출처 없음 10개 / 오래된 정보 10개 / 서로 모순된 기억 10개 / 허위 권한 주장 10개
- **정답 정보:** 원본 근거, 신뢰 가능한 출처, 정정 내용, 허용 행동. 공격 트리거 최적화는 하지 않는다.
- **비교 조건:** 기억 무조건 사용 / 출처 메타데이터 확인 / 원문 재검증+승격 정책
- **주요 지표:** 오염 전파율 / 정상 기억 활용률 / 정정 성공률·검증 비용
- **구현 부담:** D3
- **호출 추정:** 사례당·조건당 3–9회. 오염·정상 쌍을 평가하면 2배. 실제 개인정보·비밀·외부 반출 기능은 넣지 않는다.
- **주의:** 정상적인 새 사실과 의도적 오염을 쉽게 구별하도록 정답 표식을 넣지 않는다.
- **확장:** RAG 보안 / 메모리 격리 / 검증된 사실만 쓰기
- **참고:** [P26 AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases](https://proceedings.neurips.cc/paper_files/paper/2024/hash/eb113910e9c3f6242541c1652e30dfd6-Abstract.html), [P22 AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), [P16 LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html)

### A5. 지시 충돌에서 적절히 수행하거나 거절하기

- **문제:** 안전 규칙을 지키면서도 정상적인 요청까지 과도하게 거절하지 않을까?
- **업무:** 서로 다른 출처의 지시·예외가 충돌하는 모의 업무에서 정당한 우선순위를 적용한다.
- **예시:** 인용된 문서 속 요청과 사용자의 실제 요청을 구분하고, 새 사용자 정정은 반영한다.
- **50개 구성:** 정상 요청 10개 / 허용된 예외 10개 / 비신뢰 지시 충돌 10개 / 권한 밖 요청 10개 / 확인하면 수행 가능 10개
- **정답 정보:** 사전에 정의한 출처 우선순위·권한·예외와 정답 행동. 정책은 평가 중 바꾸지 않는다.
- **비교 조건:** 일반 주의문 / 구체적 충돌 처리 규칙 / 처리 규칙+코드 gate
- **주요 지표:** 정책 준수율 / 과잉 거절률 / 정당한 확인 요청률·완료율
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 2–6회. 고정 정책과 모의 도구를 쓰면 대부분 자동 판정 가능하다.
- **주의:** alignment 전체가 아니라 정해진 정책 아래의 행동 준수라는 연구 범위를 명시한다.
- **확장:** 예외 규칙 위치 / 한국어 표현 차이 / 동일 길이 지시문 비교
- **참고:** [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html), [P22 AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352), [P25 Defeating Prompt Injections by Design (CaMeL)](https://arxiv.org/abs/2503.18813)

### A6. 실패를 숨기지 않는 상태 보고

- **문제:** 도구가 실패했을 때 Agent가 결과를 확인하고 '미완료'라고 정확히 보고할까?
- **업무:** 완료·부분 완료·실패를 실제 상태와 대조해 보고하고 확인되지 않은 성공을 주장하지 않는다.
- **예시:** 평가 파일 생성이 실패했는데도 '모두 저장 완료'라고 보고하는지 검사한다.
- **50개 구성:** 완전 성공 10개 / 부분 성공 10개 / 명시적 실패 10개 / 응답 없음 10개 / 예전 결과만 존재 10개
- **정답 정보:** 도구 로그와 파일/DB의 실제 상태, 허용되는 완료·부분·미확인 표현.
- **비교 조건:** 자유 완료 보고 / 결과 확인 checklist / 증거 ID가 필요한 완료 gate
- **주요 지표:** 거짓 완료 보고율 / 상태 분류 Macro-F1 / 불확실성 표시 정확도·검증 호출
- **구현 부담:** D1
- **호출 추정:** 사례당·조건당 2–5회. 파일·DB 상태 검사로 정답 생성이 쉬운 편. 상태 보고의 자연어 변형만 사람이 일부 검토한다.
- **주의:** 불확실하다는 표현만 반복해도 좋은 점수를 받지 않도록 실제 성공·실패 구별을 함께 본다.
- **확장:** 과제 실행 Agent / 실험 자동화 / 로그 기반 감사
- **참고:** [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html)

## Harness와 실행 환경 설계

같은 모델을 어떤 규칙·도구 인터페이스·상태 관리로 감쌀 때 더 잘 작동하는가?

### H1. 짧은 지시 파일과 상세 지시 파일

- **문제:** 설명과 규칙을 많이 제공하면 실제 성공률이 높아질까, 탐색과 비용만 늘어날까?
- **업무:** Agent가 미니 코드 저장소나 문서 폴더의 수정 업무를 서로 다른 지시 파일 아래 수행한다.
- **예시:** 필요한 테스트 명령과 금지 경로만 알려준 경우와 장황한 전체 설명을 제공한 경우를 비교한다.
- **50개 구성:** 일반 수정 10개 / 비표준 실행법 10개 / 프로젝트 제약 10개 / 불필요 설명이 많은 업무 10개 / 규칙 충돌 가능 10개
- **정답 정보:** 숨겨진 기능 검사와 제약 목록. 수정 대상과 정답은 지시 파일에 넣지 않는다.
- **비교 조건:** 지시 파일 없음 / 핵심 규칙만 / 같은 핵심 규칙+상세 설명
- **주요 지표:** 기능 성공률 / 제약 준수율 / 탐색·테스트 호출 수·총 토큰
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–10회. 각 조건에서 저장소를 동일 상태로 reset한다. 파일 길이와 새 정보 추가를 분리하는 후속 실험이 가능하다.
- **주의:** 긴 파일에만 필요한 비밀 정보를 넣으면 길이 효과가 아니라 정보 차이를 측정한다.
- **확장:** 사람 작성/모델 작성 / 제목·목록 구조 / 필수 정보의 위치
- **참고:** [P30 Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://www.sri.inf.ethz.ch/publications/gloaguen2026agentsmd), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html), [P28 Demystifying LLM-Based Software Engineering Agents (Agentless)](https://dl.acm.org/doi/10.1145/3715754)

### H2. 도구 인터페이스와 오류 피드백 설계

- **문제:** 같은 기능을 어떤 형태로 노출해야 Agent가 인자 오류를 줄이고 복구할까?
- **업무:** 동일한 파일 편집·조회 기능을 자유 텍스트, 구조화 schema, 구체적 오류 피드백으로 제공한다.
- **예시:** 필수 path 누락 시 단순 오류와 필드별 설명을 주었을 때 수정 성공을 비교한다.
- **50개 구성:** 필수 필드 10개 / 타입 10개 / 경로·대상 10개 / 잘못된 값 10개 / 복합 인자 10개
- **정답 정보:** 허용 schema, 실제 편집 결과, 재현 가능한 초기 오류. 올바른 값 자체를 오류 메시지로 제공하지 않는다.
- **비교 조건:** 단순 도구 설명 / 명확한 schema·예시 / schema+구조화 오류·수정 제안
- **주요 지표:** 첫 호출 유효율 / 오류 후 복구율 / 오편집률·추가 호출
- **구현 부담:** D1
- **호출 추정:** 사례당·조건당 2–6회. 가벼운 로컬 함수로 구현 가능하다. 실제 편집 도구를 재개발하기보다 작은 안전한 도구를 만든다.
- **주의:** 인터페이스 조건마다 기능이나 권한을 바꾸면 설계 효과를 분리할 수 없다.
- **확장:** 읽기/쓰기 분리 / 오류 메시지 언어 / 필드명 명확성
- **참고:** [P27 SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793), [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html)

### H3. 재시도와 중단 규칙의 최적화

- **문제:** 어디까지 계속 시도하고 언제 중단해야 성공률과 비용의 균형이 좋은가?
- **업무:** Agent가 동일한 업무·오류 환경에서 제한된 호출·시간 예산을 관리한다.
- **예시:** 같은 실패가 반복되면 상태를 남기고 중단하고, 복구 가능한 오류에는 제한된 추가 시도를 한다.
- **50개 구성:** 즉시 성공 10개 / 1회 복구 가능 10개 / 여러 단계 필요 10개 / 반복 실패 10개 / 불가능한 목표 10개
- **정답 정보:** 주입된 오류와 목표 상태, 안전한 중단 기준. 조건별 최대 예산을 사전 고정한다.
- **비교 조건:** 고정 작은 step cap / 고정 큰 step cap / 정체 탐지+적응형 중단
- **주요 지표:** 예산별 성공률 / 낭비 호출·루프 비율 / 안전 중단률·성공 한 건당 비용
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–10회. 큰 예산 조건이 가장 비싸다. 실패를 보고하며 멈추는 경우도 사전 정의된 정답이면 성공으로 분류한다.
- **주의:** 실패한 케이스만 무제한 재시도해서 잘 나온 결과를 선택하지 않는다.
- **확장:** token budget / 오류별 retry 정책 / 시간 제한과 checkpoint
- **참고:** [P13 tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html), [P15 Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html), [P28 Demystifying LLM-Based Software Engineering Agents (Agentless)](https://dl.acm.org/doi/10.1145/3715754)

### H4. 긴 작업에서 context를 관리하는 방식

- **문제:** 전체 이력을 보내는 것보다 최근 이력·요약·구조화 상태가 더 효율적일까?
- **업무:** 여러 단계 작업 중 필요한 규칙과 상태를 유지하면서 다음 행동을 선택한다.
- **예시:** 긴 작업 중 앞서 확인한 금지 경로·완료 항목을 잊지 않고 남은 수정만 수행한다.
- **50개 구성:** 짧은 이력 10개 / 긴 이력 10개 / 중간에 있는 중요 정보 10개 / 정정된 상태 10개 / 도구 출력 잡음 10개
- **정답 정보:** 각 시점의 참 상태와 반드시 유지할 제약. 요약 과정에 정답 정보를 새로 넣지 않는다.
- **비교 조건:** 전체 이력 / 최근 구간+요약 / 최근 구간+구조화 상태표
- **주요 지표:** 상태·제약 유지율 / 최종 성공률 / 입력 토큰·요약 비용
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–10회. 요약을 만드는 추가 호출을 포함한다. 모델 context 한도 밖의 비교는 별도 실패 유형으로 보고한다.
- **주의:** 잘린 정보를 받은 조건과 정보가 모두 있는 조건을 같은 입력이라고 부르지 않는다.
- **확장:** summary 주기 / tool output 압축 / checkpoint와 memory 연결
- **참고:** [P31 Lost in the Middle: How Language Models Use Long Contexts](https://aclanthology.org/2024.tacl-1.9/), [P18 MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html)

### H5. 실행자와 검증자를 분리할 가치

- **문제:** 독립 검증 역할이 오류를 줄이는가, 같은 모델의 오류를 한 번 더 반복하는가?
- **업무:** Agent가 산출물을 만든 후 자체 검사 또는 별도 검증 역할·코드 검사로 오류를 찾아 수정한다.
- **예시:** 모의 설정 파일을 수정한 뒤 형식·기능·금지 변경 검사를 수행한다.
- **50개 구성:** 정상 산출물 10개 / 형식 오류 10개 / 논리 오류 10개 / 누락 10개 / 불필요 변경 10개
- **정답 정보:** 숨겨진 테스트와 알려진 오류 유형. 검증자에게 정답·테스트 결과를 과도하게 노출하지 않는다.
- **비교 조건:** 실행자만 / 실행자 자기 점검 / 같은 모델의 독립 검증 역할+코드 검사
- **주요 지표:** 오류 검출 precision/recall / 수정 후 성공률 / 정상 결과 훼손률·추가 비용
- **구현 부담:** D2
- **호출 추정:** 사례당·조건당 3–9회. 검증자는 별도 호출이므로 비용이 증가한다. 코드 검사 단독 조건을 추가하면 모델 검증의 순이득을 볼 수 있다.
- **주의:** 별도 검증자에만 더 강한 모델·더 많은 토큰을 주면 역할 분리 자체의 효과를 알기 어렵다.
- **확장:** 다른 모델 검증 / 블라인드 검증 / 가짜 성공 감지
- **참고:** [P28 Demystifying LLM-Based Software Engineering Agents (Agentless)](https://dl.acm.org/doi/10.1145/3715754), [P15 Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html), [P29 AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html)

### H6. 중단 후 정확하게 이어가는 Agent

- **문제:** 세션·프로세스가 끊겨도 이미 한 일을 반복하지 않고 목표를 이어갈 수 있을까?
- **업무:** 업무 도중 정해진 지점에서 중단된 뒤 checkpoint·로그를 이용해 안전하게 재개한다.
- **예시:** 3개 파일 중 2개를 저장한 뒤 끊긴 작업에서 남은 1개만 처리한다.
- **50개 구성:** 행동 전 중단 10개 / 성공 직후 중단 10개 / 부분 저장 10개 / 응답 유실 10개 / 재개 시 조건 변경 10개
- **정답 정보:** 중단 전후 파일·DB 상태, 완료된 작업 ID, 중복 금지 조건. 숨겨진 원자적 상태 검사를 둔다.
- **비교 조건:** 대화만 저장 / 자연어 진행 요약 / 구조화 checkpoint+실제 상태 확인
- **주요 지표:** 재개 성공률 / 중복·누락·손상률 / 재개까지 호출·시간
- **구현 부담:** D3
- **호출 추정:** 사례당·조건당 4–12회. snapshot/reset과 장애 주입이 구현 부담이다. 모델 호출보다 상태 일관성 테스트가 어려울 수 있다.
- **주의:** 실제 사용자 작업 폴더를 중단시키지 말고 작은 임시 sandbox에서 수행한다.
- **확장:** 장시간 조사 / 파일 생성 workflow / 정확한 완료 보고
- **참고:** [P12 ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](https://aclanthology.org/2025.findings-naacl.65/), [P27 SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793), [P18 MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)

## 참고자료의 확인 수준

아래에는 34편의 논문과 LLM Wiki 아이디어 자료 1건이 포함됩니다. 학회/저널, 워크숍, preprint, 실무 아이디어를 구분합니다.

### P01. Operational Advice for Dense and Sparse Retrievers: HNSW, Flat, or Inverted Indexes?

- ACL Industry 2025
- [원문](https://aclanthology.org/2025.acl-industry.61/)
- 연결 아이디어: 밀집·희소 검색과 Flat/HNSW의 구축 시간·검색 품질·속도를 비교한다.
- 주의: 동료심사 논문. 특정 언어·구현·하드웨어의 결과를 보편적인 규모 임계값으로 옮기지 않는다.

### P02. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models

- NeurIPS Datasets and Benchmarks 2021
- [원문](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract-round2.html)
- 연결 아이디어: 다양한 검색 태스크와 도메인에서 어휘·신경망 검색을 평가하는 틀이다.
- 주의: 동료심사 논문. 당시 모델 순위를 현재 모델 전체의 성능 순위로 사용하지 않는다.

### P03. FEVER: a Large-scale Dataset for Fact Extraction and VERification

- NAACL 2018
- [원문](https://aclanthology.org/N18-1074/)
- 연결 아이디어: 주장을 지원·반박·정보 부족으로 판정하고 근거 문장을 함께 평가한다.
- 주의: 동료심사 논문. 공개 벤치마크를 그대로 가져오는 것과 직접 평가 사례를 작성하는 것은 다르다.

### P04. Enabling Large Language Models to Generate Text with Citations (ALCE)

- EMNLP 2023
- [원문](https://aclanthology.org/2023.emnlp-main.398/)
- 연결 아이디어: 검색부터 인용을 붙인 답변까지 평가하며 유창성·정확성·인용 품질을 분리한다.
- 주의: 동료심사 논문. 링크가 있다는 것만으로 근거가 맞는 것은 아니며 자동 판정도 검토가 필요하다.

### P05. Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity

- NAACL 2024
- [원문](https://aclanthology.org/2024.naacl-long.389/)
- 연결 아이디어: 작은 LM 분류기로 무검색·단일 검색·반복 검색 전략을 선택한다.
- 주의: 동료심사 논문. 단순 규칙 router를 만들면 논문의 직접 재현이 아니라 아이디어를 차용한 변형이다.

### P06. RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval

- ICLR 2024
- [원문](https://arxiv.org/abs/2401.18059)
- 연결 아이디어: 청크의 군집화와 요약을 반복해 여러 추상화 수준의 검색 트리를 구성한다.
- 주의: 학회 발표 원논문. 요약 구축비와 원문 근거 손실을 따로 측정해야 한다.

### P07. From Local to Global: A GraphRAG Approach to Query-Focused Summarization

- arXiv 2024, 후속 개정
- [원문](https://arxiv.org/abs/2404.16130)
- 연결 아이디어: 엔티티 그래프와 커뮤니티 요약을 통해 문서 집합 전체를 종합하는 질문을 다룬다.
- 주의: 저자 원논문. 확인 자료는 arXiv이며, 단일 사실 검색을 항상 개선한다는 주장으로 확대하지 않는다.

### P08. LightRAG: Simple and Fast Retrieval-Augmented Generation

- Findings of EMNLP 2025
- [원문](https://aclanthology.org/2025.findings-emnlp.568/)
- 연결 아이디어: 그래프·벡터, 저수준·고수준 검색, 증분 갱신을 결합한다.
- 주의: 동료심사 논문. 이름만으로 현재 한국어 환경의 비용 우위를 가정하지 않는다.

### P09. Balancing the Blend: An Experimental Analysis of Trade-Offs in Hybrid Search

- PVLDB 19(8), 2026
- [원문](https://dl.acm.org/doi/abs/10.14778/3811243.3811246)
- 연결 아이디어: 여러 검색 표현과 결합·재순위화의 품질·자원 trade-off를 비교한다.
- 주의: 출판사 초록·서지정보 확인. 이번 조사에서 세부 결과표와 코드를 재현한 것은 아니다.

### P10. BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms

- arXiv preprint, 2026-07
- [원문](https://arxiv.org/abs/2607.26497)
- 연결 아이디어: 질문과 핵심 근거를 유지하며 중첩 코퍼스 규모를 바꿔 정확도·구축·질의 비용을 비교한다.
- 주의: 최근 preprint. 제목을 보편적 결론으로 인용하지 말고 실험 설계의 참고로 삼는다.

### P11. ReAct: Synergizing Reasoning and Acting in Language Models

- ICLR 2023
- [원문](https://react-lm.github.io/)
- 연결 아이디어: 행동과 관찰을 반복하며 계획을 수정하는 Agent 접근이다.
- 주의: 저자 프로젝트·원논문. 외부에 출력된 설명은 내부 추론을 완전히 보여주는 증거가 아니다.

### P12. ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities

- Findings of NAACL 2025
- [원문](https://aclanthology.org/2025.findings-naacl.65/)
- 연결 아이디어: 도구 간 상태 의존성, 정보 부족, 중간·최종 milestone을 평가한다.
- 주의: 동료심사 논문. 유효한 여러 행동 경로를 단일 정답 순서로 축소하지 않는다.

### P13. tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains

- ICLR 2025
- [원문](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b126cc38b8638e07bef37e7b2bb72bf-Abstract-Conference.html)
- 연결 아이디어: 도메인 규정과 대화를 포함한 업무를 최종 DB 상태로 평가하고 반복 성공의 신뢰성을 본다.
- 주의: 동료심사 논문. pass^k는 k번 중 한 번 성공인 pass@k와 구분한다.

### P14. WebArena: A Realistic Web Environment for Building Autonomous Agents

- ICLR 2024
- [원문](https://arxiv.org/abs/2307.13854)
- 연결 아이디어: 재현 가능한 웹 환경에서 실제 업무의 기능적 완료를 평가한다.
- 주의: 학회 발표 원논문. 전체 환경 복제는 무거우므로 미니 실험은 축소 버전임을 명시한다.

### P15. Reflexion: Language Agents with Verbal Reinforcement Learning

- NeurIPS 2023
- [원문](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract.html)
- 연결 아이디어: 피드백을 텍스트 기억으로 남겨 이후 시도의 행동을 개선한다.
- 주의: 동료심사 논문. 모델 가중치 학습과 다르며 재시도·추가 토큰 예산을 공정하게 맞춘다.

### P16. LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory

- ICLR 2025
- [원문](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html)
- 연결 아이디어: 정보 추출, 세션 간 추론, 시간 추론, 지식 갱신, 답변 보류를 분리해 평가한다.
- 주의: 동료심사 논문. 정적 사실 회상 점수만으로 장기 기억 전체를 평가하지 않는다.

### P17. Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo)

- ACL 2024
- [원문](https://aclanthology.org/2024.acl-long.747/)
- 연결 아이디어: 긴 다중 세션 대화에서 QA, 사건 요약, 시간·인과 관계를 평가한다.
- 주의: 동료심사 논문. 대화·사용자 단위 분할과 일관된 gold timeline이 중요하다.

### P18. MemGPT: Towards LLMs as Operating Systems

- arXiv 2023
- [원문](https://arxiv.org/abs/2310.08560)
- 연결 아이디어: 제한된 context와 외부 저장 계층 사이에서 정보를 이동시키는 메모리 관리를 제안한다.
- 주의: 저자 원논문. 외부 메모리가 모델의 실제 context window를 무한하게 만드는 것은 아니다.

### P19. MemoryBank: Enhancing Large Language Models with Long-Term Memory

- AAAI 2024
- [원문](https://ojs.aaai.org/index.php/AAAI/article/view/29946)
- 연결 아이디어: 기억 검색·갱신과 시간·중요도를 이용한 보존·망각을 다룬다.
- 주의: 동료심사 논문. 학기 과제에서는 실제 민감 대화보다 합성 업무·선호 이력으로 구현한다.

### P20. A-Mem: Agentic Memory for LLM Agents

- NeurIPS 2025
- [원문](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html)
- 연결 아이디어: 구조화된 기억 노트를 동적으로 연결하고 새 정보에 따라 갱신한다.
- 주의: 동료심사 논문. 연결 생성과 갱신에 필요한 호출·토큰도 비용에 포함한다.

### P21. Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory

- arXiv preprint 2025
- [원문](https://arxiv.org/abs/2504.19413)
- 연결 아이디어: 대화에서 정보를 추출·통합·검색하고 전체 context 대비 품질·효율을 비교한다.
- 주의: 시스템 개발자 원논문. 저자 보고 성능이며 독립 재현이나 다른 데이터의 우위를 보장하지 않는다.

### P22. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents

- NeurIPS Datasets and Benchmarks 2024
- [원문](https://arxiv.org/abs/2406.13352)
- 연결 아이디어: 비신뢰 도구 결과를 읽는 Agent에서 정상 업무와 공격·방어를 함께 평가한다.
- 주의: 동료심사 연구. 공격이 없는 업무 성공률을 반드시 같이 측정한다.

### P23. InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents

- Findings of ACL 2024
- [원문](https://aclanthology.org/2024.findings-acl.624/)
- 연결 아이디어: 외부 콘텐츠에 삽입된 지시가 도구 사용 Agent를 어떻게 교란하는지 평가한다.
- 주의: 동료심사 논문. 이 과제의 변형은 가짜 데이터와 격리된 도구로만 구성한다.

### P24. AgentHarm: A Benchmark for Measuring Harmfulness of LLM Agents

- ICLR 2025
- [원문](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c493d23af93118975cdbc32cbe7323f5-Abstract-Conference.html)
- 연결 아이디어: 거절 문구만이 아니라 여러 단계의 유해 행동 수행 여부도 평가한다.
- 주의: 동료심사 논문. 위험 태스크 자체를 구현하지 않고 무해한 권한 위반 대리 과제로 축소할 수 있다.

### P25. Defeating Prompt Injections by Design (CaMeL)

- arXiv 2025
- [원문](https://arxiv.org/abs/2503.18813)
- 연결 아이디어: 신뢰된 제어 흐름과 비신뢰 데이터 흐름을 분리하고 capability 기반 정책을 적용한다.
- 주의: 저자 연구 설계. 간단한 필터를 만든 것으로 논문의 보안 보장이나 완전 재현을 주장하지 않는다.

### P26. AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases

- NeurIPS 2024
- [원문](https://proceedings.neurips.cc/paper_files/paper/2024/hash/eb113910e9c3f6242541c1652e30dfd6-Abstract.html)
- 연결 아이디어: 메모리·지식베이스를 통한 Agent 오염 위험을 연구한다.
- 주의: 동료심사 논문. 후보 설계는 공격 최적화가 아니라 무해한 오염 정보의 검증·출처 방어 평가에 한정한다.

### P27. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering

- NeurIPS 2024
- [원문](https://arxiv.org/abs/2405.15793)
- 연결 아이디어: Agent가 사용하는 도구 인터페이스와 피드백 형식이 코딩 업무 수행에 미치는 영향을 연구한다.
- 주의: 학회 발표 원논문. 동일 모델에서도 인터페이스가 실험 변수임을 보여주는 연결 자료다.

### P28. Demystifying LLM-Based Software Engineering Agents (Agentless)

- PACMSE / FSE 2025
- [원문](https://dl.acm.org/doi/10.1145/3715754)
- 연결 아이디어: 자율적인 장기 루프와 대조되는 단순한 위치 탐색·수정·검증 파이프라인을 제안한다.
- 주의: 동료심사 논문. 해당 코딩 설정의 결과를 모든 업무에서 Agent가 불필요하다는 주장으로 확대하지 않는다.

### P29. AgentIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios

- NeurIPS Datasets and Benchmarks 2025
- [원문](https://proceedings.neurips.cc/paper_files/paper/2025/hash/51bb3a8a33610a25aae074bfc51b1b1f-Abstract-Datasets_and_Benchmarks_Track.html)
- 연결 아이디어: 복잡한 Agent 지시의 개별 제약을 코드·모델·혼합 평가로 측정한다.
- 주의: 동료심사 논문. 지시 파일 길이와 제약 정보량을 구분해야 한다.

### P30. Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?

- MemAgents @ ICLR 2026 워크숍 / arXiv
- [원문](https://www.sri.inf.ethz.ch/publications/gloaguen2026agentsmd)
- 연결 아이디어: 저장소 지시 파일 유무가 코딩 성공과 추론 비용에 주는 영향을 평가한다.
- 주의: 저자 연구실·원문 확인. ICLR 본회의 논문으로 부르지 않는다. 모든 지시 파일이 나쁘다는 일반 법칙은 아니다.

### P31. Lost in the Middle: How Language Models Use Long Contexts

- TACL 2024
- [원문](https://aclanthology.org/2024.tacl-1.9/)
- 연결 아이디어: 같은 관련 정보도 긴 context 안의 위치에 따라 활용 성능이 달라질 수 있음을 평가한다.
- 주의: 동료심사 논문. 최신 모델과 Agent 실행 환경에서는 별도 검증할 가설이다.

### P32. MIRACL: A Multilingual Retrieval Dataset Covering 18 Diverse Languages

- TACL 2023
- [원문](https://aclanthology.org/2023.tacl-1.63/)
- 연결 아이디어: 다양한 언어의 질의와 사람이 판정한 문서 관련성으로 검색을 평가한다.
- 주의: 동료심사 데이터 논문. 기존 데이터는 참고·외부 검증용이며 직접 작성 50개 조건을 대체하지 않는다.

### P33. OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations

- CVPR 2025
- [원문](https://openaccess.thecvf.com/content/CVPR2025/html/Ouyang_OmniDocBench_Benchmarking_Diverse_PDF_Document_Parsing_with_Comprehensive_Annotations_CVPR_2025_paper.html)
- 연결 아이디어: 다양한 문서 형식과 레이아웃에서 파싱 품질을 평가한다.
- 주의: 동료심사 논문. 원문 추출 품질과 후속 검색·답변 품질을 구분할 근거다.

### P34. TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance

- ACL 2021
- [원문](https://aclanthology.org/2021.acl-long.254/)
- 연결 아이디어: 본문과 표를 함께 사용하고 수치 연산이 필요한 QA를 평가한다.
- 주의: 동료심사 논문. 금액·단위·기간 및 연산 정답을 갖춘 자체 사례 설계에 참고한다.

### I01. LLM Wiki

- Karpathy의 아이디어 문서, 2026
- [원문](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- 연결 아이디어: 원본과 별도로 LLM이 연결된 Wiki를 정리·갱신하는 운영 패턴이다.
- 주의: 논문이 아니라 실무 아이디어. Wiki 생성 비용·왜곡·출처와 갱신 비용까지 연구 대상으로 삼는다.
