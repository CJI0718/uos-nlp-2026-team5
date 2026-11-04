# Ev2R · 한국어 절별 해설

Ev2R: Evaluating Evidence Retrieval in Automated Fact-Checking

**D27 · 2025 · preprint v2 · 3장, 15장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf) · [공식 서지·원문](https://arxiv.org/abs/2411.05375v2)

## 먼저 붙잡을 질문

정답 근거와 문장이 다르지만 독립적으로 같은 사실을 입증한 자료를 어떻게 인정할까요?

**왜 선택했나 — 실제 웹에서는 다른 문서도 정답 근거가 될 수 있다.** 정확히 gold 문장/URL과 일치하는지만 보면 유효한 대체 근거를 오답 처리할 수 있고, 최종 라벨만 보면 근거 자체의 질을 평가할 수 없다.

## 논문의 논증을 먼저 따라가기

실제 팩트체크에서는 금 근거와 다른 기사가 같은 사실을 입증할 수 있고, 반대로 비슷한 단어를 많이 쓰면서도 결정적인 사실을 빼놓을 수 있다. Ev2R는 후보와 참조 근거를 작은 사실 단위로 나눈 뒤, 후보의 사실이 얼마나 참조와 정합하는지, 참조의 중요 사실을 얼마나 덮는지 평가한다. 이것이 참조 기반 경로의 정밀도와 재현율이다.

두 번째 경로는 금 판정을 대리 참조로 쓴다. 주장과 후보 증거로 도출한 판정이 금 판정과 얼마나 맞는지 검사한다. 첫 경로는 내용 누락을 포착하고 두 번째는 참조와 표현·경로가 다른 유효 근거에도 신호를 줄 수 있다. §3.3은 두 점수를 결합한다. 이때 금 판정은 평가기의 입력이며, 실행 중인 검색 에이전트가 보는 힌트와 엄격히 구분된다.

AVeriTeC·FEVER·VitaminC에서 사람의 근거 품질 평정과의 상관, 중복·잡음 등을 넣은 근거에 대한 반응을 별도로 비교한다. 연구의 성적은 팩트체커의 라벨 정확도가 아니라 **근거를 채점하는 방법이 사람 판단과 얼마나 잘 맞는지**다. 우리 50개 사례의 사람 검수에서도 다른 문서로 같은 사실을 확인한 경우와 결론만 되풀이한 경우를 이 두 경로로 분리해 검토할 수 있다.

## §§1–2 · 근거 채점기 자체가 연구 대상인 이유

[PDF pp. 1–3](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=1)

하나의 사람 주석 근거와 문자열이 다른 유효한 웹 문서가 많습니다. 반대로 단어가 비슷하지만 중요한 사실을 빠뜨린 문서도 있습니다. 저자들의 목표는 사실 판정기를 새로 만드는 것보다, 검색한 근거의 가치를 자동으로 평가하는 방법을 검증하는 데 있습니다.

## §§3.1–3.3, Figure 1 · 참조 기반 점수와 대리 참조 점수

[PDF pp. 4–5](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=4)

한 성분은 검색 근거와 주석 근거가 공유하는 정보를 정밀도·재현율 관점에서 평가합니다. 다른 성분은 주장과 검색 근거로 검증기가 정답 라벨에 부여하는 확률을 봅니다. 가중합에서 α가 0.5라면 양쪽에 같은 비중을 둡니다. 한쪽은 근거의 정보 일치, 다른 쪽은 판정에 대한 유용성을 근사합니다.

## §4 · 점수의 성능을 어떻게 평가했나요?

[PDF pp. 5–8](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=5)

관련 없는 정보, 중복, 일부만 포함된 근거 등으로 채점기가 적절히 반응하는지 시험합니다. 이어 사람이 평가한 근거 품질과 점수의 상관을 비교하고 다른 데이터셋에서도 확인합니다. 여기서 ‘모델 성능’의 대상은 증거 품질을 평가하는 점수 함수입니다.

## §5 · 높은 점수가 항상 충분한 근거를 뜻할까요?

[PDF pp. 8–12](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=8)

정성 분석에서 주석 근거를 그대로 되풀이하지 않은 대안과, 중요한 정보를 결여한 사례를 구분합니다. 대리 검증기가 문서를 보지 않아도 답을 맞힐 수 있다면 확률이 높아도 자료가 충분했다고 단정할 수 없습니다. 우리 C0는 이 가능성을 해석하는 참고가 됩니다.

## §§6–7 · 50개 평가에 적용하는 방식

[PDF p. 12](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=12)

두 신호를 따로 보는 생각을 빌려올 수 있습니다. 예컨대 대체 출처로 정확한 시간대를 확인했다면 주석 URL과 달라도 인정합니다. 사람이 결정적 사실과 시점을 검수한 뒤, 자동 점수가 어느 사례에서 어긋나는지 살펴보는 편이 지표의 의미를 보존합니다.

## 원문 장면과 읽는 순서

Figure 1의 두 평가 경로가 §3.3에서 합쳐집니다. 앞 경로는 주석 근거와의 일치, 뒤 경로는 같은 근거에서 검증기가 정답 라벨을 얼마나 지지하는지 묻습니다.

**Figure 1 · evidence scorer** · [PDF p. 2](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=2)

![PDF p. 2 · Figure 1 · evidence scorer](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D27_PDF_02_1.jpg)

Mubashara Akhtar; Michael Schlichtkrull; Andreas Vlachos · [원문](https://arxiv.org/pdf/2411.05375v2#page=2) · [이미지 이용 조건](http://creativecommons.org/licenses/by/4.0/)

**Section 3.3 · weighted evidence scorer** · [PDF p. 5](../../team_guide/papers/FC29_2025_Ev2R_Evaluating_Evidence_Retrieval_in_Automated_Fact-Checking.pdf#page=5)

![PDF p. 5 · Section 3.3 · weighted evidence scorer](%EC%9B%90%EB%AC%B8%EC%9E%A5%EB%A9%B4/D27_PDF_05_2.jpg)

Mubashara Akhtar; Michael Schlichtkrull; Andreas Vlachos · [원문](https://arxiv.org/pdf/2411.05375v2#page=5) · [이미지 이용 조건](http://creativecommons.org/licenses/by/4.0/)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** gold-equivalent evidence의 허용 기준과 acquisition/interpretation 분해를 설계한다. 자동 점수 자체에도 오류가 있으므로 작은 50개 연구에서는 사람 검수 표를 기본으로 두고, 자동 평가는 검수 부담을 줄이는 보조 실험으로 검토한다.

**팀에서 풀어 볼 질문.** 참조 기반 점수가 0.7, 대리 참조 점수가 0.9이고 α=0.5라면 결합점수는 0.8입니다(설명용). 이 수치로 문서의 발행 시점까지 맞다고 할 수 있을까요?

### Ev2R는 무엇을 평가하고, 정답 라벨이 왜 들어가나요?

**30초 답변:** “Ev2R는 **검색된 근거의 품질을 평가하는 scorer**입니다. 기준 근거와의 내용 대응, 그리고 그 근거가 기준 판정으로 이어지는지를 함께 봅니다.”

**풀어서 설명:** Reference-based 부분은 기준 근거와 검색 근거를 **atomic facts**로 나눠 정밀도·재현율을 계산합니다. Proxy-reference 부분은 주장과 검색 근거를 받은 분류기가 **gold verdict에 부여한 점수**를 사용합니다. 후자는 기준 근거와 표현·경로가 달라도 올바른 판정을 지지하는 자료를 인정하려는 장치입니다.

**연구 연결:** Gold evidence·gold verdict는 **평가기의 입력**입니다. 에이전트가 문제를 풀 때 주는 입력과 분리해야 답 누출을 피할 수 있습니다. 식은 15번 장에서 설명합니다.

### Ev2R의 최종 식을 말로 설명해 주세요.

**30초 답변:** “**기준 근거와의 사실 대응 F1**과, **검색 근거로 기준 판정을 지지하는 점수**를 절반씩 합칩니다.”

**식:** s_Ev2R = α × [2PR/(P+R)] + (1−α) × s_proxy, 원 논문의 α = **0.5**.

**기호:** P는 검색 근거의 atomic facts가 기준 근거로 지지되는 비율, R은 기준 근거의 atomic facts가 검색 근거에 포함·지지되는 비율입니다. s_proxy는 주장·검색 근거를 입력받은 분류기가 **gold verdict**에 부여한 softmax 값입니다. α는 두 평가 성분의 가중치이며 검색 비율·오염 비율이 아닙니다.

**가상 계산:** P=0.8, R=0.6이면 F1≈0.686입니다. s_proxy=0.9일 때 최종 점수는 0.5×0.686+0.5×0.9≈**0.793**입니다. 이 숫자는 설명용이며 논문 결과가 아닙니다.

**연구 연결:** softmax 0.9는 자동으로 잘 보정된 ‘실제로 참일 확률 90%’가 아닙니다. 또한 이 식은 **평가기**에 속하므로 gold를 에이전트에게 노출하지 않습니다.

[읽기 목록으로 돌아가기](README.md)
