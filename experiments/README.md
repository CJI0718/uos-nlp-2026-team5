# 실험 실행 안내

평가데이터 50개를 조건별로 돌리고 채점하는 방법이에요. 모든 실험은 [scripts/run_task_a.py](../scripts/run_task_a.py) 하나로 해요. 결과 해석은 [기말 보고서](../docs/research/fact_checking/final-20261125/README.md)에 있어요.

> **이 실행기는 모델과 Tavily를 호출해 비용이 들어요.** 팀이 승인한 예산 안에서만 돌려요. 실패는 재시도하지 않고 실패로 기록해요.

## 준비

```bash
uv sync --python 3.12
uv run pytest -q
cp .env.example .env          # MISTRAL_API_KEY(또는 쓸 모델의 키), TAVILY_API_KEY
```

C1·C2 조건은 근거 자료집이 필요해요. 평가데이터의 근거 URL에서 본문을 받아 만들어요(원문 저작권 때문에 Git 제외). 수집 날짜에 따라 페이지가 바뀔 수 있어요. 자세한 내용은 [data/README.md](../data/README.md)에 있어요.

```bash
uv run python scripts/build_corpus.py     # data/raw/task_a/corpus_c1.jsonl
```

웹만 쓰는 조건(C2W, C2P)은 자료집 없이 돌아요.

## 조건

| `--arms` 값 | 에이전트가 받는 것 | 재는 것 | 자료집 | Tavily |
| --- | --- | --- | :---: | :---: |
| `C0` | 주장만(제출 도구만) | 모델이 아는 지식 | | |
| `C1` | 주장 + 고정 자료집 검색·열람 | 근거가 주어졌을 때 판단력 | 필요 | |
| `C2` | C1 + 웹 검색·열기 | 자료집에 웹이 더해질 때 | 필요 | 사용 |
| `C2W` | 웹 검색·열기만, 하네스 있음 | 스스로 근거를 찾는 능력 | | 사용 |
| `C2P` | 웹 검색·열기·제출만, 하네스 없음(라벨 정의만 안내) | 하네스 효과의 비교 기준 | | 사용 |

여러 조건은 쉼표로 이어요(`--arms C0,C1,C2`).

## 명령

```bash
# 계획만 보기(호출 없음)
uv run python scripts/run_task_a.py run --exp-id exp-100-test --arms C2W --claims FC001,FC002 --dry-run

# 실행 → 채점 → 누적 사용량
uv run python scripts/run_task_a.py run   --exp-id exp-100-test --arms C2W
uv run python scripts/run_task_a.py score --exp-id exp-100-test
uv run python scripts/run_task_a.py ledger
```

- **`--exp-id`는 항상 새 이름으로 적어요.** 기본값이 `exp-005-baseline`이라, 빼면 기존 실험 기록에 이어 쓰게 돼요.
- 같은 `--exp-id`로 다시 실행하면 **이미 기록이 있는 주장은 건너뛰어요.** 중간에 멈춘 실행은 같은 명령으로 이어서 돌아요. 실패한 주장을 다시 돌리려면 그 기록을 `results/raw/<exp-id>/<조건>/`에서 다른 폴더로 옮겨 두고 실행해요(보고서에 사유를 적어요).

## 자주 쓰는 옵션

| 옵션 | 기본값 | 뜻 |
| --- | --- | --- |
| `--claims` | `all` | `FC001,FC002`처럼 일부만 |
| `--harness-v3` | 꺼짐 | 문서 안 찾기(`find_in_page`), 같은 검색·열기 재사용, 인용문 대조·예측 주장 게이트, 결과물 값 대조(수치·일시가 인용 문서나 그 값으로 한 계산에 있어야 결과물 생성). C2P에는 적용 안 됨 |
| `--block-self-citation` | 꺼짐 | 주장이 나온 글을 근거로 인용 금지(읽기는 허용). C2P에는 적용 안 됨 |
| `--no-skill` | 꺼짐 | Skill 대신 C2P와 같은 최소 안내만(도구·게이트 유지). openai 방식만 |
| `--max-external-calls` | 4 | 에피소드당 웹 검색·열기 상한. 웹만 쓰는 조건은 25를 써 왔어요 |
| `--max-tool-calls` · `--max-turns` | 12 · 20 | 에피소드당 도구 호출·대화 턴 상한. 한도 25와 함께 32 · 40 |
| `--workers` | 4 | 동시에 돌릴 주장 수 |
| `--backend` | `openai` | `claude`면 주장마다 `claude -p` 세션(Claude Code 설치 필요) |
| `--model` · `--base-url` · `--api-key-env` | DeepSeek V4.1 Flash · Mistral API · `MISTRAL_API_KEY` | 다른 OpenAI 호환 API로 바꿀 때. 키 값이 아니라 환경변수 이름을 적어요 |
| `--price-input` · `--price-output` | 0.3 · 1.2 | 100만 토큰당 USD. 다른 모델이면 그 모델 가격으로 바꿔요 |
| `--max-cost-usd` · `--tavily-cap` | 5 · 600 | **누적 상한**(아래 참고) |
| `--ledger` | `results/raw/task_a_budget_ledger.jsonl` | 비용 장부. 따로 셀 실행(예: Claude)은 다른 파일 |

### 예산 상한은 누적이에요

`--max-cost-usd`는 **장부에 기록된 모든 실행을 합친** 모델 비용 상한이에요. `--tavily-cap`은 **모든 장부를 합친** Tavily 검색 상한이에요. 이번 실행만의 한도가 아니에요.

- 실행 전에 `ledger`로 지금까지의 사용량을 보고, 그 값에 이번 실행 예산을 더해 상한을 정해요.
- 남은 Tavily가 `--max-external-calls`보다 적으면 새 주장을 시작하지 않아요.
- 장부는 Git에 올라가지 않아요. 새로 받은 저장소는 0부터 시작해요.
- 비용은 가격표로 계산한 추정이고 캐시 할인을 넣지 않아요. 실제 청구는 보통 더 적어요.

## 기말 실험에 쓴 명령

| 실험 | 명령(`uv run python scripts/run_task_a.py run` 뒤에) |
| --- | --- |
| 하네스 개선 후 C0·C1·C2 (exp-006) | `--exp-id exp-006-improved --arms C0,C1,C2 --prompt-version skill-v3-forecast-rule` |
| Claude 확인 (exp-007) | `--backend claude --model claude-sonnet-5-5 --exp-id exp-007-claude-sonnet --ledger results/raw/task_a_budget_ledger_claude.jsonl` |
| 원래 글 인용 금지, 웹만, 한도 25 (exp-011) | `--exp-id exp-011-webonly-noself-b25 --arms C2W --max-external-calls 25 --max-tool-calls 32 --max-turns 40 --block-self-citation` |
| 하네스 v3 (exp-012) | `--exp-id exp-012-harness-v3 --arms C2W --max-external-calls 25 --max-tool-calls 32 --max-turns 40 --block-self-citation --harness-v3` |
| 하네스 없음, 한도 25 (exp-013) | `--exp-id exp-013-plainweb-b25 --arms C2P --max-external-calls 25 --max-tool-calls 32 --max-turns 40` |
| Skill 없음 (exp-014) | `--exp-id exp-014-v3-no-skill --arms C2W --max-external-calls 25 --max-tool-calls 32 --max-turns 40 --block-self-citation --harness-v3 --no-skill` |

`--prompt-version`과 코드 커밋은 서버 기록(`results/raw/<exp-id>/`)의 `config`에 남아요. 누적 상한(`--max-cost-usd`, `--tavily-cap`)은 실행 당시 장부에 맞춰 정한 값이라 위 표에서 뺐어요.

## 결과가 쌓이는 곳

| 위치 | 내용 | Git |
| --- | --- | :---: |
| `results/<exp-id>/summary.md` · `summary.json` | 조건별 정확도, Macro-F1, 라벨별 재현율, 독립 출처로 맞힘, 비용 | 올림 |
| `results/<exp-id>/episodes.jsonl` | 주장별 판정, 정답 여부, 인용 수, 도구 호출 수, 비용 | 올림 |
| `results/raw/<exp-id>/<조건>/` | 서버 기록(도구 호출 궤적), 대화 기록, 웹 캐시, 미션 결과물 | 제외(원문 포함) |

채점(`score`)만 정답 파일(`data/task_a/gold.jsonl`)을 읽어요. 지표 정의는 `summary.json`의 `notes`에 있어요.

## 범위와 한계

- 근거 조건은 "근거 충분"(`sufficient`)만 구현돼 있어요. 오도 문서·누락·충돌 조건은 자료집 변형이 없어 서버가 실행을 거부해요.
- 조건마다 한 번씩 돌린 결과예요. 50개에서 1개는 2%p라, 1~2개 차이는 잡음으로 봐요.
- 개선은 같은 50개의 오답을 보고 했어요. 개발용 데이터는 따로 없어요.
- 웹 페이지는 지금 내용을 가져와요. 발행일 없는 페이지는 기준 시점 필터를 통과할 수 있어요.
- 자세한 내용은 [보고서 §11](../docs/research/fact_checking/final-20261125/README.md)에 있어요.

## 이전 실험(exp-001~004)

중간 단계 실험은 지금 실행기 이전의 스크립트로 돌렸어요(`run_comparison.py`, `run_action_safety.py`). 결과와 설정은 [results/](../results/README.md)의 각 `summary.md`에 남아 있고, 그 기록을 재현할 때만 써요. 새 실험에는 쓰지 않아요.
