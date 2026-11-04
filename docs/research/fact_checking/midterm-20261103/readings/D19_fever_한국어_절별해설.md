# FEVER · 한국어 절별 해설

FEVER: a Large-scale Dataset for Fact Extraction and VERification

**D19 · 2018 · NAACL · 2장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf) · [공식 서지·원문](https://aclanthology.org/N18-1074/)

## 먼저 붙잡을 질문

판정이 맞고 인용 문장도 관련 있어 보이면 FEVER에서는 항상 정답일까요?

**왜 선택했나 — 판정과 근거를 함께 평가하는 출발점.** 텍스트 entailment처럼 근거가 이미 주어진 설정에서 더 나아가, 많은 문서에서 검증 근거를 직접 찾는 과제를 구성했다.

## 논문의 논증을 먼저 따라가기

FEVER의 데이터 작성은 주장 만들기와 근거 검증을 분리한다. 한 주석자가 Wikipedia 문장을 바탕으로 주장을 만들거나 사실을 변형하면 다른 주석자가 그 주장을 지지·반박하거나 정보가 부족하다고 판정한다. 처음 어떤 문장을 보고 문제를 냈는지 모르는 검증자는 다른 문장 조합으로도 같은 결론을 정당화할 수 있다. 그래서 정답 근거를 문장 하나가 아니라 하나 이상의 충분한 문장 집합으로 표현한다.

모델은 말뭉치에서 관련 문서를 찾고, 그 안에서 증거 문장을 선택한 뒤, 선택한 증거와 주장 사이의 관계를 분류한다. 파이프라인 각 부분에 사람이 고른 정답을 넣는 oracle 비교를 통해 앞 단계의 검색 손실과 뒤 단계의 판정 손실을 구분한다. Figure 1의 폭동 사례에서는 사건이 벌어진 카운티와 그곳의 인구 순위가 서로 다른 문서에 있다. 한 문서만 찾은 경우 최종 답을 맞힐 수 있어도 근거 집합은 불완전하다.

당시 baseline에서 라벨만 채점하면 50.91%, 지지·반박에 맞는 근거까지 요구하면 31.87%였다. 저자들은 특히 증거 문장 선택의 어려움을 드러냈다. 우리 자료에도 이 논리를 적용할 수 있다. 다만 웹에서는 다른 기관의 유효한 1차 자료도 동일한 사실을 입증할 수 있으므로 특정 URL 일치보다 필수 사실 집합을 충족하는지 평가해야 한다.

## §§1–2 · 사실 검증을 데이터로 만들려면

[PDF pp. 1–3](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf#page=1)

주장과 라벨만 있으면 모델이 어떤 사실을 이용했는지 평가하기 어렵습니다. 저자들은 위키백과에서 시작해 사람이 쓴 주장, 사실 관계 라벨, 판정을 입증하는 문장 집합을 함께 만듭니다. 관련 문서가 있다는 것과 그 문서가 특정 주장을 지지한다는 것은 다릅니다.

## §3 · 주장 작성과 근거 주석을 분리하기

[PDF pp. 3–5](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf#page=3)

한 단계에서는 위키 문장을 바탕으로 주장을 작성·변형하고, 다른 단계에서는 근거를 찾아 Supported, Refuted, Not Enough Info를 판단합니다. 일부 주장은 두 문장 이상이 합쳐져야 입증됩니다. 한 주장에 가능한 완전한 근거 집합도 여럿일 수 있습니다. ‘찾지 못함’ 라벨이 어떤 자료 범위에 의존하는지도 이 단계에서 읽어야 합니다.

## §§4–5.4 · 기준 시스템은 어디서 실패할 수 있나요?

[PDF pp. 5–6](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf#page=5)

주장에서 관련 문서를 찾고 그 안의 문장을 고른 뒤, 자연어 추론기로 라벨을 정합니다. 주석 문서를 제공하거나 문장 선택을 따로 평가하면, 마지막 라벨 오류가 검색 실패인지 추론 실패인지 좁힐 수 있습니다. 우리 코퍼스에서 가짜 문서가 선택되지 않은 경우도 이와 비슷하게 분리할 수 있습니다.

## §§5.5–5.9 · 50.91와 31.87의 차이

[PDF pp. 6–9](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf#page=6)

기준 시스템은 라벨만 볼 때 50.91%, 지지·반박에 충분한 근거까지 요구할 때 31.87%를 기록합니다. 한 근거 집합의 일부만 가져와도 라벨은 맞힐 수 있습니다. NEI에는 지지·반박과 동일한 양성 증거 문장 요건을 붙이지 않습니다. 모델이 낸 다른 근거가 사람 주석에 없어 평가와 실제 유용성이 어긋날 수도 있습니다.

## §§6–7 · C1·C2에 무엇을 가져갈까요?

[PDF p. 9](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf#page=9)

총 185,445개 주장은 모두 같은 방식의 현실 뉴스 표본은 아닙니다. 가져올 것은 ‘판정과 충분한 근거를 함께 채점한다’는 원리입니다. 우리 GSR은 시점·범위까지 따로 확인하므로 팀 지표로 이름 붙이고, 대체 원출처도 사람이 인정할 수 있게 설계합니다.

## 원문 장면과 읽는 순서

Figure 1의 단위는 주장 하나와 그 판정에 필요한 증거 문장입니다. 두 문장을 묶어야 지지할 수 있다면 한 문장만 검색된 경우는 완전한 근거가 아닙니다.

**Figure 1 · claim and evidence** · [PDF p. 2](../../team_guide/papers/FC02_2018_FEVER_a_Large-scale_Dataset_for_Fact_Extraction_and_VERification.pdf#page=2)

![PDF p. 2 · Figure 1 · claim and evidence](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D19_PDF_02_1.jpg)

James Thorne et al. · [원문](https://aclanthology.org/N18-1074.pdf#page=2) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** GSR의 논리적 선행 근거다. 다만 Wikipedia 내부의 근거 ID 일치와 공개 웹의 근거 동등성은 다르다. 실제 게시글 50개에 대해서는 다른 URL의 동등한 결정적 자료도 인정하는 검수 규칙을 둔다.

**팀에서 풀어 볼 질문.** 우리 자료에서 출처 두 개 중 하나만으로도 충분하다면 두 URL을 모두 요구해야 할까요? 서로 대안인 근거 집합과 함께 필요한 근거 집합을 구분해 보세요.

### FEVER의 이름과 라벨, FEVER score는 무엇인가요?

**30초 답변:** “FEVER는 **Fact Extraction and VERification**입니다. Wikipedia 기반 주장을 **Supported / Refuted / Not Enough Info**로 판정하며, 일부 평가는 올바른 라벨뿐 아니라 필요한 근거 회수까지 요구합니다.”

**풀어서 설명:** 원 논문 데이터는 **185,445개 주장**입니다. Supported·Refuted 사례에는 판정을 뒷받침하는 문장 집합이 주석됩니다. 단순 Label Accuracy는 라벨만 비교합니다. **FEVER score**는 Supported/Refuted에서 정답 라벨과 함께 **적어도 하나의 완전한 gold evidence set**을 회수해야 성공으로 보는 결합 평가입니다. NEI는 충분한 정답 근거 집합이 없는 라벨로 별도 처리합니다.

**연구 연결:** 우리의 GSR도 라벨과 근거를 결합한다는 발상을 참고하지만, **동일한 공식 지표**라고 부르려면 FEVER의 정확한 채점 규칙을 따라야 합니다.

### NEI는 에이전트가 검색을 못 했다는 뜻인가요?

**30초 답변:** “아닙니다. **정답의 NEI**와 **시스템의 검색 실패·기권**을 구분해야 합니다.”

**풀어서 설명:** Gold가 Refuted인 문제에서 반박 근거를 못 찾았다고 gold를 NEI로 바꾸지는 않습니다. 모델이 ‘자료가 부족해 판단을 보류한다’고 출력하는 것은 **Abstention** 또는 실패 유형으로 기록할 수 있습니다. 반대로 실제 corpus 범위에서 판정 근거가 없는 경우에는 그 기준에 맞게 NEI를 정의할 수 있습니다.

**연구 연결:** Fixed-corpus에서만 판단할지, 허용된 외부 자료까지 포함한 현실의 참거짓을 판단할지 **Task의 정보 범위**를 먼저 정해야 합니다.

[읽기 목록으로 돌아가기](README.md)
