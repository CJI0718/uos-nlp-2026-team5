# FaithEval · 한국어 절별 해설

FaithEval: Can Your Language Model Stay Faithful to Context, Even If “The Moon is Made of Marshmallows”

**D22 · 2025 · ICLR · 8장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf) · [공식 서지·원문](https://arxiv.org/abs/2410.03727v3)

## 먼저 붙잡을 질문

문맥에 충실한 시스템과 현실의 사실을 잘 검증하는 시스템이 같은 점수를 받을까요?

**왜 선택했나 — 우리 연구와 목표가 다른 문헌을 명시적으로 비교하기 위해.** 주어진 문맥에 충실한가를 평가하는 연구이며, 그 문맥이 현실과 다를 수도 있다. ‘문맥을 따른다’와 ‘현실의 사실을 맞힌다’를 구분하는 데 핵심적이다.

## 논문의 논증을 먼저 따라가기

저자들은 ‘문맥에 충실하라’는 말이 서로 다른 행동 셋을 가리킨다고 본다. 필요한 연도의 정보가 없는 경우에는 답을 보류하고, 두 문서가 서로 다른 값을 지지하면 모순을 지적하고, 현실 상식과 어긋나더라도 과제가 가상의 문맥을 전제한 경우에는 그 안에서 답해야 한다. 공통점은 외부의 상식이 아니라 문제에서 허용한 정보로 무엇을 결론 내릴 수 있는지 평가한다는 것이다.

첫 두 유형은 기존 문맥 QA를 편집해 결정적인 근거를 제거하거나 대안 답을 지지하는 문서를 만든다. 세 번째는 ARC-Challenge의 과학 질문에 상식을 뒤집은 선택지를 뒷받침하는 문단을 생성한다. 합성 후 자동 평가와 사람 검수를 조합해 약 4,900개 문항을 구성한다. 같은 모델이 정보 부재, 문서 간 불일치, 상식과의 충돌에 각기 다른 반응을 보여야 하므로 유형별로 따로 채점한다.

여러 공개·상용 모델의 결과에서는 큰 모델도 일부 조건에서 문맥을 따르지 못하고, 규모 증가가 모든 유형의 개선으로 연결되지는 않는다. 우리 실험에서 ‘기사 A에 따르면 X’가 맞는지 묻는 문항과 ‘실제로 X인가’라는 문항을 섞으면 이런 성능 차이를 해석할 수 없다. 같은 거짓 패킷에 대해 중간 문맥 판단과 독립 판정을 나눠 채점하는 데 이 연구를 쓸 수 있다.

## §§1–2 · 질문이 요구하는 진실의 기준

[PDF pp. 1–3](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=1)

저자들이 묻는 것은 주어진 컨텍스트를 근거로 응답할 수 있는가입니다. 문서가 현실과 반대인 경우에도 ‘이 문서의 세계에서는 무엇이 맞나’라는 지시를 지키면 문맥 충실성이 높습니다. 팩트체커가 실제 사실을 맞히는 Task와 평가 기준이 갈라지는 지점입니다.

## §3.1–3.2, Figures 2–3 · 문맥 조건은 어떻게 다른가

[PDF pp. 3–5](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=3)

Unanswerable은 필요한 답이 문맥에 없습니다. Inconsistent는 서로 맞지 않는 정보가 있어 한 답으로 정리하기 어렵습니다. Counterfactual에서는 문맥 안의 답이 일반 지식과 달라집니다. 자료 생성·검증 절차는 이러한 상태를 실제 문항이 제대로 구현했는지 확인하기 위한 단계입니다.

## §3.3 및 §4 · 조건마다 ‘맞는 행동’이 달라지는 이유

[PDF pp. 5–8](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=5)

불충분한 문맥에서 답을 단정하기보다 답할 수 없다고 해야 하는 경우가 있습니다. 충돌하는 문맥에서는 모순을 식별해야 하고 반사실 컨텍스트에서는 제시된 내용을 따라야 합니다. 조건을 합쳐 평균 정확도 하나만 보면 어떤 행동이 실패했는지 모호해집니다.

## §5 · 더 큰 모델이나 더 강한 지시가 해결하는가

[PDF pp. 8–10](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=8)

모델 규모와 지시 방식 등을 바꿔 문맥 충실성을 점검합니다. 모델이 답을 ‘원래 알고 있는’ 경우 문맥에 맞춰 대답하는 것이 더 어려울 수도 있습니다. 반대로 문맥을 그대로 따르면 현실 정답은 훼손될 수 있어, 출력 지시와 채점 대상이 같아야 합니다.

## §6 · 우리 4조건에서 물을 질문

[PDF p. 10](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=10)

누락·충돌의 구분을 빌리고, 겉보기에는 일관되지만 틀린 자료 묶음을 별도로 만듭니다. ‘문서들이 무엇을 말하는가’와 ‘독립 근거에 비추어 실제 주장이 맞는가’를 따로 채점하면 문맥 독해 실패와 거짓 정보 채택을 구별할 수 있습니다.

## 원문 장면과 읽는 순서

Figure 2에서는 세 유형에서 문맥에 맞는 응답이 무엇인지, Figure 3에서는 그 문항을 어떻게 검증했는지 보세요. 생성과 검수 단계가 구분됩니다.

**Figure 2 · three context conditions** · [PDF p. 4](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=4)

![PDF p. 4 · Figure 2 · three context conditions](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D22_PDF_04_1.jpg)

Ming et al. · [원문](https://arxiv.org/pdf/2410.03727v3#page=4) · [이미지 이용 조건](http://creativecommons.org/licenses/by-nc-sa/4.0/)

**Figure 3 · construction and validation** · [PDF p. 5](../../team_guide/papers/E45_2025_FaithEval_Can_Your_Language_Model_Stay_Faithful_to_Context%2C_Even_If_%E2%80%9CThe_Moon_is_Made_of_Marshmallows%E2%80%9D.pdf#page=5)

![PDF p. 5 · Figure 3 · construction and validation](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D22_PDF_05_2.jpg)

Ming et al. · [원문](https://arxiv.org/pdf/2410.03727v3#page=5) · [이미지 이용 조건](http://creativecommons.org/licenses/by-nc-sa/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** 프롬프트에서 ‘문서만 기준으로 관계를 판단’하는 조건과 ‘현실의 진위를 외부 확인’하는 조건을 명시한다. 평가가 모델에게 요구한 것과 일치해야 한다. 문맥 충실성 benchmark 점수를 사실 검증 능력의 대용으로 쓰지 않는 근거다.

**팀에서 풀어 볼 질문.** 문서만 따르면 정답이지만 외부 세계 사실로는 오답인 사례를 우리 팀은 한 척도로 평가할까요, 두 단계로 나눌까요?

### FaithEval의 세 문맥은 무엇인가요?

**30초 답변:** “**Unanswerable은 답할 정보가 없는 문맥, Inconsistent는 문서끼리 답이 충돌하는 문맥, Counterfactual은 현실 지식과 다른 내용을 제시하는 문맥**입니다.”

**풀어서 설명:** Figure 2의 Unanswerable 예시는 2009년 통근 방식 질문에 필요한 정보 대신 다른 연도의 정보를 포함합니다. Inconsistent 예시는 호랑이 이름이 문서마다 다릅니다. Counterfactual 예시는 일반적 세계 지식과 다른 설명을 문맥에 넣습니다. Figure 3은 LLM 생성·자동 검증·사람의 검수를 거쳐 조건을 만드는 절차입니다.

**연구 연결:** 우리의 missing·conflicting·misleading 조건을 설계할 때 참고할 수 있습니다. ‘관련 단어가 있음’과 ‘질문에 필요한 답이 있음’은 다릅니다.

### FaithEval은 거짓 문맥을 믿으면 좋은 모델이라고 평가하나요?

**30초 답변:** “그 논문의 **문맥 충실성 과제**에서는 주어진 가정·문맥에 맞게 답하는 것이 목표일 수 있습니다. 우리 Task의 **현실 사실 검증**과 정답 기준이 다릅니다.”

**작은 예:** 문맥이 ‘이 가상 세계의 달은 마시멜로다’라고 정하면 문맥 기반 QA에서는 그 설정을 따라야 합니다. 현실의 달을 검증하는 Task에서는 별도 gold에 따라 반박해야 합니다.

**연구 연결:** FaithEval에서 **환경을 구성하는 아이디어**를 가져오되 **라벨·성공 조건**을 그대로 옮기지 않습니다. ‘Faithful하지만 factually wrong’이 동시에 가능하다는 점이 발표의 핵심입니다.

[읽기 목록으로 돌아가기](README.md)
