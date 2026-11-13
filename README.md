# UOS NLP 5조 · 팩트체크 Agent (Task A)

2026년 서울시립대학교 NLP 수업 5조의 과제 작업 공간입니다.

> **이 브랜치는 과제 수행에 필요한 파일만 남긴 작업용 브랜치입니다.**
> 논문 PDF·해설·발표 자료·이전 후보 탐색 기록은 삭제하지 않았으며
> [main 브랜치](https://github.com/CJI0718/uos-nlp-2026-team5/tree/main)에 그대로 있습니다.
> 이 브랜치를 main에 합칠지는 팀 합의 전입니다.

## 과제

2026-11-12 팀 내 전달 내용 기준입니다. 제출 형식과 세부 요구는 교수님의 원본 안내를 확인합니다.

1. AI Agent로 풀 수 있는 태스크를 설정한다.
2. 그 태스크의 평가데이터 50개를 직접 작성한다.
3. 태스크를 실제로 수행해 본다.
4. 결과를 분석한다.
5. 분석을 바탕으로 Action Item을 도출·실행해 개선했는지 확인한다.

## 우리 태스크

**주장 하나를 받아 근거를 찾고, 더 찾을지 멈출지 스스로 정한 뒤, 근거와 함께 판정한다.**

| 요소 | 내용 |
| --- | --- |
| 입력 | 정규화한 단일 주장, 대상 시점, 원문 발췌 |
| 행동 | 근거 검색, 본문 읽기, 수치·시간대 계산, 추가 검증 여부와 종료 선택 |
| 출력 | Supported / Refuted / Not Enough Evidence, 인용 근거, 짧은 이유, 정정 사실 |

태스크 정의의 전체 문안은 [팀 논의·연구 방향·Task](docs/research/fact_checking/midterm-20261103/팀논의_연구방향과_Task.md)에 있습니다.
그 문서의 근거 조건 4변형, C0/C1/C2 비교, RL 제어기는 **설계 제안**이며 실행한 실험이 아닙니다.

## 현재 상태

| 과제 단계 | 상태 |
| --- | --- |
| 1. 태스크 설정 | 완료 — [결정 002](docs/decisions/002-task-a-midterm-20261105.md) |
| 2. 평가데이터 50개 | 작성됨, 독립 검수 전 초안. FC038은 판정 보류 — [evaluation.md §9](docs/research/fact_checking/evaluation.md) |
| 3. 태스크 수행 | **미실행.** 실모델 실험 기록 없음 |
| 4. 결과 분석 | 3단계 이후 |
| 5. Action Item·개선 | 4단계 이후 |

모델·provider·호출 예산·외부 검색 API는 정해지지 않았습니다.

### 3단계 전에 필요한 것

- 에이전트가 검색할 대상: 기사 원문 코퍼스 또는 웹 검색 provider 합의.
- 2026-11-12 코드 검토에서 확인한 `src/task_a/loop.py` 결함 2건(멀티턴 도구 호출 기록 누락, 도구 예산 소진 시 판정 기회 박탈)은 수정 및 테스트 고정 완료(`tests/task_a/test_mcp_and_missions.py`).

## 파일 안내

| 위치 | 내용 |
| --- | --- |
| [src/](src/README.md) | 에이전트 루프, 도구, 검색, 정책, 후속 미션 게이팅, MCP 서버, 채점 |
| [skills/](skills/factcheck-mission-agent/SKILL.md) | 외부 AI 에이전트 장착용 4단계 팩트체크·왜곡특정·미션수행 Skill |
| [missions/](missions/README.md) | 검증 게이팅 통과 후 생성되는 후속 미션 결과물(`.ics`, `.md`) 및 장기 추적 레지스트리 |
| [tests/](tests/) | 오프라인 테스트 (192개) |
| [scripts/](scripts/) | 데이터 추출, 배치 실행, MCP/CLI 에이전트 도구, 채점 명령 |
| [data/](data/README.md) | 주장 50개(에이전트 입력)와 참조 판정·근거(채점기 전용) |
| [experiments/](experiments/README.md) | 실행 방법과 실험 기록 양식 |
| [results/](results/README.md) · [reports/](reports/README.md) | 결과 요약, 보고서 |
| [docs/decisions/](docs/decisions/README.md) | 확정한 결정 |
| [docs/research/](docs/research/README.md) | 태스크·평가·도구 설계 문서 |

## 실행

```bash
uv sync --python 3.12
uv run pytest -q
uv run python scripts/run_eval.py --arm C1 --policy react --limit 5 --out /tmp/c1.jsonl   # dry-run, 비용 0
uv run python scripts/score_run.py --run /tmp/c1.jsonl
```

dry-run은 모의 모델이 모든 주장에 보류로 답하는 파이프라인 점검이며 결과가 아닙니다.

## 원칙

- 실모델 호출은 모델과 호출 예산을 합의한 뒤에만 합니다. 자동 재시도·모델 자동 변경은 없습니다.
- 참조 판정은 채점기에만 주고 에이전트 입력에서 제외합니다.
- 논문 수치, 설계 제안, 우리가 관찰한 결과를 구분해서 씁니다. 결과를 지어내지 않습니다.
- API 키, 개인정보, 권한 없는 원문·PDF, 원본 로그는 올리지 않습니다.
- main 직접 수정 대신 branch → PR로 작업합니다. [협업 안내](CONTRIBUTING.md) · [Agent 지침](AGENTS.md)
