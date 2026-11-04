# FIRE · 한국어 절별 해설

FIRE: Fact-checking with Iterative Retrieval and Verification

**D08 · 2025 · Findings of NAACL · 13장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf) · [공식 서지·원문](https://aclanthology.org/2025.findings-naacl.158/)

## 먼저 붙잡을 질문

팩트체커는 무엇을 보고 한 번 더 검색할지, 언제 답을 제출할지 결정할까요?

**왜 선택했나 — 우리가 구현할 수 있는 작은 fact-checking agent의 가까운 모델.** 원자적 주장을 True/False로 확인하는 과정에서 검색을 무조건 정해진 횟수 수행하는 비용을 줄이고자 한다. 질문 생성과 검증을 분리된 두 단계로 고정하지 않고, 지금 답할지 더 검색할지를 반복 선택한다.

## 논문의 논증을 먼저 따라가기

비용 문제를 보려면 먼저 언제 질의 수가 정해지는지 살펴야 한다. 한 번 자료를 모은 뒤 판정하는 시스템과, 질의를 반복하되 N회가 끝나야 판정하는 시스템은 쉬운 주장에도 정해진 만큼 비용을 쓴다. FIRE는 현재까지의 자료를 본 같은 단계에서 ‘판정을 제출’하거나 ‘다음 검색어를 생성’하도록 한다. 새 자료를 읽은 뒤에는 같은 선택을 다시 한다.

두 가지 실패에 별도 장치를 둔다. 비슷한 질의를 되풀이하면 정보는 거의 늘지 않아도 호출 비용이 쌓이므로 이전 검색과의 유사성을 점검한다. 모델이 너무 일찍 확신하면 조사 자체가 생략되므로 단계별 판단 방식도 비교한다. §4에서 평가 데이터의 라벨을 공통 조건에 맞추고, §5에서 모델 비용과 검색 비용을 구분해 기존 팩트체크 파이프라인과 비교한다.

논문이 보고한 평균 절감 배수는 LLM 비용 7.6배, 검색 비용 16.5배이며 해당 과제와 비교군에 대한 값이다. §6의 오류 분석에서는 기준 자료로 지지되기 어려운 주장 등 벤치마크 자체의 문제도 다룬다. 우리 조건에서는 ‘답을 맞힐 자신이 있음’과 ‘그 답을 제출할 충분한 유효 근거를 확보함’이 다른 종료 신호가 될 수 있다.

## §§1–2, Figure 1 · 고정 검색 횟수로는 보이지 않는 선택

[PDF pp. 1–3](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf#page=1)

모든 주장에 미리 정한 양만큼 자료를 수집하면 쉬운 주장에서도 비용이 들고 어려운 주장은 근거가 부족할 수 있습니다. FIRE는 현재의 판단과 그 확신을 바탕으로 종료하거나 다음 검색 질의를 내는 반복 구조를 제안합니다.

## §3.1 · 판정과 검색이 하나의 반복 안에 있는 구조

[PDF pp. 3–4](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf#page=3)

주장과 지금까지의 근거로 충분히 판단할 수 있는지를 검토합니다. 더 찾아야 하면 질의를 발행하고 새 결과를 입력에 더합니다. 외부 검색은 결과를 실제로 가져온 사건입니다. ‘검색할 필요가 있다’는 문장 생성만으로 한 회를 셌다고 해석하지 마세요.

## §§3.2–3.3 · 두 가지 실패에 대응하는 장치

[PDF p. 4](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf#page=4)

이미 사용한 질의를 되풀이하면 근거는 늘지 않고 비용만 커집니다. 또 최초 판단이 과신에 차 있으면 조기에 멈춥니다. 저자들은 반복 질의 및 과신을 줄이는 절차를 둡니다. 모델의 높은 확신과 원출처가 제공하는 근거 충분성이 서로 다른 개념이라는 점이 우리 연구에 중요합니다.

## §§4–5, Table 3 · 어떤 비용과 어떤 라벨 성적을 비교했나

[PDF pp. 4–7](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf#page=4)

Factcheck-Bench의 해당 비교에 사용한 631개 항목에서 GPT-4o-mini 설정의 LLM 비용 0.19달러, 검색 비용 0.44달러가 합쳐 0.63달러입니다. True F1은 0.87, False F1은 0.67입니다. 첫 수치는 실험 묶음의 비용, 뒤 수치는 라벨별 F1이므로 ‘문제당 비용’이나 전체 정확도로 옮겨 적으면 안 됩니다.

## §§6–7 · 우리 C2의 종료 기준

[PDF pp. 8–9](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf#page=8)

오류 분석에서는 참조 자료가 주장을 충분히 뒷받침하기 어려운 사례도 다룹니다. 우리 실험에서는 같은 예산으로 고정 검색과 적응 검색을 비교하고, 검색률과 최종 GSR을 함께 봅니다. 호출을 아낀 사례가 적절한 조기 종료였는지 확인하려면 처음 받은 근거의 충분성도 알아야 합니다.

## 원문 장면과 읽는 순서

Table 3의 비용 열은 모델 호출과 검색 비용을 나누고, 품질 열은 라벨별 P/R/F1을 보입니다. 비용 절감 배수와 F1의 분모를 구분해 읽으세요.

**Table 3 · accuracy and cost** · [PDF p. 6](../../team_guide/papers/FC15_2025_FIRE_Fact-checking_with_Iterative_Retrieval_and_Verification.pdf#page=6)

![PDF p. 6 · Table 3 · accuracy and cost](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D08_PDF_06_1.jpg)

Zhuohan Xie et al. · [원문](https://aclanthology.org/2025.findings-naacl.158.pdf#page=6) · [이미지 이용 조건](https://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**원문에서 보고한 결과.** 논문은 비교 대상 대비 비슷하거나 소폭 높은 성능에 LLM 비용 평균 7.6배, 검색 비용 16.5배 절감을 보고한다.

**우리 연구로 가져올 부분.** search-or-finish 의사결정은 좋은 기본 구조다. 우리 과제는 인용과 근거 충분성을 요구하므로 자신감이 높다는 이유만으로 끝낸 답과, 검증을 마친 답을 구분한다. 검색이 줄었다는 결과와 GSR이 올랐다는 결과를 별도로 측정한다.

**팀에서 풀어 볼 질문.** 빠르게 끝난 두 사례 중 하나는 충분한 근거로 멈췄고 다른 하나는 오보를 믿고 멈췄습니다. 평균 검색 횟수 외에 무엇이 필요할까요?

### FIRE의 충분성 판단과 최대 반복 횟수는 같은 것인가요?

**30초 답변:** “다릅니다. 충분성은 **현재 근거로 판정할 수 있는지**, 상한은 **자원이 끝나 강제로 종료하는지**입니다.”

**풀어서 설명:** FIRE는 **Fact-checking with Iterative Retrieval and Verification**입니다. 검색 결과를 보고 다음 질의를 생성하거나 판정하며, 반복 검색을 줄이기 위한 장치도 비교합니다. 논문은 유사·반복 질의를 감지하는 window·다양성 유도 등의 설정을 다룹니다.

**연구 연결:** Agent가 종료했을 때 이유를 **근거 충분 / 새로운 근거 없음 / 예산 소진 / 도구 오류**로 기록하면 비용과 실패를 연결해 해석할 수 있습니다.

### FIRE Table 3의 0.19+0.44, True F1 0.87, False F1 0.67은 무엇인가요?

**30초 답변:** “GPT-4o-mini 행의 **LLM 비용 0.19달러와 검색 비용 0.44달러**, 그리고 **True·False 각 클래스를 기준으로 계산한 F1**입니다.”

**풀어서 설명:** 표 제목은 Factcheck-Bench에서의 성능·비용 비교입니다. 전처리 후 이 데이터는 **True 472개, False 159개, 합계 631개**입니다. 0.19+0.44는 그 논문 실험의 **총 비용 구성**으로 읽으며, 한 질문 가격이나 현재 API 가격으로 읽지 않습니다. True의 Precision 0.91·Recall 0.84·F1 0.87과 False의 0.61·0.74·0.67은 클래스마다 관찰 대상이 다릅니다.

**연구 연결:** 라벨 불균형 때문에 전체 정확도와 각 클래스 성능이 다르게 보일 수 있습니다. 우리도 **라벨별 성능과 호출·토큰·시간**을 함께 보고해야 합니다.

[읽기 목록으로 돌아가기](README.md)
