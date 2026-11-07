"""OpenAI-compatible chat client.

Works with any provider exposing /chat/completions (OpenAI, DashScope/Qwen,
OpenRouter, a local server) by setting base_url.

Two rules from the team docs are built in rather than left to the caller:

- No automatic retry. tools.md section 4 and AGENTS.md both forbid unlimited
  re-execution, and a silent retry would also corrupt the cost log. The client
  is constructed with max_retries=0 and a failed call surfaces as an exception
  that the loop records as PROVIDER_ERROR.
- No automatic model substitution. model_id is fixed for the run and recorded.

The price table is intentionally empty. AGENTS.md forbids inventing figures, so
cost stays unknown until the team enters real quotes with the date they were
taken. Unpriced calls are counted, and the runner reports them rather than
showing a cost of zero that would read as 'free'.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from task_a.loop import LLMResponse, ToolCall
from task_a.schema import Usage


@dataclass(frozen=True)
class Pricing:
    """USD per million tokens. `quoted_at` is part of the record (Q28)."""

    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None
    quoted_at: str = ""


#: Fill from an actual provider quote before reporting any cost figure.
PRICES: dict[str, Pricing] = {}


def estimate_cost(usage: Usage, pricing: Pricing | None) -> float | None:
    if pricing is None:
        return None
    billable_input = max(usage.input_tokens - usage.cached_tokens, 0)
    cost = (billable_input * pricing.input_per_million
            + usage.output_tokens * pricing.output_per_million) / 1_000_000
    if pricing.cached_input_per_million is not None:
        cost += (usage.cached_tokens * pricing.cached_input_per_million) / 1_000_000
    return cost


class OpenAICompatibleClient:
    """Implements the LLMClient protocol used by ReActAgent."""

    def __init__(
        self,
        model_id: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        max_tokens: int = 1024,
        pricing: Pricing | None = None,
        client=None,
        timeout: float = 120.0,
    ) -> None:
        self.model_id = model_id
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.pricing = pricing if pricing is not None else PRICES.get(model_id)
        self.unpriced_calls = 0
        self.calls = 0
        if client is not None:
            self._client = client
        else:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key or os.environ.get("TASK_A_API_KEY"),
                base_url=base_url or os.environ.get("TASK_A_BASE_URL"),
                timeout=timeout,
                max_retries=0,          # never retry silently
            )

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        kwargs = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if self.seed is not None:
            kwargs["seed"] = self.seed

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        usage = self._usage(response)

        cost = estimate_cost(usage, self.pricing)
        if cost is None:
            self.unpriced_calls += 1
        else:
            usage.cost_usd = cost

        message = choice.message
        return LLMResponse(
            content=message.content,
            tool_calls=[self._tool_call(tc) for tc in (message.tool_calls or [])],
            usage=usage)

    def _usage(self, response) -> Usage:
        raw = getattr(response, "usage", None)
        if raw is None:
            return Usage(llm_calls=1)
        details = getattr(raw, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", 0) or 0 if details else 0
        return Usage(
            input_tokens=getattr(raw, "prompt_tokens", 0) or 0,
            output_tokens=getattr(raw, "completion_tokens", 0) or 0,
            cached_tokens=cached,
            llm_calls=1)

    @staticmethod
    def _tool_call(raw) -> ToolCall:
        function = raw.function
        try:
            args = json.loads(function.arguments) if function.arguments else {}
        except json.JSONDecodeError:
            # Keep the raw text so the failure is visible instead of vanishing.
            args = {"_unparsed": function.arguments}
        if not isinstance(args, dict):
            args = {"_unparsed": args}
        return ToolCall(id=raw.id or "", name=function.name or "", args=args)

    def pricing_note(self) -> dict:
        return {"model_id": self.model_id,
                "pricing_available": self.pricing is not None,
                "pricing_quoted_at": self.pricing.quoted_at if self.pricing else None,
                "calls": self.calls,
                "unpriced_calls": self.unpriced_calls}
