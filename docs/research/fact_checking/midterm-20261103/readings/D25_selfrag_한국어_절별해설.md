# Self-RAG · 한국어 절별 해설

Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

**D25 · 2023 · preprint v1 · 13장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf) · [공식 서지·원문](https://arxiv.org/pdf/2310.11511v1)

## 먼저 붙잡을 질문

‘필요하면 검색하세요’라는 프롬프트와 검색 여부 자체를 학습한 모델은 어떻게 다를까요?

**왜 선택했나 — 검색 필요성과 답의 근거성을 함께 학습하는 접근.** 무조건 같은 수의 문서를 검색하면 불필요한 정보가 유입되고, 관련 문서를 주더라도 생성 내용이 이를 따르지 않을 수 있다는 문제를 다룬다.

## 논문의 논증을 먼저 따라가기

Self-RAG는 검색 여부와 근거 판단을 생성 과정의 학습 목표로 만든다. 문장을 이어 쓸 때 검색할지, 후보 passage가 질문과 관련 있는지, 생성한 내용이 그 문서로 지지되는지, 응답이 유용한지 등을 별도 reflection token으로 표현한다. 모델이 최종 답 전체에 사후 점수 하나를 붙이는 것과 달리, 생성 중 어느 부분이 어떤 자료를 필요로 했는지 표현할 자리가 생긴다.

훈련을 위해 먼저 critic이 학습 사례에 반성 신호를 붙이는 과정을 구성하고, 생성기가 답과 그 신호가 어우러진 시퀀스를 학습하도록 한다. 추론 때에는 필요한 시점에 검색하고 여러 passage에 조건부로 다음 구간 후보를 생성한다. 관련성·지지·유용성 등의 점수를 이용해 후보를 선택하며, 어떤 기준을 얼마나 강조할지는 디코딩 단계의 선택이기도 하다.

이 가이드가 사용하는 v1의 실험은 개방형 QA·사실 검증·장문 생성에서 정답과 사실성·인용 품질을 살핀다. 팀이 프롬프트에 ‘자료가 충분한가?’를 적는 것과, 반성 신호 자체를 학습한 모델은 다른 처치다. 우리의 같은 기반 모델 비교에서는 출처 점검 질문이 실제 검색을 유도했는지, 그리고 그 자료가 판정에 기여했는지를 행동 기록으로 확인할 수 있다.

## §§1–2, Figure 1 · 무조건 검색하는 RAG의 문제에서 출발하기

[PDF pp. 1–3](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=1)

모든 문장에 고정된 수의 문서를 주면 쉬운 문장에도 불필요한 정보가 들어갈 수 있습니다. 관련 문서를 가져와도 생성한 문장이 그 자료의 지지를 받는지는 또 다른 문제입니다. 저자들은 이 두 판단을 토큰 생성 과정에 직접 넣습니다.

## §3.1 · 네 종류의 반성 토큰을 읽는 법

[PDF pp. 3–4](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=3)

Retrieve는 검색 여부, ISREL은 문서 관련성, ISSUP은 답이 문서에 얼마나 지지되는지, ISUSE는 답의 유용성을 나타냅니다. 관련 있는 문서에도 결정적 사실이 없을 수 있고, 유용해 보이는 설명이 근거를 벗어날 수 있습니다. 이 토큰들은 모두 같은 척도의 확률 숫자가 아닙니다.

## §3.2 · critic과 generator가 각각 무엇을 배우나

[PDF pp. 4–6](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=4)

critic이 지도 예시에서 반성 신호를 부여하도록 학습하고 그 신호로 생성기 학습 자료를 구성합니다. 생성기는 일반 텍스트와 반성 토큰이 섞인 출력을 학습합니다. 동결 모델에 지시문 하나를 추가하는 구현과 다른 비용·학습 자료가 필요합니다.

## §3.3 및 §4 · 추론 때 여러 passage를 어떻게 비교하나

[PDF pp. 6–7](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=6)

필요한 지점에서 문서를 검색하고, 각 문서로 다음 생성 구간 후보를 만듭니다. 관련성·지지·유용성 신호로 후보를 평가합니다. 개방형 QA, 사실 검증, 장문 생성은 응답 단위와 채점 방식이 달라 §4의 평가 정의를 함께 봐야 합니다.

## §§5–6 · 우리에게 필요한 관측 단위

[PDF pp. 8–10](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=8)

반성 토큰과 검색·생성 구성을 바꿨을 때 과제별 성적이 어떻게 변하는지 분석합니다. 우리 C2에서는 토큰을 학습하지 않아도 ‘왜 이 문서가 결정적 근거인가’와 ‘추가 검증을 실행했는가’를 기록할 수 있습니다. 이 가이드의 페이지는 로컬에 확보한 arXiv v1을 기준으로 합니다.

## 원문 장면과 읽는 순서

Figure 1에서 검색 실행 시점과 후보 생성 경로를, Table 1에서 각 특수 토큰이 무엇을 판정하는지 읽으세요. 관련성·근거 지지·유용성은 같은 개념이 아닙니다.

**Figure 1 · retrieval and reflection** · [PDF p. 2](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=2)

![PDF p. 2 · Figure 1 · retrieval and reflection](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D25_PDF_02_1.jpg)

저자명은 연결한 공식 서지와 PDF 첫 면 참조 · [원문](https://arxiv.org/pdf/2310.11511v1#page=2) · [이미지 이용 조건](http://creativecommons.org/licenses/by/4.0/)

**Table 1 · reflection-token types** · [PDF p. 4](../../team_guide/papers/P26_2023_Self-RAG_Learning_to_Retrieve%2C_Generate%2C_and_Critique_through_Self-Reflection_arXiv-v1.pdf#page=4)

![PDF p. 4 · Table 1 · reflection-token types](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D25_PDF_04_2.jpg)

저자명은 연결한 공식 서지와 PDF 첫 면 참조 · [원문](https://arxiv.org/pdf/2310.11511v1#page=4) · [이미지 이용 조건](http://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** 단순히 프롬프트에 ‘self-reflect’라고 쓰는 것과 다른 학습 기반 방법이다. 동결 모델로 학부 실험을 한다면 원 방법을 재현했다고 부르기보다 reflection을 차용한 정책으로 명시한다. 모델 자체와 harness 정책을 구분하는 발표의 좋은 기준이다.

**팀에서 풀어 볼 질문.** 거짓 문서가 질문과 아주 관련 있고 그 문서가 생성 답을 직접 지지한다면, 어떤 반성 신호가 높아져도 현실 판정은 틀릴 수 있을까요?

### Self-RAG의 Retrieve·ISREL·ISSUP·ISUSE는 무엇인가요?

**30초 답변:** “검색 여부, 문서 관련성, 답변 지지 여부, 답변 유용성을 표현하도록 학습한 **reflection token 유형**입니다.”

| 토큰 | 평가 입력 | 출력의 뜻 |
|---|---|---|
| Retrieve | x 또는 x와 이미 생성한 y | yes / no / continue로 검색 여부를 나타냅니다. |
| ISREL | 질문 x, 문서 d | relevant / irrelevant: 질문 해결에 도움이 되는 자료인가요? |
| ISSUP | x, d, 출력 y | fully / partially / no support: 출력의 검증할 내용이 문서로 지지되나요? |
| ISUSE | x, 출력 y | 1–5의 유용성 척도입니다. 사실일 확률 20–100%가 아닙니다. |

**연구 연결:** 관련성과 지지 관계를 분리하는 아이디어를 참고할 수 있습니다. 프롬프트에 ISREL이라는 문자열을 쓰는 것만으로 **원 논문의 학습된 Self-RAG**가 구현되었다고 할 수는 없습니다.

[읽기 목록으로 돌아가기](README.md)
