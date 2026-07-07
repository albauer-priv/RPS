"""Deterministic contract/context-block building for CrewAI task descriptions."""

from __future__ import annotations

import json
from typing import Any

from rps.agents.output_normalization import extract_loaded_document
from rps.agents.tasks import AgentTask
from rps.crewai_runtime.guardrails_context import current_guardrail_runtime_context

JsonMap = dict[str, Any]


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _render_json_block(label: str, payload: object) -> str:
    """Render structured intermediate results as compact JSON context."""

    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    try:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        rendered = json.dumps(str(payload), ensure_ascii=False)
    return f"{label}:\n```json\n{rendered}\n```"


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
                "Season finalizer bundle shape: top-level `event_priority`, `macrocycle`, and `phase_blueprints` are mandatory. "
                "Season final output uses `constraints[]` and `load_governance[]` only. "
                "Do not emit singular top-level `constraint_audit` or `load_governance_audit` keys. "
                "`phase_blueprints` are produced earlier by `season_phase_blueprint_draft` and must be preserved here."
            )
            blocks.append(
                "Season audit-slot ownership: preserve and consolidate canonical `constraints[]` from "
                "`season_constraint_review`, `season_historical_context_review`, and `season_kpi_guidance_review`, "
                "and canonical `load_governance[]` from `season_load_corridor_draft` and `season_progression_review`. "
                "Do not flatten them into row-shaped findings such as `constraint_type`, `status`, or `summary`."
            )
            blocks.append(
                "Season finalization rule: consume these deterministic contracts directly. "
                "Do not search the workspace for non-persisted phase-load recommendation artefacts."
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
