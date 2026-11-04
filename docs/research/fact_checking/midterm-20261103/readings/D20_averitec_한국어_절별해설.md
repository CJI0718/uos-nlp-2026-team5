# AVeriTeC · 한국어 절별 해설

AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web

**D20 · 2023 · NeurIPS · 2장**

[전체 읽기 목록](README.md) · [해설 기준 판본 PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf) · [공식 서지·원문](https://proceedings.neurips.cc/paper_files/paper/2023/hash/cd86a30526cd1aff61d6f89f107634e4-Abstract-Datasets_and_Benchmarks.html)

## 먼저 붙잡을 질문

웹의 실제 주장을 검증할 때 왜 증거 문장 대신 질문–답 쌍을 기록했을까요?

**왜 선택했나 — 우리 50개 실제 링크를 평가 데이터로 바꾸는 가장 직접적인 참고.** 인위적으로 만든 주장, 불완전한 근거, 주장 이후에 나온 자료를 사용한 시간 누출이라는 기존 데이터 문제를 함께 다룬다.

## 논문의 논증을 먼저 따라가기

실제 발언을 가져오면 지시 대상과 검증 기준일이 문장 밖에 있는 경우가 많다. AVeriTeC은 50개 팩트체크 기관에서 수집한 실제 주장 4,568개에 발언 맥락을 정리한 뒤, 결론을 내려면 무엇을 알아야 하는지 질문을 만들고, 답과 웹 근거를 연결한다. 주석에는 개별 질문의 답이 어떻게 합쳐져 최종 라벨이 되는지 설명도 붙인다. 여러 차례 검수해 불충분한 근거와 시간 누출을 줄인다.

이 구조는 평가 방식도 바꾼다. 웹의 두 URL이 같은 사실을 입증할 수 있으므로 FEVER처럼 금 문장 ID와의 정확한 일치만 검사하기 어렵다. §6은 시스템이 낸 질문–답변 쌍과 참조 쌍 사이에 유사도 점수를 만들고, 쌍 전체가 얼마나 잘 대응하는지 매칭한다. 타당한 증거를 찾았을 때 판정에도 점수를 주는 방식이므로 정답 라벨만 맞히는 지름길이 줄어든다.

§7의 baseline은 검색 질문 생성, 웹 자료 검색, 확보한 내용으로 질문·근거 재구성, 재정렬, 판정과 설명 생성으로 이어진다. 사람이 판정에 합의하는 정도도 κ=.619였다는 사실은 실제 주장 검수에 드는 노력을 보여준다. 우리 50개 링크에는 정답 라벨을 먼저 붙이는 것만큼 검증 기준일·결정적 질문·인정할 근거와 그 이유를 합의하는 작업이 필요하다.

## §§1–2 · 현실의 주장이 위키 한 문장보다 어려운 이유

[PDF pp. 1–3](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=1)

실제 발언은 특정 시점이나 비교 대상을 생략할 수 있고, 자료가 서로 충돌할 수도 있습니다. 저자들은 여러 팩트체크 기관에서 실제 주장을 수집하고 웹 자료로 검증하는 과제를 구성합니다. 주장 이후 작성된 팩트체크 기사 자체가 답안지 역할을 할 위험도 시간 통제를 설명하는 배경입니다.

## §3 · 한 주장에 필요한 사실을 질문으로 기록하기

[PDF pp. 3–4](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=3)

주장에 답할 때 필요한 하위 질문, 답, 출처와 설명을 남깁니다. ‘수치가 얼마인가’와 ‘그 숫자의 대상 기간은 언제인가’는 다른 질문입니다. 최종 라벨에는 지지·반박·근거 부족 외에 서로 충돌하는 근거 또는 선택적 제시도 있습니다.

## §§4–5 · 자료를 어떻게 주석했나요?

[PDF pp. 4–5](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=4)

주석자는 검증 가능한 질문을 만들고 웹에서 답을 찾은 뒤 이를 종합해 판정합니다. 50개 기관에서 기원한 4,568개 주장의 통계와 주석 절차를 함께 읽으면, 표본의 개수와 검증 노동의 크기가 다른 문제임을 볼 수 있습니다. 데이터 제작자의 답과 근거는 실험 모델 입력에서 분리해야 합니다.

## §§6–7 · 판정과 증거를 함께 평가하기

[PDF pp. 6–8](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=6)

같은 사실을 다른 문장으로 찾을 수 있으므로 질의응답 근거의 일치 정도와 판정을 함께 봅니다. 기준 시스템은 관련 자료를 검색한 뒤 쓸 만한 정보를 골라 라벨을 만듭니다. 이 원 논문의 평가 절과 후속 연도 공유과제의 채점기 버전을 구분해서 읽으세요.

## §§8–9 · 우리 뉴스·SNS 50건에 적용할 때

[PDF p. 10](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=10)

회고적으로 오늘 자료를 허용할지, 주장 당시 공개된 자료까지만 허용할지 정해야 합니다. 범위를 정하지 않으면 나중에 알려진 사실을 당시 검증 가능한 주장으로 잘못 평가할 수 있습니다. 글 전체를 대상으로 한 판단과 그 안에서 선정한 주장 한 개의 판단도 나누어야 합니다.

## 원문 장면과 읽는 순서

Figure 2에서는 원 주장과 이를 확인하는 하위 질문의 답·근거를 순서대로 보세요. Figure 1로 돌아가 이 자료를 누가 어느 단계에서 작성했는지 확인하면 모델 입력과 gold를 구분하기 쉽습니다.

**Figure 2 · claim, questions and evidence** · [PDF p. 4](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=4)

[원문 전체 4페이지 열기](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=4)

**Figure 1 · annotation workflow** · [PDF p. 2](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=2)

[원문 전체 2페이지 열기](https://proceedings.neurips.cc/paper_files/paper/2023/file/cd86a30526cd1aff61d6f89f107634e4-Paper-Datasets_and_Benchmarks.pdf#page=2)

## 논문 결과와 우리 설계의 경계

**우리 연구에서의 역할.** 팀원이 모은 링크를 그대로 gold라고 두기보다, 검증 질문·핵심 사실·기준 시점·근거 집합을 붙인다. 또한 역사적 시점에서 검증할 것인지 현재 시점에서 과거 주장을 재평가할 것인지 먼저 정한다. AVeriTeC의 네 라벨을 우리 세 라벨로 사용한다면 매핑과 제외 기준을 공개해야 한다.

**팀에서 풀어 볼 질문.** 오늘 공개된 정정 보도로 과거 주장을 확인하는 경우와 당시 공개 자료만 허용하는 경우에 같은 gold를 사용할 수 있을까요?

### AVeriTeC는 FEVER와 무엇이 다른가요?

**30초 답변:** “AVeriTeC는 **실제 세계의 주장을 웹 자료와 중간 질문·답변으로 검증**하는 데이터셋입니다. 문서 시점과 맥락, 복합적인 실제 주장이라는 측면이 더 강조됩니다.”

**풀어서 설명:** 원 논문은 **4,568개 실제 주장**, **50개 팩트체크 기관**을 바탕으로 합니다. Supported·Refuted·Not Enough Evidence·Conflicting Evidence/Cherrypicking의 라벨 구분과 QA 형태의 근거 주석을 사용합니다. 화면의 Figure 1은 주석 절차, Figure 2는 사례이며, 예시 한 건을 전체 성능으로 읽지 않습니다.

**연구 연결:** 팀원 자료처럼 기사·게시글을 쓰면 **대상 시점, 원문 맥락, 출처와 질문의 분해**가 중요합니다. FEVER의 세 라벨로 옮기려면 AVeriTeC 라벨을 어떻게 처리하는지 명시해야 합니다.

[읽기 목록으로 돌아가기](README.md)
