# ClaimDecomp · 한국어 절별 해설

Generating Literal and Implied Subquestions to Fact-check Complex Claims

**D30 · 2022 · EMNLP · 6장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf) · [공식 서지·원문](https://aclanthology.org/2022.emnlp-main.229/)

## 먼저 붙잡을 질문

주장에 명시되지 않은 질문을 만드는 일이 왜 팩트체크에 필요한가요?

**왜 선택했나 — 필요한 확인 질문이 주장 표면에 모두 쓰여 있지는 않다.** 숫자 둘이 각각 참이어도 비교한 기간이나 지표가 다르면 전체 주장이 오도될 수 있다. 단순 문장 분할과 의미 있는 검증 질문 생성의 차이를 보여준다.

## 논문의 논증을 먼저 따라가기

정치적 주장은 각 수치가 맞아도 서로 다른 기간이나 지표를 비교해 잘못된 인상을 줄 수 있다. 연구진은 PolitiFact의 복합 주장 1,000여 개와 전문 검증자의 설명을 주석자에게 주고, 그 설명이 성립하려면 답해야 할 예/아니오 질문을 작성하게 했다. 문장에 드러난 사실과 그 비교가 공정하려면 암묵적으로 참이어야 하는 조건이 모두 포함된다. Figure 1의 범죄율 예시에서 ‘15% 감소했나’와 ‘두 통계는 비교 가능한가’가 다른 종류의 질문이다.

자동 생성 모델이 이러한 질문을 만들어낼 수 있는지 시험할 때, 주장만 읽는 조건에서는 검증자가 사후에 확보한 배경을 알 수 없다는 비대칭이 생긴다. 실제로 함축 질문이 특히 어렵다. §5는 생성 질문의 유형과 관련성을 분석하고, 일부 검증 항목에서는 ‘예’의 비율을 여섯 단계 판정에 매핑하는 단순 집계도 시험한다. 모든 하위 질문의 중요도가 같지 않다는 사례가 이 규칙의 약점을 드러낸다.

§6은 분해한 질문이 원 주장 전체를 한 번에 질의할 때보다 필요한 근거를 찾는 데 도움을 주는지도 본다. 질문이 자연스럽게 들리는지와 검증에 필요한 문서를 가져오는지는 다른 평가다. 우리 금 근거를 만들 때 팀은 암묵적 조건을 적어 둘 수 있지만, 실행 모델에는 그 답안지를 주지 않고 어떤 확인 질문을 스스로 제기했는지 봐야 한다.

## §§1–2, Figure 1 · 문장에 없지만 확인해야 할 조건

[PDF pp. 1–2](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf#page=1)

수치가 늘었다는 주장은 과거와 현재의 비교 단위·분모·기준일을 알아야 검증할 수 있습니다. 문장에서 직접 읽히는 literal 질문과, 판정하려면 추가로 알아야 하는 implied 질문을 구분합니다. 분해의 출력은 원 주장에 필요한 정보를 찾는 하위 질문입니다.

## §3 · 사람의 팩트체크 설명을 어떻게 주석에 쓰는가

[PDF pp. 3–4](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf#page=3)

실제 팩트체크 설명을 참고하여 주장의 검증에 필요한 질문을 구성합니다. 설명에 접근한 사람이 중요한 조건을 잘 찾는 것과, 추론 시 모델이 주장만 보고 같은 조건을 찾는 것은 다른 과제입니다. 우리 gold를 만들 때 사용하는 배경 설명을 모델에 그대로 보여 주면 두 역할이 섞입니다.

## §§4–5.2 · 자동 분해와 사람 평가의 차이

[PDF pp. 4–7](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf#page=4)

하위 질문 생성 방식을 비교하고 질문 유형·유용성을 평가합니다. QABriefs와 비교한 Table 5에서는 210개 예시의 질문 세트 유용성(1~5) 평균이 2.88과 3.60입니다. 이 점수는 주장 판정 정확도가 아니라 사람이 평가한 질문의 도움 정도입니다.

## §§5.3–6 · 더 나은 질문이 더 나은 근거를 찾는가

[PDF pp. 7–8](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf#page=7)

답을 모아 원 주장의 진위를 설명할 수 있는지와, 하위 질문으로 검색했을 때 관련 근거를 더 잘 찾는지를 따로 봅니다. 하위 질문 하나가 유창해도 기간이나 주체를 틀리면 다른 사실에 대한 자료를 찾게 됩니다.

## §§7–9 · 우리의 원자적 주장 선택과 양립하는 부분

[PDF pp. 9–10](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf#page=9)

검증 단위는 한 주장으로 두더라도, 그 주장에 필요한 확인 질문을 복수로 만들 수 있습니다. ‘한국시간 오전 5시’ 판정에는 발표 원시각과 시간대 변환이 필요합니다. 둘은 두 개의 독립 평가 사례가 아니라 하나의 판정에 필요한 정보입니다.

## 원문 장면과 읽는 순서

Figure 1에서 원 주장에 문자 그대로 적힌 요소와, 그것을 확인할 때만 드러나는 비교 기준을 나누어 읽어 보세요.

**Figure 1 · explicit and implicit questions** · [PDF p. 1](../../team_guide/papers/P14_2022_Generating_Literal_and_Implied_Subquestions_to_Fact-check_Complex_Claims_%28ClaimDecomp%29.pdf#page=1)

![PDF p. 1 · Figure 1 · explicit and implicit questions](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D30_PDF_01_1.jpg)

저자명은 연결한 공식 서지와 PDF 첫 면 참조 · [원문](https://aclanthology.org/2022.emnlp-main.229.pdf#page=1) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** evidence ledger의 requirement를 날짜·정의·분모·비교 대상까지 확장하는 참고다. 데이터 작성 때 전문가 설명을 보고 만든 질문을 실험 입력으로 그대로 주면 solver에 정보를 누출할 수 있으므로, annotation과 task-time 생성 질문을 분리한다.

**팀에서 풀어 볼 질문.** ‘매출이 두 배’라는 한 주장을 검증할 때 어느 기간·회사·회계 기준을 묻는 것이 원래 주장을 보존하는 질문일까요?

### Atomic claim과 subquestion은 같은 것인가요?

**30초 답변:** “Atomic claim은 **단일 판정 대상으로 만든 명제**, subquestion은 그 명제를 검증하기 위해 **알아봐야 할 질문**입니다. 표현 형태와 역할이 다릅니다.”

**작은 예:** 주장 ‘범죄가 15% 줄었다’에 대해 ‘어느 기간인가요?’, ‘어떤 범죄 정의인가요?’, ‘분모가 같은가요?’가 subquestions입니다. 원자적 주장으로 만들면 ‘정해진 지역·기간·분류에서 건수가 기준 대비 15% 감소했다’처럼 판정 단위를 명시합니다.

**연구 연결:** ClaimDecomp의 Literal 질문은 명시된 내용을, Implied 질문은 비교를 성립시키는 숨은 조건을 점검합니다. 자연어 질문·주장 목록이며 **Horn clause 논리식으로 변환했다는 뜻은 아닙니다.**

[읽기 목록으로 돌아가기](README.md)
