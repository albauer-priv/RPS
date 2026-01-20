"""Strict tool-calling runner for multi-output tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.agents.tasks import AgentTask, OUTPUT_SPECS, OutputSpec
from app.openai.vectorstore_state import VectorStoreResolver
from app.prompts.loader import PromptLoader
from app.schemas.bundler import SchemaBundler
from app.tools.store_output_tools import build_strict_store_tool
from app.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from app.workspace.guarded_store import GuardedValidatedStore


@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for multi-output agent runs."""
    client: OpenAI
    model: str
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


def _item_type(item: Any) -> str | None:
    """Return the type field for response output items."""
    if isinstance(item, dict):
        return item.get("type")
    return getattr(item, "type", None)


def _item_field(item: Any, name: str) -> Any:
    """Safely read a field from a response output item."""
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def run_agent_multi_output(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    agent_vs_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    force_file_search: bool = True,
    max_num_results: int = 6,
) -> dict[str, Any]:
    """Run an agent that can emit multiple strict tool outputs."""
    output_specs: list[OutputSpec] = [OUTPUT_SPECS[task] for task in tasks]

    model = model_override or runtime.model
    shared_vs_id = runtime.vs_resolver.id_for_store_name(runtime.shared_vs_name)
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)
    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)

    bundler = SchemaBundler(runtime.schema_dir)
    store_tools = [build_strict_store_tool(bundler, spec) for spec in output_specs]

    read_ctx = ReadToolContext(athlete_id=athlete_id, workspace_root=runtime.workspace_root)
    read_defs = read_tool_defs()
    read_handlers = read_tool_handlers(read_ctx)

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )

    tools = [
        _file_search_tool(shared_vs_id, agent_vs_id, max_num_results),
        *read_defs,
        *store_tools,
    ]

    input_list: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    produced: dict[str, Any] = {}
    wanted_tool_names = {spec.tool_name for spec in output_specs}

    force_search = force_file_search
    response = runtime.client.responses.create(
        model=model,
        tools=tools,
        input=input_list,
        tool_choice={"type": "file_search"} if force_search else None,
    )
    input_list += response.output
    force_search = False

    safety = 0
    while True:
        safety += 1
        if safety > 30:
            return {"ok": False, "error": "Too many tool iterations", "produced": produced}

        function_calls = [item for item in response.output if _item_type(item) == "function_call"]
        if not function_calls:
            all_done = wanted_tool_names.issubset(set(produced.keys()))
            return {"ok": all_done, "produced": produced, "final_text": response.output_text}

        for call in function_calls:
            name = _item_field(call, "name")
            args_raw = _item_field(call, "arguments") or "{}"
            call_id = _item_field(call, "call_id")
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {}

            if name in read_handlers:
                try:
                    result = read_handlers[name](args)
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}

                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue

            spec = next((item for item in output_specs if item.tool_name == name), None)
            if spec is None:
                result = {"ok": False, "error": f"Unknown store tool: {name}"}
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
                continue

            document = args if spec.envelope else args.get("workouts")
            try:
                saved = guarded.guard_put_validated(
                    output_spec=spec,
                    document=document,
                    run_id=run_id,
                    producer_agent=agent_name,
                    update_latest=True,
                )
                produced[name] = saved
                result = saved
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

        if wanted_tool_names.issubset(set(produced.keys())):
            return {"ok": True, "produced": produced}

        response = runtime.client.responses.create(
            model=model,
            tools=tools,
            input=input_list,
            tool_choice={"type": "file_search"} if force_search else None,
        )
        input_list += response.output
