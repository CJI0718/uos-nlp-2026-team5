# 실험 설정과 재현

이 브랜치(`feat/agent-skill-mcp`)에서는 외부 AI 에이전트(Claude Code 등)에 MCP 서버([scripts/mcp_stdio.py](../scripts/mcp_stdio.py))와
[skills/factcheck-mission-agent/SKILL.md](../skills/factcheck-mission-agent/SKILL.md)를 연결해 실험합니다.
실험마다 `exp-001`처럼 고유 ID를 붙입니다. 실제 모델 실행은 팀이 승인한 호출 예산 안에서만 합니다.

## 실행 순서

```bash
uv sync --python 3.12
uv run pytest -q

# 0) 에이전트용 코퍼스 수집 (C1·C2 필수, 원문 사이트에 접속, 결과는 data/README.md)
uv run python scripts/build_corpus.py

# 1) 격리 작업공간 생성 — 저장소 밖, gold 없음, 내장 파일·셸·웹 도구 차단
uv run python scripts/make_agent_workspace.py \
    --workspace ~/agent-runs/exp-001-c1 --run-id exp-001-c1 --arm C1 \
    --model-id claude-code-<버전>+<모델ID>

# 2) 작업공간의 RUN.md에 적힌 명령으로 주장마다 새 세션을 실행
#    로그는 results/exp-001-c1/run.jsonl에 쌓입니다

# 3) 채점 — gold.jsonl을 읽는 유일한 명령
uv run python scripts/score_run.py --run results/exp-001-c1/run.jsonl
uv run python scripts/score_run.py --run results/exp-001-c1/run.jsonl --c2 results/exp-001-c2/run.jsonl
```

저장소 루트의 `.mcp.json`은 개발 중에 도구를 눌러 보는 용도입니다(`run_id=dev-interactive`, 로그는 Git 제외 위치).
저장소 안에서 실행한 에이전트는 gold 파일을 직접 읽을 수 있으므로, 이 설정으로 만든 로그는 실험 결과로 쓰지 않습니다.

## 비교 축

- `--arm`: 도달 가능한 정보 범위. `C0`는 코퍼스·웹 없음, `C1`은 코퍼스만, `C2`는 코퍼스와 외부 웹(`--live-web`).
- Skill 유무: `make_agent_workspace.py --no-skill`은 도구만 연결합니다(`prompt_version=tools-only-v2`).
- 에이전트·모델: `--model-id`로 기록합니다. 비교할 때는 이 값만 바꾸고 나머지는 고정합니다.
- `--condition`: 지금은 `sufficient`만 구현되어 있습니다. 아래 "범위와 남은 한계"를 봅니다.

## 조건 비교 실험

`scripts/run_action_safety.py`는 합성 사례 6건으로 Skill·출처 정보 표시·서버 게이트(`--gate off|verdict|provenance`)를 바꿔 가며 잘못된 일정 등록을 셉니다([exp-002](../results/exp-002-action-safety/summary.md)).
`scripts/run_comparison.py`는 같은 주장을 세 조건(도구 없음, 그냥 Claude Code+웹, 하네스)과 여러 모델로 실행하고 채점합니다. 모델을 호출하므로 승인된 예산 안에서만 실행합니다.

```bash
uv run python scripts/run_comparison.py run --dry-run      # 세션 수와 명령 확인
uv run python scripts/run_comparison.py run --workers 6    # 실행 (실패는 재시도하지 않음)
uv run python scripts/run_comparison.py score              # results/<exp-id>/summary.json, episodes.jsonl
```

## 실험 기록

`finish_verification`이 호출될 때마다 결과 로그의 `config`에 `run_id`, `arm`, `condition`, `model_id`, `prompt_version`,
`code_commit`(작업 트리가 바뀌었으면 `+dirty`)이 기록됩니다. `result`에는 판정, 인용 근거, 도구 호출 궤적(`events`),
왜곡 정보, 미션 결과(`mission_output`, 서버가 생성)가 기록됩니다.

채점 결과에는 다음 항목이 함께 나옵니다.
- `reference_baselines`: 한 라벨만 답했을 때의 점수. 지금 gold로는 항상 `supported`라고 답해도 정확도가 37/49 = 75.5%이고
  Macro-F1은 0.287입니다. 정확도는 이 값과 함께 읽어야 합니다.
- `mission_safety`: 미션 요청 수, 게이트 차단 수, gold와 다른 판정으로 실행된 실행형 미션의 비율.

## 범위와 남은 한계

이 장에 모아 둡니다. 2026-11-19 검토에서 확인한 내용입니다.
팀이 정할 항목과 선택지는 [결정 기록 003](../docs/decisions/003-task-a-agent-harness-open-decisions.md)에 정리했습니다.

**아직 없는 것**
- 코퍼스에는 참조 근거의 원문 54개만 있고 방해 문서가 없습니다. 어떤 문서를 몇 개 넣을지는 팀이 정해야 합니다. FC021·FC036·FC038·FC045는 원문을 받지 못해 C1에서 근거가 없습니다.
- 코퍼스는 수집한 날의 페이지입니다. 같은 결과를 재현하려면 팀이 한 번 만든 파일을 Git 밖에서 공유해야 합니다(`content_hash`로 같은 파일인지 확인).
- 페이지 본문 추출은 단순 태그 제거라서 일부 문서 앞부분에 메뉴·검색창 문구가 남습니다.
- `missing`·`conflict`·`misleading` 조건은 코퍼스 변형이 없어서 구현되지 않았습니다. 서버가 실행을 거부합니다. 성능 하락·오도 근거 노출·채택 지표는 아직 만들 수 없습니다.
- [exp-002-action-safety](../results/exp-002-action-safety/summary.md)에서는 Skill만으로 합성 사례의 잘못된 등록이 0/12가 되어, Skill 위에 얹은 게이트의 추가 효과는 보이지 않았습니다. Skill 없이 게이트만 두면 잘못된 실행은 막지만 정상 등록도 2/6으로 줄었습니다.
- 실제 모델 실행은 [exp-001-compare](../results/exp-001-compare/summary.md) 하나입니다(주장 20건, sufficient 조건, C1만). 하네스는 웹을 쓰는 Claude Code보다 정확도가 낫지 않았고, 틀린 답은 주로 코퍼스 공백과 `read_evidence`의 4,000자 제한 때문이었습니다.

**평가 설계의 한계**
- 자동 채점은 판정 라벨(정확도, Macro-F1, 커버리지)과 미션 안전성까지입니다. gold에 `distortion_type` 필드가 없어서 왜곡 유형·구간·정정문은 채점하지 않습니다. 근거 충분성(E)과 시점·범위(T)는 사람 채점이 필요합니다.
- 표본이 작습니다. 채점 대상 49건에서 1건은 2%p이고, 반박 11건에서 1건은 재현율 9%p입니다. 근거 부족 정답은 1건뿐이라 Macro-F1이 그 1건에 크게 흔들립니다.
- gold는 독립 검수 전 초안이고, FC038은 판정 보류입니다.
- Skill은 같은 50건을 보며 다듬어졌습니다. FC002의 정답 예시와 평가 사례에 나오는 기관명은 지웠지만, 개발용과 평가용 사례가 나뉘어 있지 않아서 Skill 효과는 낙관적으로 추정될 수 있습니다. 나누는 방법은 팀이 정해야 합니다.
- 2010~2025년의 유명한 사실은 모델이 이미 알고 있을 수 있습니다. 도구 효과는 C0와 비교해서 따로 확인해야 합니다.

**격리의 한계**
- 격리 작업공간은 Claude Code의 내장 파일·셸·웹 도구를 끄고(`permissions.deny`, `--disallowedTools`), `--strict-mcp-config`로 다른 MCP 서버를 막습니다. 사용자 전역 Skill·플러그인은 끄지 않으므로 실행 환경 기록에 남깁니다.
- CLI 모드(`scripts/agent_cli.py`)는 셸로 구동하므로 에이전트가 저장소를 읽거나 상태 파일을 고칠 수 있습니다. 격리 경계로 쓰지 않습니다.
- C2 웹 검색은 `evidence_cutoff`를 강제하지 않습니다. Skill이 지키도록 지시할 뿐입니다.
- Codex·Cursor용 설정은 생성하지 않습니다. 같은 격리를 각 도구의 설정 형식으로 따로 맞춰야 합니다.
