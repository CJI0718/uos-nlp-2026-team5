# ALCE · 한국어 절별 해설

Enabling Large Language Models to Generate Text with Citations

**D26 · 2023 · EMNLP · 3장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf) · [공식 서지·원문](https://aclanthology.org/2023.emnlp-main.398/)

## 먼저 붙잡을 질문

답이 맞는데 인용이 엉뚱한 경우와 인용문은 충실한데 답이 틀린 경우를 구분할 수 있을까요?

**왜 선택했나 — 인용이 붙었다는 사실과 인용이 답을 지지한다는 것을 구분한다.** 생성 결과의 사실성·검증 가능성을 높이기 위해 검색부터 인용을 포함한 답변 생성까지의 benchmark를 만든다.

## 논문의 논증을 먼저 따라가기

‘출처를 달아 설명하라’는 요구에는 답 자체가 맞는지와 인용이 답을 뒷받침하는지가 함께 들어 있다. ALCE는 이를 분리해 유창성·정확성·인용 품질을 평가한다. ASQA의 다양한 짧은 정답, QAMPARI의 여러 개체 목록, ELI5의 긴 설명은 정답 형태가 달라 내용 정확성 계산도 다르게 설계한다. 긴 답에서는 참조 설명에서 얻은 하위 사실을 모델 답이 얼마나 덮는지 점검한다.

인용 평가에서는 생성 문장을 가설, 그 문장이 인용한 passage들을 전제로 두고 함의를 검사한다. 인용 재현율은 뒷받침되는 문장이 얼마나 되는지 묻고, 인용 정밀도는 뒷받침에 기여하는 인용의 비율을 묻는다. 한 문장에 두 문서가 함께 필요할 수 있어 개별 문서와 문서 집합의 효과를 구별한다. p. 4의 두 그림을 함께 보면 답 속에 정확한 개체가 있어도 인용 점수는 낮을 수 있다는 점이 보인다.

검색기, 문맥에 넣는 passage 수, 생성 방식과 사후 편집을 비교하고 사람 평가로 자동 지표를 점검한다. ELI5에서는 가장 좋은 모델에서도 인용 지원의 공백이 남았다. 다만 유효한 함의 판정은 ‘그 문서가 그렇게 말한다’는 뜻이다. 우리 실험에는 그 문서가 기준일을 충족하는지, 다른 기사가 같은 원문을 반복하지는 않았는지 확인하는 단계가 더 필요하다.

## §§1–2 · 평가하려는 출력은 무엇인가

[PDF pp. 1–3](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf#page=1)

질문에 긴 답을 쓰면서 문장별로 출처를 제시하는 과제입니다. ASQA, QAMPARI, ELI5는 정답 구성과 답변 방식이 다릅니다. 여러 정답 항목을 나열하는 문제와 설명을 전개하는 문제를 같은 문자열 일치 기준으로 채점할 수 없어 지표를 나눕니다.

## §3, Figure 2 · 품질을 세 축으로 분리하기

[PDF pp. 3–5](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf#page=3)

유창성, 내용 정답성, 인용 품질을 따로 평가합니다. 인용 recall은 설명의 각 주장이 붙인 출처로 뒷받침되는지를, precision은 붙여 둔 각 인용이 실제로 기여하는지를 봅니다. 여러 출처를 묶어야 문장의 모든 부분을 입증하는 경우도 있습니다. 여기서 recall의 분모는 전체 코퍼스의 정답 문서가 아닙니다.

## §4 · 검색·작성·사후 편집이 나뉘는 이유

[PDF pp. 5–6](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf#page=5)

검색기로 후보를 가져오고 모델이 문서를 읽으며 답과 인용을 생성합니다. 긴 문서를 압축해 주거나, 생성 후 인용을 추가하는 방법도 비교합니다. 출처를 답 생성 전후 어느 시점에 사용했는지가 다르므로, 같은 URL 목록이 결과에 붙었다고 같은 절차라고 볼 수 없습니다.

## §5 · 문서를 더 주면 모든 인용이 좋아질까요?

[PDF pp. 6–8](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf#page=6)

모델·검색기·문서 수와 구성에 따른 결과를 나눕니다. 관련 자료를 충분히 가져왔어도 생성기가 설명의 일부를 근거 없이 덧붙일 수 있습니다. 반대로 검색 결과에 정답 정보가 빠졌다면 생성기 alone의 성능이라고 해석하기 어렵습니다.

## §§6–8 · 사람 평가와 우리 GSR의 관계

[PDF pp. 8–9](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf#page=8)

자동 함의 판단이 사람 평가와 어느 정도 맞는지 살핍니다. 오염 문서가 거짓 주장을 그대로 쓰면 문서와 생성 문장 사이의 함의는 성립할 수 있습니다. 우리 평가에서는 그래서 ‘인용문이 답을 지지하는가’와 ‘출처가 대상 시점의 실제 사실을 입증하는가’를 별도로 확인합니다.

## 원문 장면과 읽는 순서

Figure 3에서 생성 문장과 그 문장의 인용 묶음을 대응시키세요. 출처가 여러 개 붙었다는 것만으로 모든 인용이 필요한지도, 설명 전체가 지지되는지도 결정되지 않습니다.

**Figure 3 · citation evaluation** · [PDF p. 4](../../team_guide/papers/FC27_2023_Enabling_Large_Language_Models_to_Generate_Text_with_Citations_%28ALCE%29.pdf#page=4)

![PDF p. 4 · Figure 3 · citation evaluation](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D26_PDF_04_1.jpg)

Tianyu Gao; Howard Yen; Jiatong Yu; Danqi Chen · [원문](https://aclanthology.org/2023.emnlp-main.398.pdf#page=4) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** 최종 판정 근거를 문서 ID뿐 아니라 실제 span으로 남기고, 설명의 중요한 주장마다 지지가 있는지 본다. 인용 충실성이 오염 문서의 진실성까지 확인해 주는 것은 아니므로 provenance·유효성 검수와 결합한다.

**팀에서 풀어 볼 질문.** 기사 제목은 같은데 본문에서 단위를 잘못 옮겼습니다. 인용문은 에이전트의 답을 지지하지만 실제 정답과는 어긋날 때 어떤 점수가 갈라질까요?

### ALCE의 citation precision과 recall은 검색 precision/recall인가요?

**30초 답변:** “ALCE는 **출력 문장과 붙인 인용의 지지 관계**를 평가합니다. corpus에서 관련 문서를 얼마나 찾았는지를 직접 계산하는 검색 precision/recall과 평가 단위가 다릅니다.”

**풀어서 설명:** ALCE는 **Automatic LLMs’ Citation Evaluation**입니다. Citation recall은 출력의 검증할 문장들이 붙인 근거로 지지되는지를 보고, citation precision은 붙인 개별 인용 중 관련 없는 인용을 찾습니다. 여러 인용을 합쳐 지지할 수 있으므로 개별 문서 하나가 문장의 모든 내용을 단독으로 설명해야 하는 것은 아닙니다.

**연구 연결:** 가짜 문서가 가짜 답을 잘 지지하면 **인용 지지 관계는 높고 현실의 사실성은 낮을 수 있습니다**. 따라서 판정 정확성·근거 유효성·인용 적절성을 구분합니다.

[읽기 목록으로 돌아가기](README.md)
