# 평가 데이터

최종 태스크가 정해진 뒤 직접 작성할 평가 사례를 관리합니다.

## task_a/ — Task A 평가 사례 50개

`docs/research/fact_checking/evaluation.md` §9.8에서 `scripts/extract_fc_data.py`로 추출합니다.
원본 Markdown이 기준이며 스크립트는 원본을 읽기만 하고 수정하지 않습니다.

```bash
uv run python scripts/extract_fc_data.py
```

| 파일 | 받는 사람 | 내용 |
| --- | --- | --- |
| `task_a/claims.jsonl` | **해결 에이전트** | 주장 50개, 시점, 출처, 입력 본문 |
| `task_a/gold.jsonl` | **채점기 전용** | 참조 판정·이유·평가 포인트·주장 위치 |
| `task_a/evidence.jsonl` | **채점기 전용** | 참조 근거 64건과 확인 상태 |

구성(§9.2.2·§9.2.1과 일치): 지지 37·반박 11·근거 부족 1·판정 보류 1, 한국어 기사 29·영어 기사 8·Threads 9·X 4.
분할 그룹은 47개이며 `family_id`로 관리합니다(FC032·FC034, FC015·FC019·FC020).

`주장 위치`는 gold에만 있습니다. FC044의 값은 "기사 제목의 10월 24일; 본문의 10월 14일과 비교"로
그 자체가 정답을 밝히기 때문입니다. 에이전트 입력 필드 집합은 테스트로 고정했습니다.

**아직 없는 것:** 기사 37건의 원문 본문(21건은 발췌도 없음). URL만 있고 본문 수집은 별도 단계이며,
수집한 원문은 저작권 때문에 `data/raw/`(Git 제외)에 두고 manifest만 커밋합니다.
참조 판정은 독립 검수 전 초안이고 FC038은 판정 보류 상태입니다.

## 에이전트용 코퍼스 (C1·C2)

C1·C2는 에이전트가 `search_evidence`·`read_evidence`로 검색하는 고정 코퍼스가 있어야 실행됩니다.
코퍼스가 없으면 서버가 시작을 거부합니다. 예전에는 빈 코퍼스로 조용히 실행되어 C1이 사실상 C0였습니다.
코퍼스는 원문 저작권 때문에 Git에 올리지 않으므로, 각자 아래 명령으로 만듭니다.

```bash
uv run python scripts/build_corpus.py                           # 참조 근거의 원문 URL 63개
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

2026-11-19 수집 결과입니다. 사이트가 바뀌면 달라집니다.
- URL 63개 중 54개를 받았고, 50개 주장 중 46개에 원문 문서가 하나 이상 있습니다.
- 실패 9개: 본문이 너무 짧은 동적 페이지 4개(FC004 PDF 1개, FC021, FC038 2개), 인증서 만료 2개(FC036), HTTP 403 2개(FC039, FC045), `evidence_cutoff` 이후 발행 1개(FC032의 Hugging Face 파일 목록).
- 원문 문서가 없는 주장: FC021, FC036, FC038, FC045. C1에서는 이 주장의 근거를 찾을 수 없습니다.
- FC039의 YouTube 페이지는 제목과 하단 문구만 추출됩니다. 영상 내용은 들어 있지 않습니다.
- 주장 문장을 질의로 BM25 검색을 하면 맞는 문서가 1위인 경우는 46건 중 15건(Kiwi)·17건(bigram), 5위 안은 21건·25건입니다.
  참조 근거 요약으로 검색하면 49/50이 1위였으므로, 원문 코퍼스가 훨씬 어렵습니다. 방해 문서는 아직 넣지 않았습니다.

- 위치: `data/raw/task_a/corpus_c1.jsonl`. 기사 원문이 들어가므로 Git에서 제외되는 `data/raw/` 아래에 둡니다.
- 한 줄에 문서 하나를 둡니다. 필수 필드는 `evidence_id`, `title`, `text`(문서 본문)이고, 선택 필드는
  `source_url`, `publisher`, `source_type`, `published_at`, `provenance_group`(같은 보도자료 전재 묶음),
  `document_validity`입니다.
- `evidence.jsonl`은 코퍼스로 쓸 수 없습니다. 이 파일은 채점 전용이고, 내용이 판정 문구가 섞인 요약입니다.
  64건 중 10건에 "맞지 않는다", "실제 실적 확인이 아니다" 같은 문구가 있습니다.
  서버는 이 파일 경로와 `claim_id`·`check_status`·`locator`·`content` 필드를 거부합니다.
- `evidence_id`에 주장 ID(`FC002` 등)를 넣지 않습니다. 넣으면 어느 문서가 어느 주장의 근거인지 드러나서 서버가 거부합니다.
  채점에 쓰는 `sufficient_evidence_ids`와의 대응표는 채점기 쪽에 따로 둡니다.
- 정답 근거 문서만 넣으면 검색이 너무 쉽습니다. 참조 근거 요약 64건만으로 BM25를 돌리면 50건 중 49건이 1위로 맞습니다.
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
