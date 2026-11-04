# VitaminC · 한국어 절별 해설

Get Your Vitamin C! Robust Fact Verification with Contrastive Evidence

**D21 · 2021 · NAACL · 7장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf) · [공식 서지·원문](https://aclanthology.org/2021.naacl-main.52/)

## 먼저 붙잡을 질문

같은 주장에 대해 편집 전후 두 문장이 서로 다른 판정을 요구하도록 만들면 무엇을 측정할 수 있을까요?

**왜 선택했나 — 같은 주장에 근거만 바꾸는 대조 실험의 강한 선행연구.** 근거의 작은 사실 변화에 맞게 판정을 바꾸는가를 묻는다. 주장 문장만 보고 찍는 모델과 실제 근거를 읽는 모델을 구분하려는 목적이다.

## 논문의 논증을 먼저 따라가기

비슷한 문장을 찾는 시스템이 사실이 달라진 지점까지 읽는지 확인하려면 두 자료가 거의 같아야 한다. 저자들은 Wikipedia의 편집 전후 문장 중 사실이 달라진 사례를 모으고, 그 작은 차이에 따라 지지·반박 관계가 달라지는 주장을 만든다. 자연 편집에 합성 자료도 더해 40만 개 이상의 주장–근거 쌍을 구성한다. 주장 텍스트가 같아도 입력 문서의 날짜나 값에 따라 정답이 달라지는 구조다.

Figure 2에서는 한 날짜 변경이 네 과제로 이어진다. 편집에서 사실이 바뀌었는지 찾고, 각 버전이 주장을 지지하는지 분류하고, 판단을 바꾸는 단어를 표시하고, 모순되는 문장을 근거에 맞게 다시 쓴다. 저자들은 이 과제들을 각각 평가하고, 대조 자료로 학습한 검증기가 다른 데이터의 어려운 대조·적대 사례에서도 더 잘 작동하는지 조사한다. 이미 확보된 증거에 대한 추론을 분리하기 위해 검증 과제에서는 oracle retriever를 가정한다.

팀의 짝지은 패킷도 날짜 한 곳을 바꿨을 때 무엇이 달라지는지 분리할 수 있다. 단, VitaminC가 채점하는 것은 그 버전의 문장과 주장 사이의 관계다. 우리 최종 판정은 독립적으로 확인한 현실 사실에 매겨지므로 같은 편집을 따라 라벨을 뒤집으면 오히려 실패할 수 있다. 중간 단계의 문서 해석 점수와 최종 세계 사실 판정을 두 개로 두는 학술적 이유다.

## §§1–2 · 대조쌍을 만들려는 동기

[PDF pp. 1–3](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf#page=1)

보통의 지지·반박 데이터에서는 모델이 주제나 표현만으로 라벨을 맞힐 수도 있습니다. 두 근거의 대부분을 같게 두고 핵심 사실만 바꾸면, 모델이 실제로 그 차이를 읽는지 관찰할 수 있습니다. 날짜 표식 자체를 맞히는 과제로 이해하기보다 두 버전의 의미를 비교해 보세요.

## §3, Table 1 · 편집 이력에서 사례로 넘어가는 과정

[PDF pp. 3–4](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf#page=3)

위키백과 수정 이력에서 의미 있는 사실 변경을 찾고 그 전후 문장에 대해 주장을 작성합니다. 단순한 문체 수정과 사실 수정은 구분됩니다. 실제 편집에 합성 편집도 추가하여 규모와 다양성을 확보합니다. 모든 편집이 거짓 정보를 의도적으로 작성한 사례라는 가정은 필요하지 않습니다.

## §4 · 하나의 자료로 서로 다른 네 과제를 평가하기

[PDF pp. 4–6](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf#page=4)

사실 편집 탐지, 주장 검증, 결정을 좌우하는 단어 찾기, 사실에 맞게 생성문 고치기를 제시합니다. 같은 문장에서 어떤 단어가 달라졌는지 표시할 수 있으므로 정답 라벨만 있는 데이터보다 더 세밀한 진단이 가능합니다. 각 과제의 입력과 출력은 다릅니다.

## §5 · 학습 효과와 우리가 가져올 설계 원리

[PDF pp. 6–9](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf#page=6)

이 자료를 사용해 학습한 모델이 대조적 자료와 다른 검증 데이터에서 어떻게 일반화하는지 평가합니다. 두 버전 모두 맞히려면 근거 변화에 반응해야 합니다. 우리는 동결 모델에도 이 대조 설계를 적용할 수 있습니다. 우리 실험에서 무엇을 바꿀지와 원 논문이 학습으로 얻은 효과를 분리해 설명하세요.

## §6 · 문서와의 관계와 현실 정답의 다른 역할

[PDF p. 9](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf#page=9)

원문 버전별 문장 관계가 변하면 VitaminC에서는 올바른 라벨도 달라집니다. 우리는 원 주장과 실제 참조 판정을 고정하고 잘못된 문장을 주입합니다. 따라서 오염 문서와의 관계를 정확히 읽고도 그것을 현실 사실로 채택하면 최종 판정은 틀릴 수 있습니다.

## 원문 장면과 읽는 순서

Table 1에서 Before/After만 읽지 말고 Claim까지 따라가세요. 결정적 사실을 고친 편집과 철자·문체를 고친 편집은 같은 주장에 미치는 효과가 다릅니다.

**Table 1 · factual and non-factual revisions** · [PDF p. 4](../../team_guide/papers/P02_2021_Get_Your_Vitamin_C%21_Robust_Fact_Verification_with_Contrastive_Evidence.pdf#page=4)

![PDF p. 4 · Table 1 · factual and non-factual revisions](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D21_PDF_04_1.jpg)

저자명은 연결한 공식 서지와 PDF 첫 면 참조 · [원문](https://aclanthology.org/2021.naacl-main.52.pdf#page=4) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** 올바른/오도 초기 패킷의 길이·표현을 맞추는 이유를 제공한다. 다만 해당 task는 주어진 문맥에 따라 판정을 조정하는 성질이 강하다. 우리 외부 진실 검증에서는 조작된 근거를 따라 라벨을 바꾸는 것이 오히려 실패일 수 있으므로 정답 기준을 분리한다.

**팀에서 풀어 볼 질문.** 우리의 인위적 KST 수정본을 보고 ‘이 문서는 오전 5시 KST라고 한다’는 진술과 ‘실제로 오전 5시 KST였다’는 진술을 각각 판정해 보세요.

### VitaminC는 비타민 연구인가요? 왜 여기 넣었나요?

**30초 답변:** “팩트 검증 데이터셋·학습 연구의 이름입니다. **거의 같은 문서에서 결정적인 사실만 바뀌는 대조 사례**로 모델이 근거 변화에 민감하게 반응하는지 봅니다.”

**풀어서 설명:** Table 1의 Before/After는 Wikipedia 편집 전후입니다. Factual revision은 사실 판단에 영향을 주는 편집, non-factual revision은 의미가 유지되는 편집입니다. Claim 1·Claim 2는 이 근거와 함께 판정할 주장입니다. **모든 편집이 악의적 거짓 작성인 것은 아닙니다.** 문서 버전·주장과의 관계가 변하는 데이터 구성을 보여 줍니다.

**연구 연결:** 우리는 모델을 추가 학습하지 않더라도 **주장을 고정하고 결정적 근거만 바꾸는 paired design**을 참고할 수 있습니다. 데이터 구성 원리를 참고하는 것과 원 논문의 학습 성과를 재현하는 것은 구분합니다.

[읽기 목록으로 돌아가기](README.md)
