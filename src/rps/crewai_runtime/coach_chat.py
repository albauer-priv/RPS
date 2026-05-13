"""CrewAI-backed conversational planning runner with small, single-purpose specialists."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from rps.agents.knowledge_injection import build_injection_block
from rps.prompts.loader import PromptLoader

from .compat import crewai_runtime_status
from .provider import build_crewai_llm_kwargs
from .telemetry import runtime_event_scope

logger = logging.getLogger(__name__)

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class CoachTool:
    """Simple tool descriptor used by conversational planning pages."""

    name: str
    description: str
    parameters: JsonMap
    handler: Callable[..., str]


@dataclass(frozen=True)
class SpecialistToolsets:
    """Strict per-specialist tool visibility for the conversational crew."""

    context: list[CoachTool] = field(default_factory=list)
    recommendation: list[CoachTool] = field(default_factory=list)
    preview: list[CoachTool] = field(default_factory=list)
    pending: list[CoachTool] = field(default_factory=list)


@dataclass(frozen=True)
class ConversationalSurface:
    """Configuration for one chat surface using the shared specialist crew."""

    name: str
    scope_summary: str
    shared_context: str
    prompts_dir: Path


def _history_block(messages: list[JsonMap]) -> str:
    lines: list[str] = []
    for message in messages:
        role = str(message.get("role") or "unknown")
        content = str(message.get("content") or "")
        if not content.strip():
            continue
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _tool_name_map(tools: list[CoachTool]) -> list[str]:
    return [tool.name for tool in tools]


def build_runtime_profile(*, surface_name: str, toolsets: SpecialistToolsets) -> dict[str, object]:
    """Return a testable summary of knowledge and tool assignment per specialist."""

    return {
        "surface": surface_name,
        "knowledge_modes": {
            "conversation_manager": surface_name,
            "week_context_analyst": surface_name,
            "coaching_recommendation_specialist": surface_name,
            "week_preview_specialist": surface_name,
            "pending_resolution_specialist": surface_name,
        },
        "tool_names": {
            "conversation_manager": [],
            "week_context_analyst": _tool_name_map(toolsets.context),
            "coaching_recommendation_specialist": _tool_name_map(toolsets.recommendation),
            "week_preview_specialist": _tool_name_map(toolsets.preview),
            "pending_resolution_specialist": _tool_name_map(toolsets.pending),
        },
    }


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


def _build_agent(
    crewai: Any,
    *,
    agent_name: str,
    tool_specs: list[CoachTool],
    model_override: str | None,
    temperature_override: float | None,
    prompts_dir: Path,
    surface_name: str,
) -> Any:
    Agent = getattr(crewai, "Agent")
    LLM = getattr(crewai, "LLM")
    llm = LLM(
        **build_crewai_llm_kwargs(
            agent_name,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    )
    prompt_loader = PromptLoader(prompts_dir)
    prompt = prompt_loader.combined_system_prompt(agent_name)
    injected = build_injection_block(agent_name, mode=surface_name)
    if injected:
        prompt = f"{prompt}\n\n{injected}"
    return Agent(
        role=agent_name.replace("_", " ").title(),
        goal=prompt,
        backstory=prompt,
        llm=llm,
        tools=_build_crewai_tools(tool_specs),
        allow_delegation=False,
        verbose=False,
    )


def _extract_model(task: Any, result: Any, model_cls: type[BaseModel]) -> BaseModel:
    for candidate in (
        getattr(getattr(task, "output", None), "pydantic", None),
        getattr(result, "pydantic", None),
        getattr(task, "output", None),
        result,
    ):
        if isinstance(candidate, model_cls):
            return candidate
    for raw in (
        getattr(getattr(task, "output", None), "raw", None),
        getattr(result, "raw", None),
        result if isinstance(result, str) else None,
    ):
        if isinstance(raw, str) and raw.strip():
            return model_cls.model_validate_json(raw)
    raise ValueError(f"CrewAI task did not produce {model_cls.__name__}")


def _extract_text(task: Any, result: Any) -> str:
    raw = getattr(getattr(task, "output", None), "raw", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(result, str) and result.strip():
        return result.strip()
    result_raw = getattr(result, "raw", None)
    if isinstance(result_raw, str) and result_raw.strip():
        return result_raw.strip()
    raise ValueError("CrewAI task produced no assistant text")


def _run_structured_task(
    *,
    task_name: str,
    agent_name: str,
    description: str,
    expected_output: str,
    output_model: type[BaseModel],
    tool_specs: list[CoachTool],
    model_override: str | None,
    temperature_override: float | None,
    prompts_dir: Path,
    surface_name: str,
) -> BaseModel:
    crewai = import_module("crewai")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    Task = getattr(crewai, "Task")
    agent = _build_agent(
        crewai,
        agent_name=agent_name,
        tool_specs=tool_specs,
        model_override=model_override,
        temperature_override=temperature_override,
        prompts_dir=prompts_dir,
        surface_name=surface_name,
    )
    task = Task(
        name=task_name,
        description=description,
        expected_output=expected_output,
        agent=agent,
        output_pydantic=output_model,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    return _extract_model(task, result, output_model)


def _run_text_task(
    *,
    task_name: str,
    agent_name: str,
    description: str,
    expected_output: str,
    tool_specs: list[CoachTool],
    model_override: str | None,
    temperature_override: float | None,
    prompts_dir: Path,
    surface_name: str,
) -> str:
    crewai = import_module("crewai")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    Task = getattr(crewai, "Task")
    agent = _build_agent(
        crewai,
        agent_name=agent_name,
        tool_specs=tool_specs,
        model_override=model_override,
        temperature_override=temperature_override,
        prompts_dir=prompts_dir,
        surface_name=surface_name,
    )
    task = Task(
        name=task_name,
        description=description,
        expected_output=expected_output,
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    return _extract_text(task, result)


def _shared_turn_context(*, surface: ConversationalSurface, user_message: str, history: list[JsonMap]) -> str:
    history_text = _history_block(history)
    return "\n".join(
        [
            f"Surface: {surface.name}",
            f"Scope: {surface.scope_summary}",
            "",
            "Injected memory and page context:",
            surface.shared_context or "(none)",
            "",
            "Conversation history:",
            history_text or "(no prior conversation)",
            "",
            "Current user message:",
            user_message,
        ]
    )


def run_conversational_turn(
    *,
    surface: ConversationalSurface,
    user_message: str,
    history: list[JsonMap],
    toolsets: SpecialistToolsets,
    model_override: str | None = None,
    temperature_override: float | None = None,
    workspace_root: Path | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
) -> str:
    """Run one manager-led conversational turn with narrow specialist tool sets."""

    status = crewai_runtime_status()
    if not status.ok:
        raise RuntimeError(status.message)

    from .models import (
        AdjustmentIntentModel,
        CoachingRecommendationModel,
        CoachPreviewSummaryModel,
        PendingResolutionResultModel,
        TurnModeModel,
        WeekContextAssessmentModel,
    )

    shared = _shared_turn_context(surface=surface, user_message=user_message, history=history)

    def _classify() -> TurnModeModel:
        return _run_structured_task(
            task_name="classify_turn",
            agent_name="conversation_manager",
            description="\n".join(
                [
                    shared,
                    "",
                    "Choose exactly one mode: analyze, recommend, create_preview, or resolve_pending.",
                    "Use resolve_pending whenever the conversation already contains a pending preview or the user is asking to show, apply, confirm, or discard one.",
                    "Use create_preview for broad or specific change requests that should lead to a preview now.",
                    "Use recommend for coaching advice without immediate preview creation.",
                    "Use analyze for read-only context questions.",
                ]
            ),
            expected_output="A structured turn mode with one of analyze, recommend, create_preview, or resolve_pending.",
            output_model=TurnModeModel,
            tool_specs=[],
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _analyze() -> WeekContextAssessmentModel:
        return _run_structured_task(
            task_name="analyze_week_context",
            agent_name="week_context_analyst",
            description="\n".join(
                [
                    shared,
                    "",
                    "Produce a factual selected-week context assessment.",
                    "Prefer injected snapshot memory before using read-only tools.",
                ]
            ),
            expected_output="A structured week context assessment.",
            output_model=WeekContextAssessmentModel,
            tool_specs=toolsets.context,
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _recommend(context_result: WeekContextAssessmentModel) -> CoachingRecommendationModel:
        return _run_structured_task(
            task_name="form_coaching_recommendation",
            agent_name="coaching_recommendation_specialist",
            description="\n".join(
                [
                    shared,
                    "",
                    "Week context assessment:",
                    context_result.model_dump_json(indent=2),
                    "",
                    "Provide direct coaching advice only. Do not create a preview in this task.",
                ]
            ),
            expected_output="A structured coaching recommendation.",
            output_model=CoachingRecommendationModel,
            tool_specs=toolsets.recommendation,
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _intent(context_result: WeekContextAssessmentModel) -> AdjustmentIntentModel:
        return _run_structured_task(
            task_name="form_adjustment_intent",
            agent_name="coaching_recommendation_specialist",
            description="\n".join(
                [
                    shared,
                    "",
                    "Week context assessment:",
                    context_result.model_dump_json(indent=2),
                    "",
                    "Produce one clean adjustment intent for preview creation.",
                    "The field `message_for_preview` must be a concise instruction suitable for the preview tool.",
                ]
            ),
            expected_output="A structured adjustment intent.",
            output_model=AdjustmentIntentModel,
            tool_specs=toolsets.recommendation,
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _preview(intent_result: AdjustmentIntentModel) -> CoachPreviewSummaryModel:
        return _run_structured_task(
            task_name="create_week_preview",
            agent_name="week_preview_specialist",
            description="\n".join(
                [
                    shared,
                    "",
                    "Adjustment intent:",
                    intent_result.model_dump_json(indent=2),
                    "",
                    "Create exactly one bounded preview now.",
                ]
            ),
            expected_output="A structured preview result.",
            output_model=CoachPreviewSummaryModel,
            tool_specs=toolsets.preview,
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _resolve_pending() -> PendingResolutionResultModel:
        return _run_structured_task(
            task_name="resolve_pending_operation",
            agent_name="pending_resolution_specialist",
            description="\n".join(
                [
                    shared,
                    "",
                    "Inspect pending state and either show it, apply it, or discard it.",
                    "Do not create a new preview in this task.",
                ]
            ),
            expected_output="A structured pending-resolution result.",
            output_model=PendingResolutionResultModel,
            tool_specs=toolsets.pending,
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _finalize(mode: str, payload: BaseModel) -> str:
        return _run_text_task(
            task_name="finalize_reply",
            agent_name="conversation_manager",
            description="\n".join(
                [
                    shared,
                    "",
                    f"Selected mode: {mode}",
                    "Specialist result:",
                    payload.model_dump_json(indent=2),
                    "",
                    "Produce the final user-facing reply in the language of the current user message.",
                    "Mention preview/apply status only when relevant to the current result.",
                ]
            ),
            expected_output="One concise direct assistant reply.",
            tool_specs=[],
            model_override=model_override,
            temperature_override=temperature_override,
            prompts_dir=surface.prompts_dir,
            surface_name=surface.name,
        )

    def _run() -> str:
        mode_result = _classify()
        if mode_result.mode == "resolve_pending":
            payload = _resolve_pending()
            return _finalize(mode_result.mode, payload)
        context_result = _analyze()
        if mode_result.mode == "analyze":
            return _finalize(mode_result.mode, context_result)
        if mode_result.mode == "recommend":
            payload = _recommend(context_result)
            return _finalize(mode_result.mode, payload)
        intent_result = _intent(context_result)
        preview_result = _preview(intent_result)
        return _finalize(mode_result.mode, preview_result)

    if workspace_root is not None and athlete_id and run_id:
        with runtime_event_scope(
            root=workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component="coach_turn",
        ):
            return _run()
    return _run()


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
    """Backward-compatible single-agent wrapper retained for legacy callers."""

    status = crewai_runtime_status()
    if not status.ok:
        raise RuntimeError(status.message)

    crewai = import_module("crewai")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    Task = getattr(crewai, "Task")
    agent = _build_agent(
        crewai,
        agent_name=agent_name,
        tool_specs=tools,
        model_override=model_override,
        temperature_override=temperature_override,
        prompts_dir=Path("prompts"),
        surface_name="coach",
    )
    history_text = _history_block(history)
    description = "\n".join(
        [
            instructions,
            "",
            "Conversation history:",
            history_text or "(no prior conversation)",
            "",
            "Current user message:",
            user_message,
        ]
    )
    task = Task(
        name="legacy_chat_turn",
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
    try:
        return _extract_text(task, result)
    except ValueError:
        logger.warning("Coach turn produced no raw text output.")
        return "I could not produce a coach response for that turn."
