"""Structured output extraction and parsing for CrewAI task results."""

from __future__ import annotations

from typing import Any

from rps.crewai_runtime.bindings import output_model_for_kind
from rps.crewai_runtime.generated_artifact_models import (
    artifact_model_for_schema_file,
    artifact_model_for_task_name,
)
from rps.crewai_runtime.guardrails_utilities import decode_json_object_from_text
from rps.crewai_runtime.models import (
    PhaseBundleManagerSynthesisModel,
    PhaseDraftBundleModel,
    SeasonPlanDraftBundleModel,
    SeasonPlanManagerSynthesisModel,
)

JsonMap = dict[str, Any]

_SEASON_CONSTRAINT_AUDIT_TASKS: tuple[str, ...] = (
    "season_constraint_review",
    "season_historical_context_review",
    "season_kpi_guidance_review",
)

_SEASON_LOAD_GOVERNANCE_TASKS: tuple[str, ...] = (
    "season_load_corridor_draft",
    "season_progression_review",
)


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


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

    parsed = decode_json_object_from_text(raw_text)
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


def _collect_typed(
    task_names: tuple[str, ...],
    *,
    result: object,
    tasks_by_name: dict[str, object],
    task_blueprints: dict[str, Any],
) -> list[JsonMap]:
    """Collect typed structured output mappings from a fixed set of already-completed sibling tasks."""

    collected: list[JsonMap] = []
    for task_name in task_names:
        task_obj = tasks_by_name.get(task_name)
        task_blueprint = task_blueprints.get(task_name)
        if task_obj is None or task_blueprint is None:
            continue
        execution_policy = _as_map(getattr(task_blueprint, "execution_policy", {}))
        output_mode = str(execution_policy.get("output_mode") or "pydantic")
        structured = _extract_structured_output(
            result,
            task_obj,
            task_name=task_name,
            output_mode=output_mode,
        )
        mapping = structured.model_dump() if hasattr(structured, "model_dump") else structured
        if isinstance(mapping, dict):
            collected.append(mapping)
    return collected


def _assemble_season_plan_draft_bundle(
    manager_synthesis: SeasonPlanManagerSynthesisModel,
    *,
    result: object,
    tasks_by_name: dict[str, object],
    task_blueprints: dict[str, Any],
) -> SeasonPlanDraftBundleModel:
    """Assemble the full Season draft bundle from the manager synthesis plus already-typed sibling outputs."""

    constraints = _collect_typed(
        _SEASON_CONSTRAINT_AUDIT_TASKS, result=result, tasks_by_name=tasks_by_name, task_blueprints=task_blueprints
    )
    load_governance = _collect_typed(
        _SEASON_LOAD_GOVERNANCE_TASKS, result=result, tasks_by_name=tasks_by_name, task_blueprints=task_blueprints
    )
    phase_task_obj = tasks_by_name.get("season_phase_blueprint_draft")
    if phase_task_obj is None:
        raise RuntimeError("CrewAI task 'season_phase_blueprint_draft' did not run; cannot assemble season bundle.")
    phase_output = _extract_typed_output(result, phase_task_obj)
    if phase_output is None:
        raise RuntimeError(
            "CrewAI task 'season_phase_blueprint_draft' did not produce a typed pydantic output."
        )
    phase_blueprints = list(phase_output.phase_blueprints)
    return SeasonPlanDraftBundleModel.model_validate(
        {
            **manager_synthesis.model_dump(),
            "constraints": constraints,
            "load_governance": load_governance,
            "phase_blueprints": phase_blueprints,
        }
    )


def _assemble_phase_draft_bundle(
    manager_synthesis: PhaseBundleManagerSynthesisModel,
    *,
    result: object,
    tasks_by_name: dict[str, object],
) -> PhaseDraftBundleModel:
    """Assemble the full Phase draft bundle from the manager synthesis plus already-typed sibling outputs."""

    def _require_typed(task_name: str) -> Any:
        task_obj = tasks_by_name.get(task_name)
        if task_obj is None:
            raise RuntimeError(f"CrewAI task '{task_name}' did not run; cannot assemble phase bundle.")
        typed_output = _extract_typed_output(result, task_obj)
        if typed_output is None:
            raise RuntimeError(f"CrewAI task '{task_name}' did not produce a typed pydantic output.")
        return typed_output

    guardrails = _require_typed("phase_guardrail_band_draft")
    structure = _require_typed("phase_structure_draft")
    preview = _require_typed("phase_preview_draft")
    return PhaseDraftBundleModel(
        **manager_synthesis.model_dump(),
        guardrails=guardrails,
        structure=structure,
        preview=preview,
    )


def _output_model_for_task(task_blueprint: Any, *, schema_file: str | None = None) -> type[Any]:
    """Resolve the strongest structured-output model for a CrewAI task."""

    if task_blueprint.output_kind == "artifact_envelope":
        if schema_file:
            return artifact_model_for_schema_file(schema_file)
        return artifact_model_for_task_name(task_blueprint.name)
    return output_model_for_kind(task_blueprint.output_kind)
