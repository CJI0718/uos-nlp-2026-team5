# 실행 코드 (`src/task_a`)

Task A(불완전한 근거 아래서의 팩트체크 및 검증 게이팅 기반 후속 미션 수행)를 위한 **MCP 도구 서버 및 채점 패키지**입니다.
자체 LLM 에이전트 루프를 두지 않고, 상용/오픈소스 AI 에이전트(Antigravity, Claude Code, Cursor, Codex 등)가 표준 MCP(Model Context Protocol) 또는 CLI를 통해 도구를 호출합니다.

```
task_a/
  schema.py       Claim / Gold / EvidenceUnit / ToolEvent / AgentResult / EpisodeState
  dataset.py      data/task_a/evaluation_cases.md 파서 (원본은 읽기만 함)
  retrieve.py     BM25 + Kiwi/bigram 토크나이저, CorpusBackend
  web.py          C2 외부 웹 검색(Tavily API + DuckDuckGo 폴백) 및 본문 추출기
  tools.py        도구 5개 + whitelisted 계산기(diff/pct_change/tz_convert/multiply/ratio 등) + fetch URL 차단
  missions.py     검증 게이팅(Verification Gate) 및 후속 Mission/Tracking 실행기
  mcp_server.py   MCP JSON-RPC 2.0 stdio 서버 & AgentEnvironment (RunLog 기록, 코퍼스 검증, 미션 실행)
  toollog.py      append-only 실행 로그, 외부 응답 캐시, 비용 집계
  scorer.py       정확도, Macro-F1, GSR, 오염 노출·채택률, C1→C2 복구율·역효과율 산식
  score_run.py    채점 — gold.jsonl을 여는 유일한 모듈. 상수 답 기준선과 미션 안전성 포함
  corpus_build.py 원문 URL에서 C1 코퍼스·채점용 대응표·수집 보고서 생성 (scripts/build_corpus.py)
  mock.py         오프라인 테스트용 모의 코퍼스 백엔드 (MockBackend)
```

## 실행

```bash
uv sync --python 3.12
uv run pytest -q

# 데이터 추출 (evaluation.md -> data/task_a/*.jsonl)
uv run python scripts/extract_fc_data.py

# 외부 에이전트 연동: 격리 작업공간 생성 (내부에서 mcp_stdio.py를 실행)
uv run python scripts/make_agent_workspace.py --workspace ~/agent-runs/exp-001-c0 \
    --run-id exp-001-c0 --arm C0 --model-id <agent+model>

# 사용자가 보여 준 주장을 바로 검증 (미리 등록한 주장 없이, 실제 웹, 결과는 ./missions)
uv run python scripts/mcp_stdio.py --arm C2 --live-web --web-only \
    --allow-user-claims --no-preset-claims --model-id <agent+model> --out results/user/run.jsonl

# CLI 어댑터 (격리 경계 아님)
uv run python scripts/agent_cli.py list --limit 5

# 결과 채점
uv run python scripts/score_run.py --run results/exp-001-c0/run.jsonl
```

실행 방법은 [experiments/README.md](../experiments/README.md)를 봅니다.

## 설계 제약

- **정답 누출 차단(서버 범위)**: `AgentEnvironment`는 `gold.jsonl`, `evidence.jsonl`, `evaluation.md`를 주장 입력이나 코퍼스로 받지 않습니다. 참조 근거 전용 필드(`claim_id`, `check_status`, `locator`, `content`)가 있는 행과 주장 ID가 들어간 `evidence_id`도 거부합니다. 파일 시스템 도구는 노출하지 않습니다. 에이전트 자체 도구 차단은 `scripts/make_agent_workspace.py`가 맡습니다.
- **조건 강제**: C1·C2는 코퍼스가 없으면 시작하지 않습니다. 아직 구현되지 않은 `condition`(missing/conflict/misleading)도 거부합니다.
- **실행 환경과 채점기의 분리**: `score_run.py`만 `gold.jsonl`을 읽어 채점합니다.
- **검증 게이팅**: 미션은 `finish_verification` 안에서만 실행되고, 제출된 최종 판정으로 게이트를 적용합니다. 미확인·보류 판정이면 차단하고, 이번 에피소드에서 읽은 근거를 인용해야 하며, 반박이면 정정값이 필요합니다. 규칙은 [missions/README.md](../missions/README.md)에 있습니다.
- **결정론적 계산**: `calculate_comparison`은 whitelisted 연산(`diff`, `pct_change`, `percentage_point_gap`, `tz_convert`, `scale_unit`, `multiply`, `ratio`)만 허용하며 임의 수식 평가(`eval`)를 쓰지 않습니다.
