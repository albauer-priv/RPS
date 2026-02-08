"""LiteLLM runtime adapter for Responses-like calls."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable
import json
import os
import re
import uuid

import litellm

from rps.core.config import normalize_agent_name


@dataclass(frozen=True)
class LLMProviderConfig:
    """Resolved provider configuration for a single agent."""

    api_key: str
    base_url: str | None
    org_id: str | None
    project_id: str | None


@dataclass
class LiteLLMResponse:
    """Minimal Responses-compatible response wrapper."""

    id: str
    output: list[dict[str, Any]]
    output_text: str | None
    usage: dict[str, Any] | None


def _agent_env_key(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", agent_name).strip("_")
    return cleaned.upper() or "AGENT"


def _resolve_env(base_key: str, agent_name: str | None) -> str | None:
    if agent_name:
        agent_key = _agent_env_key(agent_name)
        override = os.getenv(f"{base_key}_{agent_key}")
        if override:
            return override
    return os.getenv(base_key)


def resolve_provider_config(agent_name: str | None = None) -> LLMProviderConfig:
    """Resolve LiteLLM provider config with per-agent overrides."""
    api_key = _resolve_env("RPS_LLM_API_KEY", agent_name)
    if not api_key:
        raise RuntimeError("RPS_LLM_API_KEY is required")
    return LLMProviderConfig(
        api_key=api_key,
        base_url=_resolve_env("RPS_LLM_BASE_URL", agent_name),
        org_id=_resolve_env("RPS_LLM_ORG_ID", agent_name),
        project_id=_resolve_env("RPS_LLM_PROJECT_ID", agent_name),
    )


def _coerce_content(content: Any) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") in ("output_text", "text", "input_text"):
                    text = part.get("text")
                    if text:
                        parts.append(str(text))
                elif "text" in part:
                    parts.append(str(part.get("text")))
                else:
                    parts.append(str(part))
            else:
                parts.append(str(part))
        return "\n".join(p for p in parts if p)
    if content is None:
        return ""
    return str(content)


def _messages_from_input(input_items: Iterable[Any], instructions: str | None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if instructions:
        messages.append({"role": "system", "content": instructions})
    for item in input_items:
        if isinstance(item, dict) and "role" in item:
            messages.append({"role": item["role"], "content": _coerce_content(item.get("content"))})
            continue
        if isinstance(item, dict) and item.get("type") == "function_call_output":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.get("call_id"),
                    "content": _coerce_content(item.get("output")),
                }
            )
    return messages


def _tools_from_payload(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for tool in tools or []:
        if tool.get("type") != "function":
            continue
        name = tool.get("name")
        if not name:
            continue
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            }
        )
    return converted


def _tool_choice_from_payload(tool_choice: dict[str, Any] | str | None) -> dict[str, Any] | str | None:
    if not tool_choice:
        return None
    if isinstance(tool_choice, str):
        return tool_choice
    if tool_choice.get("type") == "function" and tool_choice.get("name"):
        return {"type": "function", "function": {"name": tool_choice["name"]}}
    return tool_choice


def _usage_from_response(response: Any) -> Any:
    usage = getattr(response, "usage", None) or (response.get("usage") if isinstance(response, dict) else None)
    if not usage:
        return SimpleNamespace(input_tokens=0, output_tokens=0, total_tokens=0)
    if isinstance(usage, dict):
        return SimpleNamespace(
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
    return SimpleNamespace(
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )


def _extract_choice(response: Any) -> Any:
    choices = response.get("choices") if isinstance(response, dict) else getattr(response, "choices", None)
    if not choices:
        return None
    return choices[0]


def _choice_message(choice: Any) -> Any:
    if isinstance(choice, dict):
        return choice.get("message")
    return getattr(choice, "message", None)


def _collect_tool_calls(message: Any) -> list[dict[str, Any]]:
    tool_calls = message.get("tool_calls") if isinstance(message, dict) else getattr(message, "tool_calls", None)
    if not tool_calls:
        return []
    calls: list[dict[str, Any]] = []
    for call in tool_calls:
        if isinstance(call, dict):
            func = call.get("function") or {}
            calls.append(
                {
                    "id": call.get("id") or str(uuid.uuid4()),
                    "name": func.get("name"),
                    "arguments": func.get("arguments") or "{}",
                }
            )
        else:
            func = getattr(call, "function", None)
            calls.append(
                {
                    "id": getattr(call, "id", str(uuid.uuid4())),
                    "name": getattr(func, "name", None) if func else None,
                    "arguments": getattr(func, "arguments", None) if func else "{}",
                }
            )
    return calls


def _build_output_items(text: str | None, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for call in tool_calls:
        output.append(
            {
                "type": "function_call",
                "name": call.get("name"),
                "arguments": call.get("arguments") or "{}",
                "call_id": call.get("id") or str(uuid.uuid4()),
            }
        )
    if text:
        output.append(
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        )
    return output


def _iter_stream_chunks(stream: Iterable[Any]) -> Iterable[tuple[str, list[dict[str, Any]]]]:
    tool_accumulator: dict[int, dict[str, Any]] = {}
    for chunk in stream:
        choice = _extract_choice(chunk)
        if not choice:
            continue
        delta = choice.get("delta") if isinstance(choice, dict) else getattr(choice, "delta", None)
        if not delta:
            continue
        text = delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", None)
        if text:
            yield text, []
        tool_calls = delta.get("tool_calls") if isinstance(delta, dict) else getattr(delta, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                idx = call.get("index", 0) if isinstance(call, dict) else getattr(call, "index", 0)
                entry = tool_accumulator.setdefault(
                    idx,
                    {"id": None, "name": None, "arguments": ""},
                )
                if isinstance(call, dict):
                    if call.get("id"):
                        entry["id"] = call.get("id")
                    func = call.get("function") or {}
                    if func.get("name"):
                        entry["name"] = func.get("name")
                    if func.get("arguments"):
                        entry["arguments"] += func.get("arguments") or ""
                else:
                    if getattr(call, "id", None):
                        entry["id"] = getattr(call, "id")
                    func = getattr(call, "function", None)
                    if func and getattr(func, "name", None):
                        entry["name"] = getattr(func, "name")
                    if func and getattr(func, "arguments", None):
                        entry["arguments"] += getattr(func, "arguments")
    tool_calls_out = []
    for idx in sorted(tool_accumulator):
        entry = tool_accumulator[idx]
        tool_calls_out.append(
            {
                "id": entry["id"] or str(uuid.uuid4()),
                "name": entry["name"],
                "arguments": entry["arguments"] or "{}",
            }
        )
    yield "", tool_calls_out


class _Unsupported:
    def __init__(self, name: str) -> None:
        self._name = name

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - defensive
        raise RuntimeError(f"{self._name}.{item} is not supported with LiteLLM runtime.")


class LiteLLMResponses:
    """Responses-like wrapper around LiteLLM chat completions."""

    def __init__(self, config: LLMProviderConfig, logger: Any | None = None) -> None:
        self._config = config
        self._logger = logger

    def create(self, **payload: Any):
        model = payload.get("model")
        if not model:
            raise RuntimeError("LiteLLM create requires model")
        input_items = payload.get("input") or []
        instructions = payload.get("instructions")
        messages = _messages_from_input(input_items, instructions)
        tools = _tools_from_payload(payload.get("tools"))
        tool_choice = _tool_choice_from_payload(payload.get("tool_choice"))
        temperature = payload.get("temperature")
        stream = bool(payload.get("stream"))
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "api_key": self._config.api_key,
            "api_base": self._config.base_url,
            "organization": self._config.org_id,
        }
        if self._config.project_id:
            kwargs["extra_body"] = {"project": self._config.project_id}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        if not stream:
            response = litellm.completion(**kwargs)
            choice = _extract_choice(response)
            message = _choice_message(choice) if choice else None
            text = None
            if message:
                text = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
            tool_calls = _collect_tool_calls(message or {})
            output_items = _build_output_items(text, tool_calls)
            return LiteLLMResponse(
                id=str(uuid.uuid4()),
                output=output_items,
                output_text=text,
                usage=_usage_from_response(response),
            )

        def _event_stream():
            stream_resp = litellm.completion(**kwargs)
            collected_text = ""
            collected_calls: list[dict[str, Any]] = []
            for text_delta, tool_calls in _iter_stream_chunks(stream_resp):
                if text_delta:
                    collected_text += text_delta
                    yield SimpleNamespace(type="response.output_text.delta", delta=text_delta)
                if tool_calls:
                    collected_calls = tool_calls
            for call in collected_calls:
                item = SimpleNamespace(
                    type="function_call",
                    name=call.get("name"),
                    arguments=call.get("arguments") or "{}",
                    call_id=call.get("id") or str(uuid.uuid4()),
                )
                yield SimpleNamespace(type="response.output_item.done", item=item)
            response_obj = LiteLLMResponse(
                id=str(uuid.uuid4()),
                output=_build_output_items(collected_text or None, collected_calls),
                output_text=collected_text or None,
                usage=SimpleNamespace(input_tokens=0, output_tokens=0, total_tokens=0),
            )
            yield SimpleNamespace(type="response.completed", response=response_obj)

        return _event_stream()

    def compact(self, **payload: Any):
        input_items = payload.get("input") or []
        model = payload.get("model")
        instructions = payload.get("instructions") or ""
        if not model:
            raise RuntimeError("LiteLLM compact requires model")
        compact_prompt = (
            "Summarize the following conversation for future context. "
            "Keep key facts, decisions, and open questions. "
            "Return a single concise assistant message."
        )
        messages = [
            {"role": "system", "content": compact_prompt},
            {"role": "user", "content": json.dumps(input_items, ensure_ascii=False)},
        ]
        compact_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "api_key": self._config.api_key,
            "api_base": self._config.base_url,
            "organization": self._config.org_id,
        }
        if self._config.project_id:
            compact_kwargs["extra_body"] = {"project": self._config.project_id}
        response = litellm.completion(**compact_kwargs)
        choice = _extract_choice(response)
        message = _choice_message(choice) if choice else None
        text = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
        output_items = _build_output_items(text, [])
        return LiteLLMResponse(
            id=str(uuid.uuid4()),
            output=output_items,
            output_text=text,
            usage=_usage_from_response(response),
        )

    def retrieve(self, response_id: str):  # pragma: no cover - compatibility
        raise RuntimeError("responses.retrieve is not supported with LiteLLM runtime.")


class LiteLLMClient:
    """Minimal client wrapper to emulate the OpenAI SDK surface."""

    def __init__(self, config: LLMProviderConfig, logger: Any | None = None) -> None:
        self._config = config
        self.responses = LiteLLMResponses(config, logger=logger)
        self.files = _Unsupported("files")
        self.containers = _Unsupported("containers")
        self.provider = "litellm"

    @property
    def config(self) -> LLMProviderConfig:
        return self._config
