"""CrewAI-backed one-turn chat runner for the active Coach page."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from .compat import crewai_runtime_status
from .provider import build_crewai_llm_kwargs
from .telemetry import runtime_event_scope

logger = logging.getLogger(__name__)

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class CoachTool:
    """Simple tool descriptor used by the Coach page and CrewAI turn runner."""

    name: str
    description: str
    parameters: JsonMap
    handler: Callable[..., str]


def _history_block(messages: list[JsonMap]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role") or "unknown")
        content = str(message.get("content") or "")
        if not content.strip():
            continue
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _build_crewai_tools(tools: list[CoachTool]) -> list[Any]:
    crewai_tools = import_module("crewai.tools")
    tool_decorator = getattr(crewai_tools, "tool")
    wrapped: list[Any] = []

    for spec in tools:
        def _factory(tool_spec: CoachTool = spec) -> Any:
            def _run(payload_json: str = "{}") -> str:
                try:
                    args = json.loads(payload_json) if payload_json else {}
                except json.JSONDecodeError as exc:
                    return json.dumps({"ok": False, "error": f"Invalid payload_json: {exc}"})
                if not isinstance(args, dict):
                    return json.dumps({"ok": False, "error": "payload_json must decode to an object"})
                try:
                    return tool_spec.handler(**args)
                except TypeError as exc:
                    return json.dumps({"ok": False, "error": f"Invalid tool arguments: {exc}"})
                except Exception as exc:  # pragma: no cover - runtime parity fallback
                    return json.dumps({"ok": False, "error": str(exc)})

            _run.__name__ = f"{tool_spec.name}_tool"
            _run.__doc__ = (
                f"{tool_spec.description} "
                "Pass arguments as a JSON string in the single `payload_json` parameter."
            )
            return tool_decorator(tool_spec.name)(_run)

        wrapped.append(_factory())
    return wrapped


def run_coach_turn(
    *,
    instructions: str,
    user_message: str,
    history: list[JsonMap],
    tools: list[CoachTool],
    agent_name: str = "coach",
    model_override: str | None = None,
    temperature_override: float | None = None,
    workspace_root: Path | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
) -> str:
    """Run one CrewAI-backed coach turn and return assistant text."""

    status = crewai_runtime_status()
    if not status.ok:
        raise RuntimeError(status.message)

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    LLM = getattr(crewai, "LLM")

    llm = LLM(
        **build_crewai_llm_kwargs(
            agent_name,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    )
    agent = Agent(
        role="Active Planning Coach",
        goal="Help the user inspect, preview, and confirm safe plan changes.",
        backstory="A planning coach that works through explicit tools and never claims persistence before confirmation.",
        llm=llm,
        tools=_build_crewai_tools(tools),
        allow_delegation=False,
        verbose=False,
    )

    history_text = _history_block(history)
    description = "\n".join(
        [
            "System instructions:",
            instructions,
            "",
            "Conversation history:",
            history_text or "(no prior conversation)",
            "",
            "Tool contract:",
            "- All tools accept a single string parameter named `payload_json`.",
            "- `payload_json` must be a JSON object string matching the tool arguments.",
            "- Use preview tools before apply tools for any mutating action.",
            "",
            "Current user message:",
            user_message,
            "",
            (
                "Answer directly to the user. Mention preview/confirmation status only when it is relevant to the "
                "current answer or a pending operation actually exists. If this chat already showed a startup "
                "context summary and no material context changed, do not restate the full athlete/context boilerplate. "
                "Reply in the same language as the current user message unless the user explicitly asks for another language."
            ),
        ]
    )
    task = Task(
        description=description,
        expected_output="A concise direct assistant reply to the user.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    if workspace_root is not None and athlete_id and run_id:
        with runtime_event_scope(
            root=workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component="coach_turn",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()

    raw = getattr(task.output, "raw", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(result, str) and result.strip():
        return result.strip()
    result_raw = getattr(result, "raw", None)
    if isinstance(result_raw, str) and result_raw.strip():
        return result_raw.strip()
    logger.warning("Coach turn produced no raw text output.")
    return "I could not produce a coach response for that turn."
