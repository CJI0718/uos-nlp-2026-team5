# 리서치 자료

- [후보 36개와 관련 논문](candidates.md): GitHub에서 읽고 토론하기 위한 버전
- [멀티모달 입력과 기호·도구 생성 비교](multimodal_comparison.md): 악보·스프레드시트·도식, MM1–MM6, 새 논문 12편과 공정한 실험 설계
- [candidates.json](candidates.json): 후보집의 구조화된 원자료
- [HTML 후보집](research_catalog.html): 내려받아 브라우저에서 읽는 상세본

최초 조사일은 2026-10-11, 멀티모달 추가 조사일은 2026-10-14입니다. 기존 30개 후보는 보존했고 MM1–MM6을 추가했습니다. 주제는 아직 선정하지 않았으며 이 자료는 실험 결과가 아닙니다.

## 후보집 갱신

`candidates.json`이 구조화된 원자료입니다. Markdown과 HTML은 아래 로컬 명령으로 재생성합니다. 네트워크·실험용 모델 요청은 없습니다.

```text
python tools/render_candidates.py
python tools/render_catalog_html.py
python tools/validate_research.py
```

원자료의 태스크·참고자료 ID는 기존 토론 링크를 위해 유지합니다. 비교 설계의 긴 설명은 별도 문서에 두고 README와 후보집에서 연결합니다.

새 논문 메모에는 다음을 기록합니다.

1. 제목·저자·연도·학회/저널 또는 preprint·원문 링크
2. 풀려는 문제와 제안 방법
3. 평가 데이터와 metric
4. 실제 확인한 주장과 한계 (초록 확인 / 전문 읽기 / 구현 검토 / 재현 구분)
5. 우리 후보 ID와의 연결, 그대로 적용하면 안 되는 부분
6. 다음 확인할 질문

논문 PDF 자체보다 원문 링크와 직접 작성한 요약을 공유합니다.
