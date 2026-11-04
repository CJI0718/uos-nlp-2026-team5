# Decomposition Dilemmas · 한국어 절별 해설

Decomposition Dilemmas: Does Claim Decomposition Boost or Burden Fact-Checking Performance?

**D31 · 2025 · paper version · 6장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf) · [공식 서지·원문](https://arxiv.org/abs/2411.02400v2)

## 먼저 붙잡을 질문

더 짧고 단순한 하위 주장을 만들었는데 왜 전체 판정 성능이 떨어질 수 있을까요?

**왜 선택했나 — ‘세분화하면 좋다’는 우리 설계에 대한 직접적인 반론.** Decompose-Then-Verify가 널리 쓰이지만, 분해기가 바뀌거나 입력의 단위가 달라지면 최종 성능이 떨어지는 이유를 조사한다.

## 논문의 논증을 먼저 따라가기

‘긴 주장을 잘게 나누면 검증이 쉬워진다’는 예상에는 두 과정이 섞여 있다. 하위 문장 하나는 단순해지지만, 검색할 횟수와 다시 합쳐야 할 판정의 수도 늘어난다. 저자들은 짧은 주장 단위와 더 긴 응답 단위 자료를 나누고, 분해기와 검증기를 바꿔 같은 입력을 직접 확인하는 방식과 분해한 뒤 확인하는 방식을 비교한다.

다음에는 분해 자체의 산출물을 조사한다. 너무 잘게 쪼개면 대상이 모호해지거나 뜻이 변하고, 검증하기 쉬운 문장만 남기면 중요한 문맥이 빠질 수 있다. §5는 오류 유형을 정하고 GPT-4o를 이용해 분해를 진단한다. 그 피드백으로 분해문을 수정한 뒤 동일 검증기로 다시 채점해, 진단이 실제 판정에 유용한지 Table 4에서 시험한다. 단순한 입력과 긴 응답에서 이 효과는 크기가 다르다.

§6에서는 문제를 단순하게 해서 얻는 정확도 이익과 여러 번의 검색에 따라 누적되는 잡음의 균형으로 이 현상을 설명하고, 입력 복잡도를 바꾸어 확인한다. 우리 설계에서 ‘무조건 분해’는 비교 가능한 정책 중 하나다. 같은 날짜·같은 비교 대상을 유지한 채 분해했는지와, 추가 질의가 새 근거를 얻었는지를 분리해 점검하면 분해의 이득과 손실을 각각 설명할 수 있다.

## §§1–3 · 분해에서 최종 판정까지 어떤 단계가 바뀌나

[PDF pp. 1–4](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf#page=1)

주장 분해, 하위 주장별 검증, 최종 판정 결합을 구분합니다. 분해 없이 원 주장을 평가한 조건과 동일한 데이터·검증기에서 비교해야 분해 자체의 이득을 해석할 수 있습니다. 강한 검증기와 약한 검증기가 받는 이득이 다를 가능성도 설계에 포함됩니다.

## §4 · 세분성의 이득과 손실을 비교하기

[PDF pp. 4–5](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf#page=4)

분해하면 검증기 하나가 처리할 명제는 간단해집니다. 그러나 호출과 검색이 늘고, 원래 비교 관계가 떨어져 나갈 수도 있습니다. WICE·MiniCheck 표에서 원문 조건의 BAcc 80.01과 FactScore 분해의 71.11을 같은 설정으로 비교하세요. 하위 주장 수 3.91은 평균 개수입니다.

## §5 · 어떤 오류가 분해 단계에서 새로 생기나

[PDF pp. 5–6](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf#page=5)

원문에 없던 내용을 덧붙이거나 중요한 정보를 빠뜨리는 등 분해 결과 자체의 오류를 살핍니다. 그 결과로 검증기의 오답이 생기면, 판정기만 다시 학습시키는 해결책으로는 원인을 없애기 어렵습니다. 증거가 충분한지뿐 아니라 원 질문이 제대로 보존됐는지도 봐야 합니다.

## §6 · 입력 복잡도를 바꾸는 실험은 왜 필요한가

[PDF pp. 6–9](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf#page=6)

복잡한 조건을 단순화해 얻는 이득과 여러 조각을 검증하느라 생기는 잡음을 비교합니다. 저자들은 복잡도를 높이거나 낮춘 자료로 이 설명을 점검합니다. 분해의 평균 효과를 모든 문장·모델에 일반화하지 않고 입력 조건별로 읽는 이유입니다.

## §§7–8 · 우리 50개에서 가져갈 설계 원칙

[PDF p. 9](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf#page=9)

사람이 시점·대상·수치가 보존된 하나의 주장을 먼저 확정하면, 실험 도중 달라지는 것은 근거 환경입니다. 에이전트가 검색을 위한 하위 질문을 만들면 그 질문이 보존한 조건을 따로 기록합니다. 분해 품질이 오염 근거 실험 전체를 대신 설명하지 않게 하는 방법입니다.

## 원문 장면과 읽는 순서

Tables 2–3에서 분해 방법, 하위 주장 개수, 검증기, 성능 열을 함께 봅니다. 원 주장이 간단할 때 추가 검색 단계만 늘어날 수 있습니다.

**Tables 2–3 · decomposition outcomes** · [PDF p. 4](../../team_guide/papers/E05_2025_Decomposition_Dilemmas_Does_Claim_Decomposition_Boost_or_Burden_Fact-Checking_Performance.pdf#page=4)

![PDF p. 4 · Tables 2–3 · decomposition outcomes](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D31_PDF_04_1.jpg)

Hu et al. · [원문](https://arxiv.org/pdf/2411.02400v2#page=4) · [이미지 이용 조건](http://creativecommons.org/licenses/by-nc-sa/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** 최소 요구조건 추출과 무조건 세분화하는 정책을 구별한다. ledger가 더 장황해져서 생기는 비용·의미 손실도 관찰한다. ClaimDecomp·Micro-Act와 같은 장에서 소개하면 분해의 필요성과 위험을 함께 보여줄 수 있다.

**팀에서 풀어 볼 질문.** 한 주장에 ‘전년 대비’가 붙어 있습니다. 이를 분리한 두 문장이 모두 참이어도 원 비교를 입증하지 못하는 경우는 언제일까요?

### Decomposition Dilemmas의 Claims·BAcc·F1은 무엇인가요?

**30초 답변:** “Claims는 분해 후 **평균 하위 주장 수**, BAcc는 **클래스별 재현율의 평균인 balanced accuracy**, F1은 그 논문 분류 설정의 정밀도·재현율 결합 점수입니다.”

**대표 수치:** WICE에서 MiniCheck의 baseline은 **Claims 1.00, BAcc 80.01, F1 72.32**이고, FactScore 방식으로 분해하면 **Claims 3.91, BAcc 71.11, F1 59.90**입니다. BAcc는 **8.90%포인트 감소**, F1은 해당 0–100 표기에서 **12.42점 감소**합니다. 많이 분해했다고 자동으로 더 잘 검증하는 것은 아닙니다.

**읽는 요령:** Verifier는 **검증기**, Decomp는 **분해 방법**입니다. 동일한 검증기 안에서 분해 방법을 비교해야 합니다. 논문의 F1을 우리 제안의 Macro-F1이라고 자동으로 바꿔 부르지 않습니다.

[읽기 목록으로 돌아가기](README.md)
