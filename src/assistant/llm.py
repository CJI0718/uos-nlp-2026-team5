"""Chat clients: an OpenAI-compatible HTTP client (Mistral by default) and a scripted fake.

No call is retried: a failed request raises LLMError and the run records it.
The API key is read from the environment at call time and never logged.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Protocol


class LLMError(RuntimeError):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw_arguments: str = ""


@dataclass
class ChatReply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict = field(default_factory=dict)   # prompt_tokens, completion_tokens, cached_tokens
    #: The assistant message to append to the conversation unchanged.
    message: dict = field(default_factory=dict)


class ChatClient(Protocol):
    model: str
    live: bool

    def complete(self, messages: list[dict], tools: list[dict] | None = None,
                 json_mode: bool = False) -> ChatReply: ...


def _parse_arguments(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"__invalid_json__": str(raw)[:500]}
    return value if isinstance(value, dict) else {"__invalid_json__": str(raw)[:500]}


def parse_reply(data: dict) -> ChatReply:
    """Parse an OpenAI-style chat completion response."""
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"응답 형식을 해석할 수 없음: {str(data)[:200]}") from exc
    calls = []
    for i, call in enumerate(message.get("tool_calls") or []):
        fn = call.get("function") or {}
        raw = fn.get("arguments")
        calls.append(ToolCall(id=call.get("id") or f"call_{i}", name=fn.get("name") or "",
                              arguments=_parse_arguments(raw),
                              raw_arguments=raw if isinstance(raw, str) else json.dumps(raw)))
    usage = data.get("usage") or {}
    details = usage.get("prompt_tokens_details") or {}
    clean = {"role": "assistant", "content": message.get("content") or ""}
    if message.get("tool_calls"):
        clean["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.name, "arguments": c.raw_arguments or json.dumps(c.arguments)}}
            for c in calls]
    return ChatReply(
        content=message.get("content") or "",
        tool_calls=calls,
        usage={"prompt_tokens": int(usage.get("prompt_tokens") or 0),
               "completion_tokens": int(usage.get("completion_tokens") or 0),
               "cached_tokens": int(details.get("cached_tokens") or 0)},
        message=clean,
    )


Transport = Callable[[str, dict, dict, float], dict]


def _http_post(url: str, headers: dict, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers,
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise LLMError(f"HTTP {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LLMError(f"연결 실패: {exc}") from None


class OpenAICompatClient:
    """POST {base_url}/chat/completions with tools (Mistral, DeepSeek and similar)."""

    live = True

    def __init__(self, base_url: str, model: str, api_key_env: str = "MISTRAL_API_KEY",
                 timeout_s: float = 60, transport: Transport | None = None,
                 max_tokens: int = 2048, temperature: float | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens
        self.temperature = temperature   # None: the provider default, not sent
        self._transport = transport or _http_post

    def complete(self, messages, tools=None, json_mode=False) -> ChatReply:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise LLMError(f"{self.api_key_env}가 설정되지 않았습니다(.env 또는 환경변수).")
        body: dict = {"model": self.model, "messages": messages, "max_tokens": self.max_tokens}
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
            body["parallel_tool_calls"] = False   # one step at a time, like the experiments
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        return parse_reply(self._transport(f"{self.base_url}/chat/completions", headers, body,
                                           self.timeout_s))


class ScriptedClient:
    """A fake model: `responder(messages, tools, json_mode)` returns the next ChatReply."""

    live = False

    def __init__(self, responder: Callable[[list, list | None, bool], ChatReply],
                 model: str = "scripted") -> None:
        self.responder = responder
        self.model = model

    def complete(self, messages, tools=None, json_mode=False) -> ChatReply:
        reply = self.responder(messages, tools, json_mode)
        if not reply.message:
            reply.message = {"role": "assistant", "content": reply.content}
            if reply.tool_calls:
                reply.message["tool_calls"] = [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}}
                    for c in reply.tool_calls]
        return reply


def cost_usd(usage: dict, llm_settings: dict) -> float:
    """Cost from token usage and the price table in settings (USD per 1M tokens)."""
    prompt = usage.get("prompt_tokens", 0)
    cached = min(usage.get("cached_tokens", 0), prompt)
    out = usage.get("completion_tokens", 0)
    return ((prompt - cached) * llm_settings["price_input"]
            + cached * llm_settings.get("price_cached_input", llm_settings["price_input"])
            + out * llm_settings["price_output"]) / 1_000_000


def client_from_settings(llm_settings: dict) -> OpenAICompatClient:
    return OpenAICompatClient(llm_settings["base_url"], llm_settings["model"],
                              llm_settings.get("api_key_env", "MISTRAL_API_KEY"),
                              llm_settings.get("timeout_s", 60))
