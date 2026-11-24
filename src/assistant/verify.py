"""Verify one candidate event with the Task A environment and an LLM tool loop.

The model only sees the verification tools. finish_verification is forwarded
without a mission, so the server writes nothing; the app's policy decides.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from assistant.budget import Budget
from assistant.llm import ChatClient
from assistant.policy import Verified
from task_a.missions import is_date_only
from task_a.skill import skill_body
from task_a.tools import FINISH_TOOL

KST = ZoneInfo("Asia/Seoul")
HIDDEN_TOOLS = {"list_claims", "start_episode", "submit_claim"}
#: Finish fields the app does not let the model set: the app decides the action.
MISSION_FIELDS = ("mission_type", "mission_title", "mission_summary", "tracking_condition",
                  "tracking_queries")
MAX_TOOL_RESULT_CHARS = 6_000
VERDICT_KO = {"supported": "맞음", "refuted": "틀림(정정)", "not_enough_evidence": "근거 부족"}

APP_GUIDE = """
## 일정 비서 모드
지금 너는 사용자의 일정 비서다. 아래 행사 일정 주장 하나를 검증한다. 에피소드는 이미 시작됐다.
- 주최 측 공식 공지(뉴스룸, 공식 블로그, 공식 사이트)를 search_web으로 찾고 fetch_url로 직접 연다.
  검색 결과 요약(스니펫)만 보고 날짜나 시각을 정하지 않는다. 판단에 쓴 문서는 반드시 열어서 읽는다.
- 원문 시각에 시간대가 있으면 calculate_comparison(op="tz_convert", time="YYYY-MM-DD HH:MM", from_tz=..., to_tz="KST")로 한국시간을 계산한다.
- finish_verification을 정확히 한 번 호출한다. mission_type은 넣지 않는다(등록 여부는 앱이 정한다).
  event_start_kst에 검증된 한국시간을 넣는다: 'YYYY-MM-DD HH:MM'. 시각 없이 날짜만 공식 발표됐으면 'YYYY-MM-DD'.
- 반박이면 correction에 정정된 한국 일시를 event_start_kst와 같은 표기로 적는다.
- 주장과 다른 행사를 찾았다면 그 행사로 바꾸지 않는다. 주장한 행사의 공식 일정이 아직 없으면 not_enough_evidence로 판정한다.
""".strip()


@dataclass
class Candidate:
    interest: str
    name: str                       # event name as the source writes it
    title_ko: str
    claim_text: str
    start: str                      # local 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' as claimed
    tz: str | None = None           # IANA zone of `start`, when the source gives one
    source_url: str | None = None
    excerpt: str | None = None
    recheck_of: int | None = None   # event id when this re-verifies a tracked event


def claimed_kst(c: Candidate) -> str | None:
    """The candidate's claimed start in KST ('YYYY-MM-DD' stays a date)."""
    if is_date_only(c.start):
        return c.start.strip()
    try:
        local = datetime.strptime(c.start.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    zone = c.tz or "Asia/Seoul"
    try:
        return local.replace(tzinfo=ZoneInfo(zone)).astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return None


@dataclass
class VerifyOutcome:
    verified: Verified | None = None
    finish_args: dict = field(default_factory=dict)
    error: str | None = None
    turns: int = 0


def llm_tools(mcp_tools: list[dict]) -> list[dict]:
    out = []
    for tool in mcp_tools:
        if tool["name"] in HIDDEN_TOOLS:
            continue
        params = copy.deepcopy(tool["inputSchema"])
        if tool["name"] == FINISH_TOOL:
            for name in MISSION_FIELDS:
                params.get("properties", {}).pop(name, None)
        out.append({"type": "function", "function": {
            "name": tool["name"], "description": tool["description"], "parameters": params}})
    return out


def _system_prompt() -> str:
    return skill_body() + "\n\n" + APP_GUIDE


def _user_prompt(start_payload: dict, c: Candidate) -> str:
    return ("검증할 일정 주장입니다. 공식 출처로 확인하고 finish_verification으로 끝내세요.\n"
            + json.dumps({"claim": start_payload["claim"], "budget": start_payload["budget"],
                          "claimed_start_local": c.start, "claimed_timezone": c.tz},
                         ensure_ascii=False, indent=2))


Emit = Callable[..., None]


def verify_candidate(env, client: ChatClient, c: Candidate, budget: Budget, emit: Emit,
                     max_turns: int = 10) -> VerifyOutcome:
    started = env.submit_claim({
        "text": c.claim_text, "source_url": c.source_url, "input_body": c.excerpt,
        "target_period": f"{c.name} 시작 일시",
    })
    messages = [{"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _user_prompt(started, c)}]
    tools = llm_tools(env.mcp_tools())
    allowed = {t["function"]["name"] for t in tools}
    outcome = VerifyOutcome()

    for turn in range(1, max_turns + 1):
        outcome.turns = turn
        budget.check_llm()
        reply = client.complete(messages, tools)
        budget.charge_llm(reply.usage)
        messages.append(reply.message)
        if reply.content.strip():
            emit("think", reply.content.strip()[:200])
        if not reply.tool_calls:
            messages.append({"role": "user", "content":
                             "도구를 호출해 검증을 계속하거나 finish_verification으로 끝내세요."})
            continue
        for call in reply.tool_calls:
            result = _run_tool(env, call, allowed, budget, emit, outcome)
            messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name,
                             "content": json.dumps(result, ensure_ascii=False)[:MAX_TOOL_RESULT_CHARS]})
            if outcome.verified is not None:
                return outcome
    outcome.error = f"{max_turns}턴 안에 finish_verification을 호출하지 않음"
    return outcome


def _run_tool(env, call, allowed: set[str], budget: Budget, emit: Emit, outcome: VerifyOutcome) -> dict:
    args = call.arguments
    if "__invalid_json__" in args:
        return {"status": "invalid_input", "observation": "인자가 올바른 JSON이 아닙니다."}
    if call.name not in allowed:
        return {"status": "invalid_input", "observation": f"쓸 수 없는 도구: {call.name}"}

    if call.name == FINISH_TOOL:
        clean = {k: v for k, v in args.items() if k not in MISSION_FIELDS}
        cited = [str(x) for x in (clean.get("cited_evidence_ids") or [])]
        if env.active is None:
            return {"status": "invalid_input", "observation": "에피소드가 이미 끝났습니다."}
        snap = env.episode_snapshot(cited)
        try:
            res = env.call_tool(FINISH_TOOL, clean)
        except ValueError as exc:   # missing verdict/justification: the model may fix it
            return {"status": "invalid_input", "observation": str(exc)}
        r = res["result"]
        outcome.finish_args = clean
        outcome.verified = Verified(
            verdict=r["verdict"], abstain=bool(r.get("abstain")),
            event_start=(clean.get("event_start_kst") or None), correction=r.get("correction"),
            distortion_type=r.get("distortion_type"), cited=cited, observed=snap["observed"],
            texts=snap["texts"], docs=snap["docs"], meta=snap["meta"],
            justification=r.get("justification") or "")
        emit("verdict", f"판정: {VERDICT_KO.get(r['verdict'], r['verdict'])}" + (f" · {clean.get('event_start_kst')}"
                                                   if clean.get("event_start_kst") else ""),
             (r.get("justification") or "")[:300])
        return {"status": "finished"}

    if call.name == "search_web":
        budget.check_search()
    res = env.call_tool(call.name, args)
    if call.name == "search_web" and res.get("status") not in ("blocked", "invalid_input"):
        budget.charge_search()
    if call.name == "fetch_url" and res.get("status") not in ("blocked", "invalid_input"):
        budget.charge_fetch()
    emit(_kind(call.name), _label(call.name, args, res), (res.get("observation") or "")[:240])
    return res


def _kind(tool: str) -> str:
    return {"search_web": "search", "fetch_url": "read", "read_evidence": "read",
            "calculate_comparison": "calc"}.get(tool, "tool")


def _label(tool: str, args: dict, res: dict) -> str:
    status = res.get("status")
    if tool == "search_web":
        return f"검색: {args.get('query', '')}" + ("" if status == "ok" else f" ({status})")
    if tool == "fetch_url":
        return f"열람: {args.get('url', '')}" + ("" if status == "ok" else f" ({status})")
    if tool == "calculate_comparison":
        obs = (res.get("observation") or "").splitlines()
        return "계산: " + (obs[0][:120] if obs else str(args.get("op")))
    return f"{tool}" + ("" if status == "ok" else f" ({status})")
