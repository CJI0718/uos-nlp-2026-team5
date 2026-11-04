# Real Documents · 한국어 절별 해설

Studying Large Language Model Behaviors Under Context-Memory Conflicts With Real Documents

**D03 · 2024 · COLM · 4장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf) · [공식 서지·원문](https://arxiv.org/html/2404.16032v2)

## 먼저 붙잡을 질문

질문에 자료 없이 틀린 모델에게 정답이 들어 있는 실제 문서를 주면 언제 교정될까요?

**왜 선택했나 — 우리 직관에 반대되는 결과도 포함하기 위해.** 이 논문은 이전 연구의 ‘맞는 내부 답 + 인위적으로 틀린 문서’ 설정을 바꾼다. 실제 문서가 모델의 틀린 답을 교정하는 상황에서는 생각보다 답을 잘 고친다는 것이 중요한 주장이다. 따라서 내부 지식과 문서의 충돌을 모두 같은 난제로 묶으면 안 된다.

## 논문의 논증을 먼저 따라가기

기존 실험에서 외부 문서의 정답 문자열을 가짜 값으로 바꾸면 모델이 원래 답을 고수하는 것이 오히려 바람직할 수 있다. 저자들은 그 상황을 뒤집었다. Natural Questions·SQuAD 등 여섯 독해 데이터셋의 원래 문서와 정답을 보존하고, 자료 없이 질문했을 때 해당 모델이 틀린 사례를 고른다. Figure 1의 선별 과정을 거치므로 동일한 질문 모음에서 시작해도 모델마다 최종 평가 집합이 달라진다.

선별한 사례에 실제 정답 문서를 주고 다시 묻는다. 짧은 답의 표현 차이를 처리하기 위해 답의 동등성을 평가하고, 응답을 기존 오답 유지, 정답으로 갱신, 다른 오답으로 갱신의 세 범주로 나눈다. Table 2는 이때의 입력 집합이고 Table 3은 그 집합에서 일어난 변화다. Llama2-7B의 여섯 데이터셋 평균에서 정답으로 바뀐 비율은 77.0%이고 다른 오답으로 바뀐 비율은 21.3%다.

그다음에는 원래 오답을 계속 낸 소수 사례로 돌아간다. 문서 어딘가에 기존 오답 문자열이 등장하면 모델이 그 문자열에 머무르기 쉬운지 조사한다. 문서가 정답을 포함했다는 사실과 독자가 그 문서에서 올바른 관계를 골랐다는 사실이 갈라지는 대목이다. 우리 실험에서도 에이전트가 연혁 원문을 열었는데 설립일 대신 같은 면의 개편일을 읽었다면, 검색 성공과 독해 실패를 동시에 기록할 수 있다.

## §§1–2 · 인위적으로 만든 충돌에서 실제 문서로

[PDF pp. 1–3](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=1)

기존 답과 다른 사실을 일부러 심은 문서에서는 외부 문서를 따르는 것이 오답일 수 있습니다. 이 연구는 반대로 처음 답이 틀렸고, 실제 문서에 정답이 있는 경우를 만듭니다. 같은 ‘답 변경’이 여기서는 바람직한 교정일 수 있습니다.

## §§3.1–4.1, Table 2 · 실험에 들어오는 사례의 선택

[PDF pp. 3–6](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=3)

공개 QA 데이터에서 모델이 자료 없이 틀린 사례를 선별하고, 근거 문서에 정답이 있는 상황을 구성합니다. 모델이 달라지면 처음 틀린 질문의 목록도 달라집니다. 일부러 반드시 틀리게 만든 질문을 모든 모델에 동일하게 입력한 실험이 아닙니다. 비교 전에 Table 2의 모델별 표본 수를 봐야 합니다.

## §4.2, Table 3 · 틀린 답이 사라져도 교정이라고 할 수 있나

[PDF pp. 6–7](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=6)

세 결과는 원래 오답 유지, 정답으로 수정, 다른 오답으로 수정입니다. Llama2-7B의 NQ 행은 각각 1.4%, 79.6%, 19.0%입니다. 세 수치의 분모는 선별된 그 모델의 초기 오답 사례입니다. 둘째와 셋째를 합치면 ‘변경률’이지만, 실제로 옳게 고친 비율은 둘째 열입니다.

## §§4.3–4.4 · 기존 오답 문자열이 문서 안에도 있는 경우

[PDF pp. 6–9](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=6)

오답 문자열이 다른 관계로 등장하면 모델이 그 문자열에 매달릴 수 있습니다. 저자들은 관련 문자열의 등장 여부를 바꾸는 개입으로 이 단서를 점검합니다. ‘문서에 정답 문자열 있음’과 ‘정답을 지지하는 관계를 올바르게 읽음’을 구분하는 분석입니다.

## §§5–8 · 실험 범위를 우리 데이터로 옮기기

[PDF pp. 9–11](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=9)

우리 C1은 올바른 자료를 못 찾는 상황과 틀린 자료를 찾는 상황도 포함합니다. 이 논문에서 골라 놓은 조건과 맞는 부분은 ‘올바른 자료가 실제로 노출된 초기 오답’입니다. 그 하위 집합의 회복률을 보면 검색 실패와 문서 독해 실패를 가를 수 있습니다.

## 원문 장면과 읽는 순서

Figure 1은 누가 실험에 들어오는지를, Table 3은 선별된 사례에서 오답이 어떤 방향으로 바뀌었는지를 보여줍니다. 먼저 모델별 사례 수를 보고 각 행의 세 결과를 읽으세요.

**Figure 1 · sample selection** · [PDF p. 4](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=4)

![PDF p. 4 · Figure 1 · sample selection](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D03_PDF_04_1.jpg)

Evgenii Kortukov et al. · [원문](https://arxiv.org/pdf/2404.16032v2#page=4) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

**Table 3 · update, retain, or change incorrectly** · [PDF p. 6](../../knowledge-revision/papers/D03_2024_Real_Documents_Knowledge_Conflicts.pdf#page=6)

![PDF p. 6 · Table 3 · update, retain, or change incorrectly](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D03_PDF_06_2.jpg)

Evgenii Kortukov et al. · [원문](https://arxiv.org/pdf/2404.16032v2#page=6) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**원문에서 보고한 결과.** Table 3의 Llama2-7B는 초기 오답 유지 평균 1.6%, 정확한 수정 77.0%, 다른 오답으로 수정 21.3%다. Mixtral-8x7B는 각각 2.2%, 77.4%, 20.6%다.

**우리 연구로 가져올 부분.** 이 논문은 ‘Agent가 언제나 정답 문서까지 찾아낼 것’이라는 가정을 풀어야 한다는 이유를 준다. 획득 실패와 해석 실패를 분리하고, 추가 검색이 정말 필요한 경우와 주어진 문서만 잘 읽으면 되는 경우를 구분한다. 낮은 오답 유지율도 정직하게 소개한다.

**팀에서 풀어 볼 질문.** C1이 틀리고 C2에서 다른 오답을 냈다면 ‘판정 변경’에는 들어가지만 ‘회복’에는 들어가지 않는 이유는 무엇일까요?

### Real Documents는 원래 틀릴 수밖에 없는 문제를 만든 연구인가요?

**30초 답변:** “공개 QA 데이터에서 **특정 모델이 자료 없이 틀렸던 경우**를 선별하고, 실제 정답 근거 문서를 제공했을 때 답이 어떻게 변하는지 분석한 연구입니다.”

**풀어서 설명:** NQ·SQuAD·NewsQA·TriviaQA·SearchQA·HotpotQA는 논문 저자들만의 비공개 문제집이 아니라 기존 QA 자원입니다. 모든 모델이 반드시 틀려야 하는 문제가 아니라 **모델별 기준 응답에 의해 선택된 분석 집합**입니다. Figure 1의 단계적 표본 선택이 이 분모를 정합니다.

**연구 연결:** 우리도 ‘모델이 알고 있는 사실’ 집합을 사전 응답으로 선별하면, 전체 사실에 대한 성능과 **선별된 집합에서의 강건성**을 구분해 보고해야 합니다.

### Table 3의 P(R), P(Uc), P(Ui)와 79.6은 무엇인가요?

**30초 답변:** “P(R)은 **기존 답 유지**, P(Uc)는 **올바른 답으로 수정**, P(Ui)는 **다른 오답으로 수정**한 비율입니다. 여기서 R은 recovery가 아니라 retain입니다.”

| 기호 | 원래 답 → 근거 제공 후 답 | 의미 |
|---|---|---|
| P(R) | 오답 A → 오답 A | 기존 응답 유지(Retain) |
| P(Uc) | 오답 A → 정답 | 올바른 갱신(Update correctly) |
| P(Ui) | 오답 A → 다른 오답 B | 잘못된 갱신(Update incorrectly) |

**대표 수치:** Llama2-7B의 NQ 행은 **1.4%, 79.6%, 19.0%**입니다. 이 분석 집합에서 약 79.6%가 문맥에 맞는 정답으로 교정됐다는 뜻입니다. **전체 NQ 정답률 79.6%**라는 뜻은 아닙니다. 세 열의 합은 반올림 오차를 제외하면 100%가 됩니다.

**연구 연결:** 기존 답을 버렸다는 사실만으로 성공으로 세지 않고, **정답으로 갔는지 다른 오답으로 갔는지**를 나눕니다.

[읽기 목록으로 돌아가기](README.md)
