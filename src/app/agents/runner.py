"""Agent runner for standard tool-calling flows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from app.openai.vectorstore_state import VectorStoreResolver
from app.prompts.loader import PromptLoader
from app.tools.workspace_tools import ToolContext, get_tool_defs, get_tool_handlers


@dataclass(frozen=True)
class AgentRuntime:
    """Runtime dependencies for running an agent."""
    client: OpenAI
    model: str
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
    include_debug_file_search: bool = False,
    force_file_search: bool = True,
    max_num_results: int = 6,
) -> str:
    """Run an agent with workspace tools and file search attached."""
    model = model_override or runtime.model
    shared_vs_id = runtime.vs_resolver.id_for_store_name(runtime.shared_vs_name)
    agent_vs_id = runtime.vs_resolver.id_for_store_name(agent_vs_name)

    system_prompt = runtime.prompt_loader.combined_system_prompt(agent_name)

    tool_ctx = ToolContext(
        athlete_id=athlete_id,
        agent_name=agent_name,
        workspace_root=workspace_root,
        schema_dir=schema_dir,
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
    response = runtime.client.responses.create(
        model=model,
        tools=tools,
        input=input_list,
        include=include,
        tool_choice={"type": "file_search"} if force_search else None,
    )
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

            if name not in tool_handlers:
                result = {"ok": False, "error": f"Unknown tool: {name}"}
            else:
                try:
                    result = tool_handlers[name](args)
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

        response = runtime.client.responses.create(
            model=model,
            tools=tools,
            input=input_list,
            include=include,
            tool_choice={"type": "file_search"} if force_search else None,
        )
        input_list += response.output

    return response.output_text
