# 중간 발표·팀 논의 묶음

2026-11-03 논의 기준 · 2026-11-04 공유

**[팀 논의·연구 방향·Task](팀논의_연구방향과_Task.md)**에서 시작하세요. 무엇을 검증할지, C0/C1/C2가 어떻게 다른지, 팀원의 50개 사례와 평가 지표를 어떻게 이어받을지 정리했습니다.

| 자료 | 내용 |
|---|---|
| [PowerPoint 18장](NLP_Team5_Midterm_18slides.pptx) | 문헌 15장 + Task 후보 A/B/C 3장. 제목·출처·Task 문안은 편집 가능한 텍스트이며 논문 캡처는 이미지입니다. |
| [팀 논의 HTML](팀논의_연구방향과_Task.html) · [MD](팀논의_연구방향과_Task.md) | 현재 질문, 네 근거 조건, 비교군, 데이터·metric 초안, 팀이 결정할 부분 |
| [발표 논문 읽기 지도 HTML](발표논문_읽기지도.html) · [MD](발표논문_읽기지도.md) | 15개 주제와 32편을 기존 통합·개별 해설 및 공식 원문에 연결 |
| [기존 31편 통합 가이드](../knowledge-revision/팀공유_연구가이드.html) | 기존 설명과 페이지 맥락 읽기를 보존한 공통 참고자료 |

## 개별 해설

기존 통합 가이드를 중복 작성하지 않고 빠진 **RAGuard와 Stop-RAG 두 편**을 새로 작성했습니다. 기존에 로컬에서 읽었던 개별 해설도 함께 공유합니다.

| 논문 | 읽기 문서 | 발표 연결 |
|---|---|---|
| RAGuard — 새 해설 | [HTML](papers/RAGuard_한국어_절별해설.html) · [MD](papers/RAGuard_한국어_절별해설.md) | 10장: 자연적 오도, 실제 검색/직접 노출, CRAG 외부 검색 비교 |
| Stop-RAG — 새 해설 | [HTML](papers/Stop_RAG_한국어_절별해설.html) · [MD](papers/Stop_RAG_한국어_절별해설.md) | 14장: Q-network, offline trajectory, 종료 정책과 비용 |
| ClaimCLAIRE | [HTML](papers/ClaimCLAIRE_한국어_절별해설.html) · [MD](papers/ClaimCLAIRE_한국어_절별해설.md) | 6장: 검증 단위와 Agent 구성 |
| Flip Risk | [HTML](papers/Flip_Risk_한국어_절별해설.html) · [MD](papers/Flip_Risk_한국어_절별해설.md) | 7장: 근거 비율·순서와 판정 전환 |
| HAE-GEO | [HTML](papers/HAE_GEO_한국어_절별해설.html) · [MD](papers/HAE_GEO_한국어_절별해설.md) | 8·15장: 오도 조건과 행동 평가 |
| DRNoise | [HTML](papers/DRNoise_한국어_절별해설.html) · [MD](papers/DRNoise_한국어_절별해설.md) | 10장: 오도 문서 노출과 근거 연결 실패 |
| CRAG | [HTML](papers/CRAG_한국어_절별해설.html) · [MD](papers/CRAG_한국어_절별해설.md) | 12장: 평가기와 외부 검색 분기 |
| BeliefRAG | [HTML](papers/BeliefRAG_한국어_절별해설.html) · [MD](papers/BeliefRAG_한국어_절별해설.md) | 14장: 상태를 사용하는 제어 |

[이전 연구 방향 지도](papers/연구방향_문헌지도.html)와 [중간 발표 논지 메모](papers/연구과정_중간발표_논지.html)는 질문이 구체화된 과정을 읽는 자료입니다. 현재 정리안은 위 팀 논의 문서를 기준으로 보세요.

## 사용·편집

HTML은 **Download raw file**로 내려받아 브라우저에서 열면 됩니다. 캡처는 HTML 안에 포함되어 있으며 눌러서 전체 페이지를 확대할 수 있습니다. 새 문서에는 절 검색과 목차가 있습니다. 다른 문서 사이의 링크까지 로컬에서 이용하려면 저장소를 함께 내려받으세요.

편집 원본은 Markdown입니다. 새 문서 네 개는 `tools/build_html.py`로 HTML을 생성합니다. Python의 `beautifulsoup4`와 Pandoc을 사용하며 `tools/figures.json`에 캡처 위치·공식 출처·PDF 해시를 기록했습니다. 기존 개별 해설의 HTML은 이전 생성본을 보존하고 공유 경로를 연결했습니다.

## 범위·출처

18장 PPTX는 **문헌 15장 뒤에 후보 3장을 붙인 논의용 편집본**입니다. 발표에 쓸 Task 슬라이드는 팀 논의 후 선택합니다. 별도 발표 대본은 이번 공유 묶음에 포함하지 않았습니다. 연구 질문과 metric은 제안이고 논문 표의 수치는 원 연구 결과입니다.

논문 캡처는 출처·제목·연도·페이지를 표시한 학술 설명용 인용입니다. 원문 전체 PDF나 유료 원문을 이 폴더에서 재배포하지 않습니다. 공개 원문은 각 논문의 공식 링크로 연결합니다. 기존 31편 가이드와 팀원이 작성한 평가 자료는 유지했습니다.
