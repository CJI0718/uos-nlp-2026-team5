# 기존 DOCX와 이번 확장 문헌의 연결표

[연구 지도](./팩트체크_연구지도.md) · [추가 56편 카탈로그](./문헌_용도별_카탈로그.md)

출발 자료는 `factcheck_literature_review_ko.docx`다. 아래 P01–P25는 **DOCX 핵심 목록을 이어받은 번호**다. 일부 제목은 읽기 쉽게 약칭으로 표시했다. 이번 작업에서 25편 모두를 다시 원문 정독한 것은 아니며, 이 표는 DOCX 내용과 새 카탈로그의 연결을 위한 것이다. 원문 확인 범위에 대한 DOCX의 설명을 우리의 이번 읽기 범위로 바꿔 쓰지 않았다.

## 핵심 25편

| 기존 ID | 문헌·연도·원문 | 기존 용도 | 이번에 함께 읽을 문헌/설계 |
|---|---|---|---|
| P01 | [FEVER Symmetric / Towards Debiasing Fact Verification Models](https://aclanthology.org/D19-1341/) · 2019 | 근거를 무시하는 편향과 대조 평가 | E06 CrossAug; E07–E11 편향·행동 진단 |
| P02 | [VitaminC / Get Your Vitamin C! Robust Fact Verification with Contrastive Evidence](https://aclanthology.org/2021.naacl-main.52/) · 2021 | 변경 근거에 민감하게 반응하는 검증 | E06 CrossAug; E45 FaithEval; E47 지식 충돌 |
| P03 | [Synthetic Disinformation Attacks on Automated Fact Verification Systems](https://ojs.aaai.org/index.php/AAAI/article/download/21302/21051) · 2022 | 근거 오염에 따른 검증 오류 | E44–E48 충돌·보류·누출 구분 |
| P04 | [Fact2Fiction](https://ojs.aaai.org/index.php/AAAI/article/view/40353) · AAAI 2026 | 팩트체크 Agent의 오염 근거 취약성 | E22 충분성; E46 충돌 분류; 로컬 방어적 평가 |
| P05 | [Trusting Your Evidence / Context-aware Decoding](https://aclanthology.org/2024.naacl-short.69/) · 2024 | 모델 기억과 문맥의 우선순위 | E45 FaithEval; E47 Entity-Based Knowledge Conflicts |
| P06 | [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/html/2005.11401) · 2020 | retrieval과 generation의 결합 | E12–E19 검색 baseline; E20–E25 제어 비교 |
| P07 | [ReAct: Synergizing Reasoning and Acting in Language Models](https://react-lm.github.io/) · 2023 | 관측에 따른 추론·행동 반복 | E21 QACheck; E22 종료·충분성; E24 고정 검증 비교군 |
| P08 | [LLatrieval](https://aclanthology.org/2024.naacl-long.305/) · 2024 | 반복 검색과 retrieval 개선 | E20 Adaptive-RAG; E22 Sufficient Context; E25 uncertainty 비교 |
| P09 | [Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions (IRCoT)](https://aclanthology.org/2023.acl-long.557/) · 2023 | 다단계 추론과 retrieval 결합 | E21 QACheck; E19 간접 근거 검색 |
| P10 | [DEFAME: Dynamic Evidence-based FAct-checking with Multimodal Experts](https://proceedings.mlr.press/v267/braun25b.html) · 2025 | 멀티모달 도구를 이용하는 팩트체크 | E49–E56 차트·OOC·multimodal 평가 |
| P11 | [Trafilatura](https://aclanthology.org/2021.acl-demo.15/) · 2021 | 웹 본문 추출·정제 | parser 단계는 고정하고 E12–E19 검색 효과와 분리 |
| P12 | [Document-level Claim Extraction and Decontextualisation for Fact-Checking](https://aclanthology.org/2024.acl-long.645/) · 2024 | 기사에서 검증할 주장과 맥락 추출 | E01 Claimify; E02 FEVERFact; E04–E05 분해 진단 |
| P13 | [Decontextualization: Making Sentences Stand-Alone](https://aclanthology.org/2021.tacl-1.27/) · 2021 | 대명사·생략을 풀어 독립 문장으로 변환 | E01 Claimify; 원문 span·추가 정보 구분 |
| P14 | [Generating Literal and Implied Subquestions to Fact-check Complex Claims (ClaimDecomp)](https://aclanthology.org/2022.emnlp-main.229/) · 2022 | 복합 주장을 검증 가능한 하위 질문으로 분해 | E05 분해의 상충; E21 QACheck; E26 시점 통제 |
| P15 | [FactLens: Benchmarking Fine-Grained Fact Verification](https://aclanthology.org/2025.findings-acl.929/) · 2025 | 세부 사실 검증과 분해 품질 | E04 A Closer Look; E40 RefChecker |
| P16 | [The Missing Parts: Augmenting Fact Verification with Half Truth Detection (TRACER)](https://aclanthology.org/2025.emnlp-main.1724/) · 2025 | 누락된 맥락과 반쪽 진실 | E01·E05 추출 손실; E22 충분성; 라벨 정의를 단순화하지 않기 |
| P17 | [Dense X Retrieval](https://aclanthology.org/2024.emnlp-main.845/) · 2024 | retrieval 단위·granularity 비교 | E12 BEIR; E16 BGE-M3; 총 token budget 통제 |
| P18 | [Evidence Retrieval for Fact Verification using Multi-stage Reranking](https://aclanthology.org/2024.findings-emnlp.428/) · 2024 | 다단계 근거 재순위화 | E19 CFR; 검색과 최종 판정 metric 분리 |
| P19 | [Fathom: A Fast and Modular RAG Pipeline for Fact-Checking](https://aclanthology.org/2025.fever-1.20/) · 2025 | 빠른 모듈형 고정 RAG baseline | E20–E25 적응 전략과 강한 고정 workflow 비교 |
| P20 | [FEVER: a Large-scale Dataset for Fact Extraction and VERification](https://aclanthology.org/N18-1074/) · 2018 | 근거 검색·지원/반박/NEI 데이터 | E06·E10 대조 데이터; E12 검색 평가 |
| P21 | [AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web](https://proceedings.neurips.cc/paper_files/paper/2023/hash/cd86a30526cd1aff61d6f89f107634e4-Abstract-Datasets_and_Benchmarks.html) · 2023 | 실세계 주장·웹 근거·하위 QA | E19 CFR; E26 시간 통제; E48 leakage |
| P22 | [The Automated Verification of Textual Claims (AVeriTeC) Shared Task](https://aclanthology.org/2024.fever-1.1/) · 2024 | 공통 평가·재현 조건 | 평가 스크립트 버전 고정; E22 충분성 진단 추가 |
| P23 | [The 2nd Automated Verification of Textual Claims (AVeriTeC) Shared Task](https://aclanthology.org/2025.fever-1.15/) · 2025 | 재현성·효율·open-weights 설정 | 2024와 metric/지식베이스 조건을 자동 동일시하지 않기 |
| P24 | [Enabling Large Language Models to Generate Text with Citations (ALCE)](https://aclanthology.org/2023.emnlp-main.398/) · 2023 | 생성 문장과 citation 평가 | E37 Evidence Attribution; E38 RARR; E41 CiteME |
| P25 | [FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation](https://aclanthology.org/2023.emnlp-main.741/) · 2023 | 원자 사실 단위의 생성물 평가 | E04 DecompScore; E35 KorFactScore; E40 RefChecker |

## DOCX의 확장 읽기 4편

이 네 편도 이미 DOCX에 있으므로 이번 “추가 56편”에 다시 세지 않았다.

| 문헌 | 원문 | 연결 용도 |
|---|---|---|
| Self-RAG | [공식 프로젝트](https://selfrag.github.io/) | retrieval/생성의 비판 학습과 E20–E25의 적응 제어 비교 |
| Late Chunking | [arXiv v3](https://arxiv.org/html/2409.04701v3) | embedding 전·후 chunking과 E16의 긴 문맥 표현 비교 |
| PoisonedRAG | [USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/zou-poisonedrag) | 오염된 근거에 대한 로컬 방어적 평가; 공격 실행은 범위 밖 |
| ADMIT | [arXiv](https://arxiv.org/abs/2510.13842) | 팩트체크 오염 평가의 확장 후보; 전문·게재 상태 재확인 필요 |

## 기존 팀 저장소 35개 자료의 재사용


| 기존 자료 | 연결 위치 |
|---|---|
| Guo et al. 자동 팩트체크 survey | 전체 task 정의·분류 입문 |
| FEVEROUS, HoVer, TabFact, SciFact | 구조화 근거·multi-hop·도메인별 데이터 |
| ProgramFC, FOLK, FactAgent, FIRE | 프로그램 기반/Agent 기반 비교군 |
| EMULATE, LoCal, FactSearch | multi-agent·도구 제어 확장; 기본 실험에 모두 넣을 필요 없음 |
| HerO 2, Fathom, multi-stage reranking | 강한 고정 workflow·효율 baseline |
| QuanTemp, Time Matters, ChronoFact, TSVer | 시점·수치·시계열 근거 검증 |
| SAFE, Ev2R, ALCE | 사실성·근거 검색·인용 평가 |
| 한국어 대선 토론 RAG, 한국어 대조학습 연구, 한국어 주장 판별 학위논문, KoSimpleQA | 국내 맥락·한국어 자료·언어별 성능 |
| AVerImaTeC, Selective Multimodal Retrieval | 뉴스 이미지와 텍스트·모달 선택 확장 |

위 자료의 구체적 서지와 링크는 기존 JSON을 따른다. DOCX 25편·확장 4편·저장소 35개는 **서로 중복되므로 단순 합산하지 않는다.** 이번 E01–E56은 이 핵심 목록들에 추가한 고유 논문 목록이다.

## 정정하거나 구별해 유지할 내용

1. **CrossAug를 추가해 2×2 설계의 선행연구를 강화했다.** FEVER Symmetric·VitaminC만으로 신규성을 판단하지 않는다.
2. **주장 분해는 평가기 자체의 오차 원인이다.** FActScore류 점수를 생성 모델의 사실성만으로 해석하지 않는다.
3. **Half truth·충분성·NEI·보류는 같은 라벨이 아니다.** TRACER 등에서 가져온 label schema를 다른 benchmark에 그대로 붙이지 않는다.
4. **고정 evidence store는 ReAct와 양립한다.** Agent는 고정 저장소 안에서도 쿼리·순서·종료를 선택할 수 있다.
5. **AVeriTeC 연도별 평가 조건은 별도 확인한다.** DOCX에 있는 threshold나 metric 세부를 새 실험에 적용할 때는 해당 연도 공식 코드/버전을 확인한다. 이번에는 이 숫자들을 새 실험의 고정값으로 채택하지 않았다.
6. **DOCX의 PR 상태는 스냅샷이다.** 이를 현재 main 합의나 확정 연구 설계로 취급하지 않는다.
