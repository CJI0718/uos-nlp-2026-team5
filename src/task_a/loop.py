"""The ReAct loop.

This is the agent: the model picks the next tool from the observation, and
decides when to stop. Nothing here hardcodes a search-then-answer sequence.

Q19-6: '요청별 messages를 새로 구성한다.' Each episode starts from a fresh
message list, so no state carries across claims.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Protocol

from task_a.schema import (
    AgentResult, Claim, ExecutionStatus, ToolEvent, ToolStatus, Usage, Verdict,
)
from task_a.tools import FINISH_SCHEMA, ToolRegistry

SYSTEM_PROMPT = """\
너는 원자적 주장(atomic claim) 하나를 검증하는 팩트체크 에이전트다.

행동 규칙
1. 주장을 주체·관계·대상·시점으로 분해하고, 판정에 필요한 결정적 사실을 먼저 특정한다.
2. search_evidence로 고정 코퍼스에서 근거를 찾는다. 필요하면 read_evidence로 본문을 확인한다.
   결정적 근거는 원발표 기관의 영어 원문인 경우가 많다. 한국어 질의로 결정적 사실을 담은 문서를
   찾지 못했다면, 같은 내용을 영어 질의로 다시 검색한다. 검색어가 없다고 결론 짓기 전에
   최소 두 언어로 시도한다.
3. 수치·단위·시간대·비율 판단은 반드시 calculate_comparison을 사용한다. 암산하지 않는다.
4. 코퍼스에서 결정적 근거가 없거나 문서끼리 충돌하면 search_web / fetch_url로 외부 검증을 시도한다.
   여러 문서가 같은 내용을 반복해도 출처가 하나(같은 보도자료 전재)면 독립 근거가 아니다.
5. 근거가 충분해지면 finish_verification으로 종료한다. 충분하지 않으면 추측하지 말고
   abstain=true로 종료한다. 도구가 실패한 것과 근거가 부족한 것은 다르다.

금지
- 정답을 미리 가정하고 근거를 끼워 맞추지 않는다.
- 도구 결과를 조작하거나 인용하지 않은 문서를 인용 목록에 넣지 않는다.
- 판정 라벨은 supported / refuted / not_enough_evidence 중 하나다.
"""

FINISH_TOOL = "finish_verification"


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


class LLMClient(Protocol):
    model_id: str

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


@dataclass
class Budget:
    max_steps: int = 8
    max_tool_calls: int = 12
    max_external_calls: int = 4

    def exceeded(self, steps: int, tool_calls: int, external_calls: int) -> str | None:
        if steps >= self.max_steps:
            return f"max_steps {self.max_steps}"
        if tool_calls >= self.max_tool_calls:
            return f"max_tool_calls {self.max_tool_calls}"
        if external_calls >= self.max_external_calls:
            return f"max_external_calls {self.max_external_calls}"
        return None


class ReActAgent:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        budget: Budget | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.budget = budget or Budget()
        self.system_prompt = system_prompt

    def run(self, claim: Claim) -> AgentResult:
        started = time.monotonic()
        messages = self._initial_messages(claim)
        tools = self.registry.schemas + [{
            "type": "function",
            "function": {"name": FINISH_TOOL,
                         "description": "검증을 끝내고 최종 판정을 제출한다. 반드시 마지막으로 호출한다.",
                         "parameters": FINISH_SCHEMA},
        }]

        events: list[ToolEvent] = []
        usage = Usage()
        tool_calls = external_calls = 0

        for step in range(1, self.budget.max_steps + 1):
            over = self.budget.exceeded(step - 1, tool_calls, external_calls)
            if over:
                return self._fail(claim, events, usage, step, started,
                                  ExecutionStatus.BUDGET_EXCEEDED, f"예산 소진: {over}")

            response = self._complete(messages, tools)
            if response is None:
                return self._fail(claim, events, usage, step, started,
                                  ExecutionStatus.PROVIDER_ERROR, "LLM 호출 실패")
            usage.add(response.usage)

            if not response.tool_calls:
                # Model answered in prose instead of calling finish_verification.
                parsed = _parse_finish(response.content)
                if parsed is None:
                    return self._fail(claim, events, usage, step, started,
                                      ExecutionStatus.PARSE_ERROR,
                                      "finish_verification 없이 종료")
                return self._finish(claim, parsed, events, usage, step, started)

            for call in response.tool_calls:
                if call.name == FINISH_TOOL:
                    return self._finish(claim, call.args, events, usage, step, started)

                tool_calls += 1
                t0 = time.monotonic()
                result, is_external = self.registry.call(call.name, call.args)
                elapsed = int((time.monotonic() - t0) * 1000)
                if is_external:
                    external_calls += 1
                    usage.external_calls += 1

                events.append(ToolEvent(
                    step=step, tool=call.name, args=call.args, status=result.status,
                    observation_chars=len(result.observation), elapsed_ms=elapsed,
                    evidence_ids=result.evidence_ids, ranks=result.ranks,
                    rendered_snippet_ids=result.evidence_ids,
                    corruption_flags=result.payload.get("misleading_ids", []),
                    external=is_external))
                usage.tool_calls += 1

                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": result.observation})

        return self._fail(claim, events, usage, self.budget.max_steps, started,
                          ExecutionStatus.BUDGET_EXCEEDED, "max_steps 도달")

    # -- internals ---------------------------------------------------------

    def _initial_messages(self, claim: Claim) -> list[dict]:
        parts = [f"검증할 주장: {claim.text}"]
        if claim.target_period:
            parts.append(f"주장 대상 기간·버전: {claim.target_period}")
        if claim.evidence_cutoff:
            parts.append(f"근거 허용 시점: {claim.evidence_cutoff}")
        if claim.input_body:
            parts.append(f"\n원문 입력:\n{claim.input_body}")
        return [{"role": "system", "content": self.system_prompt},
                {"role": "user", "content": "\n".join(parts)}]

    def _complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse | None:
        """No automatic retry. A failed call is recorded, not silently repeated."""
        try:
            return self.llm.complete(messages, tools)
        except Exception:
            return None

    def _finish(self, claim, args, events, usage, step, started) -> AgentResult:
        verdict_raw = (args or {}).get("verdict")
        try:
            verdict = Verdict(verdict_raw) if verdict_raw else None
        except ValueError:
            verdict = None
        cited = [c for c in (args or {}).get("cited_evidence_ids") or [] if isinstance(c, str)]
        justification = str((args or {}).get("justification") or "")
        if verdict is None or not justification:
            return self._fail(claim, events, usage, step, started,
                              ExecutionStatus.PARSE_ERROR, "finish_verification 스키마 불충분")
        usage.elapsed_ms = int((time.monotonic() - started) * 1000)
        return AgentResult(
            claim_id=claim.claim_id, verdict=verdict,
            abstain=bool((args or {}).get("abstain", False)),
            cited_evidence_ids=cited, justification=justification,
            correction=(args or {}).get("correction"),
            stop_reason=str((args or {}).get("stop_reason") or "unspecified"),
            execution_status=ExecutionStatus.OK, events=events, usage=usage, steps=step)

    def _fail(self, claim, events, usage, step, started, status, reason) -> AgentResult:
        usage.elapsed_ms = int((time.monotonic() - started) * 1000)
        return AgentResult(
            claim_id=claim.claim_id, verdict=None, abstain=False,
            cited_evidence_ids=[], justification="", correction=None,
            stop_reason=reason, execution_status=status,
            events=events, usage=usage, steps=step, error=reason)


def _parse_finish(content: str | None) -> dict | None:
    """Salvage a JSON object from prose when the model skips the tool call."""
    if not content:
        return None
    match = None
    for opener, closer in (("{", "}"), ("```json", "```")):
        start = content.find(opener)
        if start != -1:
            end = content.rfind(closer)
            if end > start:
                match = content[start + len(opener) - 1 if opener == "```json" else start:end + 1]
                break
    if match is None:
        return None
    try:
        data = json.loads(match)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
