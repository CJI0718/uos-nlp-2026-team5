"""Run the agent offline on three claims and print what it decided at each step.

Zero API calls, zero cost. The point of the demo is that the SAME code produces
DIFFERENT action sequences depending on the claim: that is what makes it an
agent rather than a fixed pipeline.

    uv run python scripts/demo_fc002.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from task_a.loop import Budget, ReActAgent  # noqa: E402
from task_a.mock import (  # noqa: E402
    MockBackend, ScriptedLLM, finish_response, tool_call_response,
)
from task_a.schema import Claim, EvidenceUnit  # noqa: E402
from task_a.tools import ToolRegistry  # noqa: E402

WIDTH = 78


def unit(evidence_id, title, text, **kw) -> EvidenceUnit:
    return EvidenceUnit(evidence_id=evidence_id, title=title, text=text, **kw)


# --- FC002: timezone error -------------------------------------------------
FC002 = Claim(
    claim_id="FC002",
    text="미국 비전 프로 사전예약은 2024년 1월 19일 한국시간 오전 5시에 시작한다.",
    source_type="korean_news",
    target_period="2024-01-19 사전예약 개시",
    input_body="사전예약은 이달 19일 오전 5시(한국시간)부터 받는다.",
)
FC002_CORPUS = [
    unit("EV_FC002_apple", "Apple Vision Pro available in the US on February 2",
         "Apple Vision Pro will be available in the US on Friday, February 2, 2024. "
         "Pre-orders begin on January 19, 2024 at 5:00 a.m. PST.",
         publisher="Apple", source_type="official_announcement",
         provenance_group="pg_apple_launch", published_at="2024-01-08",
         claim_evidence_relation="refutes", evidence_condition="sufficient"),
    unit("EV_FC002_review", "애플 비전 프로 체험기",
         "애플의 혼합현실 헤드셋을 미리 사용해 봤다. 무게와 착용감이 인상적이다.",
         publisher="example", source_type="korean_news",
         claim_evidence_relation="irrelevant", evidence_condition="sufficient"),
]
FC002_SCRIPT = [
    tool_call_response("search_evidence", {"query": "Vision Pro 사전예약 2024년 1월 19일 시작 시각"}),
    tool_call_response("read_evidence", {"evidence_id": "EV_FC002_apple"}),
    tool_call_response("calculate_comparison", {"op": "tz_convert", "time": "2024-01-19 05:00",
                                                "from_tz": "PST", "to_tz": "KST"}),
    finish_response("refuted", ["EV_FC002_apple"],
                    "공식 발표는 2024-01-19 05:00 PST이며 한국시간이 아니다. PST와 KST는 17시간 차이가 난다.",
                    "evidence_sufficient", correction="사전예약 시작은 2024-01-19 22:00 KST"),
]

# --- FC004: one search is enough -------------------------------------------
FC004 = Claim(
    claim_id="FC004",
    text="2024년 노벨문학상 수상자로 소설가 한강이 선정됐다.",
    source_type="korean_news",
    target_period="2024년 노벨문학상",
    input_body="한국인 소설가 한강을 노벨 문학상 수상자로 선정했다.",
)
FC004_CORPUS = [
    unit("EV_FC004_nobel", "The Nobel Prize in Literature 2024",
         "The Nobel Prize in Literature 2024 was awarded to the South Korean author "
         "Han Kang for her intense poetic prose that confronts historical traumas.",
         publisher="NobelPrize.org", source_type="official_announcement",
         provenance_group="pg_nobel_2024_lit", published_at="2024-10-10",
         claim_evidence_relation="supports", evidence_condition="sufficient"),
]
FC004_SCRIPT = [
    tool_call_response("search_evidence", {"query": "2024 노벨문학상 수상자 한강"}),
    finish_response("supported", ["EV_FC004_nobel"],
                    "수여 기관 공식 발표가 인물·연도·부문을 모두 일치시킨다. 추가 검증이 불필요하다.",
                    "evidence_sufficient"),
]

# --- FC041: nothing verifiable, so the correct answer is to abstain ---------
FC041 = Claim(
    claim_id="FC041",
    text="40바이트 추론 코어와 웹검색 조합은 Galaxy S23에서 14GB Llama 7B보다 "
         "모든 면에서 우수하며 비교 점수는 75점 대 70점이다.",
    source_type="x_post",
    target_period="수집 시점에 제공된 게시글과 허용 공개 자료",
    input_body="결과: 점수 기존 LLM 14GB 70점 / 당신 방식 + 웹검색 75점",
)
FC041_CORPUS = [
    unit("EV_FC041_ragtruth", "RAGTruth: A Hallucination Corpus",
         "Retrieval-augmented generation systems still produce content that conflicts "
         "with the retrieved evidence or is unsupported by it. 배경 자료이며 특정 시스템의 "
         "성능을 평가한 논문은 아니다.",
         publisher="ACL Anthology", source_type="paper",
         claim_evidence_relation="background", evidence_condition="missing"),
]
FC041_SCRIPT = [
    tool_call_response("search_evidence", {"query": "40바이트 추론 코어 벤치마크 75점 70점 Galaxy S23"}),
    tool_call_response("search_web", {"query": "40바이트 추론 코어 벤치마크 Llama 7B 비교"}),
    finish_response("not_enough_evidence", [],
                    "주장한 시스템을 식별할 코드·설정·측정 환경을 찾지 못했다. 배경 논문만으로 "
                    "특정 미공개 코어의 성능을 반박할 수는 없다.",
                    "no_further_tools_helpful", abstain=True),
]

CASES = [
    (FC002, FC002_CORPUS, FC002_SCRIPT),
    (FC004, FC004_CORPUS, FC004_SCRIPT),
    (FC041, FC041_CORPUS, FC041_SCRIPT),
]


def show(claim: Claim, corpus: list[EvidenceUnit], script: list) -> None:
    backend = MockBackend(corpus)
    llm = ScriptedLLM(list(script))
    agent = ReActAgent(llm, ToolRegistry(backend), Budget())

    print("=" * WIDTH)
    print(f"{claim.claim_id} · {claim.source_type}")
    print("=" * WIDTH)
    print(f"주장: {claim.text}")
    if claim.input_body:
        print(f"원문: {claim.input_body}")
    print(f"코퍼스: {len(corpus)}개 문서\n")

    result = agent.run(claim)

    for event in result.events:
        external = " [외부]" if event.external else ""
        args = ", ".join(f"{k}={v!r}" for k, v in event.args.items())
        print(f"  {event.step}. 에이전트 선택 → {event.tool}{external}")
        print(f"     인자: {args}")
        print(f"     상태: {event.status.value} · {event.elapsed_ms}ms"
              + (f" · 문서 {event.evidence_ids}" if event.evidence_ids else ""))
    print(f"\n  {result.steps}. 에이전트 선택 → finish_verification")
    print(f"     판정: {result.verdict.value}"
          + ("  (보류)" if result.abstain else ""))
    print(f"     인용: {result.cited_evidence_ids or '(없음)'}")
    print(f"     이유: {result.justification}")
    if result.correction:
        print(f"     정정: {result.correction}")
    print(f"     종료 사유: {result.stop_reason}")
    print(f"\n  도구 호출 {result.usage.tool_calls}회"
          f" (외부 {result.usage.external_calls}회) · 단계 {result.steps}"
          f" · 상태 {result.execution_status.value}")
    print()


def main() -> None:
    print("\n같은 코드, 다른 주장, 다른 행동 순서\n")
    for claim, corpus, script in CASES:
        show(claim, corpus, script)
    print("=" * WIDTH)
    print("위 세 사례는 동일한 ReActAgent 클래스로 실행됐다.")
    print("단계 수는 각각 4 / 2 / 3이고, 호출한 도구도 서로 다르다.")
    print("검색-계산-종료 순서를 코드가 강제하지 않았다. 모델이 매번 골랐다.")
    print("=" * WIDTH)


if __name__ == "__main__":
    main()
