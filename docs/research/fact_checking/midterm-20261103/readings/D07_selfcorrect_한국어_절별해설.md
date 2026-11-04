# Intrinsic Self-Correction · 한국어 절별 해설

Large Language Models Cannot Self-Correct Reasoning Yet

**D07 · 2024 · ICLR · 11장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf) · [공식 서지·원문](https://arxiv.org/pdf/2310.01798)

## 먼저 붙잡을 질문

모델에 ‘다시 확인해 보라’고 하면 언제 원래 맞은 답이 틀리게 바뀔까요?

**왜 선택했나 — 긍정적인 자기교정 연구와 함께 읽을 대조 문헌.** 모델이 정답을 모르는 상태에서 자신의 답을 평가하고 고칠 수 있는지 엄격하게 묻는다. 제목의 부정적 인상을 모든 시기의 LLM에 대한 불가능성 정리로 받아들이기보다, 무엇을 intrinsic self-correction으로 정의했는지부터 읽어야 한다.

## 논문의 논증을 먼저 따라가기

저자들은 ‘다시 풀었더니 나아졌다’는 관찰에 어떤 정보가 들어 있었는지부터 묻는다. 외부 근거와 정답 신호 없이 모델이 자신의 초기 답을 재검토하는 상황을 intrinsic self-correction으로 정의한다. 추론 문제에 첫 답을 받은 뒤 비판·수정을 시키고, 전체 정확도뿐 아니라 처음 맞은 답과 틀린 답이 각각 어디로 이동했는지 확인한다.

일부 오답이 고쳐져도, 처음 맞은 답을 틀린 답으로 바꾼 수가 그보다 많으면 평균은 떨어진다. 정답을 이미 알고 오답만 골라 재시도하거나 적절한 시점에 반복을 멈추게 해 주는 설정에서는 이 손실이 보이지 않는다. §3.3은 모델이 오류 여부를 얼마나 잘 구별하는지 살펴본다. §4에서는 여러 답을 낸 효과를 분리하기 위해 에이전트 토론을 여러 독립 답의 합의(self-consistency)와도 비교한다.

§5는 수정 요청의 표현 자체가 ‘첫 답이 틀렸으니 바꾸라’는 신호로 작용할 수 있음을 다룬다. 그래서 같은 문제를 다시 묻는 프롬프트도 하나의 실험 조건이 된다. D06과 나란히 읽으면 두 연구의 질문 차이가 또렷하다. 외부 관찰을 얻는 우리 에이전트에서는 비평 문구와 새 근거를 각각 기록해야 무엇이 판정을 바꿨는지 따질 수 있다.

## §§1–2 · ‘스스로 고친다’의 정보 조건

[PDF pp. 1–3](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=1)

도구나 정답 신호 없이 같은 모델이 기존 추론을 재검토하는 intrinsic self-correction을 연구합니다. 외부 검증기가 틀렸다는 사실을 먼저 알려 준 조건은 더 많은 정보를 줍니다. 실험을 비교하려면 수정 시작 전에 모델이 무엇을 알았는지부터 같게 맞춰야 합니다.

## §§3.1–3.2 · 초기 답과 수정 답을 짝으로 저장하기

[PDF pp. 3–4](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=3)

여러 추론 문제에 대해 초기 풀이를 만든 뒤 검토·수정을 요구합니다. 처음부터 맞힌 문제도 수정 대상에 남겨야 오답 교정과 정답 손상을 모두 볼 수 있습니다. Table 3의 GPT-4·GSM8K 설정에서 호출 1·3·5회의 점수는 95.5, 91.5, 89.0입니다.

## §3.3 · 평균이 낮아진 경로를 찾기

[PDF pp. 4–7](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=4)

처음 틀린 풀이를 고치는 경우가 있더라도, 더 많은 정답을 잘못 수정하면 전체 성능은 떨어집니다. ‘다시 생각하라’는 요청 자체가 앞선 답에 오류가 있다는 신호처럼 작용할 수도 있습니다. 교정과 손상의 분모를 각각 초기 오답과 초기 정답으로 둬야 하는 근거입니다.

## §§4–5 · 다중 에이전트와 프롬프트를 해석하는 법

[PDF pp. 7–8](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=7)

여러 답을 생성해 토론하는 방식은 같은 계산량에서 독립 샘플의 self-consistency와 비교합니다. 수정 지시의 표현도 실험 조건으로 다룹니다. 단순히 호출 수가 늘어난 효과를 에이전트 간 협력의 효과로 돌리지 않도록 하는 비교입니다.

## §§6–7 · 외부 검색이 있는 우리 실험과 연결하기

[PDF pp. 8–9](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=8)

C2에는 새 관찰이 있으므로 이 논문의 결과만으로 C2 성능 저하를 예측할 수 없습니다. 다만 C1 정답까지 C2 비교에 포함하고, 새 자료가 없는 재추론 조건과 실제 검색 조건을 나누면 무엇이 판정을 바꿨는지 설명할 수 있습니다.

## 원문 장면과 읽는 순서

Tables 3–4에서 각 열의 호출 수와 ‘처음부터 맞은 문제’를 수정 대상으로 두는지 함께 보세요. 평균이 조금 변한 결과에도 회복과 손상이 동시에 들어 있을 수 있습니다.

**Table 3 · intrinsic self-correction** · [PDF p. 4](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=4)

![PDF p. 4 · Table 3 · intrinsic self-correction](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D07_PDF_04_1.jpg)

Jie Huang et al. · [원문](https://arxiv.org/pdf/2310.01798v2#page=4) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

**Table 4 · intrinsic self-correction** · [PDF p. 5](../../knowledge-revision/papers/D07_2024_Large_Language_Models_Cannot_Self-Correct_Reasoning_Yet.pdf#page=5)

![PDF p. 5 · Table 4 · intrinsic self-correction](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D07_PDF_05_2.jpg)

Jie Huang et al. · [원문](https://arxiv.org/pdf/2310.01798v2#page=5) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**원문에서 보고한 결과.** Table 4에서 GPT-4-Turbo의 GSM8K 정확도는 초기 91.5에서 첫 수정 88.0, 두 번째 수정 90.0으로 변화한다. 정답을 오답으로 바꾸는 현상이 주요 원인이다.

**우리 연구에서의 역할.** CRITIC과 모순되는 결론으로 나란히 세우기보다, 둘이 주는 정보가 다르다는 점을 설명한다. 우리의 agent는 외부 관측을 사용할 수 있지만 그 관측의 질도 평가해야 한다. 정답 유지, 잘못된 번복, 보류를 따로 기록하는 설계를 정당화하는 문헌이다.

**팀에서 풀어 볼 질문.** 처음 틀린 4개 중 2개를 고치고 맞은 6개 중 1개를 망쳤다면 회복률과 손상률은 각각 얼마인가요?

### #calls 1·3·5와 GSM8K 95.5→91.5→89.0은 무엇인가요?

**30초 답변:** “Calls는 모델 호출 수이고, 숫자는 해당 추론 benchmark 점수입니다. **더 호출했는데도 정확도가 떨어진 사례**입니다.”

**풀어서 설명:** 초기 답변 1회에 검토·수정을 추가하면 1→3→5가 됩니다. Table 3에서 GPT-4의 GSM8K는 **95.5 → 91.5 → 89.0**으로 내려갑니다. 최종값은 초기 대비 **6.5%포인트 낮습니다**. Table 4에서 GPT-4-Turbo는 91.5→88.0→90.0으로, 마지막 수정이 직전보다 개선되어도 초기보다 높지는 않습니다.

**연구 연결:** 평균 정확도와 함께 **정답→오답 손상**, **오답→정답 회복**, 호출 비용을 함께 기록해야 실제 효과를 판단할 수 있습니다.

[읽기 목록으로 돌아가기](README.md)
