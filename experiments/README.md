# 실험 설정과 재현

현재 **실모델 실험은 미실행**입니다. dry-run(모의 모델)만 수행했으며 그 결과는 성과로 인용하지 않습니다.
실험마다 exp-001처럼 고유 ID를 부여합니다.

## 실행 방법

```bash
uv sync --python 3.12

# 1) dry-run — provider 연락 없음, 비용 0. 파이프라인 검증용
uv run python scripts/run_eval.py --arm C1 --policy react --limit 5 \
    --out results/exp-000/c1-react.jsonl

# 2) 실호출 — 승인·예산 합의 후에만. 키는 환경변수로만 받습니다
TASK_A_API_KEY=... uv run python scripts/run_eval.py --live \
    --model-id <모델 ID> --base-url <endpoint> \
    --arm C1 --policy react --condition sufficient \
    --budget-usd 2.00 --out results/exp-001/c1-react.jsonl

# 3) 채점 — gold를 읽는 유일한 명령
uv run python scripts/score_run.py --run results/exp-001/c1-react.jsonl \
    --c2 results/exp-001/c2-react.jsonl --grades data/task_a/grades.jsonl
```

비교 축은 서로 독립입니다. `--arm`(C0/C1/C2)은 도달 가능한 정보, `--condition`
(sufficient/missing/conflict/misleading)은 제공된 코퍼스 변형, `--policy`
(react/fixed_workflow/closed_book)는 다음 행동을 누가 정하는지를 나타냅니다.

안전장치는 코드에 들어 있습니다. `--live` 없이는 provider를 호출하지 않고, `--budget-usd`는
누적 비용이 상한을 넘으면 실행을 중단하며, 자동 재시도와 모델 자동 변경은 없고, 이미 완료된
에피소드는 재실행하지 않습니다. C1은 캐시가 따뜻해도 외부 검색을 거부합니다.

## 실험 기록

실험 기록:
- 연구 질문, 비교/고정 조건
- 데이터 버전과 code commit
- 정확한 모델 ID, provider, prompt 버전, seed 등 적용 가능한 설정
- 실행 명령, Python 및 의존성 버전
- 사례·조건·반복 수, 최대 호출 수, token/금액 상한
- 성공 판정, 오류·재시도·중단 정책
- 시작/종료 시각, 전체 시도 수와 결과 위치

`run_eval.py`는 이 중 대부분을 결과 로그의 `config`에 자동 기록합니다(run_id, arm, condition,
policy, model_id, prompt_version, data_version, seed, code_commit, replay).
남은 항목(연구 질문, 예산 합의, 시작·종료 시각, 중단 정책)은 `exp-NNN.md`로 남깁니다.

실행 승인이 있기 전에는 API 호출하지 않습니다.
자동 재시도·자동 모델 변경은 기본적으로 하지 않습니다.
원본 실패 기록은 보존하되 비공개 원문·키가 있는 raw log는 공개 저장소에 넣지 않습니다.
GPU/LLM 실험을 GitHub Actions에 자동 등록하지 않습니다.

## 아직 없는 것

- 코퍼스 파일: 기사 37건의 원문 수집이 남았습니다. 수집 본문은 저작권 때문에 `data/raw/`
  (Git 제외)에 두고 manifest만 커밋합니다.
- 근거 조건 4변형: 오염 문서 주입은 사람이 설계·검수하는 단계입니다.
- E·T rubric 등급 파일: 없으면 GSR·노출률·채택률은 0이 아니라 계산 불가로 표시됩니다.
- 모델·provider·단가: `llm.PRICES`는 비어 있으며 실제 견적과 조회일을 넣기 전까지 비용은 미확인입니다.
