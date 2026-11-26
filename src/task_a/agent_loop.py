"""Drive one Task A episode with an OpenAI-compatible chat model.

The model gets the same tools the MCP server offers (minus episode control),
the same Skill text, and the same `start_episode` payload a Claude Code agent
would see. Tool calls go straight to `AgentEnvironment.call_tool`, so the gate,
the citation rules and the run log are the server's own - only the transport
differs from the MCP path.

No retries: a provider error, a turn limit or a model that stops calling tools
ends the episode with an execution failure that is logged, not hidden.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from task_a.schema import AgentResult, ExecutionStatus, Usage
from task_a.skill import skill_body
from task_a.tools import FINISH_TOOL

# Episode control stays with the runner. Re-calling start_episode would reset
# the episode mid-way, and list_claims would show other claims.
HIDDEN_TOOLS = frozenset({"list_claims", "start_episode", "submit_claim"})
MAX_TOOL_RESULT_CHARS = 12_000
MAX_NUDGES = 2

HARNESS_NOTE = """

## 실행 환경 안내

- 이 세션에서는 에피소드가 이미 시작되어 있습니다. 첫 메시지가 `start_episode` 응답입니다. `start_episode`는 다시 부르지 않습니다.
- 도구 호출로만 진행합니다. 판단이 끝나면 `finish_verification`을 정확히 한 번 호출해 끝냅니다.
"""

USER_TEMPLATE = """다음은 start_episode 응답입니다. 이 주장을 검증하세요.

```json
{payload}
```"""

NUDGE = ("도구 호출 없이 답하면 판정이 기록되지 않습니다. 필요한 도구를 호출하고, "
         "끝낼 때는 finish_verification을 호출하세요.")


class ChatClient(Protocol):
    model: str

    def complete(self, messages: list[dict], tools: list[dict] | None = None,
                 json_mode: bool = False): ...


class BudgetExceeded(RuntimeError):
    """The run-wide money cap was reached; stop starting or continuing episodes."""


@dataclass
class Price:
    """USD per 1M tokens."""
    input: float
    output: float
    cached_input: float | None = None

    def cost(self, prompt: int, completion: int, cached: int = 0) -> float:
        cached = min(cached, prompt)
        cached_rate = self.input if self.cached_input is None else self.cached_input
        return ((prompt - cached) * self.input + cached * cached_rate
                + completion * self.output) / 1_000_000


class Budget:
    """Run-wide money cap shared by all episodes (and threads) of a run.

    `spent_before` carries what earlier runs already used, so one cap covers
    the pilot, the baseline and the rerun together.
    """

    def __init__(self, cap_usd: float, spent_before: float = 0.0) -> None:
        self.cap_usd = cap_usd
        self.spent = spent_before
        self._lock = threading.Lock()

    def add(self, usd: float) -> None:
        with self._lock:
            self.spent += usd

    def remaining(self) -> float:
        with self._lock:
            return self.cap_usd - self.spent

    def check(self) -> None:
        if self.remaining() <= 0:
            raise BudgetExceeded(f"모델 비용 상한 ${self.cap_usd:.2f}에 도달했습니다(사용 ${self.spent:.4f}).")


@dataclass
class EpisodeOutcome:
    claim_id: str
    arm: str
    execution_status: str
    verdict: str | None = None
    finished: bool = False
    turns: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float = 0.0
    tool_counts: dict = field(default_factory=dict)
    invalid_tool_calls: int = 0
    nudges: int = 0
    duration_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def openai_tools(env) -> list[dict]:
    """The server's tools in OpenAI function format.

    C0 offers only finish_verification: the server blocks every other tool there,
    and listing them would only waste turns on refusals.
    """
    out = []
    for tool in env.mcp_tools():
        name = tool["name"]
        if name in HIDDEN_TOOLS:
            continue
        if env.arm == "C0" and name != FINISH_TOOL:
            continue
        out.append({"type": "function",
                    "function": {"name": name, "description": tool["description"],
                                 "parameters": tool["inputSchema"]}})
    return out


def system_prompt(skill_path: str | Path | None = None) -> str:
    body = skill_body(skill_path) if skill_path else skill_body()
    return body + HARNESS_NOTE


def _text(content) -> str:
    """Message content as text; reasoning models may return a list of chunks."""
    if isinstance(content, str):
        return content
    parts = []
    for chunk in content or []:
        if isinstance(chunk, dict) and chunk.get("type") == "text":
            parts.append(chunk.get("text") or "")
    return "".join(parts)


def _history_message(reply) -> dict:
    """The assistant turn to send back: text plus tool calls, no reasoning chunks."""
    msg = dict(reply.message or {"role": "assistant", "content": ""})
    msg["content"] = _text(msg.get("content"))
    return msg


def run_episode(env, client: ChatClient, claim_id: str, *, price: Price, budget: Budget,
                max_turns: int = 20, system: str | None = None,
                transcript: Callable[[list[dict]], None] | None = None) -> EpisodeOutcome:
    """Run one claim to completion or to a logged failure."""
    started = time.monotonic()
    payload = env.start_episode(claim_id)
    tools = openai_tools(env)
    allowed = {t["function"]["name"] for t in tools}
    messages: list[dict] = [
        {"role": "system", "content": system or system_prompt()},
        {"role": "user", "content": USER_TEMPLATE.format(
            payload=json.dumps(payload, ensure_ascii=False, indent=2))},
    ]
    out = EpisodeOutcome(claim_id=claim_id, arm=env.arm, execution_status=ExecutionStatus.OK.value)

    try:
        while out.turns < max_turns:
            budget.check()
            try:
                reply = client.complete(messages, tools)
            except Exception as exc:   # provider/transport error: logged, never retried
                return _fail(env, out, started, _status_for(exc), f"{type(exc).__name__}: {exc}",
                             messages, transcript)
            out.turns += 1
            usage = reply.usage or {}
            p, c, k = (int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)),
                       int(usage.get("cached_tokens", 0)))
            usd = price.cost(p, c, k)
            out.prompt_tokens += p
            out.completion_tokens += c
            out.cached_tokens += k
            out.cost_usd += usd
            budget.add(usd)
            messages.append(_history_message(reply))

            if not reply.tool_calls:
                out.nudges += 1
                if out.nudges > MAX_NUDGES:
                    return _fail(env, out, started, ExecutionStatus.PARSE_ERROR.value,
                                 "모델이 도구를 호출하지 않고 답을 끝냈습니다.", messages, transcript)
                messages.append({"role": "user", "content": NUDGE})
                continue

            for call in reply.tool_calls:
                out.tool_counts[call.name] = out.tool_counts.get(call.name, 0) + 1
                result = _call(env, call, allowed, out)
                messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name,
                                 "content": json.dumps(result, ensure_ascii=False)[:MAX_TOOL_RESULT_CHARS]})
                if result.get("status") == "finished":
                    out.finished = True
                    out.verdict = (result.get("result") or {}).get("verdict")
                    break
            if out.finished:
                out.duration_ms = int((time.monotonic() - started) * 1000)
                if transcript:
                    transcript(messages)
                return out
        return _fail(env, out, started, ExecutionStatus.BUDGET_EXCEEDED.value,
                     f"턴 한도({max_turns})에 도달했습니다.", messages, transcript)
    except BudgetExceeded as exc:
        _fail(env, out, started, ExecutionStatus.BUDGET_EXCEEDED.value, str(exc), messages, transcript)
        raise


def _call(env, call, allowed: set[str], out: EpisodeOutcome) -> dict:
    if "__invalid_json__" in call.arguments:
        out.invalid_tool_calls += 1
        return {"status": "invalid_input", "observation": "도구 인자가 올바른 JSON이 아닙니다."}
    if call.name not in allowed:
        out.invalid_tool_calls += 1
        return {"status": "invalid_input",
                "observation": f"이 조건에서 쓸 수 없는 도구입니다: {call.name}. 쓸 수 있는 도구: {sorted(allowed)}"}
    try:
        return env.call_tool(call.name, call.arguments)
    except (ValueError, TypeError, KeyError) as exc:
        # e.g. finish_verification without verdict/justification: the episode stays
        # open and the model sees why, as an MCP client would.
        out.invalid_tool_calls += 1
        return {"status": "invalid_input", "observation": str(exc)}


def _status_for(exc: Exception) -> str:
    text = str(exc)
    if "429" in text:
        return ExecutionStatus.RATE_LIMITED.value
    if "timed out" in text.lower() or "timeout" in text.lower():
        return ExecutionStatus.TIMEOUT.value
    return ExecutionStatus.PROVIDER_ERROR.value


def _fail(env, out: EpisodeOutcome, started: float, status: str, error: str,
          messages: list[dict], transcript) -> EpisodeOutcome:
    """Log an unfinished episode in the server's run log so it is scored as a failure."""
    out.execution_status = status
    out.error = error[:500]
    out.duration_ms = int((time.monotonic() - started) * 1000)
    ep = env.active
    if ep is not None:
        result = AgentResult(
            claim_id=ep.claim.claim_id, verdict=None, abstain=False, cited_evidence_ids=[],
            justification="", correction=None, stop_reason="execution_failure",
            execution_status=ExecutionStatus(status), events=list(ep.events),
            usage=Usage(input_tokens=out.prompt_tokens, output_tokens=out.completion_tokens,
                        cached_tokens=out.cached_tokens, llm_calls=out.turns,
                        tool_calls=ep.tool_calls, external_calls=ep.external_calls,
                        cost_usd=round(out.cost_usd, 6), elapsed_ms=out.duration_ms),
            steps=ep.step, error=out.error)
        env.log.append(env.config, result)
        env.active = None
    if transcript:
        transcript(messages)
    return out


# --------------------------------------------------------------------------
# Plain baseline: the same model and web, without the harness
# --------------------------------------------------------------------------
# What is removed: the Skill, the decision rules, calculate_comparison, paged
# reading, provenance labels, distortion analysis and missions. What stays,
# because it is the evaluation protocol rather than the harness: the same
# Tavily search, the evidence-cutoff filter, the block on the public answer
# key, the external-call budget and the run log the scorer reads.

PLAIN_PAGE_CHARS = 12_000

PLAIN_SYSTEM = """당신은 사실 검증을 돕는 조수입니다. 도구로 웹을 검색하고 페이지를 읽은 뒤 submit_answer로 답을 한 번 제출하세요."""

PLAIN_USER = """다음 주장을 사실 검증하세요.

판정은 셋 중 하나입니다.
- supported: 신뢰할 수 있는 근거가 주장을 지지한다
- refuted: 근거가 주장의 일부라도 틀렸음을 보여 준다 (수치·날짜·시간대·주체·범위 포함)
- not_enough_evidence: 판정할 근거가 부족하다

evidence_cutoff 이후에 나온 정보는 판정 근거로 쓰지 마세요.
판정 근거(justification)와 참고한 출처 URL(cited_sources)을 함께 내세요. 주장이 틀렸다면 correction에 정정 문장을 쓰세요.

주장 정보(JSON):
{claim}
"""

PLAIN_TOOLS = [
    {"type": "function", "function": {
        "name": "web_search", "description": "웹을 검색해 제목·URL·발행일·요약을 받는다.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch_page", "description": f"웹 페이지 본문을 앞 {PLAIN_PAGE_CHARS:,}자까지 읽는다.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "submit_answer", "description": "최종 판정을 제출하고 끝낸다.",
        "parameters": {"type": "object", "properties": {
            "verdict": {"type": "string", "enum": ["supported", "refuted", "not_enough_evidence"]},
            "justification": {"type": "string"},
            "cited_sources": {"type": "array", "items": {"type": "string"}},
            "correction": {"type": ["string", "null"]}},
            "required": ["verdict", "justification", "cited_sources"]}}},
]


def _plain_call(env, call, out: EpisodeOutcome) -> dict:
    args = call.arguments
    if "__invalid_json__" in args:
        out.invalid_tool_calls += 1
        return {"status": "invalid_input", "observation": "도구 인자가 올바른 JSON이 아닙니다."}
    try:
        if call.name == "web_search":
            res = env.call_tool("search_web", {"query": str(args.get("query") or "")})
            return {"status": res.get("status"), "results": res.get("observation")}
        if call.name == "fetch_page":
            url = str(args.get("url") or "")
            res = env.call_tool("fetch_url", {"url": url})
            doc = env.registry.fetched.get(url)
            if res.get("status") == "ok" and doc:
                return {"status": "ok", "url": url, "published_at": doc.get("published_at"),
                        "text": doc["text"][:PLAIN_PAGE_CHARS]}
            return {"status": res.get("status"), "observation": res.get("observation")}
        if call.name == "submit_answer":
            return env.call_tool("finish_verification", {
                "verdict": args.get("verdict"), "justification": args.get("justification"),
                "cited_evidence_ids": [str(u) for u in args.get("cited_sources") or []],
                "correction": args.get("correction"), "abstain": False,
                "stop_reason": "submitted"})
    except (ValueError, TypeError, KeyError) as exc:
        out.invalid_tool_calls += 1
        return {"status": "invalid_input", "observation": str(exc)}
    out.invalid_tool_calls += 1
    return {"status": "invalid_input", "observation": f"없는 도구: {call.name}"}


def run_plain_episode(env, client: ChatClient, claim_id: str, *, price: Price, budget: Budget,
                      max_turns: int = 20,
                      transcript: Callable[[list[dict]], None] | None = None) -> EpisodeOutcome:
    """One claim with a plain web agent; logged in the server's run log like the harness."""
    started = time.monotonic()
    payload = env.start_episode(claim_id)
    messages: list[dict] = [
        {"role": "system", "content": PLAIN_SYSTEM},
        {"role": "user", "content": PLAIN_USER.format(
            claim=json.dumps(payload["claim"], ensure_ascii=False, indent=2))},
    ]
    out = EpisodeOutcome(claim_id=claim_id, arm="C2P", execution_status=ExecutionStatus.OK.value)
    try:
        while out.turns < max_turns:
            budget.check()
            try:
                reply = client.complete(messages, PLAIN_TOOLS)
            except Exception as exc:
                return _fail(env, out, started, _status_for(exc), f"{type(exc).__name__}: {exc}",
                             messages, transcript)
            out.turns += 1
            usage = reply.usage or {}
            p, c, k = (int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)),
                       int(usage.get("cached_tokens", 0)))
            usd = price.cost(p, c, k)
            out.prompt_tokens, out.completion_tokens, out.cached_tokens = (
                out.prompt_tokens + p, out.completion_tokens + c, out.cached_tokens + k)
            out.cost_usd += usd
            budget.add(usd)
            messages.append(_history_message(reply))
            if not reply.tool_calls:
                out.nudges += 1
                if out.nudges > MAX_NUDGES:
                    return _fail(env, out, started, ExecutionStatus.PARSE_ERROR.value,
                                 "모델이 도구를 호출하지 않고 답을 끝냈습니다.", messages, transcript)
                messages.append({"role": "user", "content": "submit_answer 도구로 답을 제출하세요."})
                continue
            for call in reply.tool_calls:
                name = {"web_search": "search_web", "fetch_page": "fetch_url"}.get(call.name, call.name)
                out.tool_counts[name] = out.tool_counts.get(name, 0) + 1
                result = _plain_call(env, call, out)
                messages.append({"role": "tool", "tool_call_id": call.id, "name": call.name,
                                 "content": json.dumps(result, ensure_ascii=False)[:MAX_TOOL_RESULT_CHARS + 2000]})
                if result.get("status") == "finished":
                    out.finished = True
                    out.verdict = (result.get("result") or {}).get("verdict")
                    break
            if out.finished:
                out.duration_ms = int((time.monotonic() - started) * 1000)
                if transcript:
                    transcript(messages)
                return out
        return _fail(env, out, started, ExecutionStatus.BUDGET_EXCEEDED.value,
                     f"턴 한도({max_turns})에 도달했습니다.", messages, transcript)
    except BudgetExceeded as exc:
        _fail(env, out, started, ExecutionStatus.BUDGET_EXCEEDED.value, str(exc), messages, transcript)
        raise
