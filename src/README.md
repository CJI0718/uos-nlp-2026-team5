# 실행 코드 (`src/task_a`)

Task A(주장 하나를 근거로 검증하고, 검증을 통과했을 때만 후속 미션을 수행)의 **하네스 서버, 실행 루프, 채점기**예요.
같은 서버를 두 방식으로 써요. API 모델은 실행 루프(`agent_loop.py`)가 서버 도구를 직접 호출하고, Claude Code 같은 MCP 에이전트는 `scripts/mcp_stdio.py`로 붙어요.

```
task_a/
  mcp_server.py   AgentEnvironment(에피소드, 조건별 도구 목록, 예산, 제출 검사, 실행 기록) + MCP stdio 서버
  tools.py        도구: 자료집 검색·열람, find_in_page, 계산기(diff/pct_change/tz_convert 등), 웹 검색·열기, 차단 규칙
  claim_gate.py   하네스 v3 제출 검사: 인용문 대조, 주장 유형(사실·예측·발언), 예측 주장 규칙
  value_check.py  하네스 v3 결과물 값 대조: 미션 결과물의 수치·일시가 인용 문서나 그 값으로 한 계산에 있는지
  agent_loop.py   OpenAI 호환 API용 실행 루프(하네스 조건)와 하네스 없는 비교 에이전트(C2P)
  skill.py        Skill 본문 읽기
  missions.py     검증 게이트와 후속 미션(.ics, .md, 추적 등록)
  retrieve.py     BM25 + Kiwi/bigram 토크나이저, 자료집 검색
  web.py          Tavily 웹 검색(DuckDuckGo 폴백)과 본문 추출
  article.py      본문 추출 보조(Next.js 페이지 데이터 등)
  provenance.py   본문 겹침으로 출처군 묶기, 전재 기사 표시
  corpus_build.py 근거 URL에서 C1 자료집 만들기(scripts/build_corpus.py)
  dataset.py      data/task_a/evaluation_cases.md 파서(원본은 읽기만 함)
  schema.py       Claim / Gold / EvidenceUnit / ToolEvent / AgentResult
  toollog.py      실행 기록, 외부 응답 캐시
  scorer.py       정확도, Macro-F1 등 산식
  score_run.py    채점: gold.jsonl을 여는 유일한 모듈
  mock.py         오프라인 테스트용 모의 백엔드
```

## 실행

실험 실행은 [experiments/README.md](../experiments/README.md)를 봐요. 개발할 때 자주 쓰는 명령은 이거예요.

```bash
uv run pytest -q                                   # 오프라인 테스트
uv run python scripts/extract_fc_data.py           # evaluation_cases.md -> data/task_a/*.jsonl
uv run python scripts/build_corpus.py              # C1 자료집 수집(원문 사이트 접속)

# MCP 서버를 직접 띄우기: 등록되지 않은 주장도 검증(웹만, 하네스 v3). .mcp.json과 같은 설정
uv run python scripts/mcp_stdio.py --arm C2 --live-web --web-only --allow-user-claims --no-preset-claims \
    --harness-v3 --block-self-citation --max-external-calls 15 --model-id <에이전트+모델> --out results/raw/user/run.jsonl
```

## 설계 제약

- **정답 누출 차단(서버 범위)**: `AgentEnvironment`는 `gold.jsonl`, `evidence.jsonl`, `evaluation.md`를 주장 입력이나 코퍼스로 받지 않습니다. 참조 근거 전용 필드(`claim_id`, `check_status`, `locator`, `content`)가 있는 행과 주장 ID가 들어간 `evidence_id`도 거부합니다. 파일 시스템 도구는 노출하지 않습니다. API 모델에는 파일 도구가 없고, Claude 실행(`--backend claude`)은 저장소 밖 작업 폴더에서 MCP 도구만 허용해요.
- **조건 강제**: C1·C2는 코퍼스가 없으면 시작하지 않습니다. 아직 구현되지 않은 `condition`(missing/conflict/misleading)도 거부합니다.
- **실행 환경과 채점기의 분리**: `score_run.py`만 `gold.jsonl`을 읽어 채점합니다.
- **검증 게이팅**: 미션은 `finish_verification` 안에서만 실행되고, 제출된 최종 판정으로 게이트를 적용합니다. 미확인·보류 판정이면 차단하고, 이번 에피소드에서 읽은 근거를 인용해야 하며, 반박이면 정정값이 필요합니다. 규칙은 [missions/README.md](../missions/README.md)에 있습니다.
- **제출 검사(하네스 v3, `--harness-v3`)**: 지지·반박 판정은 인용 문서 문장을 그대로 옮긴 `evidence_quote`가 읽은 본문과 맞아야 접수해요. 예측 주장은 보도·전망·확률 표현이 든 인용으로 판정할 수 없어요. 거절하면 사유를 돌려주고 에피소드는 계속돼요(`claim_gate.py`). 실행형 미션은 결과물에 쓴 수치·일시가 인용한 읽은 문서나 그 값으로 한 계산기 결과에 있어야 만들어져요. 없으면 결과물만 막고 판정은 기록해요(`value_check.py`).
- **결정론적 계산**: `calculate_comparison`은 whitelisted 연산(`diff`, `pct_change`, `percentage_point_gap`, `tz_convert`, `scale_unit`, `multiply`, `ratio`)만 허용하며 임의 수식 평가(`eval`)를 쓰지 않습니다.
