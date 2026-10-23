# 리서치 자료

## 현재 집중 주제 — 팩트체크 Agent

큰 방향은 2026-10-23 팀 논의로 합의했습니다. 세부 실험은 미확정입니다.

- [구상·연구 질문](fact_checking/README.md)
- [문헌 지도: 논문 34편·학위논문 1편](fact_checking/literature.md)
- [데이터·비교·metric·비용](fact_checking/evaluation.md)
- [공식 API/RSS와 도구 설계](fact_checking/tools.md)
- [조사 기록과 확인 경계](fact_checking/research_log.json)

## 이전 폭넓은 탐색 기록

- [후보 49개와 관련 논문](candidates.md): GitHub에서 읽고 토론하기 위한 버전
- [멀티모달 입력과 기호·도구 생성 비교](multimodal_comparison.md): 악보·스프레드시트·도식, MM1–MM6, 새 논문 12편과 공정한 실험 설계
- [candidates.json](candidates.json): 후보집의 구조화된 원자료
- [HTML Research Atlas](research_catalog.html): 오프라인 전체 지도·이론·후보 검색/비교·논문·메모 내보내기
- [Agent 필요성을 검증하는 업무 X1–X7](agent_tasks_20261023.md)
- [강화학습·멀티모달 RL1–RL6](rl_multimodal_20261023.md)
- [배경 이론·지표 원자료](atlas_guide.json)
- [2026-10-23 통합 기록](update_20261023.md)

최초 조사일은 2026-10-11, 멀티모달 추가일은 2026-10-14, 적응 업무·RL 연계 추가일은 2026-10-23입니다. 기존 후보와 ID는 보존했습니다. 후보집 내부의 미선정 표시는 당시 탐색 기록이며, 현재 합의는 위 팩트체크 자료를 따릅니다. 모든 문서는 실험 결과가 아닙니다.

GitHub 파일 화면에서는 HTML이 실행되지 않습니다. Download raw file로 내려받아 여세요. 토론 메모는 브라우저 로컬 저장이고 팀원 자동 동기화가 아닙니다. 내보낸 Markdown을 PR·Issue로 공유하세요.

## 후보집 갱신

`candidates.json`이 구조화된 원자료입니다. Markdown과 HTML은 아래 로컬 명령으로 재생성합니다. 네트워크·실험용 모델 요청은 없습니다.

```text
python tools/render_candidates.py
python tools/render_catalog_html.py
python tools/validate_research.py
python tools/validate_fact_checking.py
```

후보·참고자료는 candidates.json, 배경 이론과 지표는 atlas_guide.json이 원자료입니다. HTML 템플릿과 스타일·동작은 tools/atlas/에 있고 생성 시 한 HTML에 내장합니다. 세부 리서치 Markdown도 HTML에 포함합니다. 기존 태스크·참고자료 anchor ID를 유지합니다. 생성은 네트워크나 모델 호출 없이 동작합니다.

새 논문 메모에는 다음을 기록합니다.

1. 제목·저자·연도·학회/저널 또는 preprint·원문 링크
2. 풀려는 문제와 제안 방법
3. 평가 데이터와 metric
4. 실제 확인한 주장과 한계 (초록 확인 / 전문 읽기 / 구현 검토 / 재현 구분)
5. 우리 후보 ID와의 연결, 그대로 적용하면 안 되는 부분
6. 다음 확인할 질문

논문 PDF 자체보다 원문 링크와 직접 작성한 요약을 공유합니다.
