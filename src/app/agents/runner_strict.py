"""Strict tool-calling runner for single-output tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.agents.tasks import AgentTask, OUTPUT_SPECS
from app.openai.vectorstore_state import VectorStoreResolver
from app.prompts.loader import PromptLoader
from app.schemas.bundler import SchemaBundler
from app.tools.store_output_tools import build_strict_store_tool
from app.workspace.guarded_store import GuardedValidatedStore


@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for strict agent runs."""
    client: OpenAI
    model: str
    temperature: float | None
    prompt_loader: PromptLoader
    vs_resolver: VectorStoreResolver
    shared_vs_name: str
    schema_dir: Path
    workspace_root: Path


def _file_search_tool(shared_vs_id: str, agent_vs_id: str, max_num_results: int) -> dict[str, Any]:
    """Build a file_search tool payload for Responses API."""
    return {
        "type": "file_search",
        "vector_store_ids": [shared_vs_id, agent_vs_id],
        "max_num_results": max_num_results,
    }


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
    max_num_results: int = 6,
) -> dict[str, Any]:
    """Run one strict task and persist the resulting artifact."""
    output_spec = OUTPUT_SPECS[task]

    model = model_override or runtime.model
    temperature = temperature_override if temperature_override is not None else runtime.temperature
    shared_vs_id = runtime.vs_resolver.id_for_store_name(runtime.shared_vs_name)
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)

    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)

    bundler = SchemaBundler(runtime.schema_dir)
    store_tool = build_strict_store_tool(bundler, output_spec)

    tools = [
        _file_search_tool(shared_vs_id, agent_vs_id, max_num_results),
        store_tool,
    ]

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )

    input_list: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    def _create_response(force_search_flag: bool):
        payload: dict[str, Any] = {
            "model": model,
            "tools": tools,
            "input": input_list,
        }
        if force_search_flag:
            payload["tool_choice"] = {"type": "file_search"}
        if temperature is not None:
            payload["temperature"] = temperature
        return runtime.client.responses.create(**payload)

    force_search = force_file_search
    response = _create_response(force_search)
    input_list += response.output
    force_search = False

    safety = 0
    while True:
        safety += 1
        if safety > 10:
            raise RuntimeError("Too many tool iterations")

        function_calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
        if not function_calls:
            return {
                "ok": False,
                "error": "Model did not call store tool. Output:\n" + response.output_text,
            }

        for call in function_calls:
            if call.name != output_spec.tool_name:
                continue

            args = json.loads(call.arguments or "{}")
            document = args if output_spec.envelope else args.get("workouts")

            try:
                result = guarded.guard_put_validated(
                    output_spec=output_spec,
                    document=document,
                    run_id=run_id,
                    producer_agent=agent_name,
                    update_latest=True,
                )
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

            return result

        response = _create_response(force_search)
        input_list += response.output
