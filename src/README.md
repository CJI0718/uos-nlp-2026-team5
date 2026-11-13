# 실행 코드 (`src/task_a`)

Task A(불완전한 근거 아래서의 팩트체크 및 검증 게이팅 기반 후속 미션 수행)를 위한 **MCP 도구 서버 및 채점 패키지**입니다.
자체 LLM 에이전트 루프를 두지 않고, 상용/오픈소스 AI 에이전트(Antigravity, Claude Code, Cursor, Codex 등)가 표준 MCP(Model Context Protocol) 또는 CLI를 통해 도구를 호출합니다.

```
task_a/
  schema.py       Claim / Gold / EvidenceUnit / ToolEvent / AgentResult / EpisodeState
  dataset.py      evaluation.md §9.8 파서 (원본은 읽기만 함)
  retrieve.py     BM25 + Kiwi/bigram 토크나이저, CorpusBackend
  web.py          C2 외부 웹 검색(Tavily API + DuckDuckGo 폴백) 및 본문 추출기
  tools.py        도구 5개 + whitelisted 계산기(diff/pct_change/tz_convert/multiply/ratio 등) + fetch URL 차단
  missions.py     검증 게이팅(Verification Gate) 및 후속 Mission/Tracking 실행기
  mcp_server.py   MCP JSON-RPC 2.0 stdio 서버 & AgentEnvironment (자동 RunLog 기록 및 정답 누출 차단)
  toollog.py      append-only 실행 로그, 외부 응답 캐시, 비용 집계
  scorer.py       정확도, Macro-F1, GSR, 오염 노출·채택률, C1→C2 복구율·역효과율 산식
  score_run.py    채점 — gold.jsonl을 여는 유일한 모듈
  mock.py         오프라인 테스트용 모의 코퍼스 백엔드 (MockBackend)
```

## 실행

```bash
uv sync --python 3.12
uv run pytest -q

# 데이터 추출 (evaluation.md -> data/task_a/*.jsonl)
uv run python scripts/extract_fc_data.py

# 외부 에이전트 연동 1: MCP JSON-RPC stdio 서버
uv run python scripts/mcp_stdio.py --arm C1 --out results/exp-mcp/c1.jsonl

# 외부 에이전트 연동 2: CLI 어댑터
uv run python scripts/agent_cli.py list --limit 5

# 결과 채점
uv run python scripts/score_run.py --run results/exp-mcp/c1.jsonl
```

실행 방법은 [experiments/README.md](../experiments/README.md)를 봅니다.

## 설계 제약

- **정답 누출 원천 차단**: `AgentEnvironment`(`mcp_server.py`)는 `gold.jsonl`, `evidence.jsonl`, `evaluation.md`를 열 수 없으며 파일 시스템 도구를 노출하지 않습니다.
- **실행 환경과 채점기의 분리**: `score_run.py`만 `gold.jsonl`을 읽어 채점합니다.
- **검증 게이팅(Verification Gate)**: `missions.py`는 미검증(`not_enough_evidence`) 또는 정정값(`correction`) 없는 반박(`refuted`) 주장에 대해 일정 등록·아티팩트 생성을 코드 수준에서 거부합니다.
- **결정론적 계산**: `calculate_comparison`은 whitelisted 연산(`diff`, `pct_change`, `tz_convert`, `multiply`, `ratio`, `range_check`)만 허용하며 임의 수식 평가(`eval`)를 쓰지 않습니다.
