# UOS NLP 5조 · 검증 게이팅 기반 팩트체크 & 미션 에이전트 (Task A — MCP & Skill)

2026년 서울시립대학교 NLP 수업 5조의 과제 작업 공간입니다.

> **처음이면 [빠른 시작](#빠른-시작)부터 보세요.** 기말 실험 결과는 [최종 보고서](docs/research/fact_checking/final-20261125/README.md)([PDF](docs/research/fact_checking/final-20261125/final_report.pdf))에 있어요.

## 과제

2026-11-12 팀 내 전달 내용 기준입니다. 제출 형식과 세부 요구는 교수님의 원본 안내를 확인합니다.

1. AI Agent로 풀 수 있는 태스크를 설정한다.
2. 그 태스크의 평가데이터 50개를 직접 작성한다.
3. 태스크를 실제로 수행해 본다.
4. 결과를 분석한다.
5. 분석을 바탕으로 Action Item을 도출·실행해 개선했는지 확인한다.

## 우리 태스크

**주장 하나를 받아 근거를 찾고, 사실 여부와 왜곡 지점을 검증한 뒤, 검증 게이팅(Verification Gate)을 통과한 경우에만 후속 미션(일정 `.ics` 생성, 비교 아티팩트 `.md` 생성, 장기 추적 등록)을 수행한다.**

| 요소 | 내용 |
| --- | --- |
| 입력 | 정규화한 단일 주장, 대상 시점, 원문 발췌 (`data/task_a/claims.jsonl`) |
| 행동 | 근거 검색(코퍼스·웹), 본문 읽기, 수치·시간대 계산, 검증 게이팅 기반 후속 미션 실행, 종료 선택 |
| 출력 | Supported / Refuted / Not Enough Evidence, 인용 근거, 왜곡 유형·구간, 정정 사실, 후속 미션 산출물 |

태스크 정의의 전체 문안은 [팀 논의·연구 방향·Task](docs/research/fact_checking/midterm-20261103/팀논의_연구방향과_Task.md)에 있습니다.

## 구조

| 구성 | 역할 |
| --- | --- |
| **하네스 서버** ([src/task_a/mcp_server.py](src/task_a/mcp_server.py)) | 에피소드마다 도구(근거 검색·열람, 문서 안 찾기, 계산기, 웹 검색·열기)를 주고, 판정 제출을 검사(검증 게이트)하고, 모든 호출을 기록해요 |
| **Skill** ([skills/factcheck-mission-agent/SKILL.md](skills/factcheck-mission-agent/SKILL.md)) | 검증 절차와 판정 기준 지침. 평가 사례는 들어 있지 않아요(테스트로 확인) |
| **실행기** ([scripts/run_task_a.py](scripts/run_task_a.py)) | 평가데이터 50개를 조건별로 돌리고 채점해요. 두 가지 방식으로 같은 서버를 써요 |
| └ `--backend openai` (기본) | OpenAI 호환 API 모델(Mistral, DeepSeek, OpenRouter 등)이 서버 도구를 직접 호출([agent_loop.py](src/task_a/agent_loop.py)) |
| └ `--backend claude` | 주장마다 새 `claude -p` 세션이 MCP로 서버에 붙음(저장소 밖 작업 폴더에서 실행) |
| **MCP 서버** ([scripts/mcp_stdio.py](scripts/mcp_stdio.py)) | Claude Code 등 MCP를 쓰는 에이전트에 같은 하네스를 붙여요. 등록되지 않은 주장도 바로 검증할 수 있어요 |
| **채점기** ([src/task_a/score_run.py](src/task_a/score_run.py)) | 정답(`gold.jsonl`)을 여는 유일한 코드. 실행기의 `score`가 써요 |

## 빠른 시작

```bash
uv sync --python 3.12
uv run pytest -q                       # 오프라인 테스트(모델·웹 호출 없음)
cp .env.example .env                   # 키 두 개를 채워 넣기(커밋되지 않음)
```

`.env`에는 모델 API 키(기본 `MISTRAL_API_KEY`)와 웹 검색용 `TAVILY_API_KEY`를 넣어요.

**1) 주장 3개로 시험하기.** 아래 명령은 모델과 Tavily를 호출해 비용이 들어요(DeepSeek 기준 몇 센트). `--dry-run`을 붙이면 호출 없이 계획만 보여 줘요.

```bash
uv run python scripts/run_task_a.py run --exp-id my-test --arms C2W --claims FC001,FC002,FC003 \
    --harness-v3 --block-self-citation --max-external-calls 25 --max-tool-calls 32 --max-turns 40
uv run python scripts/run_task_a.py score --exp-id my-test      # results/my-test/summary.md
```

**2) 50개 전체.** `--claims`를 빼면 돼요. 조건과 옵션은 [실험 안내](experiments/README.md)에 있어요.

**3) 내 주장 하나 검증하기(Claude Code).** 저장소의 [.mcp.json](.mcp.json)이 하네스를 웹 검색 모드로 붙여요. Claude Code를 이 폴더에서 열고 "이 주장 검증해 줘: …"라고 하면, `submit_claim`으로 시작해 근거를 찾고 판정해요. 기록은 `results/raw/dev-interactive/`(Git 제외)에 쌓여요. 이 모드는 저장소의 정답 파일을 에이전트가 읽을 수 있으므로 실험에는 쓰지 않아요.

## 파일 안내

| 위치 | 내용 |
| --- | --- |
| [docs/research/fact_checking/final-20261125/](docs/research/fact_checking/final-20261125/README.md) | **기말 실험 보고서**(분석·개선·한계)와 PDF |
| [experiments/](experiments/README.md) | 실행 방법, 조건, 옵션, 예산 |
| [results/](results/README.md) | 실험별 결과 요약(exp-001~014) |
| [data/](data/README.md) | 평가데이터 50개(에이전트 입력과 채점 자료를 분리), 근거 자료집 수집 방법 |
| [src/](src/README.md) | 하네스 서버, 도구, 게이트, 실행 루프, 채점기 |
| [skills/](skills/factcheck-mission-agent/SKILL.md) | 에이전트에 주는 검증 지침(Skill) |
| [missions/](missions/README.md) | 검증을 통과한 뒤 만드는 후속 결과물(`.ics`, `.md`) 규칙 |
| [src/assistant/](src/assistant/README.md) | 일정 비서 앱(검증한 행사만 달력에 넣는 로컬 웹 앱, `scripts/assistant_app.py serve --demo`) |
| [tests/](tests/) | 오프라인 테스트 |
| [docs/decisions/](docs/decisions/README.md) · [docs/research/](docs/research/README.md) | 결정 기록, 태스크·평가·도구 설계 문서 |

## 원칙

- 참조 판정(`data/task_a/gold.jsonl`, `evidence.jsonl`, `evaluation_cases.md`)은 채점기만 읽어요. 하네스 서버는 이 파일들을 주장 입력이나 자료집으로 받지 않아요. API 모델에는 파일 도구가 없고, Claude 실행은 저장소 밖 작업 폴더에서 MCP 도구만 허용해요. 남은 한계는 [실험 안내](experiments/README.md#범위와-한계)와 [보고서 §11](docs/research/fact_checking/final-20261125/README.md)에 있어요.
- 논문 수치, 설계 제안, 우리가 관찰한 결과를 구분해서 씁니다. 결과를 지어내지 않습니다.
- API 키, 개인정보, 권한 없는 원문·PDF, 원본 로그는 올리지 않습니다.
- main 직접 수정 대신 branch → PR로 작업합니다. [협업 안내](CONTRIBUTING.md) · [Agent 지침](AGENTS.md)
