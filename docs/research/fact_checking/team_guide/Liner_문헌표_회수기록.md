# Liner Scholar 문헌표 회수 기록

- 조사일: 2026-10-28
- 별도 Scholar 대화: [팩트체크 Agent 문헌 확장 2026-10-28](https://scholar.liner.com/)
- 사용자 연구 요청 전송: **1회**. 추가 질문·재생성·재요청: **0회**.
- 결과: **30편 문헌표 생성은 확인·회수 완료. 최종 장문 보고서 생성은 “일시적인 오류가 발생했어요”로 중단.** 따라서 Liner 전체 응답 성공으로 표시하지 않는다.
- 표시 크레딧: **2,125 → 2,025 (100 감소)**. 내부 검색·표 생성·오류 단계별 과금 내역은 확인하지 못했다.
- 표의 Markdown 내보내기는 업그레이드 안내를 표시했고 파일 다운로드가 되지 않았다. 결제하지 않고 브라우저에 이미 표시된 표 본문과 30개 원문 링크를 읽어 보존했다.
- 기존 다른 연구 대화는 수정하지 않았다. 이 작업 중 생긴 완료 확인 예약은 삭제 확인했다.

## 사용 전 주의

아래는 **Liner가 만든 표의 화면 텍스트**다. 로컬 검토와 구별해 보존했으며 정답으로 취급하지 않는다. 최종 카탈로그는 논문 원문을 대조한 별도 문서다.

확인한 정정:

1. BEIR의 저자는 Thakur et al.이다. 아래의 Johnston 표기는 원문과 다르다.
2. BEIR에 팩트체크 태스크가 없다는 표의 설명은 부정확하다. FEVER·Climate-FEVER·SciFact 등을 포함한다.
3. FaVIQ는 정식 ACL 2022, ColBERTv2는 NAACL 2022, HyDE는 ACL 2023, Complex Claim Verification은 NAACL 2024다. 표는 일부 항목에서 최초 preprint 날짜를 노출한다.
4. Decomposition Dilemmas는 arXiv 서지에 NAACL 2025 Main으로 표시된다. A Closer Look은 *SEM 2024다.
5. ‘수백 ms’, ‘최초’, ‘매우 낮은 비용’, 가정에 대한 단정 등은 그대로 채택하지 않았다. 우리의 비용은 실제 시스템에서 측정해야 한다.
6. 논문표의 30편은 모두 추가 문헌 카탈로그에 포함하되, Exa와 겹치는 후보는 중복 계산하지 않았다.

## 표에서 회수한 원문 링크

1. [A Closer Look at Claim Decomposition](https://arxiv.org/abs/2403.11903)
2. [Decomposition Dilemmas: Does Claim Decomposition Boost or Burden Fact-Checking Performance?](https://arxiv.org/abs/2411.02400)
3. [Complex Claim Verification with Evidence Retrieved in the Wild](https://arxiv.org/abs/2305.11859)
4. [Annotation Artifacts in Natural Language Inference Data](http://aclweb.org/anthology/N18-2017)
5. [Hypothesis Only Baselines in Natural Language Inference](http://aclweb.org/anthology/S18-2023)
6. [Counterfactual Debiasing for Fact Verification](https://aclanthology.org/2023.acl-long.374)
7. [FaVIQ: FAct Verification from Information-seeking Questions](https://aclanthology.org/2022.acl-long.354)
8. [ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction](https://aclanthology.org/2022.naacl-main.272)
9. [BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information  Retrieval Models](https://arxiv.org/abs/2104.08663)
10. [Unsupervised Dense Information Retrieval with Contrastive Learning](https://arxiv.org/abs/2112.09118)
11. [Precise Zero-Shot Dense Retrieval without Relevance Labels](https://aclanthology.org/2023.acl-long.99)
12. [Contrastive Learning to Improve Retrieval for Real-World Fact Checking](https://arxiv.org/abs/2410.04657)
13. [Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity](https://arxiv.org/abs/2403.14403)
14. [Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884)
15. [Chain-of-Verification Reduces Hallucination in Large Language Models](https://arxiv.org/abs/2309.11495)
16. [Adaptive Retrieval Without Self-Knowledge? Bringing Uncertainty Back Home](https://arxiv.org/abs/2501.12835)
17. [FinQA: A Dataset of Numerical Reasoning over Financial Data](https://aclanthology.org/2021.emnlp-main.300)
18. [Time-Aware Language Models as Temporal Knowledge Bases](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00459/110012/Time-Aware-Language-Models-as-Temporal-Knowledge)
19. [FreshLLMs: Refreshing Large Language Models with Search Engine Augmentation](https://arxiv.org/abs/2310.03214)
20. [X-Fact: A New Benchmark Dataset for Multilingual Fact Checking](https://aclanthology.org/2021.acl-short.86)
21. [KorQuAD1.0: Korean QA Dataset for Machine Reading Comprehension](https://arxiv.org/abs/1909.07005)
22. [CiteME: Can Language Models Accurately Cite Scientific Claims?](https://arxiv.org/abs/2407.12861)
23. [AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions](https://arxiv.org/abs/2506.09038)
24. [Detecting hallucinations in large language models using semantic entropy](https://www.nature.com/articles/s41586-024-07421-0)
25. [Knowledge Conflicts for LLMs: A Survey](https://arxiv.org/abs/2403.08319)
26. [Entity-Based Knowledge Conflicts in Question Answering](https://aclanthology.org/2021.emnlp-main.565)
27. [No Hindsight for LLM Fact-Checkers: Measuring Leakage Channels in Misinformation Detection](https://arxiv.org/abs/2610.04888)
28. [ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning](https://arxiv.org/abs/2203.10244)
29. [COSMOS: Catching Out-of-Context Image Misuse Using Self-Supervised Learning](https://ojs.aaai.org/index.php/AAAI/article/view/26648)
30. [VeriTaS: The First Dynamic Benchmark for Multimodal Automated Fact-Checking](https://arxiv.org/abs/2601.08611)

## 회수한 표 본문 — 미교정 원자료

```text
자동 팩트체크 시스템을 위한 주장 분해와 검색 기반 검증 연구
Untitled

필터

관련순

AI로 열 추가하기

공유하기

내보내기



논문 (30)



이 논문이 사용된 이유



키워드



팀 파이프라인 활용 위치



구현 난도·비용



핵심 한계






A Closer Look at Claim Decomposition

Wanner et al.

arXiv (Cornell University)

2024-03-18

인용 수 37

PDF 열기



LLM 기반 주장 분해 방식이 FActScore류 평가 점수를 좌우함을 보이고, 분해 품질 자체를 측정하는 DecompScore와 논리원자론·신오데이비드语义 기반 분해기를 제안해 기존 분해기보다 품질을 높였다.


claim decomposition
DecompScore
FActScore


주장 분해 단계(1)의 품질 진단 도구로, 분해기 선정·오류 추적에 사용



낮음: 프롬프트 기반 분해 + 메트릭 계산만으로 재현 가능



영어 위키피디아 중심 평가라 한국어 적용 시 기준 재정의 필요





Decomposition Dilemmas: Does Claim Decomposition Boost or Burden Fact-Checking Performance?

Hu et al.

arXiv (Cornell University)

2024-10-17

인용 수 25

PDF 열기



Decompose-Then-Verify 패러다임에서 분해가 정확도 향상과 노이즈 유입을 동시에 일으키는 트레이드오프를 오류 유형 분류로 실증해 분해 도입 여부의 판단 기준을 제시했다.


decompose-then-verify
error taxonomy
trade-off


분해 도입 여부 결정과 오류 사례 분류 체계로 활용



낮음: 기존 파이프라인에 오류 분석 코드만 추가



영어 데이터셋 중심, 한국어 오염 사례에 대한 외삽은 미검증





Complex Claim Verification with Evidence Retrieved in the Wild

Chen et al.

arXiv (Cornell University)

2023-05-19

인용 수 118

PDF 열기



주장 제시 시점 이전 문서로만 검색을 제한한 최초의 완전 자동 실전 팩트체크 파이프라인(분해→검색→요약→판정)을 제시하고, ClaimDecomp 정치 주장에서 근거 요약의 신뢰성을 사람 평가로 확인했다.


real-world claims
temporal restriction
evidence retrieval


시간누출 통제 설계의 직접적 참조: 검색 인덱스에 주장 시점 필터 적용



중간: 시점 제한 검색 인덱스 구축 필요



영어 정치 주장 중심, 근거 요약 품질이 검색 품질에 의존





Annotation Artifacts in Natural Language Inference Data

Gururangan et al.

ArXiv

2018-03-06

인용 수 1,196

PDF 열기



가설(hypothesis)만 보고 라벨을 맞추는 분류기가 SNLI 67%, MultiNLI 53%에 도달함을 보여 NLI 데이터셋의 주석 아티팩트를 최초로 체계화했다.


annotation artifacts
hypothesis-only
NLI


c0/c1×e0/e1 최소대조 평가의 이론적 근거: claim-only 기준선 설계



매우 낮음: claim-only 분류기 학습만 필요



2018년 크라우드소싱 데이터 기준이라 LLM 시대 아티팩트와는 양상 다름





Hypothesis Only Baselines in Natural Language Inference

Poliak et al.

ArXiv

2018-05-02

인용 수 589

PDF 열기



10개 NLI 데이터셋에서 가설-only 기준선이 다수 클래스 기준선을 유의미하게 상회함을 보여 부분 입력 기준선을 데이터셋 진단 도구로 정립했다.


hypothesis-only baseline
partial-input
NLI diagnosis


근거 무시 shortcut 진단: e0 없이 c만으로 판정하는 기준선 구축



매우 낮음



부분 입력 기준선의 실패가 아티팩트 부재를 보장하지 않음(후속 연구 존재)





Counterfactual Debiasing for Fact Verification

Xu et al.

Annual Meeting of the Association for Computational Linguistics (ACL)

2023-01-01

인용 수 33

PDF 열기



추론 시점에 claim-only 모델의 출력을 claim-근거 융합 모델 출력에서 빼는, 데이터 증강 불필요한 counterfactual 디바이싱(CLEVER)으로 여러 검증 데이터셋의 편향을 완화했다.


counterfactual debiasing
CLEVER
claim-only bias


판정 모듈의 claim-only 바이어스 보정 기법 후보



중간: 두 모델(융합·claim-only) 학습 필요



두 모델의 오차가 독립이라는 가정에 의존, LLM 시대 재검증 필요





FaVIQ: FAct Verification from Information-seeking Questions

Park et al.

Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)

2021-07-05

인용 수 46

PDF 열기



정보탐색 질문의 모호성에서 자동으로 참/거짓 주장 쌍 188k를 구축해 어휘 편향이 적고 근거 전체 이해가 필요한 현실적 검증 벤치마크를 만들었고, FEVER 학습 모델보다 최대 17% 우위를 보였다.


FaVIQ
claim pairs
lexical bias


c0/c1 대조 주장 쌍 구축 방법론의 직접 참조(질문→주장 변환)



중간: 한국어 질문 데이터로 재구축 시 어노테이션 비용 발생



영어 위키피디아 근거 중심, 한국어 변환 시 모호성 통제 재설계 필요





ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction

Santhanam et al.

Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies

2021-12-02

인용 수 638

PDF 열기



잔차 압축과 디노이즈 감독으로 late interaction 검색의 저장 부담을 6-10배 줄이면서 도메인 내외에서 SOTA 품질을 달성했다.


late interaction
ColBERTv2
multi-vector retrieval


근거 검색(3)의 late-interaction 후보: 토큰 수준 정밀 매칭



중간: PLAID 엔진 사용 시 CPU로도 수백 ms 이내 서빙 가능



영어 중심 학습, 한국어는 다국어 버전(mColBERT 등) 필요





BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information\n Retrieval Models

Johnston

arXiv (Cornell University)

2021-04-17

인용 수 101

PDF 열기



18개 이질적 도메인·태스크에서 lexical/dense/late-interaction/reranking 검색기를 제로샷 비교해 BM25가 여전히 강건한 기준선임을 입증했다.


BEIR
zero-shot IR
BM25 baseline


검색기 선택의 표준 평가 프로토콜: 도메인 외 일반화 측정



낮음: 공개 코드·리더보드로 재현 용이



한국어 포함 여부는 개별 서브셋 확인 필요, 팩트체크 특화 태스크 부재





Unsupervised Dense Information Retrieval with Contrastive Learning

Izacard et al.

arXiv (Cornell University)

2021-12-16

인용 수 1,276

PDF 열기



라벨 없는 대조학습만으로 BEIR 15개 중 11개에서 BM25를 능가하는 dense retriever를 학습했고, 다국어·교차언어 검색에서도 강한 성능을 보였다.


Contriever
unsupervised dense retrieval
contrastive learning


한국어 근거 검색의 비지도 백본 후보(한국어 파인튜닝 없이 시작)



낮음: 공개 체크포인트 사용



한국어 이탈리아어 등 저자원 언어에서는 도메인 적응 필요





Precise Zero-Shot Dense Retrieval without Relevance Labels

Gao et al.

arXiv (Cornell University)

2022-12-20

인용 수 564

PDF 열기



가상 문서를 생성해 임베딩한 뒤 실제 코퍼스에 정착시키는 제로샷 검색(HyDE)으로 Contriever를 능가하고 한국어(ko) 포함 다국어에서 강한 성능을 보였다.


HyDE
zero-shot retrieval
query expansion


질문 분해 후 검색쿼리 확장 기법: 분해된 질문→가상 근거 문서 생성



낮음: LLM 1회 호출 + 임베딩, 라벨 불필요



생성 문서의 환각이 검색 품질을 저해할 수 있음, 도메인 특화 쿼리에선 이득 제한





Contrastive Learning to Improve Retrieval for Real-World Fact Checking

Sriram et al.

arXiv (Cornell University)

2024-10-07

인용 수 4

PDF 열기



AVeriTeC의 하위질문-답을 감독신호로 Contriever를 파인튜닝한 팩트체크 특화 재순위기(CFR)로 종단 veracity 정확도를 6% 개선하고 FEVER·ClaimDecomp로 전이되는 이득을 확인했다.


fact-checking retrieval
reranker
AVeriTeC


근거 재순위화(3)의 최우선 참조: 암묵적 관련성(백신 개발 문서↔성분 주장) 학습



중간: GPT-4 증류 신호 생성 비용(또는 오픈 모델 대체)



AVeriTeC(영어) 학습 기반이라 한국어 재순위기는 별도 감독 필요





Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity

Jeong et al.

arXiv (Cornell University)

2024-03-21

인용 수 383

PDF 열기



질문 복잡도 분류기(소형 LM)로 검색 없음/한 번/반복 검색 전략을 동적 선택해 단순 질문의 불필요한 연산과 복잡 질문의 검색 부족을 동시에 해소했다.


Adaptive-RAG
query complexity
routing


적응형 Agent(4)의 라우팅 설계 참조: 예산 제한 하 전략 선택



중간: 복잡도 라벨 자동 수집 + 분류기 학습



QA 데이터셋 기준 복잡도라 팩트체크 3클래스 판정에의 매핑은 미검증





Corrective Retrieval Augmented Generation

Yan et al.

arXiv (Cornell University)

2024-01-29

인용 수 180

PDF 열기



경량 검색 평가기로 근거 품질을 진단해 웹 검색 확장·문서 재구성을 트리거하는 플러그앤플레이 보정 프레임워크로 4개 데이터셋에서 RAG 강건성을 개선했다.


CRAG
corrective RAG
retrieval evaluator


근거 충분성 판단(4)의 구조 참조: 검색 결과 품질 평가→재검색 분기



중간: 평가기(T5 기반) 학습, 오픈소스 재현 연구 존재



원 구현이 상용 검색 API·폐쇄 모델 의존, 평가기가 개체명 정렬에 의존한다는 분석 보고됨





Chain-of-Verification Reduces Hallucination in Large Language Models

Dhuliawala et al.

arXiv (Cornell University)

2023-09-20

인용 수 400

PDF 열기



초안→검증질문 계획→독립 답변→반영의 4단계 검증 사슬(CoVe)로 리스트 질문·장문 생성 등 여러 과제에서 환각을 줄였다.


chain-of-verification
CoVe
self-verification


자기교정(4)의 강한 비-agent baseline 후보: 고정 워크플로형 검증



낮음: 프롬프트만으로 구성 가능, 검증 답변 수만큼 호출 증가



동일 모델이 검증하므로 독립 근거 없으면 효과 제한, 분해기 민감도 존재





Adaptive Retrieval Without Self-Knowledge? Bringing Uncertainty Back Home

Moskvoretskii et al.

ArXiv.org

2025-01-22

인용 수 15

PDF 열기



적응검색 방법 35종(최근 8종+불확실성 추정 27종)을 6개 데이터셋·10개 지표로 비교해 단순 불확실성 추정이 복잡한 적응 파이프라인과 대등하거나 효율에서 우위임을 보였다.


adaptive retrieval
uncertainty estimation
efficiency


Agent 대 비-agent 비교 설계(4)의 핵심 근거: 단순 기준선을 먼저 세워야 함



낮음: 기존 방법 재현 중심의 비교 실험



영어 QA 중심, 팩트체크 판정 태스크로의 확장은 미검증





FinQA: A Dataset of Numerical Reasoning over Financial Data

Chen et al.

Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing

2021-09-01

인용 수 504

PDF 열기



금융 보고서 위 전문가 작성 질문-정답-추론 프로그램 쌍을 대규모 구축해 다단계 수치 추론의 해석 가능한 골드를 제공했다.


FinQA
numerical reasoning
financial reports


수치·표 근거 처리(5)의 진단용: 수치 계산 모듈(코드 실행) 평가



낮음: 공개 데이터셋으로 평가만 수행



영어 금융 도메인, 검색 QA 정확도이지 팩트체크 진위 성능이 아님





Time-Aware Language Models as Temporal Knowledge Bases

Dhingra et al.

Transactions of the Association for Computational Linguistics

2021-06-29

인용 수 331

PDF 열기



타임스탬프 결합 사전학습으로 시간 변화 사실의 암기와 미래 사실 예측 교정을 개선하고 재학습 없는 모델 refresh를 제안했다.


temporal knowledge
timestamp modeling
calibration


시간축(5) 설계 참조: 시간 변화 사실의 진단 데이터셋 구축 방식



높음(사전학습): 진단 데이터셋 사용은 낮음



영어 위키피디아 기반, 폐쇄형 설정 중심이라 검색 증강 시스템과의 결합은 별도 과제





FreshLLMs: Refreshing Large Language Models with Search Engine Augmentation

Vu et al.

arXiv (Cornell University)

2023-10-05

인용 수 321

PDF 열기



빠르게 변하는 지식·거짓 전제 질문을 포함한 동적 벤치마크(FreshQA)와 검색 증강 프롬프팅(FreshPrompt)을 제시하고 근거 개수·순서가 정답률에 미치는 영향을 분석했다.


FreshQA
freshness
false premise
search augmentation


시점 확인(4)·신선도 평가(5): 근거 순서·개수 민감도 실험 설계 참조



낮음: 벤치마크 공개, 정기 갱신 운영은 별도



영어 중심, 사람 평가 50k 판단에 의존한 채점이라 자동화 시 편향 가능





X-Fact: A New Benchmark Dataset for Multilingual Fact Checking

Gupta & Srikumar

Annual Meeting of the Association for Computational Linguistics

2021-06-17

인용 수 110

PDF 열기



25개 언어의 실전 팩트체크 주장을 전문가 라벨로 구축한 최대 규모 다국어 검증 데이터셋으로 도메인 외·제로샛 일반화를 측정했다(최고 F-score 약 40%).


X-Fact
multilingual fact-checking
real-world claims


다국어 확장(5): 한국어 포함 여부 확인 후 제로샛 평가 세트로 활용



낮음: 공개 데이터셋 평가



근거가 뉴스 검색 기반이라 시간누출 통제 없음, 짧은 주장 중심





KorQuAD1.0: Korean QA Dataset for Machine Reading Comprehension

Lim et al.

arXiv (Cornell University)

2019-09-16

인용 수 99

PDF 열기



한국어 위키피디아 기반 70,000+ 사람 작성 질의응답 쌍(KorQuAD 1.0)을 공개해 한국어 추출형 독해의 표준 벤치마크를 세웠다.


KorQuAD
Korean QA
machine reading comprehension


한국어 근거 검색·독해(5)의 기초 진단: 검색기·판독기 색인 구축



매우 낮음: 공개 데이터셋



2019년 스냅샷이라 시간 민감 사실은 진화, 위키피디아 단일 출처





CiteME: Can Language Models Accurately Cite Scientific Claims?

Press et al.

arXiv (Cornell University)

2024-07-10

인용 수 34

PDF 열기



최신 ML 논문의 인용 귀속 과제에서 LM 4.2-18.5% vs 인간 69.7% 격차를 측정하고, 검색·판독 에이전트(CiteAgent)로 35.3%까지 향상시켰다.


CiteME
citation attribution
claim attribution


인용·출처 검증(6): 생성된 출처가 실제 문서인지 검증하는 평가 설계 참조



중간: 벤치마크 평가는 낮음, 에이전트 구현은 검색 API 비용



영어 ML 논문 도메인, 한국어 학술 인용으로의 확장은 미검증





AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions

Kirichenko et al.

ArXiv.org

2025-06-10

인용 수 36

PDF 열기



20개 데이터셋에서 답 불가·모호·거짓 전제 질문 유형별 abstention을 측정해 reasoning 튜닝이 오히려 abstention을 평균 24% 저하시킴을 밝혔다.


AbstentionBench
abstention
unanswerable questions


근거부족 판정(6)의 평가 체계: 답변 거부(모르겠다) 성능의 표준 측정



낮음: 공개 벤치마크 평가



영어 중심, 팩트체크 3클래스(지지/반박/근거부족)와의 직접 대응은 재설계 필요





Detecting hallucinations in large language models using semantic entropy

Farquhar et al.

Nature

2024-06-01

인용 수 1,007

PDF 열기



표본들을 의미 수준에서 클러스터링해 confabulation(자의적 오답)을 탐지하는 통계적 불확실성 추정(semantic entropy)을 제안해 과제 무관 일반화를 보였다.


semantic entropy
hallucination detection
uncertainty


판정 신뢰도·교정(6): 다중 샘플링으로 근거부족/확신 오답 탐지 신호



중간: 샘플당 5-10회 생성 비용(저비용 probe 후속 연구 존재)



confabulation 일부만 탐지, 체계적 오류(모델이 일관되게 틀리는 경우)는 탐지 불가





Knowledge Conflicts for LLMs: A Survey

Xu et al.

arXiv (Cornell University)

2024-03-13

인용 수 218

PDF 열기



context-memory/inter-context/intra-memory 3류 지식갈등으로 문헌을 체계화하고 원인·모델 행동·완화법을 정리한 서베이다.


knowledge conflict
survey
RAG


반대 근거·갈등 처리(4)(7)의 개념 체계: 근거-모델 지식 충돌 실험 설계



매우 낮음: 서베이 읽기



2024년 초 기준, 이후 급증한 RAG 오염 연구는 별도 보강 필요





Entity-Based Knowledge Conflicts in Question Answering

Longpre et al.

Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing

2021-09-10

인용 수 314

PDF 열기



모순 맥락 삽입으로 모델의 파라메트릭 지식 과의존(환각 원인)을 측정하는 프레임워크를 만들고 간단한 완화법으로 OOD 일반화를 4-7% 개선했다.


knowledge conflict
parametric over-reliance
hallucination


근거 vs 모델 사전지식 갈등(7)의 실험 프로토콜: 통제된 모순 근거 주입 평가



낮음: 프레임워크 공개, 자동 갈등 구축 스크립트 재사용



영어 QA 중심, 갈등 구축 자체의 인공성(합성 문서) 한계





No Hindsight for LLM Fact-Checkers: Measuring Leakage Channels in Misinformation Detection

Lu & Setiawan

arXiv (Cornell University)

2026-10-04

PDF 열기



AVeriTeC·QuanTemp++를 주장 시점 이전 근거 조건으로 재구성해 사후 근거 허용이 제로샛 정확도를 6.3점 부풀리고 파라메트릭 누출도 존재함을 측정했다.


temporal leakage
point-in-time evidence
benchmark validity


시간누출·정답기사 누출 통제(7)의 핵심 참조: point-in-time 근거 재구성 평가



중간: 주장 시점 필터링된 인덱스 재구축 필요



2026년 10월 초 공개 최신 연구로 재현 세부는 확인 중, 영어 중심





ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning

Masry et al.

Findings of the Association for Computational Linguistics: ACL 2022

2022-03-19

인용 수 1,235

PDF 열기



사람 작성 9.6k+증강 23.1k 차트 질문으로 시각·논리 추론 벤치마크(ChartQA)를 구축하고 시각 특징+데이터 테이블 결합 모델을 제안했다.


ChartQA
chart question answering
visual reasoning


차트 근거 처리(8)의 기초 진단: 차트→표 추출 후 수치 검증



낮음: 공개 벤치마크 평가



영어 차트 중심, 차트 QA 정확도이지 주장 진위 판정이 아님





COSMOS: Catching Out-of-Context Image Misuse Using Self-Supervised Learning

Aneja et al.

Proceedings of the AAAI Conference on Artificial Intelligence

2023-06-26

인용 수 23

PDF 열기



객체-캡션 정렬 자기지도학습으로 out-of-context 이미지 오용을 85% 탐지하고 200k 이미지·450k 캡션 데이터셋을 공개했다.


COSMOS
out-of-context
image misuse


이미지-본문 불일치(8) 탐지 모듈의 참조: 문맥 도용(out-of-context) 평가



중간: 자기지도 사전학습, 공개 데이터셋으로 파인튜닝 대체 가능



영어 뉴스 중심, 한국어 뉴스 캡션 정합으로의 전이는 미검증





VeriTaS: The First Dynamic Benchmark for Multimodal Automated Fact-Checking

Rothermel et al.

ArXiv

2026-01-13

PDF 열기



104개 팩트체크 기관·54개 언어·25k 주장을 분기 단위로 자동 갱신하는 최초의 동적 멀티모달 AFC 벤치마크(VeriTaS)로 사전학습 누출 저항성을 확보했다.


VeriTaS
dynamic benchmark
multimodal fact-checking
leakage


오염 통제(7)·멀티모달(8) 평가 설계의 모델: 갱신형 평가세트 운영 방식



높음(전체 파이프라인): 평가세트 소비만은 낮음



2026년 1월 공개로 커뮤니티 검증 초기 단계, 한국어 포함 여부는 데이터 확인 필요




논문 더 추가하기
```
