# Search Wisely · 한국어 절별 해설

Search Wisely: Mitigating Sub-optimal Agentic Searches By Reducing Uncertainty

**D15 · 2025 · preprint · 15장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf) · [공식 서지·원문](https://arxiv.org/pdf/2505.17281)

## 먼저 붙잡을 질문

검색 횟수를 줄였다는 사실만으로 ‘언제 검색해야 하는지’를 잘 배웠다고 볼 수 있을까요?

**왜 선택했나 — 검색을 했다는 사실과 검색이 필요했다는 판단을 구별한다.** Agent가 이미 답할 수 있는 문제에서도 검색하거나, 외부 정보가 필요한 문제에서 검색을 생략하는 over-search/under-search를 다룬다.

## 논문의 논증을 먼저 따라가기

최종 답 하나에 검색이 세 번 들어갔다면 그 세 번이 모두 필요했을까? 저자들은 질문 전체보다 작은 ‘검색을 결정한 단계’를 단위로 삼는다. 앞선 문맥과 모델만으로도 해당 하위 답을 얻을 수 있었는데 검색한 경우를 과잉 검색으로 정의하고, 검색하지 않은 단계가 잘못된 하위 답으로 이어지는 경우를 과소 검색으로 정의한다. 최종 정확도가 같은 두 궤적에도 서로 다른 비효율이 남는다.

실행 궤적에서 검색 직전의 조건을 분석해, 검색 자료가 없더라도 하위 답을 냈을지와 검색 여부에 대한 확신을 조사한다. 한 분석에서는 특정 모델이 검색한 단계 중 27.7%가 피할 수 있는 검색으로 분류되었다. 이어 β-GRPO로 정답과 검색 결정의 확신을 고려하는 보상을 주어, 모델이 언제 자료를 구할지 학습시킨다.

일곱 QA 벤치마크에서 최종 exact match와 두 종류의 검색 오류를 점검한다. 이 논문에서 하위 답을 이미 맞힐 수 있다는 사실은 검색 효용이 낮다는 근거가 될 수 있다. 우리 인용 과제에서는 이미 알고 있는 날짜여도 원문을 확보해야 성공한다. 따라서 ‘답에는 필요 없음’과 ‘근거 제출에는 필요함’을 다른 열에 두어야 같은 행동을 공정하게 해석할 수 있다.

## §§1–2 · 검색한 단계와 검색하지 않은 단계

[PDF pp. 1–3](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf#page=1)

모델이 이미 답할 수 있는 정보에도 검색을 쓰는 over-search, 정보가 부족한데 검색 없이 진행하는 under-search를 구분합니다. 후자는 ‘검색한 횟수’를 세는 로그만으로는 발견하기 어렵습니다. 저자들은 실제 단계에서 검색이 유용했는지를 진단하는 방식으로 두 오류를 구별합니다.

## §2, Figures 1–3 · 분모가 질문인지 검색 단계인지 확인하기

[PDF pp. 2–3](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf#page=2)

R1-Searcher의 20.2%, Search-R1의 27.7%는 해당 분석에서 불필요한 것으로 진단된 검색 단계 비율입니다. 한 질문에서 두 번 검색하면 두 단계가 생길 수 있습니다. 우리 외부 검색률처럼 ‘질문 중 적어도 한 번 검색한 비율’과 수치가 다릅니다.

## §3 · 불확실성을 학습 신호로 연결하기

[PDF pp. 3–4](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf#page=3)

β-GRPO는 검색 질의를 생성하는 구간의 불확실성을 보상·학습에 반영하는 GRPO 변형입니다. 최종 답의 정오만으로는 중간 질의가 적절했는지 충분히 알려주지 않는다는 발상입니다. 이 기법을 쓰려면 정책 학습이 필요하지만 지표를 이해하는 데 팀의 RL 도입은 필요하지 않습니다.

## §§4–5 · 품질과 탐색 행동의 변화를 같이 보기

[PDF pp. 4–6](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf#page=4)

정답 지표와 과소·과잉 검색 진단을 비교합니다. 검색을 일괄 줄인 정책이라면 비용은 줄면서도 필요한 탐색을 놓칠 수 있으므로, 평균 호출 횟수 하나로는 학습 목표를 달성했다고 말할 수 없습니다.

## §6 · 발표 15장으로 이어지는 질문

[PDF p. 5](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf#page=5)

우리 C1에서 실제로 본 문서가 충분했는지를 사람이 주석하고, C2의 검색률을 조건별로 계산합니다. 그것은 이 논문의 단계별 과잉 검색 지표와 다른 팀 정의 지표입니다. 비용 판단은 판정 회복·손상과 나란히 놓았을 때 의미가 있습니다.

## 원문 장면과 읽는 순서

Figures 1–3의 분석 단위는 탐색 결정의 단계입니다. 이미 아는 것을 다시 검색하는 경우와, 새 정보가 필요한데 검색을 생략한 경우가 다른 분모에서 계산됩니다.

**Figures 1–3 · over-search and under-search** · [PDF p. 2](../../knowledge-revision/papers/D15_2025_Search_Wisely_Mitigating_Sub-optimal_Agentic_Searches_By_Reducing_Uncertainty.pdf#page=2)

![PDF p. 2 · Figures 1–3 · over-search and under-search](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D15_PDF_02_1.jpg)

Peilin Wu et al. · [원문](https://arxiv.org/pdf/2505.17281v2#page=2) · [이미지 이용 조건](https://creativecommons.org/licenses/by-sa/4.0/)

## 논문 결과와 우리 설계의 경계

**원문에서 보고한 결과.** 논문은 한 모델의 검색 단계 중 27.7%가 회피 가능했던 분석과 여러 QA 데이터의 개선을 보고한다.

**우리 연구에서의 역할.** 인용 없는 QA에서는 이미 맞힐 수 있으면 검색이 낭비일 수 있다. 우리 task는 검증 근거도 제출하므로 같은 검색이 필요한 행동이 될 수 있다. 따라서 질문별 정답률뿐 아니라 인용의 충분성과 비용을 함께 놓고, 학습 기반 controller와 프롬프트 기반 정책을 구별한다.

**팀에서 풀어 볼 질문.** 한 주장에서 세 번 검색한 경우 우리 C2 외부 검색률의 분자에 몇 건으로 넣나요? 검색 비용에는 몇 회로 기록하나요?

[읽기 목록으로 돌아가기](README.md)
