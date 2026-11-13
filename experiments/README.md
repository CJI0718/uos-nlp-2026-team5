# 실험 설정과 재현

이 브랜치(`feat/agent-skill-mcp`)에서는 외부 AI 에이전트(Antigravity, Claude Code, Cursor 등)에 [skills/factcheck-mission-agent/SKILL.md](../skills/factcheck-mission-agent/SKILL.md)와 MCP 서버([scripts/mcp_stdio.py](../scripts/mcp_stdio.py))를 장착하여 실험을 수행합니다.
실험마다 `exp-001`처럼 고유 ID를 부여합니다.

## 실행 방법

```bash
uv sync --python 3.12

# 1) MCP 서버 구동 (루트의 .mcp.json을 통해 에이전트 클라이언트가 자동 실행하거나 수동 실행)
#    - C1 조건: 로컬 코퍼스만 사용 (외부 웹 차단, API 키 불필요)
uv run python scripts/mcp_stdio.py \
    --arm C1 --condition sufficient \
    --out results/exp-001/c1-mcp.jsonl

#    - C2 조건: 코퍼스 + 실시간 외부 웹 검색 (Tavily API 키 없으면 DuckDuckGo HTML 폴백 자동 사용)
uv run python scripts/mcp_stdio.py \
    --arm C2 --condition sufficient \
    --out results/exp-001/c2-mcp.jsonl

# 2) 또는 터미널 기반 에이전트용 CLI 어댑터 사용
uv run python scripts/agent_cli.py start --claim-id FC002 --arm C1 --out results/exp-001/c1-mcp.jsonl
uv run python scripts/agent_cli.py tool search_evidence --args '{"query": "Pre-orders January 19 2024 PST"}'
uv run python scripts/agent_cli.py tool calculate_comparison --args '{"op": "tz_convert", "time": "2024-01-19 05:00", "from_tz": "PST", "to_tz": "KST"}'
uv run python scripts/agent_cli.py tool execute_mission --args '{"mission_type": "event_manager", "verdict": "refuted", "title": "비전 프로 사전예약", "summary": "22:00 KST로 시간대 정정", "cited_evidence_ids": ["EV_FC002_1"], "correction": "2024-01-19 22:00 KST", "distortion_type": "timezone_or_date_error", "event_start_kst": "2024-01-19 22:00"}'
uv run python scripts/agent_cli.py finish --args '{"verdict": "refuted", "abstain": false, "cited_evidence_ids": ["EV_FC002_1"], "justification": "05:00 PST는 22:00 KST임", "correction": "2024-01-19 22:00 KST", "stop_reason": "evidence_sufficient", "distortion_type": "timezone_or_date_error", "problematic_span": "오전 5시(한국시간)", "mission_type": "event_manager"}'

# 3) 채점 — gold.jsonl을 읽는 유일한 명령
uv run python scripts/score_run.py \
    --run results/exp-001/c1-mcp.jsonl \
    --c2 results/exp-001/c2-mcp.jsonl \
    --grades data/task_a/grades.jsonl
```

비교 축은 서로 독립입니다:
- `--arm` (`C0` / `C1` / `C2`): 도달 가능한 정보 범위 (`C0` 코퍼스·웹 차단, `C1` 코퍼스만 허용, `C2` 코퍼스+외부 웹 허용)
- `--condition` (`sufficient` / `missing` / `conflict` / `misleading`): 제공된 코퍼스 변형

## 실험 기록

`mcp_server.py`는 각 에피소드가 `finish_verification`을 호출할 때 결과 로그(`--out`)의 `config`와 `result`에 실행 설정, 도구 호출 궤적(`events`), 왜곡 특정 정보(`distortion_type`, `problematic_span`), 후속 미션 산출물(`mission_type`, `mission_output`), 도구 사용량(`usage`)을 자동으로 기록합니다.
