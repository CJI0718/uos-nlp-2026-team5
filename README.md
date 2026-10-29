# UOS NLP 5조 · AI Agents 연구 프로젝트

2026년 서울시립대학교 NLP 수업의 5조 공동 연구 공간입니다.

**현재 단계: 기사·뉴스·주장을 검증하는 팩트체크 Agent로 큰 방향 합의.**
대상 분야·세부 태스크·모델·데이터·예산·비교 조건은 아직 결정하지 않았습니다. 기존 후보집은 탐색 기록으로 보존하며, 실험을 수행한 결과가 아닙니다.

## 지금 함께 볼 자료

- **[세 사람을 위한 최신 팀 공유 안내](docs/research/fact_checking/team_guide/README.md)**: Task 6개·평가 50개 설계·진짜/가짜 주장과 근거의 4조합
- **[팀공유 HTML](docs/research/fact_checking/team_guide/팀공유.html)** · [GitHub에서 바로 읽기](docs/research/fact_checking/team_guide/팀공유.md): 논문 28편 소개·태스크 비교·전체 자료실
- **[전체 111편 원문 목록](docs/research/fact_checking/team_guide/원문_다운로드_현황.md)**: PDF 90편 포함, 21편은 공식 원문 경로 제공
- [문서 작성 지침](docs/documentation-guidelines.md): 처음 읽는 팀원에게 구체적인 Task·논문·평가를 연결하는 방식
- [팩트체크 Agent 구상](docs/research/fact_checking/README.md): 합의한 큰 틀과 3개 track·6개 연구 질문 후보
- [문헌 지도](docs/research/fact_checking/literature.md): 논문 34편·학위논문 1편, 확인 범위와 우리 실험 연결
- [평가 설계](docs/research/fact_checking/evaluation.md): 50개 구성안·강한 기준선·판정/근거/비용·누출 통제
- [RSS/API·도구 후보](docs/research/fact_checking/tools.md): 공식 자료 확인, 도구 역할·이용조건·실패 처리
- [큰 방향 합의 기록](docs/decisions/001-fact-checking-direction.md): 확정한 것과 아직 정하지 않은 것

2026-10-23 조사: Exa 17회 검색·113개 결과 항목(중복 포함)을 탐색하고 원자료 49개 URL을 직접 조회했습니다. 전체 논문 전문 정독·코드 감사·재현을 완료했다는 뜻은 아닙니다. 기존 후보집과 새 문헌집의 중복 논문은 두 번 합산하지 않습니다.

## 처음 오셨다면

1. [협업 안내](CONTRIBUTING.md)를 읽습니다. Git 명령어를 몰라도 웹에서 시작할 수 있습니다.
2. [최신 팀 공유 안내](docs/research/fact_checking/team_guide/팀공유.md)를 먼저 읽습니다. [현재 팩트체크 구상](docs/research/fact_checking/README.md)은 팀원 제안 원문이며, [49개 후보](docs/research/candidates.md)와 [HTML Research Atlas](docs/research/research_catalog.html)는 이전 탐색과 관련 개념을 확인하는 기록입니다.
3. 새 작업은 Issue로 목적과 완료 기준을 정한 뒤, 작업용 branch에서 진행합니다.
4. 변경은 PR로 제안하고 다른 팀원이 확인한 뒤 main에 합칩니다.

## 어디에 무엇을 기록하나요?

| 공간 | 기록할 내용 |
| --- | --- |
| Issues | 질문, 아이디어 토론, 할 일, 담당자, 완료 기준 |
| Pull requests (PR) | 문서·코드·평가 데이터 변경 제안과 검토 |
| [docs/research/](docs/research/) | 논문 조사, 후보 비교, 출처와 한계 |
| [docs/meetings/](docs/meetings/) | 회의 메모와 다음 행동 |
| [docs/decisions/](docs/decisions/) | 확정한 결정과 선택·기각 이유 |
| [data/](data/) | 공개 가능한 직접 작성 평가 사례, schema와 정답 작성 기준 |
| [src/](src/) | 실행 코드 |
| [experiments/](experiments/) | 실험 설정·실행 명령·예산·재현 방법 |
| [results/](results/) | 민감정보를 제거한 결과 요약과 지표 |
| [reports/](reports/) | 중간·최종 보고서와 발표 자료 |

## 현재 조사 범위

RAG, ReAct, 메모리, LLM/Agent alignment, Harness, 멀티모달 입력·기호/도구 생성의 기존 36개에 **적응적 업무 X1–X7**과 **강화학습·멀티모달 RL1–RL6**을 더해 **8개 주제군·49개 후보**를 정리했습니다.

2026-10-23 탐색 기록: [Agent의 필요성을 검증하는 업무 7가지](docs/research/agent_tasks_20261023.md), [강화학습·멀티모달 연계 6가지](docs/research/rl_multimodal_20261023.md). 이 후보집의 참고자료는 논문 58편·아이디어 1건·공식 문서 1건입니다. 이후 큰 방향은 팩트체크 Agent로 합의했으며, 개별 후보의 내용은 당시 제안으로 보존합니다.

### 팀 논의용 HTML 사용법

1. [Research Atlas 파일](docs/research/research_catalog.html)을 열고 **Download raw file**로 내려받아 브라우저에서 엽니다. GitHub 파일 화면은 HTML을 실행하지 않습니다.
2. 배경 이론과 후보·논문을 검색하고, 관심 후보를 최대 4개 **비교에 담기**로 나란히 봅니다.
3. 후보별 의견을 적고 **Markdown 내보내기**로 받은 파일을 PR·Issue에 공유합니다.

HTML 한 파일에 CSS·JavaScript·데이터·상세 리서치가 들어 있어 오프라인으로 읽을 수 있습니다. 논문 원문 링크는 인터넷이 필요합니다. 메모는 현재 브라우저에만 저장되며 팀원과 자동 동기화되지 않습니다. GitHub Pages·외부 호스팅은 설정하지 않았습니다.

2026-10-14 추가: 악보·스프레드시트·도식에서 **직접 시각 처리와 구조화된 기호·도구 경로를 어떻게 공정하게 비교할지** 조사했습니다. [새 비교 설계와 논문 12편 메모](docs/research/multimodal_comparison.md)를 먼저 읽고 MM1–MM6 후보를 살펴볼 수 있습니다. 주제·모델·예산을 확정하거나 실험을 실행한 것은 아닙니다.

- [GitHub에서 바로 읽는 후보집](docs/research/candidates.md)
- [구조화된 후보 원자료](docs/research/candidates.json)
- [HTML Research Atlas](docs/research/research_catalog.html) — 전체 지도·배경 이론·49개 후보·60개 자료·비교·논의 노트
- [추가 조사·통합 변경 기록](docs/research/update_20261023.md)
- 최초 조사: 2026-10-11. 멀티모달 추가: 2026-10-14. 적응 업무·RL 연계 추가: 2026-10-23. 기존 자료 전체를 재검증한 것은 아니며, 논문 사실·제안·실험 결과를 구분합니다.

## 연구 진행 순서

구상과 논문 조사 → 태스크·지표 결정 → 평가 데이터 작성 → 작은 파일럿 → 비교 실험 → 오류 분석·개선 → 보고서

이 순서는 운영 안내이며 연구 주제를 미리 고정하지 않습니다. 각 단계의 합의는 docs/decisions에 남깁니다.

## 공개 저장소 원칙

- 이 저장소의 파일뿐 아니라 Issues·PR 내용도 공개된다고 생각하고 작성합니다.
- API 키, .env, 비밀번호, 쿠키, 학생 개인정보, 개인 채팅/메일, 공유 권한 없는 강의자료·논문 PDF는 올리지 않습니다.
- 큰 원본 데이터·모델 가중치·캐시·원본 trajectory는 올리지 않고, 출처·버전·다운로드 방법이나 안전한 보관 위치만 기록합니다.
- .gitignore는 실수 방지 장치일 뿐입니다. PR에서 실제 변경 내용을 확인합니다.
- 실험용 API 호출은 예산과 실행 범위를 합의한 후에만 합니다. 자동 재시도·모델 변경을 기본으로 켜지 않습니다.
- GitHub는 공동 기록과 버전 관리 공간입니다. GPU 작업이나 LLM 실험은 각자 PC/서버에서 실행하고 검증 가능한 설정·결과를 공유합니다.
- 공개 여부와 이용 허락(라이선스)은 다릅니다. 프로젝트 라이선스는 팀 합의 전까지 임의로 지정하지 않습니다.

## 함께 작업하기

공개 링크로 읽기는 가능합니다. 직접 push하거나 PR branch를 함께 수정하려면 저장소 소유자가 팀원 계정을 Collaborator로 초대합니다.
계정·비밀번호를 공유하지 않습니다.

웹에서 문서를 수정하는 방법부터 시작해도 됩니다. [협업 안내 보기](CONTRIBUTING.md).
