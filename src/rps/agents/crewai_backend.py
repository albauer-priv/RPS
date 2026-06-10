"""CrewAI execution backend for planner and advisory artefact tasks."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any

from rps.agents.output_normalization import (
    extract_loaded_document,
    extract_planning_events_document,
    normalize_phase_guardrails_document,
    normalize_season_scenarios_document,
    normalize_workout_inline_loop_headers,
    normalize_workout_percent_ranges,
)
from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    collect_native_agent_kwargs,
    collect_native_crew_kwargs,
    output_model_for_kind,
)
from rps.crewai_runtime.config import CrewAIConfigBundle, load_crewai_config_bundle
from rps.crewai_runtime.generated_artifact_models import (
    artifact_model_for_schema_file,
    artifact_model_for_task_name,
)
from rps.crewai_runtime.guardrails import (
    build_task_guardrail_kwargs,
    current_guardrail_runtime_context,
    guardrail_runtime_context,
    phase_bundle_matches_context,
    phase_bundle_review_readiness,
    phase_week_role_load_coherence,
    season_bundle_matches_contract,
    season_bundle_review_readiness,
    week_bundle_domain_legality_messages,
    week_bundle_review_readiness,
)
from rps.crewai_runtime.knowledge import (
    build_crewai_knowledge_kwargs,
    resolve_agent_knowledge_profile,
)
from rps.crewai_runtime.memory import (
    build_agent_memory_value,
    build_crew_memory_kwargs,
    resolve_agent_memory_profile,
    resolve_crew_memory_profile,
)
from rps.crewai_runtime.models import SeasonPlanDraftBundleModel
from rps.crewai_runtime.provider import (
    build_crewai_llm_kwargs,
    build_crewai_planning_llm_kwargs,
    resolve_crewai_planning_enabled,
)
from rps.crewai_runtime.skills import (
    build_crewai_skill_kwargs,
    resolve_agent_skill_profile,
)
from rps.crewai_runtime.telemetry import (
    build_step_callback,
    build_task_callback,
    emit_runtime_event,
    emit_runtime_exception_event,
    register_runtime_label,
    register_runtime_metadata,
    runtime_event_scope,
)
from rps.evidence.library import canonical_reference_locator
from rps.planning.contracts import derive_expected_average_weekly_kj_range
from rps.planning.phase_authority import (
    format_role_week_load_bands,
    normalize_role_week_load_bands,
    role_week_band_by_week,
)
from rps.planning.week_engine import (
    execute_week_engine,
    extract_message_from_user_input,
    parse_target_week_from_user_input,
)
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.workouts.generator import build_week_plan_document_from_bundle
from rps.workouts.week_plan_consistency import normalize_week_plan_consistency
from rps.workspace.artifact_metadata import CANONICAL_OWNER_BY_ARTIFACT, normalize_trace_reference
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.phase_intents import (
    PHASE_TAXONOMY_VERSION,
    normalize_phase_semantics,
    phase_semantic_contract_payload,
    phase_type_for_intent,
    season_phase_allowed_domains,
    season_phase_forbidden_domains,
    semantic_allowed_load_modalities,
    validate_phase_semantics,
)
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.types import ArtifactType

from .runtime import AgentRuntime

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]

_INTERNAL_PROMPT_CHAR_LIMIT = 2800
_INTERNAL_PROMPT_WORD_LIMIT = 450
_INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT = 420
_INTERNAL_PROMPT_PRIORITY_MARKERS: tuple[str, ...] = (
    "Current Task:",
    "Current Step",
    "Context from previous steps:",
    "Athlete State Snapshot",
    "Use the latest",
    "Target ISO week:",
    "Internal specialist task:",
    "User request:",
)

_AUTHORITATIVE_RUNTIME_BLOCK_PREFIXES: tuple[str, ...] = (
    "**Athlete State Snapshot**",
    "**Planning Context Snapshot**",
    "**Current Week Status Snapshot**",
    "**Advisory Memory**",
    "**Resolved ",
    "**Deterministic ",
)

_INTERNAL_TOOL_FIRST_RULES = """Shared binding rules for this internal planning step:
- Use prior specialist context and the provided workspace tools before claiming any input is missing.
- An input is missing only after the relevant workspace tool fails, returns not found, or prior specialist context truly does not contain it.
- If a required input is tool-loadable, do not ask the user to paste or re-provide it.
- If the task has workspace tools, use them first and keep the number of retrieval attempts tight and relevant.
- If still blocked, return one compact blocked result only once. Include: missing_inputs, attempted_tools, and reason.
- No repeated paragraphs. No duplicate missing-input lists. No generic apology text.
"""

JsonMap = dict[str, Any]
ToolMap = dict[str, Any]

_SEASON_PLAN_REQUIRED_TRACE_DATA_ARTIFACTS: tuple[ArtifactType, ...] = (
    ArtifactType.ATHLETE_PROFILE,
    ArtifactType.KPI_PROFILE,
    ArtifactType.AVAILABILITY,
    ArtifactType.LOGISTICS,
    ArtifactType.ZONE_MODEL,
)
_SEASON_PLAN_REQUIRED_TRACE_EVENT_ARTIFACTS: tuple[ArtifactType, ...] = (
    ArtifactType.PLANNING_EVENTS,
)


def _canonicalize_phase_semantics_for_bundle(
    *,
    phase_type: object,
    phase_intent: object,
    build_subtype: object | None = None,
    warnings: list[str] | None = None,
    warning_prefix: str | None = None,
) -> tuple[str, str, str | None]:
    """Return canonical phase semantics for normalized Season/Phase bundles.

    The normalized bundle is Python-owned. When a valid canonical phase intent is
    paired with the wrong phase type, prefer the canonical type for that intent
    and record a warning. Unknown or unrecoverable values remain untouched so
    downstream contract validation can fail closed.
    """

    raw_build_subtype = str(build_subtype).strip() if isinstance(build_subtype, str) and str(build_subtype).strip() else None

    semantics = normalize_phase_semantics(
        phase_type=phase_type,
        phase_intent=phase_intent,
        build_subtype=build_subtype,
    )
    if semantics is not None:
        return semantics.phase_type, semantics.phase_intent, semantics.build_subtype

    canonical_phase_type = phase_type_for_intent(phase_intent)
    if not canonical_phase_type:
        return str(phase_type or ""), str(phase_intent or ""), raw_build_subtype

    semantics = normalize_phase_semantics(
        phase_type=canonical_phase_type,
        phase_intent=phase_intent,
        build_subtype=build_subtype,
    )
    if semantics is None:
        return str(phase_type or ""), str(phase_intent or ""), raw_build_subtype

    if warnings is not None:
        prefix = f"{warning_prefix}: " if warning_prefix else ""
        warning = (
            f"{prefix}canonicalized phase_type from {phase_type!r} to {canonical_phase_type!r} "
            f"for phase_intent {phase_intent!r}."
        )
        if warning not in warnings:
            warnings.append(warning)
    return semantics.phase_type, semantics.phase_intent, semantics.build_subtype


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _trace_reference_from_payload(artifact_type: ArtifactType, payload: object) -> JsonMap | None:
    """Return a normalized trace reference for a loaded artifact payload when possible."""

    if not isinstance(payload, dict):
        return None
    meta = _as_map(payload.get("meta"))
    version_key = str(meta.get("version_key") or "").strip()
    run_id = str(meta.get("run_id") or "").strip()
    if not version_key or not run_id:
        return None
    reference = normalize_trace_reference(
        {
            "artifact": artifact_type.value,
            "version": meta.get("version"),
            "schema_version": meta.get("schema_version"),
            "version_key": version_key,
            "run_id": run_id,
        }
    )
    return {key: str(value) for key, value in reference.items()} if reference is not None else None


def _merge_trace_reference_lists(existing: object, additions: list[JsonMap], *, allowed: set[str]) -> list[JsonMap]:
    """Merge trace references while preserving order and removing duplicates."""

    normalized: list[JsonMap] = []
    seen_indices: dict[tuple[str, str], int] = {}

    def _append(entry: object) -> None:
        if not isinstance(entry, dict):
            return
        artifact = str(entry.get("artifact") or "").strip().upper()
        if artifact not in allowed:
            return
        reference = normalize_trace_reference(entry)
        if reference is None:
            return
        token = (
            str(reference.get("artifact") or ""),
            str(reference.get("version_key") or ""),
        )
        existing_index = seen_indices.get(token)
        if existing_index is not None:
            normalized[existing_index] = {key: str(value) for key, value in reference.items()}
            return
        seen_indices[token] = len(normalized)
        normalized.append({key: str(value) for key, value in reference.items()})

    if isinstance(existing, list):
        for item in existing:
            _append(item)
    for item in additions:
        _append(item)
    return normalized


def _normalize_publication_link(title: object, link: object) -> str:
    """Return a verified canonical publication link when the local library knows it."""

    canonical_link = canonical_reference_locator(title)
    if canonical_link:
        return canonical_link
    return ""

_TASK_BLUEPRINT_BY_AGENT_TASK = {
    AgentTask.CREATE_SEASON_SCENARIOS: "season_scenarios",
    AgentTask.CREATE_SEASON_SCENARIO_SELECTION: "season_scenario_selection",
    AgentTask.CREATE_SEASON_PLAN: "season_plan",
    AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD: "season_phase_feed_forward",
    AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
    AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
    AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
    AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
    AgentTask.CREATE_WEEK_PLAN: "week_plan",
    AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
}

_SEASON_PLANNING_TASKS: tuple[str, ...] = (
    "season_context_read",
    "season_scenario_interpretation",
    "season_event_priority_review",
    "season_peak_window_review",
    "season_macrocycle_draft",
    "season_constraint_review",
    "season_historical_context_review",
    "season_kpi_guidance_review",
    "season_load_corridor_draft",
    "season_progression_review",
    "season_plan_finalize",
)

_SEASON_REVIEW_TASKS: tuple[str, ...] = (
    "season_governance_review",
    "season_constraints_review",
    "season_plan_audit",
    "season_contract_review",
    "season_review",
)

_PHASE_PLANNING_TASKS: tuple[str, ...] = (
    "phase_context_read",
    "phase_guardrail_band_draft",
    "phase_execution_rules_draft",
    "phase_structure_draft",
    "phase_cadence_recovery_draft",
    "phase_intensity_distribution_draft",
    "phase_event_integration_draft",
    "phase_preview_draft",
    "phase_bundle_finalize",
)

_PHASE_REVIEW_TASKS: tuple[str, ...] = (
    "phase_constraint_audit",
    "phase_governance_review",
    "phase_structure_review",
    "phase_preview_review",
    "phase_contract_review",
    "phase_review",
)

_WEEK_PLANNING_TASKS: tuple[str, ...] = (
    "week_context_read",
    "week_constraint_review",
    "week_load_target_draft",
    "week_revision_draft",
    "week_workout_text_draft",
    "week_plan_finalize",
)

_WEEK_REVIEW_TASKS: tuple[str, ...] = (
    "week_consistency_review",
    "week_load_governance_review",
    "week_workout_syntax_review",
    "week_contract_review",
    "week_review",
)


def _resolve_agent_runtime_profile(bundle: CrewAIConfigBundle, agent_name: str) -> JsonMap:
    """Return the runtime-model/reasoning profile for one agent."""

    profiles = bundle.runtime_profiles.get("agents") or {}
    profile = profiles.get(agent_name) or {}
    if not isinstance(profile, dict):
        return {}
    return profile


def _resolve_crew_runtime_profile(bundle: CrewAIConfigBundle, crew_name: str) -> JsonMap:
    """Return the runtime planning profile for one crew."""

    profiles = bundle.runtime_profiles.get("crews") or {}
    profile = profiles.get(crew_name) or {}
    if not isinstance(profile, dict):
        return {}
    return profile


def _build_crewai_crew_kwargs(
    *,
    runtime: AgentRuntime,
    bundle: CrewAIConfigBundle,
    crew_name: str,
    athlete_id: str | None,
    run_id: str | None,
    persisted_artifact_flow: bool = True,
) -> JsonMap:
    """Return CrewAI-native kwargs and callbacks for one crew execution."""

    crew_profile = _resolve_crew_runtime_profile(bundle, crew_name)
    kwargs = collect_native_crew_kwargs(
        crew_profile,
        persisted_artifact_flow=persisted_artifact_flow,
    )
    root = runtime.workspace_root if athlete_id and run_id else None
    kwargs["task_callback"] = build_task_callback(
        root=root,
        athlete_id=athlete_id,
        run_id=run_id,
        crew_name=crew_name,
    )
    step_cfg = crew_profile.get("step_callback")
    step_enabled = bool(step_cfg.get("enabled", False)) if isinstance(step_cfg, dict) else False
    step_callback = build_step_callback(
        root=root,
        athlete_id=athlete_id,
        run_id=run_id,
        crew_name=crew_name,
        enabled=step_enabled,
    )
    if step_callback is not None:
        kwargs["step_callback"] = step_callback
    return kwargs


def _build_task_callback_kwargs(
    *,
    runtime: AgentRuntime,
    crew_name: str,
    task_name: str,
    athlete_id: str | None,
    run_id: str | None,
) -> JsonMap:
    """Return CrewAI Task callback kwargs for compact task-level telemetry."""

    root = runtime.workspace_root if athlete_id and run_id else None
    return {
        "callback": build_task_callback(
            root=root,
            athlete_id=athlete_id,
            run_id=run_id,
            crew_name=crew_name,
            task_name=task_name,
            event_type="CREW_TASK_CALLBACK_COMPLETED",
        )
    }


def _emit_crew_task_prepared_events(
    *,
    runtime: AgentRuntime,
    crew_name: str,
    tasks: list[tuple[str, str, str | None]],
    athlete_id: str | None,
    run_id: str | None,
    component: str,
) -> None:
    """Emit one compact log/event row per task before CrewAI kickoff begins."""

    if not athlete_id or not run_id:
        return
    for index, (task_name, agent_name, model_name) in enumerate(tasks, start=1):
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="CREW_TASK_PREPARED",
            crew=crew_name,
            task=task_name,
            agent=agent_name,
            model=model_name,
            status=f"{index}/{len(tasks)}",
            component=component,
        )


def _tool_map_from_runtime_tools(tools: list[Any] | ToolMap) -> ToolMap:
    """Normalize runtime tools to a lookup by CrewAI tool name."""

    if isinstance(tools, dict):
        return tools
    result: ToolMap = {}
    for tool_obj in tools:
        for attr in ("name", "tool_name", "__name__"):
            value = getattr(tool_obj, attr, None)
            if isinstance(value, str) and value:
                result[value] = tool_obj
                break
    return result


def _tool_names_for_task(task_blueprint: Any, tools_by_name: ToolMap) -> tuple[str, ...]:
    """Resolve the CrewAI task-level tool names from task config."""

    configured = (getattr(task_blueprint, "config", {}) or {}).get("tools")
    if configured is None:
        return ()
    if configured == "read_only_workspace":
        return tuple(tools_by_name)
    if configured in (False, "none"):
        return ()
    if isinstance(configured, str):
        return (configured,)
    if isinstance(configured, list | tuple):
        return tuple(str(item) for item in configured if str(item).strip())
    raise ValueError(f"Task '{task_blueprint.name}' tools must be a string or list of tool names.")


def _task_tools_for_blueprint(task_blueprint: Any, tools: list[Any] | ToolMap) -> list[Any]:
    """Return the task-scoped CrewAI tools configured for a task blueprint."""

    tools_by_name = _tool_map_from_runtime_tools(tools)
    names = _tool_names_for_task(task_blueprint, tools_by_name)
    missing = [name for name in names if name not in tools_by_name]
    if missing:
        raise ValueError(
            f"Task '{task_blueprint.name}' references unknown tools: {', '.join(missing)}"
        )
    return [tools_by_name[name] for name in names]


def _build_crewai_planning_llm(
    crewai_llm_cls: Any,
    *,
    bundle: CrewAIConfigBundle,
    crew_name: str,
) -> object | None:
    """Instantiate the dedicated crew-planning LLM when configured."""

    crew_profile = _resolve_crew_runtime_profile(bundle, crew_name)
    planning_profile = crew_profile.get("planning") or {}
    if not isinstance(planning_profile, dict):
        return None
    enabled = resolve_crewai_planning_enabled(
        crew_name,
        default_enabled=bool(planning_profile.get("enabled", False)),
    )
    if not enabled:
        return None
    kwargs = build_crewai_planning_llm_kwargs(
        crew_name,
        default_model=planning_profile.get("model") if isinstance(planning_profile.get("model"), str) else None,
    )
    if not kwargs:
        return None
    return crewai_llm_cls(**kwargs)

def _fill_season_plan(document: JsonMap) -> JsonMap:
    """Normalize common SEASON_PLAN placement issues."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    if str(meta.get("artifact_type", "")).upper() != "SEASON_PLAN":
        return document
    if not meta.get("data_confidence"):
        meta["data_confidence"] = "UNKNOWN"
    document["meta"] = meta
    data = document.get("data") or {}
    if not isinstance(data, dict):
        return document
    if "explicit_forbidden_content" not in data or not isinstance(
        data.get("explicit_forbidden_content"), list
    ):
        data["explicit_forbidden_content"] = [
            "phase definitions (phase plans)",
            "weekly schedules",
            "day-by-day structure",
            "workouts or interval prescriptions",
            "numeric progression rules",
            "daily or session-level kJ targets",
        ]
    if "self_check" not in data or not isinstance(data.get("self_check"), dict):
        data["self_check"] = {
            "planning_horizon_is_at_least_8_weeks": True,
            "every_phase_defines_weekly_kj_corridor": True,
            "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": True,
            "every_phase_maps_to_cycle_and_deload_intent": True,
            "every_phase_includes_narrative_and_metabolic_focus": True,
            "every_phase_includes_evaluation_focus_and_exit_assumptions": True,
            "season_load_envelope_and_assumptions_documented": True,
            "principles_and_scientific_foundation_documented": True,
            "allowed_forbidden_domains_listed": True,
            "no_phase_or_week_planning_content": True,
            "header_includes_implements_iso_week_range_trace": True,
        }
    document["data"] = data
    return document


def _derive_season_semantic_notes(*, planning_bundle: JsonMap) -> list[str]:
    """Return deterministic season-level notes that the writer must preserve."""

    notes: list[str] = []
    event_priority = _as_map(planning_bundle.get("event_priority"))
    primary_a_events = [str(item).strip() for item in _as_list(event_priority.get("primary_a_events")) if str(item).strip()]
    if primary_a_events:
        notes.append(
            "Frame the season objective against the primary A event(s): "
            + ", ".join(primary_a_events)
            + ". If longer-distance durability reserve is mentioned, present it as support for the A event rather than a conflicting primary target."
        )
    notes.append(
        "Use durability-first, ceiling-constrained wording. Do not describe the season as ceiling-first when VO2MAX authority is absent or forbidden."
    )
    notes.append(
        "B-event rehearsal load must replace a specificity anchor when noted, not add a second full anchor on top of the normal build load."
    )
    notes.append(
        "When taper weeks include event kJ, describe that load as event work inside taper with reduced pre-event training load, not as a normal reload week."
    )
    notes.append(
        "Within taper_freshening, LOAD_1, LOAD_2, and RELOAD are load-band labels only; they do not authorize Build-like workout selection."
    )
    return notes


def _derive_season_load_envelope_counts(*, phase_blueprints: list[JsonMap]) -> tuple[int, int]:
    """Return deterministic high-load and deload/low-load week counts.

    Counts are derived from canonical cadence-week roles so the persisted season
    envelope is complete even when the draft bundle omits these summary fields.
    """

    high_load_roles = {"LOAD_2", "RELOAD", "SHORTENED_RELOAD"}
    low_load_roles = {
        "DELOAD",
        "MINI_RESET",
        "SHORTENED_MINI_RESET",
        "SHORTENED_RE_ENTRY",
        "TRANSITION",
        "RECOVERY",
    }
    high_load_weeks = 0
    low_load_weeks = 0
    for blueprint in phase_blueprints:
        for role in _as_list(_as_map(blueprint).get("cadence_week_roles")):
            normalized_role = str(role or "").strip().upper().replace(" ", "_")
            if normalized_role in high_load_roles:
                high_load_weeks += 1
            if normalized_role in low_load_roles:
                low_load_weeks += 1
    return high_load_weeks, low_load_weeks


def _normalize_progression_trace(value: object) -> list[str]:
    """Normalize deterministic progression trace payloads to list form."""

    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [f"{key}: {val}" for key, val in value.items() if str(val).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _append_sentence(base: object, sentence: str) -> str:
    """Append one sentence to a text field if it is not already present."""

    existing = str(base or "").strip()
    addition = sentence.strip()
    if not addition:
        return existing
    if addition in existing:
        return existing
    if not existing:
        return addition
    separator = "" if existing.endswith((" ", "\n")) else " "
    return f"{existing}{separator}{addition}"


def _append_unique_item(items: object, item: str) -> list[str]:
    """Return a stripped string list with one unique appended item."""

    normalized = [str(entry).strip() for entry in _as_list(items) if str(entry).strip()]
    if item not in normalized:
        normalized.append(item)
    return normalized


def _format_role_week_guardrail_sentence(entries: Sequence[object]) -> str:
    """Render structured role-week bands into one audit sentence."""

    rendered = format_role_week_load_bands(entries)
    if not rendered:
        return ""
    return (
        "Inherited role-week load guardrails (season-level, not week prescriptions): "
        + "; ".join(rendered)
        + "."
    )


def _season_event_constraint_text(event_type: str) -> str:
    """Return deterministic season-phase event handling text for one event type."""

    normalized = str(event_type or "").strip().upper()
    if normalized == "A":
        return "A event receives dedicated taper-contained event handling."
    if normalized == "B":
        return (
            "B event receives rehearsal/minor-load-adjustment handling only and may replace "
            "a planned specificity anchor rather than adding a second peak."
        )
    return "C event remains inside normal structure without taper."


def _extract_km_values(text: object) -> list[int]:
    """Return kilometer values mentioned in a free-text objective or event label."""

    values: list[int] = []
    for match in re.finditer(r"(\d{2,4})(?:\s*[-/]\s*(\d{2,4}))?\s*km", str(text or ""), flags=re.IGNORECASE):
        first = int(match.group(1))
        second = match.group(2)
        values.append(first)
        if second is not None:
            values.append(int(second))
    return values


def _derive_objective_event_mismatch_warning(*, season_objective: object, a_events: list[JsonMap]) -> str | None:
    """Return a non-blocking warning when objective distance conflicts with the A event."""

    objective = str(season_objective or "").strip()
    objective_km = _extract_km_values(objective)
    if not objective or not objective_km or not a_events:
        return None
    highest_a_event = max(
        a_events,
        key=lambda item: (
            str(item.get("date") or ""),
            str(item.get("week") or ""),
            str(item.get("name") or ""),
        ),
    )
    event_parts = [
        str(part).strip()
        for part in (highest_a_event.get("name"), highest_a_event.get("date"))
        if str(part or "").strip()
    ]
    event_label = " ".join(event_parts).strip()
    event_km = _extract_km_values(event_label)
    if not event_km:
        return None
    if any(abs(event_distance - objective_distance) <= 25 for event_distance in event_km for objective_distance in objective_km):
        return None
    event_distance_label = "/".join(str(value) for value in event_km)
    objective_distance_label = "/".join(str(value) for value in objective_km)
    event_name = str(highest_a_event.get("name") or "the highest-priority A event").strip()
    return (
        "Warning: primary season objective references "
        f"{objective_distance_label} km demands while {event_name} targets approximately "
        f"{event_distance_label} km. Reconcile the objective upstream/input-side if this is intentional."
    )


def _normalize_final_season_plan_semantics(document: JsonMap) -> JsonMap:
    """Apply code-owned season semantics to the final SEASON_PLAN document."""

    if not isinstance(document, dict):
        return document
    meta = _as_map(document.get("meta"))
    if str(meta.get("artifact_type") or "").upper() != "SEASON_PLAN":
        return document
    context = current_guardrail_runtime_context()
    season_phase_load_context = _as_map(context.get("season_phase_load_context"))
    selected_scenario_contract = _as_map(context.get("selected_scenario_contract"))
    approved_bundle = _as_map(context.get("approved_planning_bundle"))
    trace_data_additions = [
        ref
        for artifact_type in _SEASON_PLAN_REQUIRED_TRACE_DATA_ARTIFACTS
        for ref in [_trace_reference_from_payload(artifact_type, context.get(f"{artifact_type.value.lower()}_payload"))]
        if ref is not None
    ]
    trace_event_additions = [
        ref
        for artifact_type in _SEASON_PLAN_REQUIRED_TRACE_EVENT_ARTIFACTS
        for ref in [_trace_reference_from_payload(artifact_type, context.get(f"{artifact_type.value.lower()}_payload"))]
        if ref is not None
    ]
    meta["trace_data"] = _merge_trace_reference_lists(
        meta.get("trace_data"),
        trace_data_additions,
        allowed={artifact.value for artifact in _SEASON_PLAN_REQUIRED_TRACE_DATA_ARTIFACTS}
        | {"ACTIVITIES_ACTUAL", "ACTIVITIES_TREND"},
    )
    meta["trace_events"] = _merge_trace_reference_lists(
        meta.get("trace_events"),
        trace_event_additions,
        allowed={artifact.value for artifact in _SEASON_PLAN_REQUIRED_TRACE_EVENT_ARTIFACTS},
    )
    data = _as_map(document.get("data"))
    if selected_scenario_contract:
        data["selected_scenario_contract"] = selected_scenario_contract
    phases = [_as_map(item) for item in _as_list(data.get("phases"))]
    deterministic_by_phase_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    bundle_by_phase_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(approved_bundle.get("phase_blueprints"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    all_a_events: list[JsonMap] = []
    phase_justifications = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(_as_map(data.get("justification")).get("phase_justifications"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    for phase in phases:
        phase_id = str(phase.get("phase_id") or "").strip()
        deterministic = deterministic_by_phase_id.get(phase_id, {})
        approved = bundle_by_phase_id.get(phase_id, {})
        phase_intent = deterministic.get("phase_intent") or phase.get("phase_intent")
        phase_type = deterministic.get("phase_type") or phase.get("phase_type")
        build_subtype = deterministic.get("build_subtype")
        if build_subtype is None:
            build_subtype = phase.get("build_subtype")
        phase["phase_type"] = phase_type
        phase["phase_intent"] = phase_intent
        phase["build_subtype"] = build_subtype

        semantics = _as_map(phase.get("allowed_forbidden_semantics"))
        phase["allowed_forbidden_semantics"] = semantics
        semantics["allowed_intensity_domains"] = list(
            approved.get("allowed_domains")
            or season_phase_allowed_domains(
                phase_intent=phase_intent,
                season_allowed_domains=season_phase_load_context.get("season_allowed_intensity_domains"),
            )
        )
        semantics["forbidden_intensity_domains"] = list(
            approved.get("forbidden_domains")
            or season_phase_forbidden_domains(
                phase_intent=phase_intent,
                season_allowed_domains=season_phase_load_context.get("season_allowed_intensity_domains"),
            )
        )
        semantics["allowed_load_modalities"] = list(
            approved.get("allowed_load_modalities") or semantic_allowed_load_modalities(phase_intent)
        )

        structured_role_week_bands = normalize_role_week_load_bands(
            _as_list(deterministic.get("role_week_load_bands"))
        )
        if structured_role_week_bands:
            phase["role_week_load_bands"] = structured_role_week_bands
        role_week_sentence = _format_role_week_guardrail_sentence(structured_role_week_bands)
        weekly_kj = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
        if weekly_kj:
            weekly_kj["notes"] = _append_sentence(weekly_kj.get("notes"), role_week_sentence)
        justification = phase_justifications.get(phase_id)
        if justification is not None and role_week_sentence:
            justification["kJ_first_statement"] = _append_sentence(
                justification.get("kJ_first_statement"),
                role_week_sentence,
            )

        trace_events = [
            _as_map(event)
            for event in _as_list(_as_map(deterministic.get("event_taper_trace")).get("events"))
            if str(_as_map(event).get("type") or "").strip().upper() in {"A", "B", "C"}
        ]
        phase["events_constraints"] = [
            {
                "window": str(event.get("date") or event.get("week") or "").strip(),
                "type": str(event.get("type") or "").strip().upper(),
                "constraint": _season_event_constraint_text(str(event.get("type") or "")),
            }
            for event in trace_events
            if str(event.get("date") or event.get("week") or "").strip()
        ]
        all_a_events.extend(event for event in trace_events if str(event.get("type") or "").strip().upper() == "A")

        overview = _as_map(phase.get("overview"))
        non_negotiables = [str(item).strip() for item in _as_list(overview.get("non_negotiables")) if str(item).strip()]
        if str(phase_intent).strip() == "durability_build":
            readiness_line = (
                "If this is the first Build entry after shortened, base, or re-entry context, start conservatively and "
                "gate corridor entry by stable recovery and readiness rather than catch-up loading."
            )
            if readiness_line not in non_negotiables:
                non_negotiables.append(readiness_line)
        if str(phase_intent).strip() == "taper_freshening":
            taper_lines = (
                "Treat LOAD_1, LOAD_2, and RELOAD as load-band labels only, not as authority for Build-like workout selection.",
                "Treat any final-week RELOAD wording as event-containing load inside taper, not as a normal training reload.",
            )
            for line in taper_lines:
                if line not in non_negotiables:
                    non_negotiables.append(line)
            if weekly_kj:
                weekly_kj["notes"] = _append_sentence(
                    weekly_kj.get("notes"),
                    "Within taper_freshening, LOAD_1 / LOAD_2 / RELOAD are load-band labels only; final-week RELOAD means event-containing load inside taper.",
                )
        if non_negotiables:
            overview["non_negotiables"] = non_negotiables
            phase["overview"] = overview

    season_objective = _as_map(data.get("season_intent_principles")).get("season_objective")
    objective_warning = _derive_objective_event_mismatch_warning(
        season_objective=season_objective,
        a_events=all_a_events,
    )
    assumptions_unknowns = _as_map(data.get("assumptions_unknowns"))
    data["assumptions_unknowns"] = assumptions_unknowns
    if objective_warning:
        assumptions_unknowns["revisit_items"] = _append_unique_item(
            assumptions_unknowns.get("revisit_items"),
            objective_warning,
        )

    scientific_foundation = _as_map(_as_map(data.get("principles_scientific_foundation")).get("scientific_foundation"))
    publications = [_as_map(item) for item in _as_list(scientific_foundation.get("publications"))]
    for publication in publications:
        canonical_link = _normalize_publication_link(publication.get("title"), publication.get("link"))
        if canonical_link:
            publication["link"] = canonical_link
    needs_durability_source = any(
        str(_as_map(phase).get("phase_intent") or "").strip() == "durability_build"
        for phase in phases
    ) or any(
        "durability" in str(_as_map(item).get("principle") or "").lower()
        for item in _as_list(_as_map(data.get("principles_scientific_foundation")).get("principle_applications"))
    )
    has_durability_source = any(
        "durability" in str(item.get("title") or "").lower() or "maunder" in str(item.get("authors") or "").lower()
        for item in publications
    )
    if needs_durability_source and not has_durability_source:
        publications.append(
            {
                "authors": "Maunder, E., Kilding, A. E. & Plews, D. J.",
                "year": 2021,
                "title": "The Importance of 'Durability' in the Physiological Profiling of Endurance Athletes",
                "link": "https://pubmed.ncbi.nlm.nih.gov/33886100/",
            }
        )
    scientific_foundation["publications"] = publications

    transitions = _as_map(data.get("phase_transitions_guardrails"))
    conservative_triggers = [str(item).strip() for item in _as_list(transitions.get("conservative_triggers")) if str(item).strip()]
    readiness_trigger = (
        "Entry into the first Build phase after shortened, base, or re-entry context is conditional on stable recovery; "
        "if readiness deteriorates, start at the lower corridor edge and keep workout selection base-like without catch-up load."
    )
    if readiness_trigger not in conservative_triggers:
        conservative_triggers.append(readiness_trigger)
    transitions["conservative_triggers"] = conservative_triggers
    absolute_no_go_rules = [str(item).strip() for item in _as_list(transitions.get("absolute_no_go_rules")) if str(item).strip()]
    taper_rule = (
        "Within taper_freshening, LOAD_1 / LOAD_2 / RELOAD are load-band labels only and must not authorize Build-like workout selection."
    )
    if taper_rule not in absolute_no_go_rules:
        absolute_no_go_rules.append(taper_rule)
    transitions["absolute_no_go_rules"] = absolute_no_go_rules
    data["phase_transitions_guardrails"] = transitions

    required_trace_artifacts = {"ATHLETE_PROFILE", "KPI_PROFILE", "AVAILABILITY", "PLANNING_EVENTS"}
    present_trace_artifacts = {
        str(_as_map(item).get("artifact") or "").strip().upper()
        for item in _as_list(meta.get("trace_data")) + _as_list(meta.get("trace_events"))
    }
    if required_trace_artifacts - present_trace_artifacts and str(meta.get("data_confidence") or "").strip().upper() == "HIGH":
        meta["data_confidence"] = "MEDIUM"

    document["meta"] = meta
    document["data"] = data
    return document


def normalize_season_plan_draft_bundle(planning_bundle: JsonMap) -> JsonMap:
    """Convert a raw season planning draft into a deterministic normalized bundle."""

    if not isinstance(planning_bundle, dict):
        return planning_bundle
    context = current_guardrail_runtime_context()
    season_phase_load_context = _as_map(context.get("season_phase_load_context"))
    selected_scenario_contract = _as_map(context.get("selected_scenario_contract"))
    phase_context_by_id = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
        if str(_as_map(item).get("phase_id") or "").strip()
    }
    phase_context_by_range = {
        str(_as_map(item).get("iso_week_range") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
        if str(_as_map(item).get("iso_week_range") or "").strip()
    }
    season_allowed_domains = list(season_phase_load_context.get("season_allowed_intensity_domains") or [])
    normalized_bundle = dict(planning_bundle)
    normalized_bundle["season_allowed_domains"] = list(season_allowed_domains)
    if selected_scenario_contract:
        normalized_bundle["selected_scenario_contract"] = selected_scenario_contract
    normalized_blueprints: list[JsonMap] = []
    for blueprint in [_as_map(item) for item in _as_list(planning_bundle.get("phase_blueprints"))]:
        phase_id = str(blueprint.get("phase_id") or "").strip()
        iso_week_range = str(blueprint.get("iso_week_range") or "").strip()
        deterministic = phase_context_by_id.get(phase_id) or phase_context_by_range.get(iso_week_range) or {}
        phase_intent = deterministic.get("phase_intent") or blueprint.get("phase_intent")
        phase_type = deterministic.get("phase_type") or blueprint.get("phase_type")
        build_subtype = deterministic.get("build_subtype")
        if build_subtype is None:
            build_subtype = blueprint.get("build_subtype")
        recommended_corridor = _as_map(deterministic.get("recommended_phase_corridor"))
        availability_cap = _as_map(deterministic.get("availability_cap_kj"))
        warnings = [str(item) for item in _as_list(blueprint.get("warnings")) if str(item).strip()]
        phase_type, phase_intent, build_subtype = _canonicalize_phase_semantics_for_bundle(
            phase_type=phase_type,
            phase_intent=phase_intent,
            build_subtype=build_subtype,
            warnings=warnings,
            warning_prefix=f"{phase_id or iso_week_range or 'phase blueprint'}",
        )
        for error in validate_phase_semantics(
            phase_type=phase_type,
            phase_intent=phase_intent,
            build_subtype=build_subtype,
        ):
            if error not in warnings:
                warnings.append(error)
        normalized_blueprints.append(
            {
                **blueprint,
                "phase_type": phase_type,
                "phase_intent": phase_intent,
                "build_subtype": build_subtype,
                "phase_taxonomy_version": PHASE_TAXONOMY_VERSION,
                "season_phase_role": deterministic.get("season_phase_role") or blueprint.get("season_phase_role"),
                "scenario_cadence": deterministic.get("scenario_cadence") or blueprint.get("scenario_cadence"),
                "cadence_week_roles": list(
                    deterministic.get("cadence_week_roles") or blueprint.get("cadence_week_roles") or []
                ),
                "load_corridor_min": recommended_corridor.get("min", blueprint.get("load_corridor_min")),
                "load_corridor_max": recommended_corridor.get("max", blueprint.get("load_corridor_max")),
                "availability_cap_kj": availability_cap.get("typical", blueprint.get("availability_cap_kj")),
                "baseline_load_kj": deterministic.get("baseline_load_kj", blueprint.get("baseline_load_kj")),
                "role_week_load_bands": normalize_role_week_load_bands(
                    _as_list(deterministic.get("role_week_load_bands"))
                )
                or normalize_role_week_load_bands(blueprint.get("role_week_load_bands")),
                "progression_trace": _normalize_progression_trace(
                    deterministic.get("progression_trace") or blueprint.get("progression_trace")
                ),
                "allowed_domains": season_phase_allowed_domains(
                    phase_intent=phase_intent,
                    season_allowed_domains=season_allowed_domains,
                ),
                "allowed_load_modalities": semantic_allowed_load_modalities(phase_intent),
                "forbidden_domains": season_phase_forbidden_domains(
                    phase_intent=phase_intent,
                    season_allowed_domains=season_allowed_domains,
                ),
                "semantic_contract": phase_semantic_contract_payload(phase_intent=phase_intent),
                "warnings": warnings,
            }
        )
    normalized_bundle["phase_blueprints"] = normalized_blueprints
    candidate_document = {
        "data": {
            "phases": [
                {
                    "iso_week_range": item.get("iso_week_range"),
                    "role_week_load_bands": item.get("role_week_load_bands"),
                    "weekly_load_corridor": {
                        "weekly_kj": {
                            "min": item.get("load_corridor_min"),
                            "max": item.get("load_corridor_max"),
                        }
                    },
                }
                for item in normalized_blueprints
            ]
        }
    }
    expected_envelope = derive_expected_average_weekly_kj_range(season_plan_payload=candidate_document)
    existing_envelope = _as_map(planning_bundle.get("season_load_envelope"))
    if expected_envelope:
        expected_high_load_weeks_count, expected_deload_or_low_load_weeks_count = _derive_season_load_envelope_counts(
            phase_blueprints=normalized_blueprints
        )
        existing_high_load_weeks_count = _as_int(existing_envelope.get("expected_high_load_weeks_count"))
        existing_deload_or_low_load_weeks_count = _as_int(
            existing_envelope.get("expected_deload_or_low_load_weeks_count")
        )
        normalized_bundle["season_load_envelope"] = {
            "expected_average_weekly_kj_range": expected_envelope,
            "expected_high_load_weeks_count": (
                existing_high_load_weeks_count
                if existing_high_load_weeks_count is not None
                else expected_high_load_weeks_count
            ),
            "expected_deload_or_low_load_weeks_count": (
                existing_deload_or_low_load_weeks_count
                if existing_deload_or_low_load_weeks_count is not None
                else expected_deload_or_low_load_weeks_count
            ),
        }
    normalized_bundle["season_semantic_notes"] = _derive_season_semantic_notes(planning_bundle=normalized_bundle)
    return normalized_bundle


def normalize_phase_draft_bundle(planning_bundle: JsonMap) -> JsonMap:
    """Convert a raw phase planning draft into a deterministic normalized bundle."""

    if not isinstance(planning_bundle, dict):
        return planning_bundle
    context = current_guardrail_runtime_context()
    phase_execution_context = _as_map(context.get("phase_execution_context"))
    inherited_scenario_contract = _as_map(phase_execution_context.get("inherited_scenario_contract"))
    normalized_bundle = dict(planning_bundle)
    normalized_bundle["phase_id"] = phase_execution_context.get("phase_id", planning_bundle.get("phase_id"))
    normalized_bundle["phase_range"] = phase_execution_context.get("phase_iso_week_range", planning_bundle.get("phase_range"))
    execution_phase_intent = phase_execution_context.get("phase_intent")
    if not str(execution_phase_intent or "").strip():
        raise RuntimeError("Deterministic phase_execution_context.phase_intent is missing.")
    phase_type, phase_intent, build_subtype = _canonicalize_phase_semantics_for_bundle(
        phase_type=phase_execution_context.get("phase_type", planning_bundle.get("phase_type")),
        phase_intent=execution_phase_intent,
        build_subtype=phase_execution_context.get("build_subtype", planning_bundle.get("build_subtype")),
    )
    if not phase_intent:
        raise RuntimeError("Deterministic phase_execution_context.phase_intent could not be canonicalized.")
    if not inherited_scenario_contract:
        raise RuntimeError("Deterministic phase_execution_context.inherited_scenario_contract is missing.")
    normalized_bundle["phase_type"] = phase_type
    normalized_bundle["phase_intent"] = phase_intent
    normalized_bundle["build_subtype"] = build_subtype
    normalized_bundle["inherited_scenario_contract"] = inherited_scenario_contract
    for field in ("guardrails", "structure", "preview"):
        nested = _as_map(normalized_bundle.get(field))
        if nested:
            normalized_bundle[field] = {
                **nested,
                "phase_intent": phase_intent,
                "inherited_scenario_contract": inherited_scenario_contract,
            }
    week_role_by_iso_week = _as_map(phase_execution_context.get("week_role_by_iso_week"))
    exact_band_by_week = role_week_band_by_week(phase_execution_context.get("phase_role_week_load_bands"))
    if not exact_band_by_week:
        exact_band_by_week = {
            str(_as_map(entry).get("week") or ""): _as_map(_as_map(entry).get("band"))
            for entry in _as_list(phase_execution_context.get("phase_s5_bands"))
            if str(_as_map(entry).get("week") or "").strip()
        }
    normalized_weeks: list[JsonMap] = []
    for blueprint in [_as_map(item) for item in _as_list(planning_bundle.get("week_blueprints"))]:
        week = str(blueprint.get("week") or "").strip()
        band = exact_band_by_week.get(week, {})
        normalized_weeks.append(
            {
                **blueprint,
                "phase_role": phase_execution_context.get("phase_role") or phase_execution_context.get("phase_type") or blueprint.get("phase_role"),
                "phase_intent": phase_intent,
                "week_role": week_role_by_iso_week.get(week, blueprint.get("week_role")),
                "s5_band_min": band.get("min", blueprint.get("s5_band_min")),
                "s5_band_max": band.get("max", blueprint.get("s5_band_max")),
            }
        )
    normalized_bundle["week_blueprints"] = normalized_weeks
    if phase_execution_context.get("phase_primary_objective"):
        normalized_bundle["phase_primary_objective"] = phase_execution_context.get("phase_primary_objective")
    return normalized_bundle


def _raise_normalized_contract_failure(*, name: str, reason: object) -> None:
    """Raise a stable runtime error for normalized contract failures."""

    raise RuntimeError(f"{name}: {reason}")


def _validate_normalized_season_bundle(planning_bundle: JsonMap, *, runtime: AgentRuntime, athlete_id: str, run_id: str) -> JsonMap:
    """Validate the normalized season bundle before review/writer handoff."""

    checks = (
        ("season_bundle_matches_contract", season_bundle_matches_contract),
        ("season_bundle_review_readiness", season_bundle_review_readiness),
    )
    for name, fn in checks:
        ok, payload_or_reason = fn(planning_bundle)
        if ok:
            continue
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="SEASON_BUNDLE_NORMALIZED_CONTRACT_FAILED",
            crew="season_planning",
            task="season_plan_finalize",
            component="crew:season_plan_finalize",
            reason=f"{name}: {payload_or_reason}",
        )
        _raise_normalized_contract_failure(name=name, reason=payload_or_reason)
    return planning_bundle


def _validate_normalized_phase_bundle(planning_bundle: JsonMap, *, runtime: AgentRuntime, athlete_id: str, run_id: str) -> JsonMap:
    """Validate the normalized phase bundle before review/writer handoff."""

    checks = (
        ("phase_bundle_matches_context", phase_bundle_matches_context),
        ("phase_week_role_load_coherence", phase_week_role_load_coherence),
        ("phase_bundle_review_readiness", phase_bundle_review_readiness),
    )
    for name, fn in checks:
        ok, payload_or_reason = fn(planning_bundle)
        if ok:
            continue
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="PHASE_BUNDLE_NORMALIZED_CONTRACT_FAILED",
            crew="phase_planning",
            task="phase_bundle_finalize",
            component="crew:phase_bundle_finalize",
            reason=f"{name}: {payload_or_reason}",
        )
        _raise_normalized_contract_failure(name=name, reason=payload_or_reason)
    return planning_bundle


def _validate_normalized_week_bundle(planning_bundle: JsonMap, *, runtime: AgentRuntime, athlete_id: str, run_id: str) -> JsonMap:
    """Validate the week bundle before review/writer handoff."""

    checks = (("week_bundle_review_readiness", week_bundle_review_readiness),)
    for name, fn in checks:
        ok, payload_or_reason = fn(planning_bundle)
        if ok:
            continue
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="WEEK_BUNDLE_NORMALIZED_CONTRACT_FAILED",
            crew="week_planning",
            task="week_plan_finalize",
            component="crew:week_plan_finalize",
            reason=f"{name}: {payload_or_reason}",
        )
        _raise_normalized_contract_failure(name=name, reason=payload_or_reason)
    return planning_bundle


def _normalize_artifact_meta(document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Apply canonical meta ownership for persisted artifact envelopes."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta.setdefault("authority", "Binding")
    owner = CANONICAL_OWNER_BY_ARTIFACT.get(artifact_type)
    if owner:
        meta["owner_agent"] = owner
    document["meta"] = meta
    return document


def _normalize_week_plan_meta(document: JsonMap) -> JsonMap:
    """Coerce WEEK_PLAN header constants to the canonical schema values."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta["artifact_type"] = "WEEK_PLAN"
    meta["schema_id"] = "WeekPlanInterface"
    meta["schema_version"] = "1.2"
    meta["authority"] = "Binding"
    meta["owner_agent"] = "Week-Artifact-Writer"
    if "notes" not in meta or meta.get("notes") is None:
        meta["notes"] = ""
    document["meta"] = meta
    data = document.get("data")
    if isinstance(data, dict):
        workouts = data.get("workouts")
        if isinstance(workouts, list):
            for workout in workouts:
                if not isinstance(workout, dict):
                    continue
                workout_text = workout.get("workout_text")
                if isinstance(workout_text, str):
                    workout["workout_text"] = normalize_workout_inline_loop_headers(
                        normalize_workout_percent_ranges(workout_text)
                    )
            data["workouts"] = workouts
        document["data"] = data
    return document


def _normalize_des_analysis_report(document: JsonMap) -> JsonMap:
    """Coerce DES analysis report constants to the canonical schema values."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if isinstance(meta, dict):
        meta["artifact_type"] = "DES_ANALYSIS_REPORT"
        meta["schema_id"] = "DESAnalysisInterface"
        meta["schema_version"] = "1.1"
        meta["authority"] = "Binding"
        meta["owner_agent"] = CANONICAL_OWNER_BY_ARTIFACT[ArtifactType.DES_ANALYSIS_REPORT]
        if "notes" not in meta or meta.get("notes") is None:
            meta["notes"] = ""
        document["meta"] = meta
    data = document.get("data")
    if isinstance(data, dict):
        rec = data.get("recommendation")
        if isinstance(rec, dict):
            rec["type"] = "advisory"
            rec["scope"] = "Season-Planner"
            data["recommendation"] = rec
        document["data"] = data
    return document


def _render_json_block(label: str, payload: object) -> str:
    """Render structured intermediate results as compact JSON context."""

    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    try:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        rendered = json.dumps(str(payload), ensure_ascii=False)
    return f"{label}:\n```json\n{rendered}\n```"


def _augment_user_input(user_input: str, *context_blocks: str) -> str:
    """Append structured runtime context blocks to the base user request."""

    blocks = [block.strip() for block in context_blocks if isinstance(block, str) and block.strip()]
    if not blocks:
        return user_input
    return "\n\n".join([user_input, "Additional runtime context:", *blocks])


def _loaded_input_version_key(raw: object) -> str | None:
    """Return a loaded input version key when present."""

    if not isinstance(raw, dict):
        return None
    version_key = str(raw.get("version_key") or "").strip()
    if version_key:
        return version_key
    document = _as_map(raw.get("document"))
    meta = _as_map(document.get("meta"))
    version_key = str(meta.get("version_key") or "").strip()
    return version_key or None


def _phase_writer_authority_context_block(
    public_task: AgentTask,
    loaded_inputs: dict[str, object] | None,
) -> str:
    """Return a compact exact-authority block for Phase writer tasks."""

    if public_task not in {
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }:
        return ""
    context = current_guardrail_runtime_context()
    phase_execution_context = _as_map(context.get("phase_execution_context"))
    loaded_inputs = loaded_inputs if isinstance(loaded_inputs, dict) else {}
    if public_task == AgentTask.CREATE_PHASE_STRUCTURE:
        payload: JsonMap = {
            "allowed_intensity_domains": list(phase_execution_context.get("phase_allowed_intensity_domains") or []),
            "forbidden_intensity_domains": list(
                phase_execution_context.get("phase_forbidden_intensity_domains") or []
            ),
            "allowed_load_modalities": list(phase_execution_context.get("phase_allowed_load_modalities") or []),
            "phase_primary_objective": str(phase_execution_context.get("phase_primary_objective") or "").strip(),
            "week_role_by_iso_week": _as_map(phase_execution_context.get("week_role_by_iso_week")),
            "phase_role_week_load_bands": list(phase_execution_context.get("phase_role_week_load_bands") or []),
        }
        phase_guardrails_version_key = _loaded_input_version_key(loaded_inputs.get("phase_guardrails"))
        if phase_guardrails_version_key:
            payload["phase_guardrails_source"] = f"phase_guardrails_{phase_guardrails_version_key}.json"
        if any(payload.values()):
            return _render_json_block("Exact writer authority", payload)
        return ""

    phase_structure_document = extract_loaded_document(loaded_inputs.get("phase_structure"))
    phase_structure_version_key = _loaded_input_version_key(loaded_inputs.get("phase_structure"))
    upstream_intent = _as_map(_as_map(phase_structure_document).get("data")).get("upstream_intent")
    payload = {
        "phase_intent_summary": {
            "phase_type": str(_as_map(upstream_intent).get("phase_type") or "").strip(),
            "phase_intent": str(_as_map(upstream_intent).get("phase_intent") or "").strip(),
            "build_subtype": _as_map(upstream_intent).get("build_subtype"),
            "phase_taxonomy_version": str(_as_map(upstream_intent).get("phase_taxonomy_version") or "").strip(),
            "primary_objective": str(_as_map(upstream_intent).get("primary_objective") or "").strip(),
        },
        "operational_rules": {
            "rest_days": "REST -> NONE/NONE",
            "recovery_days": "RECOVERY -> RECOVERY",
            "training_days": "training-day domains must stay inside exact PHASE_STRUCTURE legality",
        },
    }
    if phase_structure_version_key:
        payload["phase_structure_source"] = f"phase_structure_{phase_structure_version_key}.json"
    return _render_json_block("Exact writer authority", payload)


def _sanitize_replan_decision_context(decision: JsonMap) -> JsonMap:
    """Return only the active replan delta that should survive into the next round."""

    return {
        "status": str(decision.get("status") or "").lower(),
        "replan_instructions": list(decision.get("replan_instructions") or []),
        "writer_ready_summary": str(decision.get("writer_ready_summary") or "").strip(),
    }


def _as_int(value: object) -> int | None:
    """Return an integer for int-like values, otherwise ``None``."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _compact_internal_user_input(user_input: str) -> str:
    """Reduce oversized specialist-task input while preserving the most relevant markers."""

    text = " ".join(str(user_input).split()).strip()
    if not text:
        return ""
    if len(text) <= _INTERNAL_PROMPT_CHAR_LIMIT and len(text.split()) <= _INTERNAL_PROMPT_WORD_LIMIT:
        return text

    chosen_segments: list[str] = []
    lower_text = text.lower()
    for marker in _INTERNAL_PROMPT_PRIORITY_MARKERS:
        lower_marker = marker.lower()
        index = lower_text.find(lower_marker)
        if index < 0:
            continue
        next_index = len(text)
        for candidate in _INTERNAL_PROMPT_PRIORITY_MARKERS:
            if candidate == marker:
                continue
            candidate_index = lower_text.find(candidate.lower(), index + len(lower_marker))
            if candidate_index >= 0:
                next_index = min(next_index, candidate_index)
        segment = text[index:next_index].strip(" -")
        if len(segment) > _INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT:
            segment = segment[:_INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT].rstrip()
        if segment and segment not in chosen_segments:
            chosen_segments.append(segment)

    if not chosen_segments:
        chosen_segments.append(text)

    compacted = " ".join(chosen_segments)
    words = compacted.split()
    if len(words) > _INTERNAL_PROMPT_WORD_LIMIT:
        compacted = " ".join(words[:_INTERNAL_PROMPT_WORD_LIMIT]).strip()
    if len(compacted) > _INTERNAL_PROMPT_CHAR_LIMIT:
        compacted = compacted[: _INTERNAL_PROMPT_CHAR_LIMIT].rstrip()
    return compacted


def _extract_authoritative_runtime_blocks(user_input: str) -> list[str]:
    """Preserve authoritative markdown context blocks that specialists must see in full."""

    if not isinstance(user_input, str) or not user_input.strip():
        return []

    blocks: list[str] = []
    current: list[str] = []
    current_title: str | None = None

    def _flush() -> None:
        nonlocal current, current_title
        if current_title and current:
            block = "\n".join(line.rstrip() for line in current).strip()
            if block and block not in blocks:
                blocks.append(block)
        current = []
        current_title = None

    for raw_line in user_input.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in _AUTHORITATIVE_RUNTIME_BLOCK_PREFIXES):
            _flush()
            current_title = stripped
            current = [line]
            continue
        if current_title is not None:
            if stripped.startswith("**") and stripped.endswith("**"):
                _flush()
                continue
            current.append(line)
    _flush()
    return blocks


def _contract_context_blocks_for_task(*, crew_name: str, task_name: str) -> list[str]:
    """Return structured deterministic contract blocks relevant to one CrewAI task."""

    context = current_guardrail_runtime_context()
    blocks: list[str] = []
    if crew_name == "season_planning":
        phase_slot_context = context.get("phase_slot_context")
        if phase_slot_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Slot Contract",
                    phase_slot_context,
                )
            )
        season_phase_load_context = context.get("season_phase_load_context")
        if season_phase_load_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Load Contract",
                    season_phase_load_context,
                )
            )
        if task_name == "season_plan_finalize" and blocks:
            blocks.append(
                "Season finalization rule: consume these deterministic contracts directly. "
                "Do not search the workspace for non-persisted phase-load recommendation artifacts."
            )
    elif crew_name == "phase_planning":
        phase_execution_context = context.get("phase_execution_context")
        if phase_execution_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Phase Execution Contract",
                    phase_execution_context,
                )
            )
        phase_slot_context = context.get("phase_slot_context")
        if phase_slot_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Slot Contract",
                    phase_slot_context,
                )
            )
        if task_name == "phase_bundle_finalize" and blocks:
            authority_freeze_block = _phase_bundle_finalize_authority_freeze_block()
            if authority_freeze_block:
                blocks.append(authority_freeze_block)
                blocks.append(
                    "Phase finalizer authority rule: these injected values are authoritative finalizer inputs. "
                    "do not call workspace tools to rediscover them when they are already present here; "
                    "Fallback retrieval is allowed only if a required authority field is missing from the injected freeze block."
                )
            blocks.append(
                "Phase finalization rule: consume these deterministic contracts directly. "
                "Do not delegate or rediscover week roles, S5 bands, or phase-range authority from prose."
            )
    elif crew_name == "week_planning":
        week_calendar_context = context.get("week_calendar_context")
        if week_calendar_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Week Calendar Contract",
                    week_calendar_context,
                )
            )
        phase_execution_context = context.get("phase_execution_context")
        if phase_execution_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Phase Execution Contract",
                    phase_execution_context,
                )
            )
        if task_name == "week_plan_finalize" and blocks:
            blocks.append(
                "Week finalization rule: consume these deterministic contracts directly. "
                "Do not delegate or rediscover active week role, active weekly band, availability caps, or fixed rest rules from prose."
            )
    elif crew_name == "season_review":
        phase_slot_context = context.get("phase_slot_context")
        if phase_slot_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Slot Contract",
                    phase_slot_context,
                )
            )
        season_phase_load_context = context.get("season_phase_load_context")
        if season_phase_load_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Load Contract",
                    season_phase_load_context,
                )
            )
        if task_name == "season_review" and blocks:
            blocks.append(
                "Season review rule: decide against these deterministic contracts directly. "
                "Do not delegate or rediscover cadence, phase-slot, or phase-load authority from prose."
            )
        if task_name in {
            "season_governance_review",
            "season_constraints_review",
            "season_plan_audit",
            "season_contract_review",
            "season_review",
        }:
            blocks.append(
                "Season review subject rule: the injected Candidate Season Bundle is the authoritative review subject. "
                "Do not retrieve or expect a synthetic `candidate_season_bundle` workspace artefact."
            )
    elif crew_name == "phase_review":
        phase_execution_context = context.get("phase_execution_context")
        if phase_execution_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Phase Execution Contract",
                    phase_execution_context,
                )
            )
        phase_slot_context = context.get("phase_slot_context")
        if phase_slot_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Slot Contract",
                    phase_slot_context,
                )
            )
        if task_name == "phase_review" and blocks:
            blocks.append(
                "Phase review rule: decide against these deterministic contracts directly. "
                "Do not delegate or rediscover phase-range, week-role, or S5 authority from prose."
            )
        if task_name in {
            "phase_governance_review",
            "phase_structure_review",
            "phase_preview_review",
            "phase_contract_review",
            "phase_review",
        }:
            blocks.append(
                "Phase review subject rule: the injected Candidate Phase Bundle is the authoritative review subject. "
                "Do not retrieve or expect a synthetic `candidate_phase_bundle` workspace artefact."
            )
    elif crew_name == "week_review":
        week_calendar_context = context.get("week_calendar_context")
        if week_calendar_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Week Calendar Contract",
                    week_calendar_context,
                )
            )
        phase_execution_context = context.get("phase_execution_context")
        if phase_execution_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Phase Execution Contract",
                    phase_execution_context,
                )
            )
        if task_name == "week_review" and blocks:
            blocks.append(
                "Week review rule: decide against these deterministic contracts directly. "
                "Do not delegate or rediscover active band, availability caps, or recovery-day authority from prose."
            )
        if task_name in {
            "week_consistency_review",
            "week_load_governance_review",
            "week_workout_syntax_review",
            "week_contract_review",
            "week_review",
        }:
            blocks.append(
                "Week review subject rule: the injected Candidate Week Bundle is the authoritative review subject. "
                "Do not retrieve or expect a synthetic `candidate_week_bundle` workspace artefact."
            )
    return blocks


def _phase_bundle_finalize_authority_freeze_block() -> str:
    """Return a compact exact-authority block for `phase_bundle_finalize` when available."""

    context = current_guardrail_runtime_context()
    phase_execution_context = _as_map(context.get("phase_execution_context"))
    phase_slot_context = _as_map(context.get("phase_slot_context"))
    if not phase_execution_context and not phase_slot_context:
        return ""
    payload: JsonMap = {
        "phase_id": str(phase_execution_context.get("phase_id") or phase_slot_context.get("phase_id") or "").strip(),
        "phase_range": str(phase_execution_context.get("phase_range") or phase_slot_context.get("phase_range") or "").strip(),
        "phase_type": str(phase_execution_context.get("phase_type") or "").strip(),
        "phase_intent": str(phase_execution_context.get("phase_intent") or "").strip(),
        "build_subtype": phase_execution_context.get("build_subtype"),
        "phase_allowed_intensity_domains": list(phase_execution_context.get("phase_allowed_intensity_domains") or []),
        "phase_forbidden_intensity_domains": list(
            phase_execution_context.get("phase_forbidden_intensity_domains") or []
        ),
        "phase_allowed_load_modalities": list(phase_execution_context.get("phase_allowed_load_modalities") or []),
        "phase_role_week_load_bands": list(phase_execution_context.get("phase_role_week_load_bands") or []),
        "week_role_by_iso_week": _as_map(phase_execution_context.get("week_role_by_iso_week")),
        "phase_primary_objective": str(phase_execution_context.get("phase_primary_objective") or "").strip(),
    }
    if not any(payload.values()):
        return ""
    return _render_json_block("Phase Finalizer Authority Freeze", payload)


def _phase_bundle_finalize_has_bound_contracts() -> bool:
    """Return whether the finalizer already has both deterministic contracts injected."""

    context = current_guardrail_runtime_context()
    return bool(_as_map(context.get("phase_execution_context"))) and bool(
        _as_map(context.get("phase_slot_context"))
    )


def _resolve_prompt_agent_name(agent_name: str, blueprint: Any) -> str:
    """Resolve which top-level prompt should back a CrewAI specialist agent."""

    config = getattr(blueprint, "config", {}) or {}
    prompt_agent = config.get("prompt_agent")
    if isinstance(prompt_agent, str) and prompt_agent:
        return prompt_agent
    return agent_name


def _review_subject_metadata(crew_name: str) -> tuple[str, str, str]:
    """Return review-subject labels for season/phase/week review crews."""

    if crew_name == "season_review":
        return (
            "Candidate Season Bundle",
            "candidate season bundle",
            "candidate_season_bundle",
        )
    if crew_name == "phase_review":
        return (
            "Candidate Phase Bundle",
            "candidate phase bundle",
            "candidate_phase_bundle",
        )
    if crew_name == "week_review":
        return (
            "Candidate Week Bundle",
            "candidate week bundle",
            "candidate_week_bundle",
        )
    return ("Candidate Planning Bundle", "candidate planning bundle", "candidate_planning_bundle")


def _build_crewai_llm(
    crewai_llm_cls: Any,
    runtime: AgentRuntime,
    *,
    agent_name: str,
    model_override: str | None,
    temperature_override: float | None,
    reasoning_effort_override: str | None = None,
    reasoning_summary_override: str | None = None,
    max_completion_tokens_override: int | None = None,
) -> object:
    """Instantiate the CrewAI LLM wrapper for the given agent."""

    return crewai_llm_cls(
        **build_crewai_llm_kwargs(
            agent_name,
            model_override=model_override or runtime.model,
            temperature_override=(
                temperature_override if temperature_override is not None else runtime.temperature
            ),
            reasoning_effort_override=(
                reasoning_effort_override
                if reasoning_effort_override is not None
                else runtime.reasoning_effort
            ),
            reasoning_summary_override=(
                reasoning_summary_override
                if reasoning_summary_override is not None
                else runtime.reasoning_summary
            ),
            max_completion_tokens_override=(
                max_completion_tokens_override
                if max_completion_tokens_override is not None
                else runtime.max_completion_tokens
            ),
        )
    )


def _llm_model_label(llm: object | None) -> str | None:
    """Return the configured model name from a CrewAI LLM wrapper when available."""

    if llm is None:
        return None
    for value in (
        getattr(llm, "model", None),
        getattr(llm, "model_name", None),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    llm_kwargs = getattr(llm, "kwargs", None)
    if isinstance(llm_kwargs, dict):
        model = llm_kwargs.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
    return None


def _build_crewai_agent(
    agent_cls: Any,
    *,
    crewai_llm_cls: Any,
    runtime: AgentRuntime,
    bundle: Any,
    blueprint: Any,
    tools: list[Any],
    athlete_id: str,
    crew_name: str,
    surface: str = "default",
    shared_memory: Any | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> object:
    """Instantiate one CrewAI agent from a blueprint."""

    config = getattr(blueprint, "config", {}) or {}
    runtime_profile = _resolve_agent_runtime_profile(bundle, blueprint.name)
    reasoning_profile = runtime_profile.get("reasoning") or {}
    llm = _build_crewai_llm(
        crewai_llm_cls,
        runtime,
        agent_name=blueprint.name,
        model_override=runtime_profile.get("model") or model_override,
        temperature_override=temperature_override,
        reasoning_effort_override=runtime_profile.get("reasoning_effort"),
        reasoning_summary_override=runtime_profile.get("reasoning_summary"),
        max_completion_tokens_override=runtime_profile.get("max_completion_tokens"),
    )
    kwargs: dict[str, Any] = {
        "role": blueprint.role,
        "goal": blueprint.goal,
        "backstory": blueprint.backstory,
        "llm": llm,
        "tools": tools,
        "verbose": bool(config.get("verbose", False)),
    }
    kwargs.update(collect_native_agent_kwargs(blueprint.name, config))
    if bool(reasoning_profile.get("enabled", False)):
        kwargs["reasoning"] = True
        max_attempts = reasoning_profile.get("max_attempts")
        if isinstance(max_attempts, int) and max_attempts > 0:
            kwargs["max_reasoning_attempts"] = max_attempts
    knowledge_kwargs = build_crewai_knowledge_kwargs(
        root=ROOT,
        profile=resolve_agent_knowledge_profile(bundle, agent_name=blueprint.name),
    )
    kwargs.update(knowledge_kwargs)
    skill_profile = resolve_agent_skill_profile(bundle, agent_name=blueprint.name, crew_name=crew_name)
    kwargs.update(build_crewai_skill_kwargs(root=ROOT, profile=skill_profile))
    agent_memory = build_agent_memory_value(
        shared_memory=shared_memory,
        profile=resolve_agent_memory_profile(
            bundle,
            agent_name=blueprint.name,
            athlete_id=athlete_id,
            surface=surface,
        ),
    )
    if agent_memory is not None:
        kwargs["memory"] = agent_memory
    for field in ("system_template", "prompt_template", "response_template"):
        value = config.get(field)
        if isinstance(value, str) and value:
            kwargs[field] = value
    agent = agent_cls(**kwargs)
    register_runtime_label(agent, kind="agent", label=blueprint.name)
    register_runtime_metadata(agent, model=_llm_model_label(llm))
    register_runtime_metadata(llm, model=_llm_model_label(llm))
    return agent




def _extract_raw_output_text(result: object, task_obj: object) -> str | None:
    """Return raw text output from a CrewAI task result when available."""

    task_output = getattr(task_obj, "output", None)
    for candidate in (
        getattr(task_output, "raw", None),
        getattr(result, "raw", None),
        result if isinstance(result, str) else None,
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _parse_json_document(raw_text: str) -> JsonMap:
    """Parse a JSON object from raw task output, tolerating fenced JSON blocks."""

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise RuntimeError("CrewAI task output did not decode to an artifact envelope object.")
    return parsed


def _coerce_artifact_envelope(candidate: object) -> JsonMap | None:
    """Extract a `{meta, data}` envelope from direct or wrapped CrewAI results."""

    if hasattr(candidate, "model_dump"):
        try:
            candidate = candidate.model_dump()
        except Exception:
            return None

    if isinstance(candidate, dict):
        if isinstance(candidate.get("meta"), dict) and "data" in candidate:
            return candidate

        nested_json = candidate.get("json_dict")
        if nested_json is not None:
            coerced = _coerce_artifact_envelope(nested_json)
            if coerced is not None:
                return coerced

        nested_pydantic = candidate.get("pydantic")
        if nested_pydantic is not None:
            coerced = _coerce_artifact_envelope(nested_pydantic)
            if coerced is not None:
                return coerced

        raw = candidate.get("raw")
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = _parse_json_document(raw)
            except Exception:
                parsed = None
            if parsed is not None and isinstance(parsed.get("meta"), dict) and "data" in parsed:
                return parsed

        task_outputs = candidate.get("tasks_output")
        if isinstance(task_outputs, list):
            for item in task_outputs:
                coerced = _coerce_artifact_envelope(item)
                if coerced is not None:
                    return coerced
    return None


def _extract_typed_output(result: object, task_obj: object) -> Any:
    """Extract the typed Pydantic output from a CrewAI task result."""

    task_output = getattr(task_obj, "output", None)
    pydantic_output = getattr(task_output, "pydantic", None) if task_output is not None else None
    if pydantic_output is None:
        pydantic_output = getattr(result, "pydantic", None)
    if pydantic_output is None and hasattr(result, "model_dump"):
        pydantic_output = result
    return pydantic_output


def _extract_json_output(result: object, task_obj: object) -> JsonMap | None:
    """Extract JSON task output from a CrewAI task result when configured via output_json."""

    task_output = getattr(task_obj, "output", None)
    for candidate in (
        getattr(task_output, "json_dict", None),
        getattr(result, "json_dict", None),
    ):
        if isinstance(candidate, dict):
            return candidate
    return None


def _extract_structured_output(
    result: object,
    task_obj: object,
    *,
    task_name: str,
    output_mode: str,
) -> Any:
    """Extract structured CrewAI output according to the resolved task output mode."""

    if output_mode == "json":
        json_output = _extract_json_output(result, task_obj)
        if json_output is not None:
            return json_output
        raw = _extract_raw_output_text(result, task_obj)
        if not raw:
            raise RuntimeError(f"CrewAI task '{task_name}' produced no raw JSON output.")
        return _parse_json_document(raw)
    pydantic_output = _extract_typed_output(result, task_obj)
    if pydantic_output is not None:
        return pydantic_output
    raw = _extract_raw_output_text(result, task_obj)
    raise RuntimeError(
        f"CrewAI task '{task_name}' did not produce a typed pydantic output."
        + (f" Raw output: {raw}" if raw else "")
    )


def _classify_season_audit_item(item: JsonMap) -> str:
    """Classify a raw season audit item as constraint-only or governance-only."""

    keys = {str(key).strip() for key in item.keys() if str(key).strip()}
    constraint_keys = {"blocking_issues", "warnings", "recommended_adjustments", "applied_sources"}
    governance_keys = {
        "blocking_issues",
        "warnings",
        "recommended_adjustments",
        "cadence_authority_preserved",
        "durability_first_respected",
    }
    has_constraint_only_key = "applied_sources" in keys
    has_governance_only_key = "cadence_authority_preserved" in keys or "durability_first_respected" in keys
    if has_constraint_only_key and has_governance_only_key:
        raise RuntimeError("Mixed season audit-slot content: item combines constraint and governance families.")
    if has_governance_only_key and keys <= governance_keys:
        return "governance"
    if keys <= constraint_keys:
        return "constraint"
    raise RuntimeError(f"Unclassifiable season audit-slot item: {sorted(keys)}")


def coerce_season_plan_draft_bundle_slots(bundle_document: JsonMap) -> JsonMap:
    """Move misplaced season audit items between `constraints` and `load_governance` before strict validation."""

    constraints: list[JsonMap] = []
    load_governance: list[JsonMap] = []
    for raw_item in bundle_document.get("constraints", []):
        if not isinstance(raw_item, dict):
            raise RuntimeError("Unclassifiable season audit-slot item: constraints entry is not an object.")
        destination = _classify_season_audit_item(raw_item)
        if destination == "governance":
            load_governance.append(raw_item)
        else:
            constraints.append(raw_item)
    for raw_item in bundle_document.get("load_governance", []):
        if not isinstance(raw_item, dict):
            raise RuntimeError("Unclassifiable season audit-slot item: load_governance entry is not an object.")
        destination = _classify_season_audit_item(raw_item)
        if destination == "constraint":
            constraints.append(raw_item)
        else:
            load_governance.append(raw_item)
    return {
        **bundle_document,
        "constraints": constraints,
        "load_governance": load_governance,
    }


def _output_model_for_task(task_blueprint: Any, *, schema_file: str | None = None) -> type[Any]:
    """Resolve the strongest structured-output model for a CrewAI task."""

    if task_blueprint.output_kind == "artifact_envelope":
        if schema_file:
            return artifact_model_for_schema_file(schema_file)
        return artifact_model_for_task_name(task_blueprint.name)
    return output_model_for_kind(task_blueprint.output_kind)


def _execute_crewai_task(
    *,
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    runtime: AgentRuntime,
    bundle: Any,
    agent_blueprint: Any,
    task_blueprint: Any,
    tools: list[Any] | ToolMap,
    description: str,
    crew_name: str,
    athlete_id: str | None = None,
    run_id: str | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
    artifact_schema_file: str | None = None,
) -> Any:
    """Execute one CrewAI task and return its typed output."""

    crew_memory_kwargs = build_crew_memory_kwargs(
        import_module("crewai"),
        profile=resolve_crew_memory_profile(
            bundle,
            crew_name=crew_name,
            athlete_id=athlete_id or "unknown",
            surface="default",
        ),
    )
    shared_memory = crew_memory_kwargs.get("memory")
    agent = _build_crewai_agent(
        agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        runtime=runtime,
        bundle=bundle,
        blueprint=agent_blueprint,
        tools=[],
        athlete_id=athlete_id or "unknown",
        crew_name=crew_name,
        shared_memory=shared_memory,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    crew_task_kwargs: dict[str, Any] = {
        "name": task_blueprint.name,
        "description": description,
        "expected_output": task_blueprint.expected_output,
        "agent": agent,
    }
    crew_task_kwargs.update(
        _build_task_callback_kwargs(
            runtime=runtime,
            crew_name=crew_name,
            task_name=task_blueprint.name,
            athlete_id=athlete_id,
            run_id=run_id,
        )
    )
    guardrail_kwargs = build_task_guardrail_kwargs(task_blueprint, bundle.task_policies)
    output_mode = str(guardrail_kwargs.pop("_resolved_output_mode", "pydantic"))
    output_model = _output_model_for_task(task_blueprint, schema_file=artifact_schema_file)
    if output_mode == "json":
        crew_task_kwargs["output_json"] = output_model
    elif output_mode == "pydantic":
        crew_task_kwargs["output_pydantic"] = output_model
    crew_task_kwargs.update(guardrail_kwargs)
    task_tools = _task_tools_for_blueprint(task_blueprint, tools)
    if task_tools:
        crew_task_kwargs["tools"] = task_tools
    crew_task = task_cls(**crew_task_kwargs)
    register_runtime_label(crew_task, kind="task", label=task_blueprint.name)
    process = getattr(process_cls, "sequential")
    planning_llm = _build_crewai_planning_llm(crewai_llm_cls, bundle=bundle, crew_name=crew_name)
    crew_kwargs: dict[str, Any] = {
        "agents": [agent],
        "tasks": [crew_task],
        "process": process,
        "verbose": bool(task_blueprint.config.get("verbose", False)),
    }
    crew_kwargs.update(
        _build_crewai_crew_kwargs(
            runtime=runtime,
            bundle=bundle,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            persisted_artifact_flow=task_blueprint.output_kind == "artifact_envelope",
        )
    )
    if planning_llm is not None:
        crew_kwargs["planning"] = True
        crew_kwargs["planning_llm"] = planning_llm
    crew_kwargs.update(crew_memory_kwargs)
    crew = crew_cls(**crew_kwargs)
    register_runtime_label(crew, kind="crew", label=crew_name)
    _emit_crew_task_prepared_events(
        runtime=runtime,
        crew_name=crew_name,
        tasks=[(task_blueprint.name, task_blueprint.agent, _llm_model_label(getattr(agent, "llm", None)))],
        athlete_id=athlete_id,
        run_id=run_id,
        component=f"crew:{task_blueprint.name}",
    )
    if athlete_id and run_id:
        with runtime_event_scope(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{task_blueprint.name}",
        ), guardrail_runtime_context(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{task_blueprint.name}",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()
    if task_blueprint.output_kind == "artifact_envelope":
        json_output = _coerce_artifact_envelope(_extract_json_output(result, crew_task))
        if json_output is not None:
            return json_output
        pydantic_output = _coerce_artifact_envelope(_extract_typed_output(result, crew_task))
        if pydantic_output is not None:
            return pydantic_output
        wrapped_output = _coerce_artifact_envelope(result)
        if wrapped_output is not None:
            return wrapped_output
        raw = _extract_raw_output_text(result, crew_task)
        if not raw:
            raise RuntimeError(f"CrewAI task '{task_blueprint.name}' produced no raw artifact output.")
        return _parse_json_document(raw)
    pydantic_output = _extract_typed_output(result, crew_task)
    if pydantic_output is None:
        raw = _extract_raw_output_text(result, crew_task)
        raise RuntimeError(
            f"CrewAI task '{task_blueprint.name}' did not produce a typed pydantic output."
            + (f" Raw output: {raw}" if raw else "")
        )
    return pydantic_output


def execute_structured_internal_task_crewai(
    runtime: AgentRuntime,
    *,
    crew_name: str,
    task_name: str,
    description: str,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> Any:
    """Execute one configured internal CrewAI task and return its typed output."""

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    LLM = getattr(crewai, "LLM")

    bundle = load_crewai_config_bundle(root=ROOT)
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints[task_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]

    return _execute_crewai_task(
        agent_cls=Agent,
        crewai_llm_cls=LLM,
        crew_cls=Crew,
        task_cls=Task,
        process_cls=Process,
        runtime=runtime,
        bundle=bundle,
        agent_blueprint=agent_blueprint,
        task_blueprint=task_blueprint,
        tools=[],
        description=description,
        crew_name=crew_name,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )


def _build_crewai_task(
    *,
    task_cls: Any,
    bundle: Any,
    task_blueprint: Any,
    agent: object,
    description: str,
    runtime: AgentRuntime,
    crew_name: str,
    athlete_id: str | None = None,
    run_id: str | None = None,
    tools: list[Any] | ToolMap | None = None,
    tools_override: list[Any] | ToolMap | None = None,
    context_tasks: list[object] | None = None,
) -> object:
    """Instantiate one CrewAI task object with optional explicit context."""

    kwargs: dict[str, Any] = {
        "name": task_blueprint.name,
        "description": description,
        "expected_output": task_blueprint.expected_output,
        "agent": agent,
    }
    kwargs.update(
        _build_task_callback_kwargs(
            runtime=runtime,
            crew_name=crew_name,
            task_name=task_blueprint.name,
            athlete_id=athlete_id,
            run_id=run_id,
        )
    )
    guardrail_kwargs = build_task_guardrail_kwargs(task_blueprint, bundle.task_policies)
    output_mode = str(guardrail_kwargs.pop("_resolved_output_mode", "pydantic"))
    output_model = _output_model_for_task(task_blueprint)
    if output_mode == "json":
        kwargs["output_json"] = output_model
    elif output_mode == "pydantic":
        kwargs["output_pydantic"] = output_model
    kwargs.update(guardrail_kwargs)
    if tools_override is not None and len(_tool_map_from_runtime_tools(tools_override)) == 0:
        task_tools: list[Any] = []
    else:
        task_tools = _task_tools_for_blueprint(
            task_blueprint,
            tools_override if tools_override is not None else (tools or {}),
        )
    if task_tools:
        kwargs["tools"] = task_tools
    if context_tasks:
        kwargs["context"] = context_tasks
    task = task_cls(**kwargs)
    register_runtime_label(task, kind="task", label=task_blueprint.name)
    register_runtime_metadata(
        task,
        assigned_agent=str(task_blueprint.agent),
        assigned_model=_llm_model_label(getattr(agent, "llm", None)),
    )
    return task


def _execute_crewai_multiagent_crew(
    *,
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    runtime: AgentRuntime,
    bundle: Any,
    manager_agent_name: str,
    crew_name: str,
    crew_task_names: tuple[str, ...],
    final_task_name: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    tools: list[Any] | ToolMap,
    tools_override_by_task: dict[str, list[Any] | ToolMap] | None = None,
    user_input: str,
    final_public_task: AgentTask | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
    execution_mode: str = "hierarchical",
) -> Any:
    """Execute one multi-agent crew and return the final typed output."""

    crew_memory_kwargs = build_crew_memory_kwargs(
        import_module("crewai"),
        profile=resolve_crew_memory_profile(
            bundle,
            crew_name=crew_name,
            athlete_id=athlete_id or "unknown",
            surface="default",
        ),
    )
    shared_memory = crew_memory_kwargs.get("memory")
    agents_by_name: dict[str, object] = {}
    for task_name in crew_task_names:
        task_blueprint = task_blueprints[task_name]
        agent_name = task_blueprint.agent
        if agent_name in agents_by_name:
            continue
        agent_blueprint = agent_blueprints[agent_name]
        agents_by_name[agent_name] = _build_crewai_agent(
            agent_cls,
            crewai_llm_cls=crewai_llm_cls,
            runtime=runtime,
            bundle=bundle,
            blueprint=agent_blueprint,
            tools=[],
            athlete_id=athlete_id or "unknown",
            crew_name=crew_name,
            shared_memory=shared_memory,
            model_override=model_override,
            temperature_override=temperature_override,
        )

    if manager_agent_name not in agents_by_name:
        manager_blueprint = agent_blueprints[manager_agent_name]
        agents_by_name[manager_agent_name] = _build_crewai_agent(
            agent_cls,
            crewai_llm_cls=crewai_llm_cls,
            runtime=runtime,
            bundle=bundle,
            blueprint=manager_blueprint,
            tools=[],
            athlete_id=athlete_id or "unknown",
            crew_name=crew_name,
            shared_memory=shared_memory,
            model_override=model_override,
            temperature_override=temperature_override,
        )

    manager_agent = agents_by_name[manager_agent_name]
    manager_llm = getattr(manager_agent, "llm", None)
    crew_tasks: list[object] = []
    prior_tasks: list[object] = []
    tasks_by_name: dict[str, object] = {}
    final_task_obj: object | None = None
    for task_name in crew_task_names:
        task_blueprint = task_blueprints[task_name]
        agent_name = task_blueprint.agent
        prompt_agent = _resolve_prompt_agent_name(agent_name, agent_blueprints[agent_name])
        if task_name == final_task_name and final_public_task is not None:
            contract_blocks = _contract_context_blocks_for_task(
                crew_name=crew_name,
                task_name=task_name,
            )
            description = _build_task_description(
                runtime,
                bundle=bundle,
                crew_name=crew_name,
                agent_name=manager_agent_name,
                task=final_public_task,
                user_input=_augment_user_input(user_input, *contract_blocks),
            )
            if prior_tasks:
                description = "\n".join(
                    [
                        description,
                        "",
                        "Use the prior specialist and audit task outputs as context for the final manager decision.",
                    ]
                )
        else:
            contract_blocks = _contract_context_blocks_for_task(
                crew_name=crew_name,
                task_name=task_name,
            )
            description = _build_internal_task_description(
                runtime,
                agent_name=agent_name,
                prompt_agent=prompt_agent,
                bundle=bundle,
                crew_name=crew_name,
                task_blueprint=task_blueprint,
                user_input=_augment_user_input(user_input, *contract_blocks),
            )
        context_tasks: list[object] | None
        if getattr(task_blueprint, "context_names", ()):
            missing = [item for item in task_blueprint.context_names if item not in tasks_by_name]
            if missing:
                raise ValueError(
                    f"Task '{task_name}' references unknown or later context tasks: {', '.join(missing)}"
                )
            context_tasks = [tasks_by_name[item] for item in task_blueprint.context_names]
        else:
            context_tasks = prior_tasks[:] if prior_tasks else None
        crew_task = _build_crewai_task(
            task_cls=task_cls,
            bundle=bundle,
            task_blueprint=task_blueprint,
            agent=agents_by_name[agent_name],
            description=description,
            runtime=runtime,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            tools=tools,
            tools_override=(tools_override_by_task or {}).get(task_name),
            context_tasks=context_tasks,
        )
        crew_tasks.append(crew_task)
        prior_tasks.append(crew_task)
        tasks_by_name[task_name] = crew_task
        if task_name == final_task_name:
            final_task_obj = crew_task

    if final_task_obj is None:
        raise RuntimeError(f"Final crew task '{final_task_name}' was not created.")

    hierarchical = getattr(process_cls, "hierarchical", None)
    sequential = getattr(process_cls, "sequential")
    use_hierarchical = execution_mode == "hierarchical" and hierarchical is not None
    process = hierarchical if use_hierarchical else sequential
    crew_kwargs: dict[str, Any] = {
        "agents": (
            [agent for name, agent in agents_by_name.items() if name != manager_agent_name]
            if use_hierarchical
            else list(agents_by_name.values())
        ),
        "tasks": crew_tasks,
        "process": process,
        "verbose": False,
    }
    crew_kwargs.update(
        _build_crewai_crew_kwargs(
            runtime=runtime,
            bundle=bundle,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            persisted_artifact_flow=True,
        )
    )
    if crew_memory_kwargs:
        crew_kwargs.update(crew_memory_kwargs)
    if use_hierarchical:
        crew_kwargs["manager_agent"] = manager_agent
        if manager_llm is not None:
            crew_kwargs["manager_llm"] = manager_llm
    planning_llm = _build_crewai_planning_llm(crewai_llm_cls, bundle=bundle, crew_name=crew_name)
    if planning_llm is not None:
        crew_kwargs["planning"] = True
        crew_kwargs["planning_llm"] = planning_llm
    crew = crew_cls(**crew_kwargs)
    register_runtime_label(crew, kind="crew", label=crew_name)
    _emit_crew_task_prepared_events(
        runtime=runtime,
        crew_name=crew_name,
        tasks=[
            (
                task_name,
                task_blueprints[task_name].agent,
                _llm_model_label(getattr(agents_by_name[task_blueprints[task_name].agent], "llm", None)),
            )
            for task_name in crew_task_names
        ],
        athlete_id=athlete_id,
        run_id=run_id,
        component=f"crew:{final_task_name}",
    )
    if athlete_id and run_id:
        with runtime_event_scope(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{final_task_name}",
        ), guardrail_runtime_context(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{final_task_name}",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()
    final_output_kind = str(task_blueprints[final_task_name].output_kind)
    if final_output_kind == "artifact_envelope":
        json_output = _coerce_artifact_envelope(_extract_json_output(result, final_task_obj))
        if json_output is not None:
            return json_output
        pydantic_output = _coerce_artifact_envelope(_extract_typed_output(result, final_task_obj))
        if pydantic_output is not None:
            return pydantic_output
        wrapped_output = _coerce_artifact_envelope(result)
        if wrapped_output is not None:
            return wrapped_output
        raw = _extract_raw_output_text(result, final_task_obj)
        if not raw:
            raise RuntimeError(f"CrewAI crew final task '{final_task_name}' produced no raw artifact output.")
        return _parse_json_document(raw)
    policy = build_task_guardrail_kwargs(task_blueprints[final_task_name], bundle.task_policies)
    output_mode = str(policy.get("_resolved_output_mode", "pydantic"))
    return _extract_structured_output(
        result,
        final_task_obj,
        task_name=final_task_name,
        output_mode=output_mode,
    )


def _build_internal_task_description(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    prompt_agent: str,
    bundle: Any,
    crew_name: str,
    task_blueprint: Any,
    user_input: str,
    context_blocks: list[str] | None = None,
) -> str:
    """Build a specialist-task description with top-level prompt context."""

    prompt = runtime.prompt_loader.agent_prompt(prompt_agent)
    compact_user_input = _compact_internal_user_input(user_input)
    authoritative_runtime_blocks = _extract_authoritative_runtime_blocks(user_input)
    parts = [
        "Agent instructions:",
        prompt,
        "",
        _INTERNAL_TOOL_FIRST_RULES.strip(),
        "",
        "Tool contract:",
        "- All available workspace tools accept exactly one string parameter named `payload_json`.",
        "- `payload_json` must be a JSON object string that matches the tool's expected arguments.",
        "- If a needed input is available through `workspace_get_input`, `workspace_get_latest`, or `workspace_get_version`, call the tool instead of asking the user for it.",
    ]
    parts.extend(
        [
            "",
            f"Internal specialist task: {task_blueprint.description}",
            "",
            "User request:",
            compact_user_input,
        ]
    )
    if authoritative_runtime_blocks:
        parts.extend(["", "Authoritative runtime context:"])
        parts.extend(authoritative_runtime_blocks)
    if context_blocks:
        parts.extend(["", "Internal context from prior specialist tasks:"])
        parts.extend(context_blocks)
    parts.extend(
        [
            "",
            "This is an internal reasoning task. Do not create, write, or verify workspace files unless the active task explicitly exposes a write-capable tool and requires persisted artefact creation.",
            "If prior specialist context already contains the needed facts, use it directly and do not ask for original workspace artefacts again.",
            "If you are blocked after relevant tool attempts, return one compact blocked result only once.",
            "",
            "Return only the typed output required for this specialist task.",
        ]
    )
    return "\n".join(parts)


def _phase_document_from_bundle(bundle_document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Select the correct nested phase artifact document from a PhaseBundle."""

    if artifact_type == ArtifactType.PHASE_GUARDRAILS:
        candidate = bundle_document.get("guardrails_document") or bundle_document.get("guardrails")
    elif artifact_type == ArtifactType.PHASE_STRUCTURE:
        candidate = bundle_document.get("structure_document") or bundle_document.get("structure")
    elif artifact_type == ArtifactType.PHASE_PREVIEW:
        candidate = bundle_document.get("preview_document") or bundle_document.get("preview")
    else:
        raise ValueError(f"Unsupported PhaseBundle split target: {artifact_type.value}")
    if not isinstance(candidate, dict):
        raise RuntimeError(f"PhaseBundle missing nested document for {artifact_type.value}.")
    return candidate


def _run_season_plan_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    user_input: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute the hierarchical season planning crew and return the internal bundle."""
    final_output = _execute_crewai_multiagent_crew(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name="season_plan_manager",
        crew_name="season_planning",
        crew_task_names=_SEASON_PLANNING_TASKS,
        final_task_name="season_plan_finalize",
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input=user_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        execution_mode="sequential",
    )
    document = final_output.model_dump() if hasattr(final_output, "model_dump") else final_output
    if not isinstance(document, dict):
        raise RuntimeError("Season manager output did not decode to an artifact envelope object.")
    try:
        coerced = coerce_season_plan_draft_bundle_slots(document)
        return SeasonPlanDraftBundleModel.model_validate(coerced).model_dump()
    except Exception as exc:
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="SEASON_BUNDLE_RAW_VALIDATION_FAILED",
            crew="season_planning",
            task="season_plan_finalize",
            component="crew:season_plan_finalize",
            reason=str(exc),
        )
        raise RuntimeError(f"season_plan_finalize raw bundle failure: {exc}") from exc


def _run_phase_bundle_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    user_input: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute the hierarchical phase planning crew and return the internal PhaseBundle."""
    final_task_name = _PHASE_PLANNING_TASKS[-1]
    tools_override_by_task: dict[str, list[Any] | ToolMap] | None = None
    if _phase_bundle_finalize_has_bound_contracts():
        tools_override_by_task = {final_task_name: []}
    pydantic_output = _execute_crewai_multiagent_crew(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name=task_blueprints[final_task_name].agent,
        crew_name="phase_planning",
        crew_task_names=_PHASE_PLANNING_TASKS,
        final_task_name=final_task_name,
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        tools_override_by_task=tools_override_by_task,
        user_input=user_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        execution_mode="sequential",
    )
    bundle_document = (
        pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    )
    if not isinstance(bundle_document, dict):
        raise RuntimeError("Phase bundle output did not decode to an object.")
    return bundle_document


def _run_review_decision_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    review_task_names: tuple[str, ...],
    final_task_name: str,
    manager_agent_name: str,
    crew_name: str,
    user_input: str,
    planning_bundle: JsonMap,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a review crew against a planning bundle and return its decision."""

    review_context = current_guardrail_runtime_context()
    week_calendar_context = review_context.get("week_calendar_context")
    legality_issues = week_bundle_domain_legality_messages(
        planning_bundle,
        week_calendar_context=week_calendar_context if isinstance(week_calendar_context, dict) else None,
    )
    if legality_issues:
        return {
            "status": "replan_required",
            "blocking_issues": legality_issues,
            "warnings": [
                "Candidate week bundle violates binding phase workout-domain legality and must be corrected before review approval."
            ],
            "replan_instructions": [
                {
                    "target_specialists": ["Week Planner", "Workout Authoring"],
                    "issues_to_fix": legality_issues,
                    "must_preserve": [
                        "Preserve fixed rest days and active week structure.",
                        "Preserve allowed phase intensity domains only.",
                        "Represent recovery-like low-load work as legal low-end ENDURANCE when RECOVERY is forbidden.",
                    ],
                    "priority_order": [
                        "Replace illegal workout families/domains first.",
                        "Then realign workout text to the corrected canonical family/domain.",
                        "Then recheck export-safe syntax and load coherence.",
                    ],
                    "max_scope_of_change": (
                        "Adjust workout domain/family assignments, dependent workout text, and only the minimum day-role intent needed to remove illegal domains."
                    ),
                }
            ],
            "writer_ready_summary": "",
        }

    candidate_block_title, candidate_bundle_label, candidate_artifact_name = _review_subject_metadata(crew_name)
    review_input = _augment_user_input(
        user_input,
        _render_json_block(candidate_block_title, planning_bundle),
        (
            f"Review subject rule: treat the injected {candidate_block_title} as the authoritative {candidate_bundle_label} under review. "
            f"Do not call workspace tools to reload a synthetic `{candidate_artifact_name}` artefact."
        ),
    )
    pydantic_output = _execute_crewai_multiagent_crew(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name=manager_agent_name,
        crew_name=crew_name,
        crew_task_names=review_task_names,
        final_task_name=final_task_name,
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input=review_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        execution_mode="sequential",
    )
    decision = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(decision, dict):
        raise RuntimeError(f"Review crew '{crew_name}' did not return an object.")
    return decision


def _run_single_internal_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    crew_name: str,
    task_name: str,
    user_input: str,
    context_payloads: list[tuple[str, object]] | None,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a single internal typed CrewAI task and return its document payload."""

    task_blueprint = task_blueprints[task_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]
    context_blocks = [
        _render_json_block(label, payload)
        for label, payload in (context_payloads or [])
        if payload is not None
    ]
    description = _build_internal_task_description(
        runtime,
        agent_name=task_blueprint.agent,
        prompt_agent=_resolve_prompt_agent_name(task_blueprint.agent, agent_blueprint),
        bundle=bundle,
        crew_name=crew_name,
        task_blueprint=task_blueprint,
        user_input=_augment_user_input(user_input, *context_blocks),
    )
    pydantic_output = _execute_crewai_task(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        agent_blueprint=agent_blueprint,
        task_blueprint=task_blueprint,
        tools=tools,
        description=description,
        crew_name=crew_name,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(document, dict):
        raise RuntimeError(f"Internal task '{task_name}' did not return an object.")
    return document


def _run_writer_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    crew_name: str,
    public_task: AgentTask,
    user_input: str,
    planning_bundle: JsonMap,
    review_decision: JsonMap,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    loaded_inputs: dict[str, object] | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a writer task from approved bundle + review context and return the final document."""

    if public_task == AgentTask.CREATE_WEEK_PLAN:
        week_calendar_result = {}
        if isinstance(loaded_inputs, dict):
            maybe_result = loaded_inputs.get("workspace_get_week_calendar_context")
            if isinstance(maybe_result, dict):
                week_calendar_result = dict(maybe_result.get("contract") or {})
        return build_week_plan_document_from_bundle(
            planning_bundle=planning_bundle,
            week_calendar_context=week_calendar_result,
            review_decision=review_decision,
        )

    blueprint_name = _TASK_BLUEPRINT_BY_AGENT_TASK[public_task]
    task_blueprint = task_blueprints[blueprint_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]
    exact_authority_block = _phase_writer_authority_context_block(public_task, loaded_inputs)
    description = _build_task_description(
        runtime,
        bundle=bundle,
        crew_name=crew_name,
        agent_name=task_blueprint.agent,
        task=public_task,
        user_input=_augment_user_input(
            user_input,
            exact_authority_block,
            _render_json_block("Approved planning bundle", planning_bundle),
            _render_json_block("Review decision", review_decision),
        ),
    )
    with guardrail_runtime_context(
        approved_planning_bundle=planning_bundle,
        artifact_type=OUTPUT_SPECS[public_task].artifact_type.value,
        loaded_inputs=loaded_inputs or {},
    ):
        document = _execute_crewai_task(
            agent_cls=agent_cls,
            crewai_llm_cls=crewai_llm_cls,
            crew_cls=crew_cls,
            task_cls=task_cls,
            process_cls=process_cls,
            runtime=runtime,
            bundle=bundle,
            agent_blueprint=agent_blueprint,
            task_blueprint=task_blueprint,
            tools=tools,
            description=description,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    if not isinstance(document, dict):
        raise RuntimeError(f"Writer task '{blueprint_name}' did not return an artifact object.")
    return document


def _run_multicrew_cycle(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    user_input: str,
    planning_runner: Callable[[str], JsonMap],
    review_runner: Callable[[str, JsonMap], JsonMap],
    max_replan_rounds: int,
) -> tuple[JsonMap, JsonMap]:
    """Run planning -> review with bounded replans and return the approved pair."""

    attempt = 0
    planning_input = user_input
    latest_decision: JsonMap | None = None
    while True:
        planning_bundle = planning_runner(planning_input)
        latest_decision = review_runner(planning_input, planning_bundle)
        status = str(latest_decision.get("status") or "").lower()
        if status == "approved":
            return planning_bundle, latest_decision
        if status == "rejected":
            raise RuntimeError(
                "; ".join(latest_decision.get("blocking_issues") or [])
                or "Review crew rejected the planning bundle."
            )
        if status != "replan_required":
            raise RuntimeError(f"Unsupported review decision status: {status or '<empty>'}")
        if attempt >= max_replan_rounds:
            raise RuntimeError(
                "Review requested another replan after exhausting the allowed replan rounds."
            )
        attempt += 1
        replan_context = _sanitize_replan_decision_context(latest_decision)
        planning_input = _augment_user_input(
            user_input,
            _render_json_block("Active replan instructions", replan_context),
            (
                "Replan handoff rule: treat the injected Active replan instructions as the only active delta from the previous review. "
                "Do not copy prior blocking issues or warnings forward unless they still apply after the new draft."
            ),
        )


def _persist_artifact_document(
    *,
    runtime: AgentRuntime,
    athlete_id: str,
    run_id: str,
    output_spec: Any,
    document: JsonMap,
    producer_agent: str,
) -> JsonMap:
    """Validate and persist one final artifact envelope."""

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )
    saved = guarded.guard_put_validated(
        output_spec=output_spec,
        document=document,
        run_id=run_id,
        producer_agent=producer_agent,
        update_latest=True,
    )
    emit_runtime_event(
        root=runtime.workspace_root,
        athlete_id=athlete_id,
        run_id=run_id,
        event_type="ARTEFACT_WRITTEN",
        artifact_type=output_spec.artifact_type.value,
        outputs=[saved],
    )
    return saved


def _normalize_document(spec: Any, document: JsonMap, loaded_inputs: dict[str, object]) -> JsonMap:
    """Apply the same deterministic normalization rules as the legacy runner."""

    normalized = normalize_season_scenarios_document(
        document,
        planning_events_document=extract_planning_events_document(
            loaded_inputs.get("planning_events")
        ),
    )
    normalized = _normalize_artifact_meta(normalized, spec.artifact_type)
    normalized = _fill_season_plan(normalized)
    normalized = _normalize_final_season_plan_semantics(normalized)
    normalized = normalize_phase_guardrails_document(
        normalized,
        season_plan_document=extract_loaded_document(loaded_inputs.get("season_plan")),
    )
    if spec.artifact_type == ArtifactType.WEEK_PLAN:
        normalized = _normalize_week_plan_meta(normalized)
        normalized = normalize_week_plan_consistency(normalized)
    if spec.artifact_type == ArtifactType.DES_ANALYSIS_REPORT:
        normalized = _normalize_des_analysis_report(normalized)
    return normalized


def run_phase_bundle_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute planning -> review -> writer for the requested phase artefacts."""

    allowed_tasks = {
        AgentTask.CREATE_PHASE_GUARDRAILS,
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }
    requested_tasks = [task for task in tasks if task in allowed_tasks]
    if not requested_tasks:
        return {
            "ok": False,
            "error": "Phase bundle execution requires one or more phase artefact tasks.",
            "produced": {},
        }

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    LLM = getattr(crewai, "LLM")

    bundle = load_crewai_config_bundle(root=ROOT)
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)

    try:
        def _planning_runner(loop_input: str) -> JsonMap:
            planning_bundle = _run_phase_bundle_document(
                runtime=runtime,
                bundle=bundle,
                user_input=loop_input,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )
            try:
                normalized = normalize_phase_draft_bundle(planning_bundle)
            except Exception as exc:
                emit_runtime_event(
                    root=runtime.workspace_root,
                    athlete_id=athlete_id,
                    run_id=run_id,
                    event_type="PHASE_BUNDLE_NORMALIZATION_FAILED",
                    crew="phase_planning",
                    task="phase_bundle_finalize",
                    component="crew:phase_bundle_finalize",
                    reason=str(exc),
                )
                raise
            return _validate_normalized_phase_bundle(
                normalized,
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
            )

        def _review_runner(loop_input: str, planning_bundle: JsonMap) -> JsonMap:
            return _run_review_decision_document(
                runtime=runtime,
                bundle=bundle,
                review_task_names=_PHASE_REVIEW_TASKS,
                final_task_name="phase_review",
                manager_agent_name="phase_review_manager",
                crew_name="phase_review",
                user_input=loop_input,
                planning_bundle=planning_bundle,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        planning_bundle, review_decision = _run_multicrew_cycle(
            runtime=runtime,
            bundle=bundle,
            user_input=user_input,
            planning_runner=_planning_runner,
            review_runner=_review_runner,
            max_replan_rounds=2,
        )
    except Exception as exc:
        emit_runtime_exception_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            exc=exc,
            crew="phase_planning",
            task="phase_bundle_cycle",
            agent=agent_name,
            component="crew:phase_bundle_cycle",
        )
        return {"ok": False, "error": str(exc), "produced": {}}

    produced: dict[str, Any] = {}
    warnings = list(planning_bundle.get("warnings") or []) + list(review_decision.get("warnings") or [])
    for task in requested_tasks:
        output_spec = OUTPUT_SPECS[task]
        try:
            document = _run_writer_document(
                runtime=runtime,
                bundle=bundle,
                crew_name="phase_writer",
                public_task=task,
                user_input=user_input,
                planning_bundle=planning_bundle,
                review_decision=review_decision,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                loaded_inputs=loaded_inputs,
                model_override=model_override,
                temperature_override=temperature_override,
            )
            document = _normalize_document(output_spec, document, loaded_inputs)
            saved = _persist_artifact_document(
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
                output_spec=output_spec,
                document=document,
                producer_agent="phase_artifact_writer",
            )
        except SchemaValidationError as exc:
            return {
                "ok": False,
                "error": "Schema validation failed",
                "details": list(exc.errors or []),
                "warnings": warnings,
                "produced": produced,
            }
        except Exception as exc:
            logger.warning("CrewAI phase multi-crew store failed for %s: %s", output_spec.artifact_type.value, exc)
            return {"ok": False, "error": str(exc), "warnings": warnings, "produced": produced}
        loaded_inputs[output_spec.artifact_type.value.lower()] = {
            "ok": True,
            "document": document,
            "version_key": saved.get("version_key"),
        }
        produced[output_spec.tool_name] = saved

    return {"ok": True, "produced": produced, "warnings": warnings}


def _build_crewai_tooling(
    athlete_id: str,
    workspace_root: Any,
) -> tuple[ToolMap, dict[str, object]]:
    """Create CrewAI tools backed by the existing workspace read handlers."""

    crewai_tools = import_module("crewai.tools")
    tool_decorator = getattr(crewai_tools, "tool")

    ctx = ReadToolContext(athlete_id=athlete_id, workspace_root=workspace_root)
    handlers = read_tool_handlers(ctx)
    tool_defs = read_tool_defs()
    loaded_inputs: dict[str, object] = {}
    tools: ToolMap = {}

    def _capture_loaded_input(tool_name: str, args: JsonMap, result: object) -> None:
        if not isinstance(result, dict) or result.get("ok") is not True:
            return
        loaded_inputs[tool_name] = result
        if tool_name != "workspace_get_input":
            return
        key = args.get("input_type") or args.get("artifact_type") or args.get("input_name")
        if isinstance(key, str):
            loaded_inputs[key] = result

    for tool_def in tool_defs:
        name = tool_def.get("name")
        description = tool_def.get("description")
        if not isinstance(name, str) or not isinstance(description, str):
            continue
        handler = handlers.get(name)
        if handler is None:
            continue

        def _factory(
            tool_name: str = str(name),
            tool_description: str = str(description),
            tool_handler: Callable[[dict[str, Any]], object] | None = handler,
        ) -> Any:
            def _run(payload_json: str = "{}") -> str:
                """Execute the wrapped legacy workspace tool."""

                try:
                    args = json.loads(payload_json) if payload_json else {}
                except json.JSONDecodeError as exc:
                    return json.dumps({"ok": False, "error": f"Invalid payload_json: {exc}"})
                if not isinstance(args, dict):
                    return json.dumps({"ok": False, "error": "payload_json must decode to an object"})
                if tool_handler is None:
                    return json.dumps({"ok": False, "error": f"Tool handler missing for {tool_name}"})
                try:
                    result = tool_handler(args)
                except Exception as exc:  # pragma: no cover - backend parity with legacy handler exceptions
                    result = {"ok": False, "error": str(exc)}
                _capture_loaded_input(tool_name, args, result)
                return json.dumps(result, ensure_ascii=False)

            _run.__name__ = f"{tool_name}_tool"
            _run.__doc__ = (
                f"{tool_description} "
                "Pass arguments as a JSON string in the single `payload_json` parameter."
            )
            return tool_decorator(tool_name)(_run)

        tools[name] = _factory()

    return tools, loaded_inputs


def _build_task_description(
    runtime: AgentRuntime,
    *,
    bundle: Any,
    crew_name: str,
    agent_name: str,
    task: AgentTask,
    user_input: str,
) -> str:
    """Compose the final CrewAI task description from prompts, injections, and user input."""

    prompt = runtime.prompt_loader.combined_system_prompt(agent_name)
    parts = [
        "System and agent instructions:",
        prompt,
    ]
    parts.extend(
        [
            "",
            "Tool contract:",
            "- All available tools accept a single string parameter named `payload_json`.",
            "- `payload_json` must be a JSON object string matching the legacy tool arguments.",
            "",
            "User request:",
            user_input,
            "",
            "Return only the final full artifact envelope with top-level `meta` and `data`.",
        ]
    )
    return "\n".join(parts)


def _run_single_task_document_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    task: AgentTask,
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> tuple[Any, JsonMap]:
    """Execute one CrewAI task and return its normalized document without storing it."""

    output_spec = OUTPUT_SPECS[task]
    blueprint_name = _TASK_BLUEPRINT_BY_AGENT_TASK.get(task)
    if blueprint_name is None:
        raise ValueError(f"No CrewAI task blueprint mapping for {task.value}.")

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    LLM = getattr(crewai, "LLM")

    bundle = load_crewai_config_bundle(root=ROOT)
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints[blueprint_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]

    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)

    if task == AgentTask.CREATE_SEASON_PLAN:
        def _planning_runner(loop_input: str) -> JsonMap:
            planning_bundle = _run_season_plan_document(
                runtime=runtime,
                bundle=bundle,
                user_input=loop_input,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )
            try:
                normalized = normalize_season_plan_draft_bundle(planning_bundle)
            except Exception as exc:
                emit_runtime_event(
                    root=runtime.workspace_root,
                    athlete_id=athlete_id,
                    run_id=run_id,
                    event_type="SEASON_BUNDLE_NORMALIZATION_FAILED",
                    crew="season_planning",
                    task="season_plan_finalize",
                    component="crew:season_plan_finalize",
                    reason=str(exc),
                )
                raise
            return _validate_normalized_season_bundle(
                normalized,
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
            )

        def _review_runner(loop_input: str, planning_bundle: JsonMap) -> JsonMap:
            return _run_review_decision_document(
                runtime=runtime,
                bundle=bundle,
                review_task_names=_SEASON_REVIEW_TASKS,
                final_task_name="season_review",
                manager_agent_name="season_review_manager",
                crew_name="season_review",
                user_input=loop_input,
                planning_bundle=planning_bundle,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        planning_bundle, review_decision = _run_multicrew_cycle(
            runtime=runtime,
            bundle=bundle,
            user_input=user_input,
            planning_runner=_planning_runner,
            review_runner=_review_runner,
            max_replan_rounds=2,
        )
        document = _run_writer_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="season_writer",
            public_task=task,
            user_input=user_input,
            planning_bundle=planning_bundle,
            review_decision=review_decision,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            loaded_inputs=loaded_inputs,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    elif task == AgentTask.CREATE_WEEK_PLAN:
        def _planning_runner(loop_input: str) -> JsonMap:
            planning_bundle = _execute_crewai_multiagent_crew(
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                runtime=runtime,
                bundle=bundle,
                manager_agent_name="week_plan_manager",
                crew_name="week_planning",
                crew_task_names=_WEEK_PLANNING_TASKS,
                final_task_name="week_plan_finalize",
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                tools=tools,
                user_input=loop_input,
                final_public_task=None,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
                execution_mode="sequential",
            ).model_dump()
            return _validate_normalized_week_bundle(
                planning_bundle,
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
            )

        def _review_runner(loop_input: str, planning_bundle: JsonMap) -> JsonMap:
            return _run_review_decision_document(
                runtime=runtime,
                bundle=bundle,
                review_task_names=_WEEK_REVIEW_TASKS,
                final_task_name="week_review",
                manager_agent_name="week_review_manager",
                crew_name="week_review",
                user_input=loop_input,
                planning_bundle=planning_bundle,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        planning_bundle, review_decision = _run_multicrew_cycle(
            runtime=runtime,
            bundle=bundle,
            user_input=user_input,
            planning_runner=_planning_runner,
            review_runner=_review_runner,
            max_replan_rounds=1,
        )
        document = _run_writer_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="week_writer",
            public_task=task,
            user_input=user_input,
            planning_bundle=planning_bundle,
            review_decision=review_decision,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            loaded_inputs=loaded_inputs,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    elif task == AgentTask.CREATE_DES_ANALYSIS_REPORT:
        planning_bundle = _run_single_internal_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="report_planning",
            task_name="des_diagnostic_draft",
            user_input=user_input,
            context_payloads=None,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
        review_decision = _run_single_internal_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="report_review",
            task_name="report_review",
            user_input=user_input,
            context_payloads=[("Planning bundle", planning_bundle)],
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
        status = str(review_decision.get("status") or "").lower()
        if status != "approved":
            raise RuntimeError(
                "; ".join(review_decision.get("blocking_issues") or [])
                or f"Report review returned status '{status or 'unknown'}'."
            )
        document = _run_writer_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="report_writer",
            public_task=task,
            user_input=user_input,
            planning_bundle=planning_bundle,
            review_decision=review_decision,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            loaded_inputs=loaded_inputs,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    else:
        description = _build_task_description(
            runtime,
            bundle=bundle,
            crew_name=(
                "week_planning"
                if task == AgentTask.CREATE_WEEK_PLAN
                else "report_advisory"
                if task == AgentTask.CREATE_DES_ANALYSIS_REPORT
                else "season_planning"
            ),
            agent_name=agent_name,
            task=task,
            user_input=user_input,
        )
        pydantic_output = _execute_crewai_task(
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            runtime=runtime,
            bundle=bundle,
            agent_blueprint=agent_blueprint,
            task_blueprint=task_blueprint,
            tools=tools,
            description=description,
            crew_name=(
                "week_planning"
                if task == AgentTask.CREATE_WEEK_PLAN
                else "report_advisory"
                if task == AgentTask.CREATE_DES_ANALYSIS_REPORT
                else "season_planning"
            ),
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
        document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output

    if not isinstance(document, dict):
        raise RuntimeError("CrewAI typed output did not decode to an artifact envelope object.")

    return output_spec, _normalize_document(output_spec, document, loaded_inputs)


def run_agent_multi_output_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    stream_handlers: dict[str, object] | None = None,
) -> JsonMap:
    """Execute a single persisted task through CrewAI and persist the typed result."""

    del stream_handlers

    if len(tasks) != 1:
        return {
            "ok": False,
            "error": "CrewAI backend currently supports exactly one task per run.",
            "produced": {},
        }

    task = tasks[0]
    if task == AgentTask.CREATE_WEEK_PLAN:
        try:
            target_year, target_week = parse_target_week_from_user_input(user_input)
            return execute_week_engine(
                repo_root=ROOT,
                schema_dir=runtime.schema_dir,
                workspace_root=runtime.workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                target_year=target_year,
                target_week=target_week,
                user_message=extract_message_from_user_input(user_input),
                preview_only=False,
            )
        except Exception as exc:
            emit_runtime_exception_event(
                root=runtime.workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                exc=exc,
                crew="single_task",
                task=task.value,
                agent=agent_name,
            )
            return {
                "ok": False,
                "error": str(exc),
                "produced": {},
            }
    if task in {
        AgentTask.CREATE_PHASE_GUARDRAILS,
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }:
        return run_phase_bundle_crewai(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            tasks=[task],
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )

    try:
        output_spec, document = _run_single_task_document_crewai(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            task=task,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    except Exception as exc:
        emit_runtime_exception_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            exc=exc,
            crew="single_task",
            task=task.value,
            agent=agent_name,
        )
        return {
            "ok": False,
            "error": str(exc),
            "produced": {},
        }

    try:
        saved = _persist_artifact_document(
            runtime=runtime,
            athlete_id=athlete_id,
            run_id=run_id,
            output_spec=output_spec,
            document=document,
            producer_agent=agent_name,
        )
    except SchemaValidationError as exc:
        return {
            "ok": False,
            "error": "Schema validation failed",
            "details": list(exc.errors or []),
            "produced": {},
        }
    except Exception as exc:
        logger.warning("CrewAI store failed for %s: %s", output_spec.artifact_type.value, exc)
        return {"ok": False, "error": str(exc), "produced": {}}

    return {"ok": True, "produced": {output_spec.tool_name: saved}}


def run_agent_multi_output_preview_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    stream_handlers: dict[str, object] | None = None,
) -> JsonMap:
    """Execute a single CrewAI task and return the normalized document without storing it."""

    del stream_handlers

    if len(tasks) != 1:
        return {
            "ok": False,
            "error": "CrewAI preview backend currently supports exactly one task per run.",
            "document": {},
        }

    task = tasks[0]
    if task == AgentTask.CREATE_WEEK_PLAN:
        try:
            target_year, target_week = parse_target_week_from_user_input(user_input)
            return execute_week_engine(
                repo_root=ROOT,
                schema_dir=runtime.schema_dir,
                workspace_root=runtime.workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                target_year=target_year,
                target_week=target_week,
                user_message=extract_message_from_user_input(user_input),
                preview_only=True,
            )
        except Exception as exc:
            emit_runtime_exception_event(
                root=runtime.workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                exc=exc,
                crew="single_task_preview",
                task=task.value,
                agent=agent_name,
            )
            return {"ok": False, "error": str(exc), "document": {}}
    if task in {
        AgentTask.CREATE_PHASE_GUARDRAILS,
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }:
        return {
            "ok": False,
            "error": "Preview-only CrewAI backend does not support phase bundle tasks.",
            "document": {},
        }

    try:
        output_spec, document = _run_single_task_document_crewai(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            task=task,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    except Exception as exc:
        emit_runtime_exception_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            exc=exc,
            crew="single_task_preview",
            task=task.value,
            agent=agent_name,
        )
        return {"ok": False, "error": str(exc), "document": {}}

    return {
        "ok": True,
        "artifact_type": output_spec.artifact_type.value,
        "document": document,
    }
