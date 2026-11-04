# Sufficient Context · 한국어 절별 해설

Sufficient Context: A New Lens on Retrieval Augmented Generation Systems

**D23 · 2025 · ICLR · 3장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf) · [공식 서지·원문](https://proceedings.iclr.cc/paper_files/paper/2025/hash/33dffa2e3d2ab74a783d1a8c292f66d9-Abstract-Conference.html)

## 먼저 붙잡을 질문

답이 틀렸을 때 모델이 문서를 잘못 읽었는지 문서에 필요한 정보가 없었는지 어떻게 구별할까요?

**왜 선택했나 — 근거 획득 실패와 해석 실패를 나누는 직접적인 이론·평가 틀.** 질문과 ‘관련 있는’ 문서가 있다고 해서 답할 만큼 충분한 것은 아니라는 문제를 제기한다. 모델이 틀렸을 때 검색기를 고칠지 생성기를 고칠지 구분하게 해 준다.

## 논문의 논증을 먼저 따라가기

RAG가 틀렸을 때 검색 문서에 정답에 필요한 정보가 있었을까? 저자들은 질문과 그 문맥만 보고 확정적인 답을 낼 수 있는지를 별도 속성으로 정의한다. 사람이 충분성을 주석할 때 정답이나 모델 출력을 보지 않게 하고, 사람이 판정한 사례로 자동 평가기를 검증한다. 보고된 Gemini 1.5 Pro 평가기의 93% 정확도는 이 충분성 분류 실험의 값이다.

그다음 각 QA 사례를 ‘충분/불충분’과 ‘정답/오답 또는 보류’로 교차해 살핀다. 자료가 충분한데 오답이면 제공된 내용을 사용하는 단계가 의심된다. 문맥이 불충분한데도 모델은 기존 지식으로 맞히거나 자신 있게 틀릴 수 있다. 이 네 칸을 만들어야 정답률 한 개로는 설명하지 못하는 검색기와 생성기의 행동이 드러난다.

마지막에는 충분성 신호를 보류 결정에 쓰는 selective generation과 미세조정을 시험한다. 보고된 2–10% 개선은 **답한 경우 중** 맞은 비율에 관한 결과여서 답을 얼마나 자주 냈는지와 함께 읽어야 한다. 우리 팀에서는 문서가 날짜를 실제로 확인해 주는지 사람이 표시하고, 최종 판정·근거 충족·보류를 함께 남기는 근거로 삼을 수 있다.

## §§1–2 · 질문과 컨텍스트를 평가 단위로 선택하기

[PDF pp. 1–3](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=1)

같은 문서라도 묻는 내용에 따라 충분성이 달라집니다. 인물이 누구인지 묻는 질문에는 소개문이 충분해도, 기관의 정확한 설립일을 묻는 질문에는 부족할 수 있습니다. 그래서 정답 생성 전에 ‘이 컨텍스트로 질문에 답할 수 있는가’를 따로 판단합니다.

## §3, Table 1 · 충분성 판정기를 먼저 검증하기

[PDF pp. 3–5](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=3)

질문과 문서를 입력으로 충분 여부를 판단하는 자동 평가기를 만듭니다. 사람이 확인한 115개 사례에서 Gemini 1.5 Pro의 1-shot 설정은 F1 0.935, 정확도 0.930입니다. 이 값은 자동 충분성 분류의 정확성이며, 그 문서를 읽은 QA 모델의 정답률과 다릅니다.

## §4, Figure 1 · 충분·불충분별로 답과 보류를 다시 나누기

[PDF pp. 5–8](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=5)

데이터셋별로 검색 결과의 충분성 비율이 다릅니다. 문맥이 부족해도 모델이 기존 지식으로 답을 맞힐 수 있고, 충분한 문맥을 보고도 틀릴 수 있습니다. 이 교차표가 검색과 독해의 실패를 분리하는 도구입니다. 질문별 실제 top-k 문서에 무엇이 있는지 기록해야 같은 분석이 가능합니다.

## §5 · 충분성 신호를 보류에 쓰면 무엇이 달라질까요?

[PDF pp. 8–10](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=8)

확신과 충분성을 활용해 일부 사례에만 응답하는 selective generation 및 학습을 시험합니다. 답한 사례에서의 정확도는 전체 사례 대비 성공률과 다릅니다. 쉬운 사례에만 답하면 수치가 오를 수 있으므로 응답 비율과 함께 봅니다.

## §6 · 우리 코퍼스의 오도 조건과 만나는 한계

[PDF p. 10](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=10)

그럴듯한 문서가 잘못된 시간대를 또렷하게 단정하면 내부적으로는 답하기에 충분해 보입니다. 우리는 근거의 정보량과 사실 유효성을 각각 주석해야 합니다. C1에는 자료가 없었지만 C2에서 답을 회복했다면 두 가지 평가가 다른 이유도 설명할 수 있습니다.

## 원문 장면과 읽는 순서

Figure 1은 데이터셋별 근거 상태를 나누고, Table 1은 그 상태를 분류하는 평가기를 검증합니다. 두 자료에서 분모가 무엇인지 각각 확인하세요.

**Figure 1 · context sufficiency and outcomes** · [PDF p. 3](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=3)

[원문 전체 3페이지 열기](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=3)

**Table 1 · sufficiency classification** · [PDF p. 5](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=5)

[원문 전체 5페이지 열기](https://proceedings.iclr.cc/paper_files/paper/2025/file/33dffa2e3d2ab74a783d1a8c292f66d9-Paper-Conference.pdf#page=5)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** GSR의 S와 답 자체의 C를 분리하는 가장 직접적인 근거다. 이 논문의 sufficiency는 답을 구성할 정보가 있는지에 대한 성질이며, 그 정보가 현실에서 참인지까지 자동 보증하지 않는다. 그래서 우리 점수에는 사실 유효성과 시점 일치가 추가된다.

**팀에서 풀어 볼 질문.** 정답을 맞혔는데 제공된 세 문서 중 어디에도 시간대가 없다면 정확도와 GSR은 각각 어떻게 채점할까요?

### Sufficient Context의 0.935와 55.4%는 무엇을 뜻하나요?

**30초 답변:** “**0.935는 문맥 충분성 분류기의 F1**, **55.4%는 Figure 1의 MuSiQue 설정에서 불충분한 문맥으로 분류된 비율**입니다. 서로 다른 대상의 숫자입니다.”

**풀어서 설명:** Table 1은 **115개 gold-labeled (질문, 문맥; 답) 사례**에서 AutoRater가 충분/불충분을 잘 구분하는지 평가합니다. Gemini 1.5 Pro 1-shot의 F1 **0.935**, Accuracy **0.930**이 제시됩니다. 1-shot은 예시 한 개를 프롬프트에 제공한 조건입니다. **No GT Answer**는 충분성 판단에 정답 문자열을 주지 않았다는 뜻이지 정답 채점이 없다는 뜻이 아닙니다.

**연구 연결:** ‘충분함’은 질문에 답할 정보가 있는지를 뜻합니다. **충분하지만 거짓인 문맥**과 **올바르지만 불충분한 문맥**을 분리하면 우리의 네 조건을 더 정확하게 정의할 수 있습니다.

[읽기 목록으로 돌아가기](README.md)
