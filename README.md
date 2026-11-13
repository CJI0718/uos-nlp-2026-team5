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

- **MCP 서버 ([.mcp.json](.mcp.json), [scripts/mcp_stdio.py](scripts/mcp_stdio.py), [src/task_a/mcp_server.py](src/task_a/mcp_server.py))**: JSON-RPC 2.0 `stdio` 표준을 통해 `start_episode`, `search_evidence`, `read_evidence`, `calculate_comparison`, `search_web`, `fetch_url`, `execute_mission`, `finish_verification` 도구를 노출하고 모든 궤적을 `RunLog` JSONL로 자동 기록합니다.
- **Agent Skill ([skills/factcheck-mission-agent/SKILL.md](skills/factcheck-mission-agent/SKILL.md))**: 4단계 워크플로우(적응적 교차언어/수치 검증 → 7대 왜곡 유형 특정 → 검증 게이팅 미션 실행 → 구조화 판정 제출) 지침서입니다.
- **CLI 어댑터 ([scripts/agent_cli.py](scripts/agent_cli.py))**: 터미널 기반 에이전트가 쉘 명령으로 동일한 도구를 호출할 수 있는 어댑터입니다.

## 파일 안내

| 위치 | 내용 |
| --- | --- |
| [.mcp.json](.mcp.json) | Claude Code / Cursor / Antigravity용 MCP 서버 설정 파일 |
| [src/](src/README.md) | MCP 서버, 도구, BM25/웹 검색, 수치·시간대 계산기, 후속 미션 게이팅, 채점기 |
| [skills/](skills/factcheck-mission-agent/SKILL.md) | 외부 AI 에이전트 장착용 4단계 팩트체크·왜곡특정·미션수행 Skill |
| [missions/](missions/README.md) | 검증 게이팅 통과 후 생성되는 후속 미션 결과물(`.ics`, `.md`) 및 장기 추적 레지스트리 |
| [tests/](tests/) | 오프라인 단위·통합 테스트 |
| [scripts/](scripts/) | 데이터 추출(`extract_fc_data.py`), MCP 서버(`mcp_stdio.py`), CLI 어댑터(`agent_cli.py`), 채점(`score_run.py`) |
| [data/](data/README.md) | 주장 50개(에이전트 입력)와 참조 판정·근거(채점기 전용) |
| [experiments/](experiments/README.md) | 실행 방법과 실험 기록 양식 |
| [results/](results/README.md) · [reports/](reports/README.md) | 결과 요약, 보고서 |
| [docs/decisions/](docs/decisions/README.md) | 확정한 결정 |
| [docs/research/](docs/research/README.md) | 태스크·평가·도구 설계 문서 |

## 실행

```bash
uv sync --python 3.12
uv run pytest -q

# 1) MCP 서버 실행 (Claude Code, Cursor, Antigravity 등이 자동 호출)
uv run python scripts/mcp_stdio.py --arm C2 --out results/exp-mcp/run.jsonl

# 2) 또는 에이전트 CLI 어댑터로 에피소드 수행
uv run python scripts/agent_cli.py start --claim-id FC002 --arm C1 --out /tmp/fc002.jsonl

# 3) 채점 (gold.jsonl을 읽는 유일한 명령)
uv run python scripts/score_run.py --run /tmp/fc002.jsonl
```

## 원칙

- 참조 판정(`data/task_a/gold.jsonl`, `evaluation.md`)은 채점기에만 주고 에이전트 환경(`mcp_server.py`, `agent_cli.py`)에서 접근을 원천 차단합니다.
- 논문 수치, 설계 제안, 우리가 관찰한 결과를 구분해서 씁니다. 결과를 지어내지 않습니다.
- API 키, 개인정보, 권한 없는 원문·PDF, 원본 로그는 올리지 않습니다.
- main 직접 수정 대신 branch → PR로 작업합니다. [협업 안내](CONTRIBUTING.md) · [Agent 지침](AGENTS.md)
