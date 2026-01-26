"""Agent runner for standard tool-calling flows."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from app.openai.reasoning import build_reasoning_payload
from app.openai.model_capabilities import supports_temperature
from app.openai.response_utils import (
    extract_file_search_results,
    extract_reasoning_summaries,
    extract_text_output,
)
from app.openai.streaming import create_response
from app.openai.vectorstore_state import VectorStoreResolver
from app.prompts.loader import PromptLoader
from app.tools.workspace_tools import ToolContext, get_tool_defs, get_tool_handlers

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for running an agent."""
    client: OpenAI
    model: str
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    prompt_loader: PromptLoader
    vs_resolver: VectorStoreResolver
    shared_vs_name: str


def _build_file_search_tool(shared_vs_id: str, agent_vs_id: str, max_num_results: int) -> dict[str, Any]:
    """Build a file_search tool payload for Responses API."""
    return {
        "type": "file_search",
        "vector_store_ids": [shared_vs_id, agent_vs_id],
        "max_num_results": max_num_results,
    }


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


def _log_file_search_results(response: Any) -> None:
    """Log file_search results for debugging."""
    results = extract_file_search_results(response)
    if not results:
        logger.info("file_search results: none")
        return
    logger.info("file_search results: %d", len(results))
    for idx, result in enumerate(results, start=1):
        logger.info(
            "file_search[%d] file=%s score=%s attrs=%s",
            idx,
            result.get("filename"),
            result.get("score"),
            result.get("attributes"),
        )


def _make_run_id(agent_name: str) -> str:
    """Generate a stable run identifier for artifact metadata."""
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in agent_name).strip("_")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{slug or 'agent'}_{stamp}"


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
    max_num_results: int = 20,
    run_id: str | None = None,
) -> str:
    """Run an agent with workspace tools and file search attached."""
    model = model_override or runtime.model
    temperature = temperature_override if temperature_override is not None else runtime.temperature
    shared_vs_id = runtime.vs_resolver.id_for_store_name(runtime.shared_vs_name)
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

    tool_ctx = ToolContext(
        athlete_id=athlete_id,
        agent_name=agent_name,
        workspace_root=workspace_root,
        schema_dir=schema_dir,
        run_id=effective_run_id,
    )
    tool_defs = get_tool_defs()
    tool_handlers = get_tool_handlers(tool_ctx)

    tools = [_build_file_search_tool(shared_vs_id, agent_vs_id, max_num_results)] + tool_defs

    include = ["file_search_call.results"] if include_debug_file_search else None

    input_list: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    force_search = force_file_search
    def _create_response(force_search_flag: bool):
        payload: dict[str, Any] = {
            "model": model,
            "tools": tools,
            "input": input_list,
        }
        reasoning = build_reasoning_payload(
            model,
            runtime.reasoning_effort,
            runtime.reasoning_summary,
        )
        if reasoning:
            payload["reasoning"] = reasoning
        if include is not None:
            payload["include"] = include
        if force_search_flag:
            payload["tool_choice"] = {"type": "file_search"}
        if temperature is not None and supports_temperature(model):
            payload["temperature"] = temperature
        return create_response(runtime.client, payload, logger)

    seen_summaries: set[str] = set()
    response = _create_response(force_search)
    last_text = response.output_text or extract_text_output(response) or ""
    if include_debug_file_search:
        _log_file_search_results(response)
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
        if include_debug_file_search:
            _log_file_search_results(response)
        for summary in extract_reasoning_summaries(response):
            if summary in seen_summaries:
                continue
            seen_summaries.add(summary)
            logger.info("Reasoning summary: %s", summary)
        input_list += response.output

    logger.debug("Agent output: %s", response.output_text)
    return response.output_text or last_text
