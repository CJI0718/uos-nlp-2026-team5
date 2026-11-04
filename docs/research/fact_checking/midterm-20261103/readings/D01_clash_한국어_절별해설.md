# ClashEval · 한국어 절별 해설

ClashEval: Quantifying the Tug-of-War between an LLM’s Internal Prior and External Evidence

**D01 · 2024 · NeurIPS · 4장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf) · [공식 서지·원문](https://proceedings.neurips.cc/paper_files/paper/2024/hash/3aa291abc426d7a29fb08418c1244177-Abstract.html)

## 먼저 붙잡을 질문

오도 문서를 무시하는 모델이 정확한 정정 문서도 무시한다면 어느 쪽이 더 좋은 모델인가요?

**왜 선택했나 — 연구 질문의 직접적인 출발점.** RAG가 더 많은 정보를 준다는 이유만으로 언제나 개선되는지 묻는 논문이다. 잘못된 외부 문맥이 올바른 기존 답을 덮어쓰는 실패와, 올바른 문맥을 주어도 기존 오답을 고집하는 실패를 같은 틀에서 다룬다. 우리가 보존과 교정을 함께 보려는 이유가 여기에 있다.

## 논문의 논증을 먼저 따라가기

먼저 같은 질문에 두 번 답하게 한다. 처음에는 아무 자료를 주지 않아 모델의 출발 답을 얻고, 다음에는 답 후보가 담긴 문서를 붙인다. 질문은 6개 분야 1,294개이며, 이름·날짜·수량·장소처럼 바꾼 부분과 정답을 식별할 수 있는 사실을 택했다. 문서 안의 값만 조금 또는 크게 바꾸면 질문을 고정한 채 모델이 어떤 차이까지 받아들이는지 볼 수 있다.

저자들은 답이 문맥 쪽으로 이동한 빈도와 그 이동이 정확했는지를 따로 센다. 처음 맞다가 틀린 문서의 값을 채택한 경우와, 실제 정답을 담은 문서를 줬는데도 기존 오답을 고집한 경우는 서로 다른 실패다. 여러 문서를 같이 줄 때, 변형의 크기를 바꿀 때, 자료 없는 답의 토큰 확률이 높거나 낮을 때를 차례로 비교해 이 선택을 설명할 단서를 찾는다.

마지막 Table 3에서야 보정이 등장한다. 토큰 확률을 얻을 수 있는 모델에서 보정 전후를 비교하면 GPT-4o의 정확도는 .615에서 .754로 올라가지만 prior bias도 .021에서 .085로 커진다. 문서가 틀린 경우의 저항을 강화한 조치가, 문서가 맞는 경우의 교정을 어렵게 만들 수 있다. 우리 에이전트의 추가 검색도 평균 점수와 함께 두 방향의 변화를 따로 봐야 한다.

## §§1–2 · 충돌을 양방향으로 보기

[PDF pp. 1–3](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=1)

검색 문맥이 모델의 기존 답과 다른 상황을 만듭니다. 두 정보원이 다를 때 문맥을 선호하는 빈도와, 그렇게 선택해 최종 답이 맞았는지를 구분합니다. 잘못된 자료에 저항하는 성질이 정확한 자료로 오류를 고치는 데에는 불리할 수 있기 때문입니다.

## §§3.1–3.3 · 같은 질문에 대한 첫 답과 두 번째 답

[PDF pp. 3–5](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=3)

자료 없이 얻은 답을 출발점으로 놓고, 문서에서 이름·날짜·수량 같은 결정적 사실을 바꿉니다. 6개 분야의 1,294개 질문을 사용합니다. 문서의 대부분은 그대로 두면서 바꾼 값과 원래 값 사이의 거리를 조정하므로, 단순히 원 주제와 무관한 문서를 넣는 상황과 다릅니다.

## §§4.1–4.3 · 값의 차이와 문서 수가 선택을 바꾸는가

[PDF pp. 6–7](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=6)

충돌 문서를 하나 줄 때와 여러 문서를 줄 때를 비교합니다. 작은 숫자 차이는 그럴듯해 보이는 한편 아주 큰 차이는 기존 답과의 충돌을 알아차리기 쉬울 수 있습니다. 읽을 때는 ‘문맥 값을 골랐는가’와 ‘그 선택이 옳았는가’를 서로 다른 열로 두세요.

## §4.4, Table 3 · 보정 뒤 정확도와 두 편향을 함께 읽기

[PDF pp. 7–9](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=7)

초기 답과 문맥 조건에서의 토큰 확률을 이용해 점수를 보정합니다. GPT-4o의 해당 결과에서 정확도는 0.615에서 0.754, context bias는 0.304에서 0.107로 바뀌지만 prior bias는 0.021에서 0.085로 올라갑니다. 정답률 증가와 기존 답 고수의 증가가 함께 일어났습니다.

## §5 · 우리 평가에서 남겨야 할 분모

[PDF p. 9](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=9)

코퍼스를 바꾸었을 때 맞던 답이 틀리는 위험과 틀리던 답이 맞는 가능성은 각각 다른 출발 집합을 갖습니다. 우리 C1→C2에서도 둘을 따로 세고, 단지 문서를 읽은 것과 외부 근거로 결정적 사실을 확인한 것을 나누면 비교의 의미가 분명해집니다.

## 원문 장면과 읽는 순서

Figure 2에서는 문서에서 바뀐 사실과 원래 질문을 짝지어 보세요. 이 비교가 먼저 있어야 Table 3의 보정이 어떤 방향의 오류를 바꿨는지 설명할 수 있습니다.

**Figure 2 · responses to modified facts** · [PDF p. 5](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=5)

[원문 전체 5페이지 열기](https://proceedings.neurips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf#page=5)

## 논문 결과와 우리 설계의 경계

**원문에서 보고한 결과.** 확률 보정은 두 오류의 균형을 바꾼다. Table 3에서 GPT-4o의 해당 평가 정확도는 0.615→0.754, context bias는 0.304→0.107로 바뀌지만 prior bias는 0.021→0.085로 증가한다. 한쪽 개선이 다른 쪽 악화와 공존한다.

**우리 연구로 가져올 부분.** 같은 초기 판단에서 출발하는 교정/보존 전이 평가를 설계한다. 토큰 확률 접근을 요구하는 보정법을 그대로 재현하기보다, 출처 확인 행동이 그 전이를 어떻게 바꾸는지 묻는다. 발표에서는 §3.1의 지표 정의 → Table 3의 양면 변화 → 우리의 전이표 순서로 연결한다.

**팀에서 풀어 볼 질문.** 날짜를 하루 바꾼 오도 문서와 100년 바꾼 오도 문서에서 채택률이 다르면 어떤 조작 난도를 기록해야 할까요?

### 외부 문서를 따르는 것이 왜 좋은 행동일 수도, 나쁜 행동일 수도 있나요?

**30초 답변:** “기존 답과 외부 근거 중 **어느 쪽이 맞는지**에 따라 달라집니다. 원래 틀렸는데 유효한 문서로 맞히면 교정이고, 원래 맞았는데 오도 문서 때문에 틀리면 손상입니다.”

**풀어서 설명:** ClashEval은 원래 문서의 이름·장소·수치 등을 바꾸어 내부 지식과 문맥 사이의 선택을 봅니다. Figure 2의 빨강·초록은 해당 예시에서 정답과 다른지 같은지를 나타냅니다. **예시 그림은 실패가 얼마나 자주 일어나는지의 분모를 제공하는 성능표는 아닙니다.**

**연구 연결:** 모델이 문서를 ‘잘 따른다’는 것과 ‘현실을 잘 검증한다’는 것을 분리하여 C0→C1과 C1→C2 전이를 봅니다.

[읽기 목록으로 돌아가기](README.md)
