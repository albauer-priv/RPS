"""Agent runner for standard tool-calling flows."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rps.openai.reasoning import build_reasoning_payload
from rps.openai.model_capabilities import supports_temperature
from rps.openai.response_utils import extract_reasoning_summaries, extract_text_output
from rps.openai.streaming import create_response
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.prompts.loader import PromptLoader
from rps.tools.workspace_tools import ToolContext, get_tool_defs, get_tool_handlers
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for running an agent."""
    client: Any
    model: str
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    max_completion_tokens: int | None
    prompt_loader: PromptLoader
    vs_resolver: VectorStoreResolver


def _parse_csv_env(name: str) -> set[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _build_web_search_tool() -> dict[str, Any]:
    tool: dict[str, Any] = {
        "type": "web_search",
        "user_location": {
            "type": "approximate",
            "country": "US",
            "timezone": "America/New_York",
            "region": "United States",
        },
    }
    allowed_domains = [
        dom for dom in os.getenv("RPS_LLM_WEB_SEARCH_ALLOWED_DOMAINS", "").split(",") if dom.strip()
    ]
    if allowed_domains:
        tool["filters"] = {"allowed_domains": [dom.strip() for dom in allowed_domains]}
    context_size = os.getenv("RPS_LLM_WEB_SEARCH_CONTEXT_SIZE", "").strip().lower()
    if context_size in {"low", "medium", "high"}:
        tool.setdefault("filters", {})["search_context_size"] = context_size
    external_access_raw = os.getenv("RPS_LLM_WEB_SEARCH_EXTERNAL_ACCESS")
    if external_access_raw is not None:
        tool["external_web_access"] = external_access_raw.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    return tool


def _web_search_enabled(agent_name: str) -> bool:
    if not _env_flag("RPS_LLM_ENABLE_WEB_SEARCH"):
        return False
    agents = _parse_csv_env("RPS_LLM_WEB_SEARCH_AGENTS")
    if agents and agent_name.lower() not in agents:
        return False
    return True


def _item_type(item: Any) -> Optional[str]:
    """Return the type field for response output items."""
    if isinstance(item, dict):
        return item.get("type")
    return getattr(item, "type", None)


def _item_field(item: Any, name: str) -> Any:
    """Safely read a field from a response output item."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _log_knowledge_search(response: Any) -> None:
    """Log knowledge_search calls when available."""
    items = getattr(response, "output", []) or []
    calls = [
        item
        for item in items
        if _item_type(item) == "function_call" and _item_field(item, "name") == "knowledge_search"
    ]
    if not calls:
        logger.info("knowledge_search calls: none")
        return
    for idx, item in enumerate(calls, start=1):
        logger.info(
            "knowledge_search[%d] args=%s",
            idx,
            _item_field(item, "arguments"),
        )


def _make_run_id(agent_name: str) -> str:
    """Generate a stable run identifier for artifact metadata."""
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in agent_name).strip("_")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{slug or 'agent'}_{stamp}"


def _parse_int(value: str | None) -> int | None:
    """Parse an int from env, returning None on invalid input."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None

def _env_flag(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return False
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}


def run_agent(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    agent_vs_name: str,
    athlete_id: str,
    user_input: str,
    workspace_root: Path,
    schema_dir: Path,
    model_override: str | None = None,
    temperature_override: float | None = None,
    include_debug_file_search: bool = False,
    force_file_search: bool = True,
    max_num_results: int | None = None,
    run_id: str | None = None,
) -> str:
    """Run an agent with workspace tools and file search attached."""
    result = run_agent_session(
        runtime,
        agent_name=agent_name,
        agent_vs_name=agent_vs_name,
        athlete_id=athlete_id,
        user_input=user_input,
        workspace_root=workspace_root,
        schema_dir=schema_dir,
        model_override=model_override,
        temperature_override=temperature_override,
        include_debug_file_search=include_debug_file_search,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
        run_id=run_id,
    )
    return result["text"]


def run_agent_session(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    agent_vs_name: str,
    athlete_id: str,
    user_input: str,
    workspace_root: Path,
    schema_dir: Path,
    model_override: str | None = None,
    temperature_override: float | None = None,
    include_debug_file_search: bool = False,
    force_file_search: bool = True,
    max_num_results: int | None = None,
    run_id: str | None = None,
    previous_response_id: str | None = None,
    injection_text: str | None = None,
    stream_handlers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run an agent and return both the text output and response id.

    This variant supports session-style chaining via `previous_response_id`
    and optional runtime knowledge injection into the system prompt.
    """
    model = model_override or runtime.model
    temperature = temperature_override if temperature_override is not None else runtime.temperature
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)
    effective_run_id = run_id or _make_run_id(agent_name)

    logger.info(
        "Run agent=%s model=%s athlete=%s run_id=%s",
        agent_name,
        model,
        athlete_id,
        effective_run_id,
    )

    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)
    if injection_text:
        system_prompt = f"{system_prompt}\n\n{injection_text}"

    if agent_name == "coach":
        read_ctx = ReadToolContext(
            athlete_id=athlete_id,
            workspace_root=workspace_root,
        )
        tool_defs = read_tool_defs()
        tool_handlers = read_tool_handlers(read_ctx)
    else:
        tool_ctx = ToolContext(
            athlete_id=athlete_id,
            agent_name=agent_name,
            workspace_root=workspace_root,
            schema_dir=schema_dir,
            run_id=effective_run_id,
        )
        tool_defs = get_tool_defs()
        tool_handlers = get_tool_handlers(tool_ctx)

    if max_num_results is None:
        max_num_results = _parse_int(os.getenv("RPS_LLM_FILE_SEARCH_MAX_RESULTS")) or 20
    tools: list[dict[str, Any]] = []
    web_search_enabled = _web_search_enabled(agent_name)
    if web_search_enabled:
        tools.append(_build_web_search_tool())
    tools += tool_defs
    debug_knowledge_search = (
        include_debug_file_search
        or _env_flag("RPS_LLM_DEBUG")
        or logger.isEnabledFor(logging.DEBUG)
    )
    logger.info(
        "tools: agent=%s stores=%s max_results=%s web_search=%s",
        agent_name,
        [agent_vs_id],
        max_num_results,
        web_search_enabled,
    )

    input_list: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    force_search = force_file_search
    previous_id_for_request = previous_response_id

    def _create_response(force_search_flag: bool):
        payload: dict[str, Any] = {
            "model": model,
            "tools": tools,
            "input": input_list,
        }
        if previous_id_for_request:
            payload["previous_response_id"] = previous_id_for_request
        reasoning = build_reasoning_payload(
            model,
            runtime.reasoning_effort,
            runtime.reasoning_summary,
        )
        if reasoning:
            payload["reasoning"] = reasoning
        if force_search_flag:
            payload["tool_choice"] = {"type": "function", "name": "knowledge_search"}
    if temperature is not None and supports_temperature(model):
        payload["temperature"] = temperature
    if runtime.max_completion_tokens is not None:
        payload["max_completion_tokens"] = runtime.max_completion_tokens
        if debug_knowledge_search:
            logger.info(
                "responses.create: tool_choice=%s tools=%d",
                payload.get("tool_choice"),
                len(payload.get("tools") or []),
            )
        return create_response(runtime.client, payload, logger, stream_handlers=stream_handlers)

    seen_summaries: set[str] = set()
    response = _create_response(force_search)
    previous_id_for_request = None
    last_text = response.output_text or extract_text_output(response) or ""
    if debug_knowledge_search:
        _log_knowledge_search(response)
    for summary in extract_reasoning_summaries(response):
        if summary in seen_summaries:
            continue
        seen_summaries.add(summary)
        logger.info("Reasoning summary: %s", summary)
    input_list += response.output
    force_search = False

    safety_counter = 0
    while True:
        safety_counter += 1
        if safety_counter > 20:
            raise RuntimeError("Too many tool call iterations; aborting.")

        function_calls = [item for item in response.output if _item_type(item) == "function_call"]
        if not function_calls:
            break

        for call in function_calls:
            name = _item_field(call, "name")
            args_raw = _item_field(call, "arguments") or "{}"
            call_id = _item_field(call, "call_id")
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {}

            logger.debug("Tool call %s args=%s", name, args)

            if name not in tool_handlers:
                result = {"ok": False, "error": f"Unknown tool: {name}"}
            else:
                try:
                    result = tool_handlers[name](args)
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}

            if isinstance(result, dict) and not result.get("ok", True):
                logger.warning("Tool %s failed: %s", name, result)
            else:
                logger.debug("Tool %s result: %s", name, result)

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

        response = _create_response(force_search)
        if response.output_text:
            last_text = response.output_text
        else:
            text_out = extract_text_output(response)
            if text_out:
                last_text = text_out
        if debug_knowledge_search:
            _log_knowledge_search(response)
        for summary in extract_reasoning_summaries(response):
            if summary in seen_summaries:
                continue
            seen_summaries.add(summary)
            logger.info("Reasoning summary: %s", summary)
        input_list += response.output

    logger.debug("Agent output: %s", response.output_text)
    text = response.output_text or last_text or "[no text output]"
    return {
        "text": text,
        "response_id": getattr(response, "id", None),
        "response": response,
    }
