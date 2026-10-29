# NLP 5조 · 팩트체크에서 다음 행동까지

세 사람이 함께 볼 현재 연구 안내다. **[팀공유.md](팀공유.md)부터 읽고, 관심 Task 두 개와 읽을 논문 두 편을 골라 보자.**

| 자료 | 내용 |
|---|---|
| [팀공유.md](팀공유.md) | 도입 사례, 수업·과제 연결, Task 6개, 네 가지 주장·근거 조합, 평가·역할 |
| [팀공유.html](팀공유.html) | 후보 비교, 논문 필터, 2×2 시나리오 버튼, 검색 자료실 |
| [논문 읽기 안내](팀공유_논문가이드.md) | 질문·구조·결과·적용·읽을 구간을 정리한 28편 소개 |
| [전체 111편 원문 목록](원문_다운로드_현황.md) | 저장소 PDF 90편, 나머지 21편의 공식 열람 경로 |
| [PDF 폴더](papers/) | 라이선스를 확인해 보관한 원문 90편 |
| [라이선스·출처](THIRD_PARTY_NOTICES.md) | 개별 논문의 출처·이용허락·원문 변경 없음 표시 |
| [구조화 목록](paper_library.json) | 111편 파일명·SHA-256·라이선스·원문 URL |
| [문서 작성 지침](../../../documentation-guidelines.md) | 앞으로 유지할 MD·HTML 구성 방식 |

## HTML 보는 방법

GitHub에서 HTML 파일을 연 뒤 **Download raw file**로 내려받아 브라우저에서 연다. CSS·JavaScript와 설명이 한 파일에 들어 있어 별도 설치 없이 읽을 수 있다. 논문 링크는 저장소 원문 또는 공식 사이트로 연결된다.

논문까지 한 번에 받으려면 저장소 첫 화면의 **Code → Download ZIP**을 이용하거나 `git clone`한다. 90편 PDF는 문서와 함께 내려받아진다.

## 추가 공개 원문 내려받기

Python 3의 표준 라이브러리만 사용한다. 저장소 루트에서:

```powershell
# 계획만 확인
python docs/research/fact_checking/team_guide/tools/download_papers.py

# 필요한 한 편만 원출처에서 받기
python docs/research/fact_checking/team_guide/tools/download_papers.py --ids E22 --execute

# 나머지 공개 다운로드 경로를 순서대로 받기
python docs/research/fact_checking/team_guide/tools/download_papers.py --execute
```

기존 사본은 SHA-256을 확인해 재사용한다. 다운로드는 `papers_downloads/`에 저장되고 오류·PDF 형식 불일치·기록된 판본과의 차이를 만나면 중단한다. 원출처 링크만 있는 자료는 출판사 화면에서 연다. 재게시 조건과 기관 접근이 필요한 항목은 [전체 목록](원문_다운로드_현황.md)의 마지막 표에서 확인한다.

## 문서를 수정할 때

1. `팀공유.md` 본문을 수정한다. 자동 생성 구간 `PAPER_GUIDE_BEGIN/END`와 `PAPER_LIBRARY_BEGIN/END`는 아래 원자료를 수정한다.
2. 논문 소개는 `tools/team_paper_cards.json`, 전체 서지는 `paper_library.json`을 편집한다.
3. 아래 명령으로 HTML·논문 가이드·연구 지도를 생성한다.

```powershell
python -m pip install -r docs/research/fact_checking/team_guide/tools/requirements.txt
python docs/research/fact_checking/team_guide/tools/build_team_guide.py
python tools/validate_team_guide.py
```

## 함께 보존한 조사 기록

- [추가 56편 용도별 카탈로그](문헌_용도별_카탈로그.md)
- [기존 문헌과의 연결표](기존_DOCX_연결표.md)
- [Liner 문헌표 회수 기록](Liner_문헌표_회수기록.md)
- [Liner 종합 조사 기록](Liner_종합문서_회수기록_20261029.md)
- [원문 파일명 정리 기록](파일명_변경기록.md)
- [헌수님의 구체화 원문](../README.md)

확인 범위와 실험 유의사항은 [팀 공유 안내 9장](팀공유.md)에 모았다.
