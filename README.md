# UOS NLP 5조 · 검증 게이팅 기반 팩트체크 & 미션 에이전트 (Task A — MCP & Skill)

2026년 서울시립대학교 NLP 수업 5조의 과제 작업 공간입니다.

> **이 브랜치(`feat/agent-skill-mcp`)는 상용/오픈소스 AI 에이전트(Claude Code, Antigravity, Cursor, Codex 등)에 우리 팀의 MCP 도구 서버와 `SKILL.md`를 장착하여 태스크를 수행하는 전용 브랜치입니다.**
> 논문 PDF·해설·발표 자료·이전 후보 탐색 기록은 삭제하지 않았으며
> [main 브랜치](https://github.com/CJI0718/uos-nlp-2026-team5/tree/main)에 그대로 있습니다.

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

## 아키텍처 (MCP 서버 + Agent Skill)

자체 제작 LLM 루프를 두지 않고, **기존 AI 에이전트에 MCP(Model Context Protocol) 서버와 `SKILL.md`를 연결**하여 구동합니다:

- **MCP 서버 ([scripts/mcp_stdio.py](scripts/mcp_stdio.py), [src/task_a/mcp_server.py](src/task_a/mcp_server.py))**: JSON-RPC 2.0 `stdio`로 `start_episode`, `search_evidence`, `read_evidence`, `calculate_comparison`, `search_web`, `fetch_url`, `finish_verification` 도구를 노출하고 모든 궤적을 `RunLog` JSONL로 기록합니다. 후속 미션은 `finish_verification` 안에서 최종 판정으로 검증 게이트를 적용한 뒤 실행합니다.
- **격리 작업공간 ([scripts/make_agent_workspace.py](scripts/make_agent_workspace.py))**: 저장소 밖에 gold가 없는 실행 디렉터리를 만들고, Claude Code의 내장 파일·셸·웹 도구를 막은 채 MCP 도구만 허용합니다. 실험은 이 작업공간에서만 실행합니다.
- **Agent Skill ([skills/factcheck-mission-agent/SKILL.md](skills/factcheck-mission-agent/SKILL.md))**: 4단계 워크플로우(근거 탐색 → 결정론적 검산·왜곡 특정 → 검증 게이팅 미션 선택 → 구조화 판정 제출) 지침서입니다. 평가 사례는 들어 있지 않습니다(테스트로 확인).
- **CLI 어댑터 ([scripts/agent_cli.py](scripts/agent_cli.py))**: 셸로 같은 도구를 호출하는 어댑터입니다. 셸을 쓰는 에이전트는 저장소를 읽을 수 있으므로 격리 경계가 아닙니다.

## 파일 안내

| 위치 | 내용 |
| --- | --- |
| [.mcp.json](.mcp.json) | 개발용 MCP 서버 설정(`dev-interactive`). 실험에는 격리 작업공간을 씁니다 |
| [src/](src/README.md) | MCP 서버, 도구, BM25/웹 검색, 수치·시간대 계산기, 후속 미션 게이팅, 채점기 |
| [skills/](skills/factcheck-mission-agent/SKILL.md) | 외부 AI 에이전트 장착용 4단계 팩트체크·왜곡특정·미션수행 Skill |
| [missions/](missions/README.md) | 검증 게이팅 통과 후 생성되는 후속 미션 결과물(`.ics`, `.md`) 및 장기 추적 레지스트리 |
| [tests/](tests/) | 오프라인 단위·통합 테스트 |
| [scripts/](scripts/) | 데이터 추출(`extract_fc_data.py`), 원문 코퍼스 수집(`build_corpus.py`), MCP 서버(`mcp_stdio.py`), 격리 작업공간(`make_agent_workspace.py`), CLI 어댑터(`agent_cli.py`), 채점(`score_run.py`) |
| [data/](data/README.md) | 주장 50개(에이전트 입력), 참조 판정·근거(채점기 전용), 원문 코퍼스 수집 방법과 결과 |
| [experiments/](experiments/README.md) | 실행 방법과 실험 기록 양식 |
| [results/](results/README.md) · [reports/](reports/README.md) | 결과 요약, 보고서 |
| [docs/decisions/](docs/decisions/README.md) | 확정한 결정 |
| [docs/research/](docs/research/README.md) | 태스크·평가·도구 설계 문서 |

## 실행

```bash
uv sync --python 3.12
uv run pytest -q

# 0) C1·C2용 원문 코퍼스 수집 (원문 사이트 접속, Git 제외 위치에 저장)
uv run python scripts/build_corpus.py

# 1) 격리 작업공간 생성
uv run python scripts/make_agent_workspace.py --workspace ~/agent-runs/exp-001-c0 \
    --run-id exp-001-c0 --arm C0 --model-id claude-code-<버전>+<모델ID>

# 2) 작업공간의 RUN.md에 적힌 명령으로 주장마다 새 세션 실행 (팀이 승인한 예산 안에서)

# 3) 채점 (gold.jsonl을 읽는 유일한 명령)
uv run python scripts/score_run.py --run results/exp-001-c0/run.jsonl
```

## 원칙

- 참조 판정(`data/task_a/gold.jsonl`, `evidence.jsonl`, `evaluation.md`)은 채점기에만 줍니다. MCP 서버는 이 파일들을 주장 입력이나 코퍼스로 받지 않고, 에이전트 자체 도구는 격리 작업공간에서 막습니다. 남은 한계는 [실험 안내](experiments/README.md#범위와-남은-한계)에 모아 둡니다.
- 논문 수치, 설계 제안, 우리가 관찰한 결과를 구분해서 씁니다. 결과를 지어내지 않습니다.
- API 키, 개인정보, 권한 없는 원문·PDF, 원본 로그는 올리지 않습니다.
- main 직접 수정 대신 branch → PR로 작업합니다. [협업 안내](CONTRIBUTING.md) · [Agent 지침](AGENTS.md)
