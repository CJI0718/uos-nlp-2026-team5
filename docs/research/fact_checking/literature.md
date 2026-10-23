# 팩트체크 Agent 문헌 지도

확인 기준일: 2026-10-23. **논문 34편 + 학위논문 1편**. [구상](README.md) · [평가 설계](evaluation.md) · [도구 후보](tools.md) · [구조화 서지](papers.json) · [조사 기록](research_log.json)

## 읽는 법과 확인 범위

- 이 자료는 폭넓은 기획용 문헌 지도이지 체계적 문헌고찰(systematic review)이나 전체 논문 전문 정독 결과가 아니다.
- 원논문 랜딩 페이지·초록·저자/공식 문서를 확인했고 필요한 평가 정의·공개 구현 설명을 대조했다. 개별 표·재현 조건·라이선스는 구현 전에 추가 검수한다.
- **논문이 제안/보고한 내용**, **팀이 가져올 아이디어**, **한계**를 분리했다. 모든 연구는 우리 환경에서 미재현이다.
- 학회 본회의, Findings, workshop, demo, preprint, 학위논문을 구분한다. 단순 arXiv 링크만 확인한 경우 후속 게재 여부를 단정하지 않는다.
- 최신 원페이지와 검색 요약이 충돌하면 원페이지를 우선하되 버전 차이를 남긴다. NumTemp/QuanTemp는 동일 논문이며, KoSimpleQA 문항 수는 확인한 페이지 사이에 차이가 있어 여기서 확정하지 않는다.
- FC ID는 이 팩트체크 문헌집 전용이다. 기존 49개 후보집의 P ID를 재번호화하지 않는다. 일부 논문은 기존 후보집과 겹치므로 두 문헌집의 숫자를 더해 고유 논문 수라고 하지 않는다.

## 먼저 읽을 묶음

1. **task와 gold**: FC01 → FC02 → FC03. 무엇을 검증하고 무엇을 정답으로 볼지 정한다.
2. **Agent 정책**: FC10 → FC11 → FC15. 분해·도구·추가 검색/종료를 비교한다.
3. **강한 baseline과 평가**: FC21 → FC04/FC05 → FC29. 고정 RAG를 약하게 만들지 않고 평가 버전을 구분한다.
4. **API·한국어 방향**: FC23 → FC26 → FC30. 수치/시점과 한국어 기존 시스템의 차이를 찾는다.

위 순서는 읽기 제안이며 사람별 담당자·최종 주제 배정이 아니다.

## 전체 색인

| ID | 연구 | 발표/확인 상태 | 우선도 |
| --- | --- | --- | --- |
| [FC01](#fc01) | A Survey on Automated Fact-Checking | TACL 2022 | core |
| [FC02](#fc02) | FEVER: a Large-scale Dataset for Fact Extraction and VERification | NAACL 2018 | core |
| [FC03](#fc03) | AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web | NeurIPS 2023 Datasets and Benchmarks | core |
| [FC04](#fc04) | The Automated Verification of Textual Claims (AVeriTeC) Shared Task | FEVER 2024 workshop | core |
| [FC05](#fc05) | The 2nd Automated Verification of Textual Claims (AVeriTeC) Shared Task: Open-weights, Reproducible and Efficient Systems | FEVER 2025 workshop | next |
| [FC06](#fc06) | FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information | NeurIPS 2021 Datasets and Benchmarks; 학회 검색 결과 + arXiv 초록 확인 | next |
| [FC07](#fc07) | HoVer: A Dataset for Many-Hop Fact Extraction And Claim Verification | Findings of EMNLP 2020 | next |
| [FC08](#fc08) | TabFact: A Large-scale Dataset for Table-based Fact Verification | arXiv 2019, 2020 버전 확인; 학회 메타데이터 별도 확인 필요 | extension |
| [FC09](#fc09) | Fact or Fiction: Verifying Scientific Claims | EMNLP 2020 | extension |
| [FC10](#fc10) | ReAct: Synergizing Reasoning and Acting in Language Models | ICLR 2023; 저자 프로젝트 페이지 확인 | core |
| [FC11](#fc11) | Fact-Checking Complex Claims with Program-Guided Reasoning | ACL 2023 | core |
| [FC12](#fc12) | Explainable Claim Verification via Knowledge-Grounded Reasoning with Large Language Models | Findings of EMNLP 2023; arXiv 수록 정보 확인 | next |
| [FC13](#fc13) | Large Language Model Agent for Fake News Detection | arXiv 2024; 후속 학회 게재 여부 이번 조사에서 미확인 | next |
| [FC14](#fc14) | Web Retrieval Agents for Evidence-Based Misinformation Detection | arXiv 2024; 후속 학회 게재 여부 이번 조사에서 미확인 | next |
| [FC15](#fc15) | FIRE: Fact-checking with Iterative Retrieval and Verification | Findings of NAACL 2025 | core |
| [FC16](#fc16) | EMULATE: A Multi-Agent Framework for Determining the Veracity of Atomic Claims by Emulating Human Actions | FEVER 2025 workshop | extension |
| [FC17](#fc17) | LoCal: Logical and Causal Fact-Checking with LLM-Based Multi-Agents | The Web Conference 2025 | extension |
| [FC18](#fc18) | DEFAME: Dynamic Evidence-based FAct-checking with Multimodal Experts | ICML 2025 | next |
| [FC19](#fc19) | FactSearch: An Interactive Agentic Fact Search System for Verifying Large Language Model Outputs | ACL 2026 System Demonstrations | next |
| [FC20](#fc20) | Evidence Retrieval for Fact Verification using Multi-stage Reranking | Findings of EMNLP 2024 | next |
| [FC21](#fc21) | Fathom: A Fast and Modular RAG Pipeline for Fact-Checking | FEVER 2025 workshop | core |
| [FC22](#fc22) | Team HUMANE at AVeriTeC 2025: HerO 2 for Efficient Fact Verification | FEVER 2025 workshop | next |
| [FC23](#fc23) | QuanTemp: A real-world open-domain benchmark for fact-checking numerical claims | SIGIR 2024; arXiv acceptance 정보 확인 | core |
| [FC24](#fc24) | Time Matters: An End-to-End Solution for Temporal Claim Verification | EMNLP 2024 Industry Track | next |
| [FC25](#fc25) | ChronoFact: Timeline-based Temporal Fact Verification | IJCAI 2025 | extension |
| [FC26](#fc26) | TSVer: A Benchmark for Fact Verification Against Time-Series Evidence | EMNLP 2025 | core |
| [FC27](#fc27) | Enabling Large Language Models to Generate Text with Citations | EMNLP 2023 | next |
| [FC28](#fc28) | Long-form factuality in large language models | arXiv 2024; 이번 확인에서는 학회 메타데이터 미확인 | next |
| [FC29](#fc29) | Ev2R: Evaluating Evidence Retrieval in Automated Fact-Checking | arXiv 2024→2025 v2; v2에 TACL accepted 명시 | core |
| [FC30](#fc30) | 한국어 팩트체크 필요성 탐지 모델 및 RAG 기반 팩트체크 자동화 시스템 개발: 대선 후보자 토론회 적용 | 한국언론학보 70(2), 86–123; DOI 10.20879/kjjcs.2026.70.2.003 | core |
| [FC31](#fc31) | A Contrastive Learning Method for Automated Fact-Checking | Journal of KIISE 50(8), 680 시작; DOI 서지·초록 확인 | next |
| [FC32](#fc32) | KoSimpleQA: A Korean Factuality Benchmark with an Analysis of Reasoning LLMs | arXiv 2025 preprint; 후속 게재 확인 안 함 | extension |
| [FC33](#fc33) | 자동화된 팩트체크 과정에서 딥러닝을 이용한 주장(claim) 판별 기법 연구 | 서울대학교 학위논문 저장소; 학위 종류 별도 미확인 | extension |
| [FC34](#fc34) | AVerImaTeC: A Dataset for Automatic Verification of Image-Text Claims with Evidence from the Web | NeurIPS 2025 Datasets and Benchmarks; arXiv acceptance 정보 확인 | extension |
| [FC35](#fc35) | Selective Multimodal Retrieval for Automated Verification of Image–Text Claims | FEVER 2026 workshop | extension |

## 분야 정의

<a id="fc01"></a>

### FC01. A Survey on Automated Fact-Checking

- **저자:** Zhijiang Guo; Michael Schlichtkrull; Andreas Vlachos
- **출처:** [원문·공식 페이지](https://aclanthology.org/2022.tacl-1.11/) · TACL 2022
- **논문에서 확인한 내용:** 검증 대상 탐지·증거 수집·판정 등 서로 다른 과제를 정리한다.
- **우리 팀의 활용 제안:** 팀 용어와 scope를 정의하는 첫 읽기.
- **주의·차이점:** 분야 지도이지 특정 Agent의 우월성을 입증한 실험이 아니다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 평가 데이터와 과제

<a id="fc02"></a>

### FC02. FEVER: a Large-scale Dataset for Fact Extraction and VERification

- **저자:** James Thorne et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/N18-1074/) · NAACL 2018
- **논문에서 확인한 내용:** Wikipedia 기반 주장에 지지·반박·정보 부족과 근거 문장을 제공한다.
- **우리 팀의 활용 제안:** 판정과 근거를 함께 채점하는 가장 단순한 기준선.
- **주의·차이점:** 합성 주장·고정 Wikipedia 환경이 실시간 한국어 뉴스와 다르다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc03"></a>

### FC03. AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web

- **저자:** Michael Schlichtkrull; Zhijiang Guo; Andreas Vlachos
- **출처:** [원문·공식 페이지](https://proceedings.neurips.cc/paper_files/paper/2023/hash/cd86a30526cd1aff61d6f89f107634e4-Abstract-Datasets_and_Benchmarks.html) · NeurIPS 2023 Datasets and Benchmarks
- **논문에서 확인한 내용:** 실제 주장 4,568개를 웹 근거·질문/답변·판정 설명과 연결한다.
- **우리 팀의 활용 제안:** 주장→검증 질문→증거→판정 구조와 데이터 작성 기준.
- **주의·차이점:** 4개 label을 임의로 3개로 합치지 않는다. 기존 fact-check 기사 유출과 시간 누출을 통제해야 한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc06"></a>

### FC06. FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information

- **저자:** Rami Aly et al.
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2106.05707) · NeurIPS 2021 Datasets and Benchmarks; 학회 검색 결과 + arXiv 초록 확인
- **논문에서 확인한 내용:** 문장과 표 셀을 함께 증거로 사용하는 87,026개 검증 주장을 제시한다.
- **우리 팀의 활용 제안:** API 표와 기사 텍스트를 연결하는 근거 형식의 참고.
- **주의·차이점:** Wikipedia 표를 다루는 성능이 한국 공식 통계 API 성능을 보장하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc07"></a>

### FC07. HoVer: A Dataset for Many-Hop Fact Extraction And Claim Verification

- **저자:** Yichen Jiang et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2020.findings-emnlp.309/) · Findings of EMNLP 2020
- **논문에서 확인한 내용:** 여러 Wikipedia 문서에서 근거를 모으는 many-hop 검증을 다룬다.
- **우리 팀의 활용 제안:** 단일/복수 근거 난도 층과 주장 분해 실험.
- **주의·차이점:** SUPPORTED/NOT-SUPPORTED를 곧바로 참/거짓으로 대응시키지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc08"></a>

### FC08. TabFact: A Large-scale Dataset for Table-based Fact Verification

- **저자:** Wenhu Chen et al.
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/1909.02164) · arXiv 2019, 2020 버전 확인; 학회 메타데이터 별도 확인 필요
- **논문에서 확인한 내용:** 표를 근거로 자연어 주장을 판정하며 신경망과 프로그램 실행 접근을 비교한다.
- **우리 팀의 활용 제안:** 단위·집계·계산을 코드 도구로 분리하는 실험의 배경.
- **주의·차이점:** 대부분 표가 주어진 설정으로, 표 자체를 찾아야 하는 검색과는 다르다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc09"></a>

### FC09. Fact or Fiction: Verifying Scientific Claims

- **저자:** David Wadden et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2020.emnlp-main.609/) · EMNLP 2020
- **논문에서 확인한 내용:** SciFact는 과학 주장과 논문 초록·근거 구간을 연결한다.
- **우리 팀의 활용 제안:** 과학 뉴스로 범위를 바꿀 경우의 도메인 후보.
- **주의·차이점:** 전문가 수준 gold 검수가 필요하며 의료 조언 서비스로 확대하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## Agent·도구 사용·검색 종료

<a id="fc10"></a>

### FC10. ReAct: Synergizing Reasoning and Acting in Language Models

- **저자:** Shunyu Yao et al.
- **출처:** [원문·공식 페이지](https://react-lm.github.io/) · ICLR 2023; 저자 프로젝트 페이지 확인
- **논문에서 확인한 내용:** 행동과 관찰을 교대로 사용해 다음 행동을 갱신하고 FEVER 등에서 평가한다.
- **우리 팀의 활용 제안:** 도구 관찰 후 검색/계산/종료를 고르는 기본 Agent 구조.
- **주의·차이점:** 도구를 사용한다는 사실만으로 고정 workflow보다 낫다는 증거가 되지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc13"></a>

### FC13. Large Language Model Agent for Fake News Detection

- **저자:** Xinyi Li; Yongfeng Zhang; Edward C. Malthouse
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2405.01593) · arXiv 2024; 후속 학회 게재 여부 이번 조사에서 미확인
- **논문에서 확인한 내용:** FactAgent는 전문가가 설계한 workflow와 도구를 이용해 뉴스를 검증한다.
- **우리 팀의 활용 제안:** 고정된 도구 workflow를 Agent 비교 기준선으로 살펴본다.
- **주의·차이점:** 동명의 다른 FactAgent 연구와 구분. 문체·출처 성향을 사실의 직접 증거로 대체하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc14"></a>

### FC14. Web Retrieval Agents for Evidence-Based Misinformation Detection

- **저자:** Jacob-Junqi Tian et al.
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2409.00009) · arXiv 2024; 후속 학회 게재 여부 이번 조사에서 미확인
- **논문에서 확인한 내용:** 주 Agent와 웹 검색 Agent를 결합하고 검색 도구·근거와 성능 관계를 분석한다.
- **우리 팀의 활용 제안:** 검색이 없는 LLM과 검색-enabled 시스템 차이를 분해한다.
- **주의·차이점:** 추가 모델·검색량 효과와 Agent 정책 효과를 혼동하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc15"></a>

### FC15. FIRE: Fact-checking with Iterative Retrieval and Verification

- **저자:** Zhuohan Xie et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2025.findings-naacl.158/) · Findings of NAACL 2025
- **논문에서 확인한 내용:** 판정과 추가 질의 생성을 반복적으로 선택하는 fact-checking framework다.
- **우리 팀의 활용 제안:** 고정 검색 횟수와 적응적 검색/종료의 정확도–비용 비교.
- **주의·차이점:** 논문 비용 개선은 해당 모델·데이터·baseline에서의 결과이며 우리 실험 결과가 아니다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc16"></a>

### FC16. EMULATE: A Multi-Agent Framework for Determining the Veracity of Atomic Claims by Emulating Human Actions

- **저자:** Spencer Hong; Meng Luo; Xinyi Wan
- **출처:** [원문·공식 페이지](https://aclanthology.org/2025.fever-1.13/) · FEVER 2025 workshop
- **논문에서 확인한 내용:** 질의 생성·검색 결과 판단·증거 평가 등을 여러 역할로 분리한다.
- **우리 팀의 활용 제안:** 역할 분리 없이도 동일 질문·검증 단계를 쓸 수 있는지 비교한다.
- **주의·차이점:** multi-agent 개수만 늘리는 확장과 비용 증가에 주의한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc19"></a>

### FC19. FactSearch: An Interactive Agentic Fact Search System for Verifying Large Language Model Outputs

- **저자:** Meng Fang; Harry Mackenzie
- **출처:** [원문·공식 페이지](https://aclanthology.org/2026.acl-demo.36/) · ACL 2026 System Demonstrations
- **논문에서 확인한 내용:** 검색 인프라와 검증 단계를 구성 가능하게 하여 재현성을 강조한다.
- **우리 팀의 활용 제안:** live 검색과 고정 evidence store를 분리하고 검색 설정을 기록한다.
- **주의·차이점:** 시스템 데모의 목표와 우리 과제의 비교 실험 목표는 다르다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 주장 분해와 논리

<a id="fc11"></a>

### FC11. Fact-Checking Complex Claims with Program-Guided Reasoning

- **저자:** Liangming Pan et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2023.acl-long.386/) · ACL 2023
- **논문에서 확인한 내용:** ProgramFC는 복잡한 주장을 전문 함수가 해결할 작은 과제로 분해한다.
- **우리 팀의 활용 제안:** 자연어 해석과 결정론적 계산을 분리하고 분해 유무를 비교한다.
- **주의·차이점:** 임의 Python 실행을 허용하는 설계로 가져오지 말고 허용 도구 집합으로 축소한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc12"></a>

### FC12. Explainable Claim Verification via Knowledge-Grounded Reasoning with Large Language Models

- **저자:** Haoran Wang; Kai Shu
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2310.05253) · Findings of EMNLP 2023; arXiv 수록 정보 확인
- **논문에서 확인한 내용:** FOLK는 논리 형태와 근거 기반 QA를 이용해 복합 주장을 검증한다.
- **우리 팀의 활용 제안:** 부분 주장의 결과를 원래 주장으로 합치는 논리를 검토한다.
- **주의·차이점:** 분해가 원래 주장과 동치인지 검수해야 하며 설명이 곧 증명은 아니다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc17"></a>

### FC17. LoCal: Logical and Causal Fact-Checking with LLM-Based Multi-Agents

- **저자:** Jiatong Ma; Linmei Hu; Rang Li; Wenbo Fu
- **출처:** [원문·공식 페이지](https://dl.acm.org/doi/10.1145/3696410.3714748) · The Web Conference 2025
- **논문에서 확인한 내용:** 주장 분해·추론과 논리/인과 검토를 분리하는 framework다.
- **우리 팀의 활용 제안:** 분해 누락과 부분 주장 합성 오류를 오류 분류에 포함한다.
- **주의·차이점:** 이름의 causal을 실제 인과 추론의 일반적 보장으로 해석하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 검색·재정렬·효율

<a id="fc20"></a>

### FC20. Evidence Retrieval for Fact Verification using Multi-stage Reranking

- **저자:** Shrikant Malviya; Stamos Katsigiannis
- **출처:** [원문·공식 페이지](https://aclanthology.org/2024.findings-emnlp.428/) · Findings of EMNLP 2024
- **논문에서 확인한 내용:** FEVEROUS의 문장·표 근거 검색에 multi-stage reranking을 사용한다.
- **우리 팀의 활용 제안:** Kiwi+BM25, dense, hybrid/reranker의 근거 회수 비교.
- **주의·차이점:** 여러 단계를 한 번에 바꾸면 개선 원인을 식별하기 어렵다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc21"></a>

### FC21. Fathom: A Fast and Modular RAG Pipeline for Fact-Checking

- **저자:** Farrukh Bin Rashid; Saqib Hakak
- **출처:** [원문·공식 페이지](https://aclanthology.org/2025.fever-1.20/) · FEVER 2025 workshop
- **논문에서 확인한 내용:** 질문 생성, BM25+semantic retrieval, 작은 모델 판정의 모듈형 pipeline이다.
- **우리 팀의 활용 제안:** 적응형 Agent에 맞설 강한 비-Agent baseline을 만드는 참고.
- **주의·차이점:** 작은 모델/대회 제한과 우리 모델·한국어 환경을 같다고 가정하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc22"></a>

### FC22. Team HUMANE at AVeriTeC 2025: HerO 2 for Efficient Fact Verification

- **저자:** Yejun Yoon; Jaeyoon Jung; Seunghyun Yoon; Kunwoo Park
- **출처:** [원문·공식 페이지](https://aclanthology.org/2025.fever-1.16/) · FEVER 2025 workshop
- **논문에서 확인한 내용:** 문서 요약·답변 재구성·양자화 등을 통해 근거와 효율을 개선한다.
- **우리 팀의 활용 제안:** 공개 구현에서 evidence 표현과 GPU 메모리 절충을 살펴본다.
- **주의·차이점:** 저자 README는 32B 모델 fine-tuning/AWQ를 설명한다. 한 GPU 추론 가능성과 학습 비용을 혼동하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 시간·수치·시계열

<a id="fc23"></a>

### FC23. QuanTemp: A real-world open-domain benchmark for fact-checking numerical claims

- **저자:** Venktesh V; Abhijit Anand; Avishek Anand; Vinay Setty
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2403.17169) · SIGIR 2024; arXiv acceptance 정보 확인
- **논문에서 확인한 내용:** 통계·시간 표현을 포함하는 실제 수치 주장과 근거를 다룬다.
- **우리 팀의 활용 제안:** API·계산 도구가 필요한 주장 유형과 함정 설계.
- **주의·차이점:** 초기 검색 제목 NumTemp와 동일 arXiv의 후속 제목 QuanTemp를 별개 논문으로 세지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc24"></a>

### FC24. Time Matters: An End-to-End Solution for Temporal Claim Verification

- **저자:** Anab Maulana Barik; Wynne Hsu; Mong-Li Lee
- **출처:** [원문·공식 페이지](https://aclanthology.org/2024.emnlp-industry.48/) · EMNLP 2024 Industry Track
- **논문에서 확인한 내용:** 시간 정보를 반영한 근거 검색과 temporal reasoning을 결합한다.
- **우리 팀의 활용 제안:** 날짜를 무시/고려하는 조건의 비교.
- **주의·차이점:** 문서 게시일·주장의 대상 시점·정보 공개 시점을 각각 기록해야 한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc25"></a>

### FC25. ChronoFact: Timeline-based Temporal Fact Verification

- **저자:** Anab Maulana Barik; Wynne Hsu; Mong Li Lee
- **출처:** [원문·공식 페이지](https://www.ijcai.org/proceedings/2025/893) · IJCAI 2025
- **논문에서 확인한 내용:** 주장과 근거의 사건을 timeline으로 정리해 시간 관계를 검증한다.
- **우리 팀의 활용 제안:** 순서·겹치는 기간·반복 사건 오류 유형.
- **주의·차이점:** 단순 숫자 비교와 복잡한 사건 timeline을 한 실험에 과도하게 섞지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc26"></a>

### FC26. TSVer: A Benchmark for Fact Verification Against Time-Series Evidence

- **저자:** Marek Strong; Andreas Vlachos
- **출처:** [원문·공식 페이지](https://aclanthology.org/2025.emnlp-main.1519/) · EMNLP 2025
- **논문에서 확인한 내용:** 실제 주장 304개와 시계열 400개를 연결하고 관련 구간·판정 설명을 제공한다.
- **우리 팀의 활용 제안:** 공식 API의 시계열·기간을 대조하는 과제의 직접적인 선행연구.
- **주의·차이점:** 제공된 시계열을 쓰는 검증과 올바른 API 지표를 찾아오는 retrieval을 분리한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 근거·인용·평가

<a id="fc04"></a>

### FC04. The Automated Verification of Textual Claims (AVeriTeC) Shared Task

- **저자:** Michael Schlichtkrull et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2024.fever-1.1/) · FEVER 2024 workshop
- **논문에서 확인한 내용:** 증거 품질 기준을 충족하고 판정도 맞을 때 인정하는 shared task를 소개한다.
- **우리 팀의 활용 제안:** 2024 Hungarian METEOR 기반 평가를 사용할 경우 버전을 고정한다.
- **주의·차이점:** 최종 판정 정확도·AVeriTeC score·다른 연도 점수는 동일한 지표가 아니다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc05"></a>

### FC05. The 2nd Automated Verification of Textual Claims (AVeriTeC) Shared Task: Open-weights, Reproducible and Efficient Systems

- **저자:** Mubashara Akhtar et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2025.fever-1.15/) · FEVER 2025 workshop
- **논문에서 확인한 내용:** open-weight·사전 knowledge store·제한된 GPU/추론시간 아래의 비교를 다룬다.
- **우리 팀의 활용 제안:** GPU 자원을 쓰되 재현성과 비용을 함께 설계하는 참고.
- **주의·차이점:** 논문 대회의 23GB GPU/분당 제약을 우리 과제 의무나 Colab 실행 보장으로 해석하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc27"></a>

### FC27. Enabling Large Language Models to Generate Text with Citations

- **저자:** Tianyu Gao; Howard Yen; Jiatong Yu; Danqi Chen
- **출처:** [원문·공식 페이지](https://aclanthology.org/2023.emnlp-main.398/) · EMNLP 2023
- **논문에서 확인한 내용:** ALCE는 생성 답의 정확성과 인용 품질 등을 구분해 평가한다.
- **우리 팀의 활용 제안:** 판정이 맞아도 인용이 뒷받침하지 못하는 오류를 따로 평가한다.
- **주의·차이점:** 링크 존재·문장 유사도만으로 citation support를 대신하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc28"></a>

### FC28. Long-form factuality in large language models

- **저자:** Jerry Wei et al.
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2403.18802) · arXiv 2024; 이번 확인에서는 학회 메타데이터 미확인
- **논문에서 확인한 내용:** SAFE는 생성된 장문을 개별 사실로 나눠 검색으로 검증한다.
- **우리 팀의 활용 제안:** 기사 주장 검증과 최종 설명 문장의 factuality 검사를 구분한다.
- **주의·차이점:** SAFE가 gold를 생성하고 같은 계열 Judge가 정답을 인증하는 순환 평가를 피한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc29"></a>

### FC29. Ev2R: Evaluating Evidence Retrieval in Automated Fact-Checking

- **저자:** Mubashara Akhtar; Michael Schlichtkrull; Andreas Vlachos
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2411.05375) · arXiv 2024→2025 v2; v2에 TACL accepted 명시
- **논문에서 확인한 내용:** 참조 근거와의 정합성과 판정 지원을 함께 보는 evidence 평가를 제안한다.
- **우리 팀의 활용 제안:** 2025 AVeriTeC의 평가와 사람 근거 검수 기준을 이해한다.
- **주의·차이점:** 자동 평가도 모델 의존·비용이 있다. 2024 Hungarian METEOR 수치와 혼용하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 한국어 선행연구

<a id="fc30"></a>

### FC30. 한국어 팩트체크 필요성 탐지 모델 및 RAG 기반 팩트체크 자동화 시스템 개발: 대선 후보자 토론회 적용

- **저자:** 이종혁 (Jong Hyuk Lee)
- **출처:** [원문·공식 페이지](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003331812) · 한국언론학보 70(2), 86–123; DOI 10.20879/kjjcs.2026.70.2.003
- **논문에서 확인한 내용:** 한국어 검증 필요성 탐지·다중 검색·LLM 판정 pipeline과 토론회 적용을 보고한다.
- **우리 팀의 활용 제안:** 한국어 RAG 팩트체크 자체를 신규성으로 주장하지 않고 구체적 개선 축을 찾는다.
- **주의·차이점:** 탐지 성능과 최종 판정 성능은 다른 평가다. 공개 데이터·코드 재사용 권한은 별도 확인.
- **확인 수준:** KCI 초록 + 원페이지 citation metadata 직접 확인 (2026-10-23). 재현 실험 없음.

<a id="fc31"></a>

### FC31. A Contrastive Learning Method for Automated Fact-Checking

- **저자:** Seonyeong Song; Jejun An; Kunwoo Park
- **출처:** [원문·공식 페이지](https://doi.org/10.5626/jok.2023.50.8.680) · Journal of KIISE 50(8), 680 시작; DOI 서지·초록 확인
- **논문에서 확인한 내용:** 한국어 fact-checking의 근거 문장 선택에 대조학습을 적용한다.
- **우리 팀의 활용 제안:** 검색기 학습/비학습 비교의 한국어 선행연구.
- **주의·차이점:** 학습 데이터·코드 공개와 실제 사용 권한은 확인 전이다.
- **확인 수준:** DOI 서지·초록 확인 (2026-10-23). 재현 실험 없음.

<a id="fc32"></a>

### FC32. KoSimpleQA: A Korean Factuality Benchmark with an Analysis of Reasoning LLMs

- **저자:** Donghyeon Ko et al.
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2510.18368) · arXiv 2025 preprint; 후속 게재 확인 안 함
- **논문에서 확인한 내용:** 한국 문화 사실 질문에서 모델의 factuality와 보류를 평가한다.
- **우리 팀의 활용 제안:** 한국어 factual QA 능력의 보조 진단 후보.
- **주의·차이점:** claim–evidence 판정 데이터셋이 아니다. 검색 요약/원문 간 문항 수 차이가 있어 숫자를 고정하지 않았다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc33"></a>

### FC33. 자동화된 팩트체크 과정에서 딥러닝을 이용한 주장(claim) 판별 기법 연구

- **저자:** 박성민
- **출처:** [원문·공식 페이지](https://hdl.handle.net/10371/182352) · 서울대학교 학위논문 저장소; 학위 종류 별도 미확인
- **논문에서 확인한 내용:** 주장의 검증가능성과 검증중요성을 별도 label로 다룬다.
- **우리 팀의 활용 제안:** 기사 전체에서 검증 대상 문장을 고르는 전처리 과제를 이해한다.
- **주의·차이점:** 참·거짓 label을 제공하는 데이터와 다르며 이번 정리는 학위논문 초록 수준이다.
- **확인 수준:** 기관 저장소 서지·초록 확인 (2026-10-23). 재현 실험 없음.

## 멀티모달 확장

<a id="fc18"></a>

### FC18. DEFAME: Dynamic Evidence-based FAct-checking with Multimodal Experts

- **저자:** Tobias Braun; Mark Rothermel; Marcus Rohrbach; Anna Rohrbach
- **출처:** [원문·공식 페이지](https://proceedings.mlr.press/v267/braun25b.html) · ICML 2025
- **논문에서 확인한 내용:** 텍스트/이미지 근거에 대해 도구와 검색 깊이를 동적으로 선택하고 구조적 보고서를 생성한다.
- **우리 팀의 활용 제안:** 선택적 OCR·이미지 근거 검색이 필요한 후속 멀티모달 실험.
- **주의·차이점:** 모든 모달리티·전문가를 첫 버전에 구현하지 않는다. 논문 SOTA 표현을 현재 순위로 재사용하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc34"></a>

### FC34. AVerImaTeC: A Dataset for Automatic Verification of Image-Text Claims with Evidence from the Web

- **저자:** Rui Cao; Zifeng Ding; Zhijiang Guo; Michael Schlichtkrull; Andreas Vlachos
- **출처:** [원문·공식 페이지](https://arxiv.org/abs/2505.17978) · NeurIPS 2025 Datasets and Benchmarks; arXiv acceptance 정보 확인
- **논문에서 확인한 내용:** 실제 이미지–텍스트 주장 1,297개와 멀티모달 근거 QA를 제시한다.
- **우리 팀의 활용 제안:** 향후 사진·캡션의 맥락 일치를 평가할 때 사용한다.
- **주의·차이점:** 이미지 재배포 권리, 역이미지 검색 비용, temporal leakage를 추가 확인한다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

<a id="fc35"></a>

### FC35. Selective Multimodal Retrieval for Automated Verification of Image–Text Claims

- **저자:** Yoana Tsoneva et al.
- **출처:** [원문·공식 페이지](https://aclanthology.org/2026.fever-1.10/) · FEVER 2026 workshop
- **논문에서 확인한 내용:** 질문 유형에 따라 모달리티를 선택적으로 활용하고 최종 판정에는 텍스트 근거를 사용한다.
- **우리 팀의 활용 제안:** 매 단계 VLM을 쓰는 방법과 필요한 순간만 쓰는 방법의 비용 비교.
- **주의·차이점:** 완전한 multimodal fusion 방법으로 잘못 소개하지 않는다.
- **확인 수준:** 원논문 랜딩 페이지/저자 초록·프로젝트 문서 확인; 전체 전문 정독·재현 아님 (2026-10-23). 재현 실험 없음.

## 아직 채워야 할 관련 연구 표

팀원이 이미 찾은 논문 목록은 아직 전달받지 않았다. 목록이 오면 제목·DOI/arXiv ID로 중복 제거하고 다음 칸을 채운다.

| 확인 항목 | 읽을 때 기록할 내용 |
| --- | --- |
| task 동일성 | 뉴스 판정 / 원자 주장 검증 / LLM 생성물 factuality 중 무엇인가 |
| 입력 정보 | claim만 / gold evidence / 검색 가능한 store / open web |
| 적응적 결정 | 질의·출처·도구·깊이·종료 중 모델이 무엇을 선택하는가 |
| 강한 baseline | 같은 모델·근거·검색 예산의 고정 workflow가 있는가 |
| 누출 | 기존 fact-check 문서, 정답 QA, 모델 학습 오염을 어떻게 통제하는가 |
| 평가 | label·evidence·citation·cost의 정의, scorer 버전, 사람 검수 |
| 재현 비용 | 모델 크기, GPU, API, index 구축, cache, Judge까지 포함 |
| 재사용 권한 | 코드·데이터·기사·이미지의 별도 라이선스 |

단순 성능 숫자로 논문 순위를 만들지 않는다. 데이터 split·지표·검색 환경·모델·예산이 다른 숫자는 직접 비교하지 않는다.
