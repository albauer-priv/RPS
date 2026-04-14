"""Strict tool-calling runner for single-output tasks."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.openai.litellm_runtime import LiteLLMClient, LiteLLMResponse
from rps.openai.model_capabilities import supports_temperature
from rps.openai.reasoning import build_reasoning_payload
from rps.openai.response_utils import extract_reasoning_summaries
from rps.openai.streaming import create_response
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.prompts.loader import PromptLoader
from rps.schemas.bundler import SchemaBundler
from rps.tools.knowledge_search import search_knowledge
from rps.tools.store_output_tools import build_strict_store_tool
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.schema_registry import SchemaValidationError

logger = logging.getLogger(__name__)

ToolDef = dict[str, object]
StrictTaskResult = dict[str, object]


@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for strict agent runs."""
    client: LiteLLMClient
    model: str
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    max_completion_tokens: int | None
    prompt_loader: PromptLoader
    vs_resolver: VectorStoreResolver
    schema_dir: Path
    workspace_root: Path


def _item_type(item: object) -> str | None:
    """Return the type field for response output items."""
    value = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
    return value if isinstance(value, str) else None


def _item_field(item: object, name: str) -> object | None:
    """Safely read a field from a response output item."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _knowledge_search_tool() -> ToolDef:
    """Build a knowledge_search tool payload for Responses API."""
    return {
        "type": "function",
        "name": "knowledge_search",
        "description": "Search the local knowledge vectorstore for relevant context.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    }


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


def _log_knowledge_search(response: LiteLLMResponse) -> None:
    items = getattr(response, "output", []) or []
    calls = [
        item
        for item in items
        if _item_type(item) == "function_call" and _item_field(item, "name") == "knowledge_search"
    ]
    if not calls:
        logger.info("knowledge_search calls: none")
        return
    logger.info("knowledge_search calls: %d", len(calls))

def run_agent_task_strict(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    agent_vs_name: str,
    athlete_id: str,
    task: AgentTask,
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    force_file_search: bool = True,
    max_num_results: int | None = None,
) -> StrictTaskResult:
    """Run one strict task and persist the resulting artifact."""
    output_spec = OUTPUT_SPECS[task]

    model = model_override or runtime.model
    temperature = temperature_override if temperature_override is not None else runtime.temperature
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)

    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)

    bundler = SchemaBundler(runtime.schema_dir)
    store_tool = build_strict_store_tool(bundler, output_spec)

    if max_num_results is None:
        max_num_results = _parse_int(os.getenv("RPS_LLM_FILE_SEARCH_MAX_RESULTS")) or 6
    debug_file_search = _env_flag("RPS_LLM_DEBUG") or logger.isEnabledFor(logging.DEBUG)

    tools: list[ToolDef] = [
        _knowledge_search_tool(),
        store_tool,
    ]
    logger.info(
        "knowledge_search tool: agent=%s stores=%s max_results=%s",
        agent_name,
        [agent_vs_id],
        max_num_results,
    )

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )

    input_list: list[dict[str, object]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    def _create_response(force_search_flag: bool) -> LiteLLMResponse:
        payload: dict[str, object] = {
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
        if force_search_flag:
            payload["tool_choice"] = {"type": "function", "name": "knowledge_search"}
        if temperature is not None and supports_temperature(model):
            payload["temperature"] = temperature
        if runtime.max_completion_tokens is not None:
            payload["max_completion_tokens"] = runtime.max_completion_tokens
        return create_response(runtime.client, payload, logger)

    force_search = force_file_search
    seen_summaries: set[str] = set()
    response = _create_response(force_search)
    if debug_file_search:
        _log_knowledge_search(response)
    for summary in extract_reasoning_summaries(response):
        if summary in seen_summaries:
            continue
        seen_summaries.add(summary)
        logger.info("Reasoning summary: %s", summary)
    input_list += response.output
    force_search = False

    safety = 0
    while True:
        safety += 1
        if safety > 10:
            raise RuntimeError("Too many tool iterations")

        function_calls = [
            item for item in response.output if _item_type(item) == "function_call"
        ]
        if not function_calls:
            output_text = response.output_text or ""
            return {
                "ok": False,
                "error": "Model did not call store tool. Output:\n" + output_text,
            }

        handled_any = False
        for call in function_calls:
            call_name = _item_field(call, "name")
            call_args = _item_field(call, "arguments")
            call_id = _item_field(call, "call_id")
            if not isinstance(call_name, str):
                continue
            if not isinstance(call_id, str):
                continue

            if call_name == "knowledge_search":
                try:
                    args = json.loads(call_args) if isinstance(call_args, str) else {}
                except json.JSONDecodeError:
                    args = {}
                results = search_knowledge(
                    agent_name,
                    str(args.get("query", "")),
                    max_results=args.get("max_results", 5),
                    tags=args.get("tags"),
                )
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps({"ok": True, "results": results}, ensure_ascii=False),
                    }
                )
                handled_any = True
                continue

            if call_name != output_spec.tool_name:
                continue

            handled_any = True
            args = json.loads(call_args) if isinstance(call_args, str) else {}
            document = args if output_spec.envelope else args.get("workouts")
            logger.debug("Tool call %s args=%s", call_name, args)

            try:
                if output_spec.envelope and not (
                    isinstance(document, dict) and "meta" in document and "data" in document
                ):
                    result = {
                        "ok": False,
                        "error": "Envelope artefact must be an object with meta and data",
                        "details": [
                            "Expected top-level keys: meta, data",
                            "Do not wrap the envelope inside payload/document/envelope keys",
                        ],
                    }
                    input_list.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result, ensure_ascii=False),
                        }
                    )
                    return result
                result = guarded.guard_put_validated(
                    output_spec=output_spec,
                    document=document,
                    run_id=run_id,
                    producer_agent=agent_name,
                    update_latest=True,
                )
            except SchemaValidationError as exc:
                details = list(exc.errors or [])
                max_items = 8
                preview = details[:max_items]
                suffix = ""
                if len(details) > max_items:
                    suffix = f" (+{len(details) - max_items} more)"
                summary = "; ".join(preview) + suffix if preview else "Unknown schema error."
                result = {
                    "ok": False,
                    "error": f"Schema validation failed ({output_spec.artifact_type.value}): {summary}",
                    "details": details,
                }
                logger.warning("Schema validation failed for %s: %s", output_spec.artifact_type.value, details)
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
                logger.warning("Store failed for %s: %s", output_spec.artifact_type.value, exc)

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

            return result

        if not handled_any:
            output_text = response.output_text or ""
            return {
                "ok": False,
                "error": "Model did not call knowledge_search or store tool. Output:\n" + output_text,
            }

        response = _create_response(force_search)
        for summary in extract_reasoning_summaries(response):
            if summary in seen_summaries:
                continue
            seen_summaries.add(summary)
            logger.info("Reasoning summary: %s", summary)
        input_list += response.output
