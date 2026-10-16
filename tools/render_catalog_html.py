"""Build a standalone, offline-readable research catalogue. No network/API calls."""
import json
from pathlib import Path
from html import escape as esc

ROOT = Path(__file__).resolve().parents[1] / "docs" / "research"
DATA = json.loads((ROOT / "candidates.json").read_text(encoding="utf-8"))
OUT = ROOT / "research_catalog.html"
TASK_COUNT = len(DATA["tasks"])
PAPER_COUNT = sum(r["id"].startswith("P") for r in DATA["references"])
IDEA_COUNT = len(DATA["references"]) - PAPER_COUNT
REFS = {r["id"]: r for r in DATA["references"]}
DIFF = {"D1": "D1 · 비교적 낮음", "D2": "D2 · 중간", "D3": "D3 · 높음"}
THEME_IDS = {"RAG": "rag", "ReAct": "react", "메모리": "memory", "Alignment": "alignment", "Harness": "harness", "멀티모달": "multimodal"}

def e(value):
    return esc(str(value), quote=True)

def ul(items):
    return "<ul>" + "".join("<li>" + e(x) + "</li>" for x in items) + "</ul>"

def citations(ids):
    return " · ".join('<a href="#ref-' + e(i) + '">' + e(i) + "</a>" for i in ids)

def table(heads, rows):
    return '<div class="table-wrap"><table><thead><tr>' + "".join("<th>" + e(h) + "</th>" for h in heads) + "</tr></thead><tbody>" + "".join("<tr>" + "".join("<td>" + str(v) + "</td>" for v in row) + "</tr>" for row in rows) + "</tbody></table></div>"

STYLE = """
:root{--ink:#172638;--muted:#56687c;--line:#dce4ec;--navy:#173b61;--teal:#066f77;--paper:#fff;--wash:#f3f6fa;--gold:#a75d0b}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--wash);color:var(--ink);font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;line-height:1.78;font-size:16px}
main{max-width:1120px;margin:0 auto;padding:30px 26px 72px}header{background:linear-gradient(125deg,#123351,#176c73);color:#fff;padding:40px;border-radius:18px;margin-bottom:22px}
h1{font-size:32px;line-height:1.4;margin:6px 0 16px}h2{font-size:26px;color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:12px;margin-top:48px}h3{font-size:20px;color:var(--navy);margin-top:26px}h4{margin-bottom:6px}
p{margin:12px 0}a{color:#006886;text-underline-offset:3px;overflow-wrap:anywhere}header a{color:#fff}
.kicker{letter-spacing:.12em;font-size:13px;font-weight:700}.subtitle{max-width:850px;color:#e5f4f5}.pills{display:flex;gap:9px;flex-wrap:wrap}.pill{padding:5px 12px;background:#ffffff20;border:1px solid #ffffff40;border-radius:30px;font-size:13px}
nav{background:#fff;padding:18px 24px;border:1px solid var(--line);border-radius:12px}nav a{display:inline-block;margin:3px 16px 3px 0}
section{margin:25px 0}.note,.warning{padding:16px 20px;border-left:4px solid var(--teal);background:#eaf6f5;border-radius:5px}.warning{border-left-color:var(--gold);background:#fff5e7}
.small{font-size:14px;color:var(--muted)}.lead{font-size:18px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;background:#fff;margin:16px 0;font-size:14px}th,td{border:1px solid var(--line);padding:12px;vertical-align:top;text-align:left}th{background:#e7eef5;color:var(--navy)}td:first-child{font-weight:600}
details.task-card{background:#fff;border:1px solid var(--line);border-radius:12px;margin:14px 0;overflow:hidden}summary{padding:18px 21px;cursor:pointer;font-size:18px;font-weight:700;color:var(--navy)}summary::marker{color:var(--teal)}details[open] summary{border-bottom:1px solid var(--line);background:#f8fbfd}.card-body{padding:3px 24px 22px}.meta{display:block;font-size:13px;font-weight:400;color:var(--muted);margin:4px 0 0 20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 26px}.grid>div{min-width:0}.label{font-weight:700;color:var(--teal)}ul,ol{padding-left:23px}li{margin:5px 0}.case-bins{font-size:15px;background:#f3f6fa;padding:12px;border-radius:6px}.refs{font-size:14px}.ref-item{padding:14px 0;border-bottom:1px solid var(--line)}.ref-title{font-weight:700}.tag{display:inline-block;background:#e8eef5;padding:2px 8px;margin-right:6px;border-radius:5px;font-size:12px}
code,pre{font-family:Consolas,monospace;background:#eaf0f5;font-size:14px}code{padding:2px 5px;border-radius:4px}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:18px;border-radius:8px}footer{border-top:1px solid var(--line);margin-top:40px;padding-top:18px}
@media(max-width:700px){main{padding:16px 14px 40px}header{padding:26px 22px}h1{font-size:26px}.grid{grid-template-columns:1fr}th,td{padding:9px}summary{font-size:16px}.card-body{padding:2px 18px 18px}}
@media print{body{background:white;font-size:10pt}main{max-width:none;padding:0}header{background:none;color:var(--navy);padding:0;border-radius:0}.subtitle{color:var(--muted)}.pill{color:var(--ink);border-color:var(--line)}nav{display:none}h2{break-before:page;font-size:19pt}h3{font-size:14pt}a{color:inherit}details.task-card .card-body{display:block!important}details.task-card{overflow:visible}summary{font-size:12pt;break-after:avoid}.grid{display:block}.ref-item{break-inside:avoid}table{font-size:9pt}tr{break-inside:avoid}.note,.warning{background:white}.table-wrap{overflow:visible}}
"""
INTRO = """
<section id="readme">
<h2>이 후보집을 읽는 방법</h2>
<p class="lead">목표는 ‘유행하는 방법을 구현하기’가 아니라 <strong>Agent가 맡을 업무를 정하고, 조건을 바꾸었을 때 무엇이 좋아지거나 나빠지는지 설명할 수 있는 연구</strong>를 찾는 것이다. 지금은 한 주제로 좁히지 않는다.</p>
<div class="note"><strong>범위:</strong> 6개 주제 × 6개 후보 = 36개. 각 후보의 50개 구성은 앞으로 직접 작성할 평가 시나리오의 설계안이다. 데이터나 실험 결과가 이미 만들어졌다는 뜻이 아니다. 비교 조건 3개, 개발용 사례, 반복 실험 등은 제안이며 과제의 추가 의무가 아니다.</div>
<p>각 후보 제목을 누르면 업무 예시, 50개 유형별 배분, 정답 정보, 비교 조건, 지표, 구현 부담, 확장 방향이 펼쳐진다. 마지막에는 논문 링크와 해석 시 주의점을 모았다. 주제 사이 경계는 겹친다. RAG를 메모리에 쓰거나, ReAct 실행을 harness가 관리하는 연구도 가능하다.</p>
<ul>
<li><strong>50개는 무엇인가?</strong> 선택한 한 태스크의 평가 사례 50개다. 6개 주제를 모두 구현하거나 50개의 서로 다른 서비스를 만들자는 뜻이 아니다. 과거 이력 → 새 요청 → 기대 상태로 묶인 하나의 에피소드도 사례가 될 수 있다.</li>
<li><strong>Agent성은 어디에 있는가?</strong> 근거 수집, 다음 도구 선택, 상태 갱신, 검증, 중단 중 무엇을 시스템이 결정하는지 드러낸다. 단순 검색 성능 측정도 중요한 구성요소 실험이지만, 최종 업무 성공에 어떻게 연결되는지까지 보여주면 Agent 과제로 설명하기 쉽다.</li>
<li><strong>다중 Agent가 필수인가?</strong> 일반적인 Agent 연구가 반드시 multi-agent일 필요는 없다. 수업에서 별도 요구한 경우만 따르며, 이 후보집의 대부분은 단일 Agent로도 가능하다.</li>
<li><strong>논문과 실험 제안은 구분:</strong> ‘비교 조건’과 ‘50개 구성’은 이 과제에 맞춘 제안이지, 인용 논문의 실험을 그대로 옮긴 것이 아니다. 논문 방법 전체의 재현이나 추가 학습도 기본 전제가 아니다.</li>
</ul>
<h3>처음부터 섞지 말아야 할 개념</h3>
""" + table(["구분", "이 연구에서의 뜻"], [
["BM25 / dense retrieval / vector DB", "BM25와 dense는 검색·표현 방식, vector DB는 저장·인덱싱·검색 인프라다. ‘BM25 대 vector DB’보다 검색 방식과 인덱스 구현을 나누어 비교한다."],
["Kiwi / 규칙 기반 처리", "Kiwi를 사용한다고 전체 파이프라인이 순수 규칙 기반인 것은 아니다. 품사 필터처럼 우리가 고정하는 전처리 규칙과 형태소 분석기의 학습된 모델을 구분한다."],
["GraphRAG / HNSW", "GraphRAG의 지식 관계 그래프와 HNSW의 근사 최근접 탐색 그래프는 목적과 평가 단위가 다르다."],
["ReAct / 모든 추론의 공개", "관찰한 결과에 따라 다음 행동을 바꾸는 실행을 비교한다. API가 제공하지 않는 내부 추론 전체를 얻을 필요는 없고, 도구·인자·관찰·상태·최종 결과를 기록하면 된다."],
["Alignment / 보안 / 신뢰성", "간접 프롬프트 인젝션, 권한 준수, 지시 충돌, 완료 보고의 정확성은 관련되지만 서로 다른 문제다. 하나의 ‘안전 점수’로 모두 뭉치지 않는다."],
["Harness / 모델 능력", "Harness는 모델 바깥의 도구 스키마, 규칙, 반복 실행, context 관리, 상태 저장과 검증 등을 뜻한다. 같은 모델에서 이 부분만 바꾸는 비교가 가능하다."]
]) + """
</section>
"""

THEME_NOTES = {
"RAG": """관심의 중심은 ‘벡터 검색이 좋은가?’라는 단일 승패보다 <strong>어떤 질문·자료·규모에서 어떤 검색 및 근거 구성 방식이 유리한가</strong>다. 검색 품질 → 근거 선택 → 답변 품질을 분리한다. corpus는 같은 정답 근거를 유지한 채 방해 문서를 늘리되, 새 자료가 정답 자체를 바꾸지 않았는지 확인한다. 작은 corpus에서도 의미 있는 태스크를 만들 수 있고, 수백만 문서 구축은 필수가 아니다.""",
"ReAct": """관심의 중심은 도구 수가 아니라 <strong>관찰을 받은 뒤 적절한 행동을 선택하고 실제 업무 상태를 완성하는가</strong>다. 검색/API/파일 도구를 모두 실서비스에 붙일 필요는 없다. 가짜 예약·재고·프로젝트 DB를 다루는 로컬 함수와 상태 검사기로도 순서, 권한, 실패 복구를 정밀하게 평가할 수 있다. 여러 정답 경로가 가능하면 하나의 호출 순서와 일치하는지만 채점하지 않는다.""",
"메모리": """관심의 중심은 ‘과거 내용을 외웠나’뿐 아니라 <strong>무엇을 저장하고, 수정·폐기하고, 지금 누구의 어떤 업무에 적용하는가</strong>다. 50개 사례 각각에 정답 이력과 시간·사용자 경계를 만들어야 한다. 긴 채팅 원문을 무작정 늘리는 대신 짧고 검증 가능한 합성 업무 이력으로 시작할 수 있다. 메모리 저장·정제 호출도 비용에 포함한다.""",
"Alignment": """‘Agent가 LLM보다 약하다’는 결론을 전제로 하지 않는다. <strong>같은 모델에 외부 정보와 행동 권한을 더했을 때 어떤 실패가 추가되는지</strong>를 질문으로 삼는다. 실제 계정·개인정보·송금·삭제를 연결하지 않고 가짜 문서와 모의 도구로 수행한다. 안전성 향상이 모든 정상 요청을 차단한 결과인지 구분하기 위해 정상 업무 성공률을 함께 측정한다.""",
"멀티모달": """입력을 보는 능력, 구조를 추론하는 능력, 파일·이미지를 출력하는 능력, 생성 후 검증하는 능력을 분리한다. 멀티모달 모델도 SVG·ABC 같은 코드를 출력할 수 있으므로 두 경로는 배타적이지 않다. <a href="multimodal_comparison.md">상세 비교 설계·12편 논문 메모</a>에서 동등한 정보·출력 계약·예산 통제와 native 출력 대조군의 자격 조건을 확인한다. 이 후보는 2026-10-14 추가했으며 모델·실험 예산은 미선정이다.""",
"Harness": """관심의 중심은 새로운 프레임워크 개발이 아니라 <strong>같은 모델에 어떤 실행 조건을 제공했을 때 성능·비용·신뢰성이 달라지는가</strong>다. 지시 파일의 길이, schema, 재시도, context, 검증, 재개 중 한 축을 주된 조작 변수로 삼는다. 수업 실습과의 차별성은 구현 규모가 아니라 비교 가설·통제 조건·실패 분석에서 만들 수 있다."""
}

def candidate(t):
    bins = " · ".join(e(label) + " " + str(n) + "개" for label, n in t["data"])
    low, high = t["calls"]
    mult = 2 if t["id"] == "A1" else 1
    suffix = " · clean/attack 쌍 포함" if mult == 2 else ""
    count = f"{150 * low * mult:,}–{150 * high * mult:,}회{suffix}"
    return f'''
<details class="task-card" id="task-{e(t["id"])}">
<summary>{e(t["id"])} · {e(t["title"])}
<span class="meta">{e(DIFF[t["difficulty"]])} | 사례당·조건당 모델 요청 {low}–{high}회 추정 | 평가 사례 50개</span></summary>
<div class="card-body">
<p><span class="label">궁금한 문제</span> — {e(t["problem"])}</p>
<p><span class="label">Agent가 수행할 업무</span> — {e(t["task"])}</p>
<p><span class="label">입력 예시</span> — {e(t["example"])}</p>
<h4>평가 사례 50개 구성</h4><div class="case-bins">{bins} <strong>→ 합계 50개</strong></div>
<p><span class="label">사례마다 작성할 정답 정보</span> — {e(t["gold"])}</p>
<div class="grid"><div><h4>비교 조건 제안</h4>{ul(t["compare"])}</div><div><h4>주요 지표</h4>{ul(t["metrics"])}</div></div>
<p><span class="label">구현·운영 부담</span> — {e(DIFF[t["difficulty"]])}. 50사례 × 3조건 × 1회 실행 시 <strong>{count}</strong>의 모델 호출이 가능한 설계 범위다. 실측·견적·필수 횟수가 아니다. {e(t["extra"])}</p>
<p class="warning"><strong>해석 주의:</strong> {e(t["pitfall"])}</p>
<p><span class="label">더 뻗어갈 방향</span> — {" / ".join(e(x) for x in t["extensions"])}</p>
<p class="refs"><span class="label">관련 자료</span> — {citations(t["refs"])}</p>
</div></details>'''

def theme_block(th):
    ts = [x for x in DATA["tasks"] if x["theme"] == th["id"]]
    rows = [[f'<a href="#task-{t["id"]}">{e(t["id"])} · {e(t["title"])}</a>', e(DIFF[t["difficulty"]]), f'{t["calls"][0]}–{t["calls"][1]}', e(t["metrics"][0])] for t in ts]
    return f'<section id="{THEME_IDS[th["id"]]}"><h2>{e(th["title"])}</h2><p class="lead">{e(th["question"])}</p><p>{THEME_NOTES[th["id"]]}</p><p class="refs">논문·자료 지도: {citations(th["papers"])}</p>' + table(["태스크 후보", "구현", "LLM 호출/사례·조건", "핵심 평가"], rows) + "".join(candidate(t) for t in ts) + "</section>"

CROSS = """
<section id="cross"><h2>주제를 가로질러 확장하는 8가지 방향</h2>
<p>아래 조합은 추가 후보이지, 지금 모두 구현하자는 뜻은 아니다. 하나의 실제 업무에 두 관점을 붙이는 방식으로 발전시킬 수 있다.</p>
""" + table(["연결", "태스크로 발전시키는 질문", "분리해서 확인할 효과"], [
["R2 + A1 · 근거 검증 × 외부 지시", "주장 검증 Agent가 검색 자료에 섞인 방해 지시를 무시하고 근거에 맞게 판정하는가?", "문서 검색 실패와 지시 오염 실패를 별도 분류"],
["R5 + M2 · 개정 지식 × 장기 기억", "지난달 처리한 업무를 이번 달 개정 규정에 맞춰 이어갈 수 있는가?", "문서의 최신성, 기억 갱신, 과거 시점 질문을 분리"],
["R4 + T2 · 문서 구조 × 계산", "표와 각주에서 필요한 값·단위를 찾아 조건에 맞는 선택을 계산하는가?", "파싱 오류 → 인자 오류 → 계산 오류 → 의사결정 오류"],
["T3 + H6 · 오류 복구 × 재개", "도구가 성공했지만 응답이 끊긴 상황에서 중복 처리 없이 이어가는가?", "모델 추론보다 상태 확인·멱등성·체크포인트의 효과"],
["M3 + H5 · 실패 경험 × 검증", "검증자가 발견한 실패를 다음 업무의 짧은 교훈으로 저장하면 재발이 줄어드는가?", "교훈 검색 효과와 검증 호출 증가 효과"],
["M5 + A4 · 기억 경계 × 출처", "삭제·만료되거나 다른 사용자에게 속한 기억, 근거가 불명확한 기억을 배제하는가?", "권한 위반, 오래된 사실 사용, 검색 누락"],
["R6 + H3 · 검색 예산 × 중단", "추가 검색의 가치가 낮으면 멈추고 근거가 부족하면 보류할 수 있는가?", "같은 비용에서의 성공률과 불필요한 호출 감소"],
["T5 + H2 · 도구 수 × 인터페이스", "도구가 많아져도 명료한 schema와 오류 설명으로 적절한 호출을 하는가?", "도구 선택 오류와 선택 후 인자 생성 오류"]
]) + """
</section>
"""

DATA_GUIDE = """
<section id="data"><h2>50개 평가 데이터를 실제로 만드는 방법</h2>
<p><strong>각 후보의 배분은 출발점이다.</strong> 쉬움·보통·어려움만으로 나누기보다, 왜 실패하는지 구분할 수 있는 유형으로 나눈다. 대부분 5유형 × 10개로 제안했지만 R1·R2·R3·R6처럼 다른 배분도 가능하다. 유형별 10개는 정밀한 통계 비교보다 실패 패턴을 보기 위한 규모다.</p>
<h3>사례 한 개의 공통 설계 양식</h3>
<pre>{
  "case_id": "task-001",
  "category": "정보 수정 후 이전 작업 이어가기",
  "user_request": "사용자가 맡긴 실제 업무",
  "initial_state": "문서·기억·도구 DB·시간·권한",
  "available_evidence": ["Agent에게 보이는 자료 ID"],
  "gold": {
    "acceptable_answer_or_final_state": "...",
    "required_evidence_or_constraints": ["..."],
    "forbidden_actions": ["..."]
  },
  "evaluation_rule": "정확 일치 / 허용 오차 / 상태 검사 / 사람 rubric",
  "difficulty_reason": "...",
  "source_and_authoring_note": "자료 출처와 직접 설계한 부분"
}</pre>
<p>정답과 판정 코드는 평가기 쪽에 두고 해결 Agent에게 노출하지 않는다. 공개 데이터셋은 문제 형식과 평가 규칙의 참고 자료로 쓸 수 있지만, 그대로 50개를 잘라 쓰는 것이 ‘직접 작성’ 요건을 만족한다고 단정하지 않는다. 모델을 초안 작성에 보조로 쓰는 허용 범위도 교수님께 확인할 사항이다.</p>
<h3>평가 제작 순서 제안</h3>
<ol>
<li><strong>업무 범위와 성공 조건:</strong> 무엇을 입력받고 어떤 최종 상태면 성공인지 먼저 적는다.</li>
<li><strong>작은 개발용 사례:</strong> 평가 50개와 별도의 몇 개로 도구와 채점기가 작동하는지 확인한다. 이것은 제안이지 추가 과제 요구가 아니다.</li>
<li><strong>50개 설계:</strong> 유형별 사례, 정답, 허용 대안, 근거, 실패 분류를 작성한다. 같은 문장을 숫자만 바꾼 사례가 대부분을 차지하지 않게 한다.</li>
<li><strong>교차 검토:</strong> 다른 조원이 Agent를 실행하지 않고도 정답을 판정할 수 있는지 확인한다. 모호한 사례는 평가 전에 고친다.</li>
<li><strong>평가본 고정:</strong> 조건별로 같은 50개와 동일한 자료·도구 상태를 제공한다. 결과를 보고 불리한 사례를 빼지 않는다.</li>
<li><strong>실패 분석 후 개선:</strong> 한 가지 원인을 겨냥한 변경을 한 뒤 같은 고정 평가본에 재평가하되, 그 평가본에 맞춘 개선이라는 한계를 명시한다. 가능하면 추가 독립 사례로 확인한다.</li>
</ol>
""" + table(["주제", "직접 작성해야 하는 핵심", "데이터 제작의 숨은 부담"], [
["RAG", "질문 + 관련 근거 집합 + 허용 답", "청킹이 달라져도 근거를 연결할 수 있는 문서·구간 ID, 여러 정답 근거의 누락 방지"],
["ReAct", "초기 상태 + 사용자 목표 + 허용·금지 동작 + 정답 최종 상태", "여러 올바른 경로를 허용하는 채점기, 도구 실패 주입의 재현성"],
["메모리", "과거 이력 + 변경 사건 + 이후 요청 + 그 시점의 정답", "모순·정정·삭제 관계의 일관성, 메모리 쓰기까지 포함한 실행 비용"],
["Alignment", "정상 업무 + 외부 방해/권한 조건 + 정상 결과 + 금지 행동", "clean/attack 대조쌍의 동등성, 무해한 모의 환경, 과잉 차단 판정"],
["Harness", "대표 업무 + 기대 산출물/상태 + 오류/중단 조건", "성능 차이가 모델·도구 정보량·호출 예산 차이 때문이 아닌지 통제"]
]) + """
<div class="warning"><strong>50개와 실행 횟수는 다르다.</strong> A1의 경우 50개 기본 업무 각각에 정상 자료와 방해 자료를 붙이면 조건당 100회 실행한다. 여전히 독립적인 기본 사례는 50개다. 메모리에서도 같은 사람의 연속된 질문 50개를 독립적인 50명/50에피소드와 동일하게 취급하지 않는다.</div>
<p class="small">작성 시간도 별도 비용이다. 예를 들어 사례당 10–30분이라는 가정을 두면 50개 초안만 약 8.3–25인시이며, 교차 검토와 수정은 추가다. 긴 이력·표·브라우저 작업은 이 범위를 넘을 수 있다. 실제 제작 시간을 측정한 추정치가 아니다.</p>
</section>
"""

METRICS = """
<section id="metrics"><h2>무엇을 metric으로 측정할까?</h2>
<p>모든 후보에 지표 10개를 붙일 필요는 없다. <strong>주된 업무 성공 지표 1개 + 원인 진단 1~2개 + 비용 지표</strong>로 시작하고, 안전성 연구에서는 정상 업무 효용도 함께 둔다. 아래 정의는 과제 설계를 위한 제안이다.</p>
""" + table(["지표", "계산/판정 기준", "주의"], [
["Task success rate", "성공 조건을 모두 충족한 사례 / 전체 평가 사례", "답변만 그럴듯한지보다 최종 상태·필수 제약을 검사"],
["Constraint satisfaction", "지킨 제약 수 / 적용되는 제약 수. 전부 충족한 사례 비율도 별도 보고", "부분 점수 평균이 금지 행동 1회의 심각성을 가리지 않게"],
["EM / 수치 정확도", "정규화한 답의 정확 일치 또는 단위·허용 오차를 포함한 판정", "표현이 다른 동등한 답, 통화·반올림·날짜 기준을 사전 정의"],
["Macro-F1", "지원/반박/정보 부족 등 클래스별 F1의 평균", "클래스별 분모와 혼동행렬도 표시; accuracy와 구분"],
["Recall@k / nDCG@k", "상위 k개에 포함된 관련 근거의 비율 / 위치와 관련성 등급을 반영한 검색 점수", "Agent가 뽑은 문서가 아니라 별도로 작성한 정답 관련성으로 채점"],
["Citation precision / coverage", "실제로 주장을 뒷받침하는 인용 비율 / 근거가 필요한 주장 중 충분히 뒷받침된 비율", "자료를 인용했다는 형식과 내용상 지원 여부를 구분"],
["도구 선택·인자 유효성", "필요한 도구 선택, schema 및 의미 조건을 만족한 호출 비율", "JSON 유효성만으로 올바른 날짜·대상·금액을 사용했다고 볼 수 없음"],
["중복·과잉 행동", "같은 효과의 중복 실행 수, 불필요한 호출 수, 금지 부작용 수", "도구 호출과 실제 상태 변화를 둘 다 기록"],
["최신 사실 정확도 / 오래된 기억 사용", "질문 시점에 맞는 사실을 사용한 비율 / 갱신 전 사실을 잘못 사용한 비율", "과거 시점 질문에서는 옛 사실이 정답일 수 있음"],
["False completion rate", "실제로 미완료인 작업을 완료라고 보고한 비율", "분모를 전체 작업으로 할지 미완료 작업으로 할지 고정하고 둘 다 표기 가능"],
["Attack success rate (ASR)", "정의한 금지 결과가 발생한 공격 사례 / 적용 가능한 공격 사례", "정상 버전에서 성공한 사례에 대한 조건부 ASR도 별도 보고; 정상 성공률을 함께 표시"],
["과잉 거절·차단", "정상적으로 수행해야 하는 사례 중 불필요하게 거절/차단한 비율", "아무것도 안 하는 Agent가 안전 최우수로 평가되지 않게"],
["Latency / 자원 / 비용", "전체 작업 및 검색 p50/p95, token, 호출 수, 구축 시간, 인덱스 크기", "모델 대기·검색·도구·재시도를 분리. CPU/GPU·버전·cold/warm 조건 기록"],
["성공 1건당 비용", "해당 조건 전체 비용 / 성공 사례 수", "실패 비용도 포함. 성공 0건이면 미정의로 표시하며 0원으로 쓰지 않음"]
]) + """
<h3>비교가 흔들리지 않게 하는 최소 장치</h3>
<ul>
<li><strong>한 번에 하나의 축:</strong> 같은 base model, 문제, 자료, 도구 권한, 출력 요구를 유지한다. 모델까지 비교하면 별도 실험 축으로 보고한다.</li>
<li><strong>실제 자원 제한:</strong> 같은 호출 수만으로 공정하지 않을 수 있다. 입력/출력 token과 지연도 기록한다. 서브에이전트가 더 많은 호출을 쓰면 그 증가를 숨기지 않는다.</li>
<li><strong>채점의 우선순위:</strong> 상태 검사·정답 수치·명시적 제약 → 사람이 검증 가능한 rubric → 필요한 부분만 LLM judge. Judge를 곧 정답으로 취급하지 않는다.</li>
<li><strong>Judge 통제:</strong> 사용하는 경우 모델/프롬프트를 고정하고, 시스템 이름을 가리고, 답 제시 순서를 통제한다. 일부를 사람이 다시 보며 일치·불일치를 기록한다.</li>
<li><strong>실패 보존:</strong> 빈 답, 잘림, 파싱 오류, timeout을 성공에서 제외하고 원인을 남긴다. 인프라 오류와 과제 수행 실패를 나누되 전체 시도 수를 숨기지 않는다. 재실행 정책은 결과를 보기 전에 정한다.</li>
<li><strong>50개의 한계:</strong> 사례 하나가 성공률 2%p다. 독립 사례 50개에서 성공률이 50% 근처면 단순 근사 95% 불확실성 폭이 약 ±14%p일 수 있다. 작은 차이를 ‘우월함 입증’으로 표현하지 않는다. 같은 사례를 공유하는 조건은 paired 비교/사례 단위 bootstrap을 고려한다.</li>
<li><strong>반복 실행:</strong> 확률적 변동을 보려면 반복이 유용하지만 비용도 곱해진다. pass@k(여러 시도 중 하나라도 성공)와 tau-bench의 pass^k(여러 시도 모두 성공)는 서로 다른 질문이다. 기본 성공률만으로 시작해도 된다.</li>
</ul>
</section>
"""

COSTS = """
<section id="cost"><h2>구현 난이도와 비용의 읽는 법</h2>
<p><strong>아래 수치는 실행 결과나 모델 견적이 아니다.</strong> Python에 익숙한 사람이 작은 로컬·모의 환경을 만든다는 가정 아래의 계획용 구간이다. 논문 재현 수준의 구현, 공개 서비스, 모델 학습은 포함하지 않는다.</p>
""" + table(["표시", "주요 구현 부담", "작동하는 작은 비교 실험까지의 예시 범위"], [
["D1 · 비교적 낮음", "간단한 함수·schema·상태 검사, 짧은 문맥, 외부 시스템 의존이 작음", "약 2–4인일 가정"],
["D2 · 중간", "검색 인덱스, 다단계 도구, 시간·기억 관리, 비교 조건 및 검증 코드", "약 5–8인일 가정"],
["D3 · 높음", "그래프/위키 구축, 복잡한 PDF·UI, 다중 역할, 장애 후 재개·일관성", "약 9–15인일 이상 가정"]
]) + """
<p class="small">인일은 하루 1명의 작업량이라는 계획 단위이며 실제 일정 보장이 아니다. 데이터 50개 작성·교차 검토, 논문 읽기, 발표·보고서 준비는 별도다. 동일 후보도 모의 환경으로 좁히면 난도가 내려가고 실서비스 연결을 요구하면 크게 올라간다.</p>
<h3>모델 호출 수를 먼저 계산한다</h3>
<pre>예상 총 LLM 호출
= 사례 수 × 비교 조건 수 × 반복 수 × 사례당 평균 호출 수
  + 자료/기억 구축 호출 + judge 호출 + LLM 사용자 시뮬레이터 호출

API 금액
= Σ(입력 token × 입력 단가 + 출력 token × 출력 단가)
  + 별도 임베딩·검색 API·서버 비용
※ 단가가 100만 token 기준이면 token 수를 1,000,000으로 나누어 적용.</pre>
""" + table(["설계 가정", "50개 × 3조건 × 1반복", "무엇이 더해질 수 있나"], [
["사례당 1–2회", "150–300회", "검색용 임베딩, 초기 지식 구축, 별도 평가"],
["사례당 3–6회", "450–900회", "기억 쓰기/정제, 재계획, 검증"],
["사례당 8–15회", "1,200–2,250회", "긴 tool loop, UI 관찰, 역할 분리"],
["clean/attack 대조쌍", "해당 기본 호출 수 × 2", "공격 없는 기준선과 공격 조건을 모두 실행"],
["3회 반복", "해당 기본 호출 수 × 3", "자동 재시도와는 별개인 사전 계획된 반복"]
]) + """
<p>예를 들어 150회 요청에 매번 입력 8,000·출력 1,000 token을 쓴다면 입력 약 120만·출력 15만 token이다. 금액은 실제로 선택한 모델의 그 시점 단가를 넣어야 한다. 여기서는 모델을 선택하지 않았으므로 달러 금액이나 무료 한도를 추정하지 않았다.</p>
<p>모델 2종이나 corpus 규모 3단계를 모두 교차 비교하면 해당 축도 곱해야 한다. 각 후보 카드의 호출량은 이런 추가 축을 제외한 3조건 기준이므로, 관심 변수를 모두 한꺼번에 넣으면 예산이 빠르게 커질 수 있다.</p>
<ul>
<li><strong>무료 API:</strong> 요금이 0이어도 할당량·대기·중단 비용은 있다. 제공 여부와 제한은 실행 직전에 확인한다.</li>
<li><strong>로컬 모델:</strong> API 금액 대신 장비 메모리·시간·동시 실행 수가 제약이다. 현재 장비에서 속도나 모델 적재를 검증하지 않았다.</li>
<li><strong>검색과 Agent 호출을 분리:</strong> 로컬 BM25 검색이나 Python 계산은 보통 LLM 요청이 아니다. 외부 검색 API에는 별도 요금/제한이 있을 수 있다.</li>
<li><strong>비용이 가려지기 쉬운 곳:</strong> GraphRAG/Wiki의 최초 구축, 문서 업데이트, 메모리 저장, 매번 재전송되는 긴 이력, judge, 오류 후 반복 요청.</li>
<li><strong>상한을 먼저 정하기:</strong> 최종 선택 뒤 작은 파일럿으로 사례당 호출·token·시간을 측정해 전체 예산을 다시 계산한다. 이번 조사는 실험 호출을 수행하지 않았으며 자동 재시도·모델 전환도 하지 않았다.</li>
</ul>
</section>
"""

TEAM = """
<section id="team"><h2>조원들과 비교할 질문 — 아직 순위를 매기지 않기</h2>
<ol>
<li><strong>어떤 실패가 가장 궁금한가?</strong> 못 찾는가, 순서를 틀리는가, 잊는가, 권한을 넘는가, 실행 환경이 방해하는가?</li>
<li><strong>‘업무 한 건’의 끝은 무엇인가?</strong> 문서/답만 내는지, 모의 DB 상태를 바꾸는지, 다음 세션까지 이어가는지 정한다.</li>
<li><strong>50개를 사람이 검증할 수 있는가?</strong> 모델 평가 없이도 정답 상태·근거·계산값을 확인할 수 있는 부분을 찾는다.</li>
<li><strong>독립 변수 하나를 말할 수 있는가?</strong> ‘복잡한 Agent 대 단순한 Agent’보다 검색 방식, 기억 갱신, tool schema처럼 무엇을 바꾸는지 구체화한다.</li>
<li><strong>좋아지지 않아도 배울 수 있는가?</strong> 어느 유형에서 왜 실패했는지와 개선 행동으로 이어지는지 확인한다.</li>
<li><strong>수업과 어떻게 차별화되는가?</strong> 이미 배운 ReAct/BM25를 쓰더라도 한국어·시간 변화·권한·비용 조건 아래의 비교 가설이 새로울 수 있다. 새로운 프레임워크 자체가 필수는 아니다.</li>
</ol>
<div class="note">관심 있는 후보에 표시만 하고, 각각 “이 업무를 맡기는 사용자 → 실패 원인 가설 → 통제된 비교 → 정답을 아는 50개 → 개선 1가지”를 한 문단으로 써보면 논의가 구체화된다. 지금은 특정 후보를 선정하거나 우선순위를 부여하지 않았다.</div>
<h3>나중에 남길 수 있는 연구 산출물</h3>
<p>50개 사례와 작성 기준, 실행 가능한 코드 및 환경 설명, 조건별 원본 실행 기록, 지표와 오류 유형 표, 개선 전후 비교, 결과가 통하지 않는 조건과 한계가 한 묶음이 된다. 여기에 수업에서 지정한 발표·저장소·보고서 형식을 맞춘다. 과제 요구로 정해진 항목과 이 후보집의 권장 실험 설계는 구별한다.</p>
</section>
"""

def bibliography():
    parts = [f'<section id="papers"><h2>관련 논문·자료 {len(REFS)}건</h2><p>{PAPER_COUNT}편의 논문과 {IDEA_COUNT}개의 실무 아이디어 자료를 묶었다. 기초 논문과 최근 자료를 함께 포함했다. 학회/저널 논문, 워크숍, preprint, 아이디어 메모를 같은 검증 수준으로 취급하지 않는다. 각 링크는 원논문·공식 학회·저자 자료로 연결된다.</p>']
    for r in DATA["references"]:
        parts.append(f'<article class="ref-item" id="ref-{e(r["id"])}"><span class="tag">{e(r["id"])}</span><span class="ref-title"><a href="{e(r["url"])}">{e(r["title"])}</a></span><p class="small">{e(r["venue"])}</p><p><strong>연결되는 아이디어:</strong> {e(r["idea"])}</p><p class="small"><strong>읽을 때 주의:</strong> {e(r["caveat"])}</p></article>')
    parts.append("</section>")
    return "".join(parts)

assert len({t["id"] for t in DATA["tasks"]}) == TASK_COUNT
assert len(REFS) == len(DATA["references"])
for t in DATA["tasks"]:
    assert sum(n for _, n in t["data"]) == 50, t["id"]
    assert all(r in REFS for r in t["refs"]), t["id"]

nav = '<nav aria-label="목차">' + " ".join(f'<a href="#{target}">{label}</a>' for target,label in [
("readme","읽는 법"),("rag","1. RAG"),("react","2. ReAct"),("memory","3. 메모리"),("alignment","4. Alignment"),("harness","5. Harness"),("multimodal","6. 멀티모달"),("cross","연결 아이디어"),("data","50개 설계"),("metrics","평가 지표"),("cost","난도·비용"),("team","팀 논의"),("papers","논문 목록")]) + "</nav>"
header = f'<header><div class="kicker">AI AGENTS · RESEARCH BRAINSTORMING</div><h1>여섯 관심사에서 출발하는<br>{TASK_COUNT}가지 태스크 연구 후보</h1><p class="subtitle">RAG · ReAct · 메모리 · LLM/Agent alignment · Harness · 멀티모달<br>태스크, 직접 작성할 평가 데이터 50개, 비교 실험, metric, 구현 부담과 비용을 함께 보는 후보집</p><div class="pills"><span class="pill">최초 2026-10-11 · 멀티모달 추가 2026-10-14</span><span class="pill">주제 미선정</span><span class="pill">{TASK_COUNT}개 후보</span><span class="pill">논문 {PAPER_COUNT}편 + 아이디어 {IDEA_COUNT}건</span><span class="pill">실험 미실행</span></div></header>'
footer = '<footer><p><strong>조사 범위와 한계:</strong> 5개 주제에서 Exa 검색 23회, 요청한 검색 결과 항목 총 115개(중복 포함)를 바탕으로 원논문·공식 학회·저자 자료를 선별했다. 115편을 정독했다는 뜻이 아니다. 최근 검토 범위는 2024-10-11–2026-10-11이며 앞선 기초 논문도 포함했다. 2026-10-14에는 3개 조사 축에서 검색 6회·결과 항목 30개(중복 포함)를 요청하고 공식 자료를 대조하여 멀티모달 관련 12편을 추가했다. 이 추가 조사로 기존 34편 전체를 재검증한 것은 아니다. 원문/공식 초록 수준의 선별 조사로, 모든 전문 정독·실험 재현·코드 감사는 수행하지 않았다.</p><p>태스크·배분·지표·비용 구간은 과제 논의를 위한 제안이다. 실행 결과, 특정 모델의 우월성, 특정 규모에서의 보편적인 성능 교차점은 주장하지 않는다. 같은 폴더의 candidates.json에 구조화한 원자료가 있다.</p></footer>'
html = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Agents 연구 후보집 — {TASK_COUNT}개 태스크</title><style>' + STYLE + '</style></head><body><main>' + header + nav + INTRO + "".join(theme_block(t) for t in DATA["themes"]) + CROSS + DATA_GUIDE + METRICS + COSTS + TEAM + bibliography() + footer + '</main></body></html>'
OUT.write_text(html, encoding="utf-8", newline="\n")
print(json.dumps({"output":str(OUT),"bytes":OUT.stat().st_size,"tasks":len(DATA["tasks"]),"references":len(REFS),"all_case_counts":50},ensure_ascii=False))
