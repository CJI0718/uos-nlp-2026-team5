# 평가 데이터

최종 태스크가 정해진 뒤 직접 작성할 평가 사례를 관리합니다.

## task_a/ — Task A 평가 사례 50개

원본은 [`task_a/evaluation_cases.md`](task_a/evaluation_cases.md)(팀이 직접 작성한 사례 50개)이고, `scripts/extract_fc_data.py`로 추출합니다. 데이터의 목적과 구성 설명은 `docs/research/fact_checking/evaluation.md` §9.1~9.6에 있습니다.
원본 Markdown이 기준이며 스크립트는 원본을 읽기만 하고 수정하지 않습니다.

```bash
uv run python scripts/extract_fc_data.py
```

| 파일 | 받는 사람 | 내용 |
| --- | --- | --- |
| `task_a/claims.jsonl` | **해결 에이전트** | 주장 50개, 시점, 출처, 입력 본문 |
| `task_a/gold.jsonl` | **채점기 전용** | 참조 판정·이유·평가 포인트·주장 위치 |
| `task_a/evidence.jsonl` | **채점기 전용** | 참조 근거 84건과 확인 상태 |

구성(2026-11-25 개정, 사례 파일 §0과 일치): 지지 30·반박 14·근거 부족 6, 한국어 기사 24·영어 기사 8·Threads 5·X 3·Bluesky 2·재가공 게시물 8.
분할 그룹은 48개이며 `family_id`로 관리합니다(FC032·FC034, FC015·FC020).

재가공 게시물 8개(변형 주장)는 실제 보도의 값 하나를 바꾼 연구자 작성 입력입니다. `source_url`이 비어 있고, 정답 값을 담은 원 보도는 `evidence.jsonl`에만 `원 보도 · …` 제목으로 들어갑니다.
근거 부족 예측 사례 6개는 `evidence_cutoff`가 게시 시각입니다. 사례마다의 `검수` 줄은 gold의 `review_status`·`review_note`로만 갑니다.

`주장 위치`는 gold에만 있습니다. FC044의 값은 "기사 제목의 10월 24일; 본문의 10월 14일과 비교"로
그 자체가 정답을 밝히기 때문입니다. 에이전트 입력 필드 집합은 테스트로 고정했습니다.

**아직 없는 것:** 기사 32건의 원문 본문(모든 사례에 짧은 발췌나 전사는 있음). URL만 있고 본문 수집은 별도 단계이며,
수집한 원문은 저작권 때문에 `data/raw/`(Git 제외)에 두고 manifest만 커밋합니다.
2026-11-25 50건 전체를 1인 검수했습니다(교체한 FC041 포함). 검수 기록은 [`task_a/review/`](task_a/review/)에 있습니다.

## 에이전트용 코퍼스 (C1·C2)

C1·C2는 에이전트가 `search_evidence`·`read_evidence`로 검색하는 고정 코퍼스가 있어야 실행됩니다.
코퍼스가 없으면 서버가 시작을 거부합니다. 예전에는 빈 코퍼스로 조용히 실행되어 C1이 사실상 C0였습니다.
코퍼스는 원문 저작권 때문에 Git에 올리지 않으므로, 각자 아래 명령으로 만듭니다.

```bash
uv run python scripts/build_corpus.py                           # 참조 근거의 원문 URL
uv run python scripts/build_corpus.py --extra-urls distractors.txt  # 방해 문서 URL 추가
```

`evidence.jsonl`의 `source_url`마다 원문 페이지를 한 번씩 받아 본문을 추출합니다. 모델은 호출하지 않지만 원문 사이트에 실제로 접속합니다.
결과는 `data/raw/task_a/` 아래 세 파일입니다.

| 파일 | 내용 | 누가 읽나 |
| :--- | :--- | :--- |
| `corpus_c1.jsonl` | 문서 ID, 페이지 제목, 본문, URL, 발행일(페이지 메타데이터) | 에이전트(서버 경유) |
| `corpus_c1.gold_map.jsonl` | 문서 ID와 참조 근거 ID·주장 ID의 대응 | 채점기만. 이름에 `gold`가 있어 서버가 코퍼스로 받지 않음 |
| `corpus_c1.report.json` | URL별 수집 결과와 실패 사유 | 사람 |

받지 못했거나 본문이 300자 미만인 페이지는 채우지 않고 실패로 기록합니다. 문서 ID는 URL의 해시(`DOC_` + 12자리)라서 어느 주장의 근거인지 드러나지 않습니다.

본문과 발행일은 [src/task_a/article.py](../src/task_a/article.py)로 뽑습니다. C2의 `fetch_url`도 같은 코드를 씁니다.
- 본문: [Trafilatura](https://github.com/adbar/trafilatura)(Apache-2.0)로 메뉴·하단 문구·관련 기사 목록을 빼고 기사 본문만 남깁니다. 결과가 200자 미만이면 태그만 지우는 방식으로 대신합니다.
- 발행일: 페이지의 발행 시각 메타데이터를 먼저 쓰고, 없으면 [htmldate](https://github.com/adbar/htmldate)로 찾습니다. htmldate는 문서 페이지에서 보통 "최종 수정일"을 찾습니다.
  그 날짜가 `evidence_cutoff` 이후면, 받은 페이지가 cutoff 이후에 수정된 판이므로 제외합니다.

2026-11-25 개정 데이터로 다시 수집한 결과입니다. 사이트가 바뀌면 달라집니다.
- 근거 URL 85개 중 78개를 받았고, **50개 주장 모두 원문 문서가 하나 이상** 있습니다.
- 받지 못한 7개와 이유입니다. 같은 주장의 다른 근거는 모두 받았습니다.

  | 주장 | 받지 못한 근거 | 이유 |
  | :--- | :--- | :--- |
  | FC029 | IEA Energy and AI 요약 | HTTP 403 (접속 환경에 따라 다름) |
  | FC031 | NVD CVE 페이지 | 스크립트로 그리는 페이지라 본문 0자 |
  | FC032 | Hugging Face 파일 목록 | 수정 시각이 기준 시점 이후(2026-11-24) |
  | FC033 | 법원 판결문 PDF | 스캔본이라 텍스트가 거의 없음(117자) |
  | FC037 | AppFunctions 문서 현재 판 | 수정 시각이 기준 시점 이후(2026-11-16). 기준 시점 이전 보관본(Wayback)을 근거로 추가해 대신 받음 |
  | FC041 | PlayStation 공식 YouTube 영상 | 영상 페이지라 본문이 거의 없음(274자) |
  | FC041 | Digital Trends 2026-08 기사 | 기준 시점(2025-10-11) 이후. 원래 배경 자료로만 둔 것 |

- FC011의 연천군 공지는 첫 수집에서 HTTP 404였고, 몇 분 뒤 두 번째 수집에서 받아졌습니다.
- 개정 전 데이터의 수집 파일(2026-11-20)은 `data/raw/task_a/corpus_c1_2026-11-20_pre-revision.*`로 이름을 바꿔 남겼습니다. 이 파일을 쓴 C1 실험 기록은 없습니다(exp-002는 합성 코퍼스, exp-003·004는 실제 웹). exp-001은 그보다 앞선 `corpus_c1_2026-11-19_strip.*`로 실행했습니다.

- 위치: `data/raw/task_a/corpus_c1.jsonl`. 기사 원문이 들어가므로 Git에서 제외되는 `data/raw/` 아래에 둡니다.
- 한 줄에 문서 하나를 둡니다. 필수 필드는 `evidence_id`, `title`, `text`(문서 본문)이고, 선택 필드는
  `source_url`, `publisher`, `source_type`, `published_at`, `provenance_group`(같은 보도자료 전재 묶음),
  `document_validity`입니다.
- `evidence.jsonl`은 코퍼스로 쓸 수 없습니다. 이 파일은 채점 전용이고, 내용이 판정 문구가 섞인 요약입니다.
  판정 문구("맞지 않는다", "실제 실적 확인이 아니다" 등)가 섞인 항목이 있습니다.
  서버는 이 파일 경로와 `claim_id`·`check_status`·`locator`·`content` 필드를 거부합니다.
- `evidence_id`에 주장 ID(`FC002` 등)를 넣지 않습니다. 넣으면 어느 문서가 어느 주장의 근거인지 드러나서 서버가 거부합니다.
  채점에 쓰는 `sufficient_evidence_ids`와의 대응표는 채점기 쪽에 따로 둡니다.
- 정답 근거 문서만 넣으면 검색이 너무 쉽습니다. 개정 전 데이터에서 참조 근거 요약 64건만으로 BM25를 돌리면 50건 중 49건이 1위로 맞았습니다.
  같은 주제의 방해 문서와 전재 기사도 함께 넣습니다.
- `published_at`이 각 주장의 `evidence_cutoff` 이후인 문서는 넣지 않습니다. 수집 스크립트가 메타데이터의 발행일로 걸러냅니다.

## 사례 작성 원칙

사례별 권장 필드:
- case_id, category, user_request
- initial_state / available_evidence
- gold_answer_or_state / required_constraints
- evaluation_rule / tolerance
- source / authoring_note / review_status

정답은 평가기에만 제공하고 해결 Agent의 입력에서 제외합니다.
개발용 사례와 고정 평가본을 구분합니다. 같은 기본 사례에서 만든 변형을 독립 사례로 중복 계산하지 않습니다.
공개 전 개인정보·저작권·공유 권한을 확인합니다. 원본 대용량 자료는 raw/ 등에 두고 Git에 올리지 않습니다.
