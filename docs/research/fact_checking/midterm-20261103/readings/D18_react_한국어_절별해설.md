# ReAct · 한국어 절별 해설

ReAct: Synergizing Reasoning and Acting in Language Models

**D18 · 2023 · ICLR · 1장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf) · [공식 서지·원문](https://arxiv.org/pdf/2210.03629v3)

## 먼저 붙잡을 질문

같은 사실을 검색했는데 검색 결과가 예상과 다르면 다음 행동이 바뀔까요?

**왜 선택했나 — 에이전트가 필요한 위치를 구체적으로 보여준다.** 사고와 행동을 따로 수행하던 설정에서, 행동으로 새 관측을 얻고 이를 바탕으로 계획을 갱신하는 반복을 제안한다.

## 논문의 논증을 먼저 따라가기

추론만 생성하면 예상했던 답을 뒷받침하는 설명이 길어질 수 있고, 행동만 예측하면 검색이 실패했을 때 다음에 무엇을 찾아야 하는지 놓칠 수 있다. ReAct는 질문·이전 행동·환경의 관찰을 이어 적는 기록에 짧은 추론 단계를 끼워 넣는다. 모델이 행동을 내면 환경이 관찰을 돌려주고, 그 결과가 다음 추론과 행동의 입력이 된다. Figure 1에서 Front Row 검색이 정확히 일치하지 않아 ‘소프트웨어’ 한정어를 붙이는 장면이 이 의존 관계를 보여준다.

HotpotQA와 FEVER에서는 Wikipedia에서 검색·찾기·종료하는 인터페이스로 네 방식의 행동 차이를 본다. 연구진은 환각을 줄이는 측면과 올바른 문서를 못 찾았을 때 검색이 발목을 잡는 측면을 모두 분석하고, 내부 추론과 검색 궤적의 장점을 결합하는 조건도 조사한다. 예시 궤적의 성공 여부는 Figure 1로, 여러 문제의 결과와 실제 실패 유형은 뒤의 표로 확인할 수 있다.

ALFWorld와 WebShop에서는 환경 상태가 변하기 때문에 관찰의 역할이 더 뚜렷하다. 물건이 없다는 응답을 받으면 다음 위치나 행동을 바꾸어야 한다. 우리 팩트체크에서도 ‘검색 계획을 설명했다’와 ‘원문을 실제로 열어 기준일을 얻었다’가 다른 사건이다. 일반 ReAct를 비교군으로 두면 같은 도구를 가진 상태에서 별도의 근거 기록 방식이 다음 행동에 더하는 효과를 물을 수 있다.

## §§1–2, Figure 1 · 생각·행동·관찰이 번갈아 등장하는 이유

[PDF pp. 1–3](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf#page=1)

CoT만으로 추론하면 외부 사실의 오류가 다음 단계로 이어질 수 있고, 행동만 나열하면 어떤 정보가 빠졌는지 계획하기 어렵습니다. ReAct의 시범 궤적에는 추론 텍스트, 도구 행동, 환경이 돌려준 관찰이 구분되어 있습니다. 모델이 검색하겠다고 서술한 것과 검색 도구가 실제 결과를 반환한 것은 다른 사건입니다.

## §§3.1–3.2 · 어떤 도구를 사용할 수 있었나요?

[PDF pp. 4–5](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf#page=4)

HotpotQA와 FEVER에서 위키백과 환경에 검색·찾기·종료 동작을 둡니다. 검색은 항목을 열어 보고, 찾기는 현재 항목에서 단어 주변의 문장을 따라갑니다. 기존 추론 방식과 행동 방식, 둘을 결합한 방식에 같은 질문을 주어 도구 관찰이 어떤 오류를 해소하는지 봅니다.

## §3.3 · 성공과 실패의 궤적을 함께 읽기

[PDF pp. 5–7](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf#page=5)

검색 근거가 기존 가정을 정정하는 경우와, 부적절한 검색을 반복해 정답에 도달하지 못하는 경우를 나눠 봅니다. 추론을 잘한다는 것과 알맞은 검색어로 도구를 쓰는 것은 별개입니다. Table 1에서는 과제별 정답률과 결합 전략을 해당 조건에서 읽어야 합니다.

## §4 · 왜 ALFWorld와 WebShop까지 평가했을까요?

[PDF pp. 7–9](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf#page=7)

물건을 찾거나 쇼핑 조건을 만족시키려면 환경 상태가 매 행동에 따라 달라집니다. 이전 관찰을 기억하고 다음 행동을 바꿨을 때 과제를 완료하는지 봅니다. QA의 한 번짜리 정답 지표와 달리 여러 행동이 이어진 최종 성공을 측정한다는 점이 중요합니다.

## §§5–6 · 팩트체크에서 가져올 단위

[PDF p. 9](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf#page=9)

우리가 기록할 단위는 ‘한 번 더 생각함’보다 검색 행동, 실제 반환 문서, 그 뒤의 판정입니다. C2가 시간대가 빠졌다고 판단한 뒤 원문을 열었는지를 보면 단순히 설명이 길어진 것과 판단에 쓸 자료가 늘어난 것을 나눌 수 있습니다.

## 원문 장면과 읽는 순서

Figure 1에서 행동 직후의 observation을 먼저 찾으세요. 이 텍스트가 모델이 써낸 추론인지, 환경이 돌려준 결과인지가 다음 단계의 의미를 바꿉니다.

**Figure 1 · prompting and interaction examples** · [PDF p. 2](../../team_guide/papers/FC10_2023_ReAct_Synergizing_Reasoning_and_Acting_in_Language_Models.pdf#page=2)

![PDF p. 2 · Figure 1 · prompting and interaction examples](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D18_PDF_02_1.jpg)

Shunyu Yao et al. · [원문](https://arxiv.org/pdf/2210.03629v3#page=2) · [이미지 이용 조건](http://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** ReAct는 핵심 비교군이다. 검색 순서를 정답에 맞춰 사람이 지정하면 Agent의 행동 선택 능력을 비교하기 어려워진다. 대신 공통 도구·예산을 주고, 각 질의가 어떤 미해결 조건을 확인하려 했는지 간단한 행동 목적과 관찰을 기록한다.

**팀에서 풀어 볼 질문.** ‘공식 발표를 찾아야겠다’에서 끝난 실행과 실제로 원문을 열고 시간대를 확인한 실행을 로그에서 어떤 필드로 구분할까요?

### ReAct는 CoT나 고정 workflow와 어떻게 다른가요?

**30초 답변:** “ReAct는 **Reasoning과 Acting을 번갈아 수행하면서 Observation을 다음 선택에 반영**합니다. 고정 workflow와 달리 중간 결과에 따라 검색 대상이나 종료 시점을 바꿀 수 있습니다.”

**풀어서 설명:** 그림의 Thought는 계획·판단을 표현한 텍스트, Act는 Search·Lookup·Finish 같은 행동, Obs는 환경이 반환한 결과입니다. CoT만 수행하면 추가 외부 정보를 얻지 않고 추론 문장을 생성할 수 있고, Act-only는 명시적인 추론 흔적 없이 행동을 진행합니다.

**연구 연결:** C2에서 근거 부족·충돌을 보고 **무엇을 확인할지 결정하는 것**이 Agent의 역할입니다. 기록된 Thought는 관찰 가능한 출력이지 모델 내부 계산을 모두 보여 주는 창은 아닙니다.

[읽기 목록으로 돌아가기](README.md)
