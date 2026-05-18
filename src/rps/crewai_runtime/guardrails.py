"""Guardrail registry and helpers for CrewAI task construction."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from rps.crewai_runtime.telemetry import emit_runtime_event
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week, parse_iso_week_range
from rps.workspace.schema_map import ARTIFACT_SCHEMA_FILE
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]
GuardrailResult = tuple[bool, Any]
GuardrailFn = Callable[[Any], GuardrailResult]
_GUARDRAIL_CONTEXT: ContextVar[JsonMap] = ContextVar("rps_guardrail_context", default={})
ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "specs" / "schemas"


@dataclass(frozen=True)
class TaskExecutionPolicy:
    """Resolved task execution policy merged from config defaults and overrides."""

    output_mode: str
    guardrails: tuple[str, ...]
    guardrail_max_retries: int


@contextmanager
def guardrail_runtime_context(**context: Any):
    """Bind runtime-only guardrail context for the current CrewAI task run."""

    current = dict(_GUARDRAIL_CONTEXT.get({}))
    current.update({key: value for key, value in context.items() if value is not None})
    token = _GUARDRAIL_CONTEXT.set(current)
    try:
        yield
    finally:
        _GUARDRAIL_CONTEXT.reset(token)


def _coerce_payload(result: Any) -> Any:
    """Extract the richest payload view from a CrewAI TaskOutput-like object."""

    if result is None:
        return None
    pydantic_payload = getattr(result, "pydantic", None)
    if pydantic_payload is not None:
        return pydantic_payload
    json_payload = getattr(result, "json_dict", None)
    if json_payload is not None:
        return json_payload
    raw_payload = getattr(result, "raw", None)
    if raw_payload is not None:
        return raw_payload
    return result


def _coerce_mapping(result: Any) -> JsonMap | None:
    payload = _coerce_payload(result)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None
    return None


def typed_output_present(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    if payload is None:
        return (False, "Task produced no structured output payload.")
    return (True, payload)


def coaching_recommendation_text_present(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    recommendation = getattr(payload, "recommendation", None)
    if isinstance(payload, dict):
        recommendation = payload.get("recommendation")
    if isinstance(recommendation, str) and recommendation.strip():
        return (True, payload)
    return (False, "Coaching recommendation must contain non-empty recommendation text.")


def adjustment_intent_has_preview_message(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    preview_message = getattr(payload, "message_for_preview", None)
    if isinstance(payload, dict):
        preview_message = payload.get("message_for_preview")
    if isinstance(preview_message, str) and preview_message.strip():
        return (True, payload)
    return (False, "Adjustment intent must include a non-empty message_for_preview field.")


def coach_preview_summary_complete(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    ok_value = getattr(payload, "ok", None)
    summary = getattr(payload, "summary", None)
    if isinstance(payload, dict):
        ok_value = payload.get("ok")
        summary = payload.get("summary")
    if isinstance(ok_value, bool) and isinstance(summary, str) and summary.strip():
        return (True, payload)
    return (False, "Coach preview summary must include boolean ok and non-empty summary.")


def pending_resolution_summary_present(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    action = getattr(payload, "action", None)
    summary = getattr(payload, "summary", None)
    if isinstance(payload, dict):
        action = payload.get("action")
        summary = payload.get("summary")
    if isinstance(action, str) and action.strip() and isinstance(summary, str) and summary.strip():
        return (True, payload)
    return (False, "Pending-resolution result must include non-empty action and summary.")


def audit_lists_are_lists(result: Any) -> GuardrailResult:
    payload = _coerce_payload(result)
    mapping = payload.model_dump() if hasattr(payload, "model_dump") else payload
    if not isinstance(mapping, dict):
        return (False, "Audit output must decode to an object.")
    for field in ("blocking_issues", "warnings", "recommended_adjustments"):
        if field in mapping and not isinstance(mapping[field], list):
            return (False, f"Audit field '{field}' must be a list.")
    return (True, payload)


def phase_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    required = ("phase_range", "guardrails", "structure", "preview", "constraint_audit", "load_governance_audit")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Phase bundle missing required keys: {', '.join(missing)}")
    return (True, mapping)


def season_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season bundle must decode to an object.")
    required = ("event_priority", "macrocycle")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Season bundle missing required keys: {', '.join(missing)}")
    return (True, mapping)


def week_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week bundle must decode to an object.")
    required = ("context_summary", "constraint_summary", "load_target_summary", "revision_summary")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Week bundle missing required keys: {', '.join(missing)}")
    return (True, mapping)


def review_decision_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Review decision must decode to an object.")
    status = mapping.get("status")
    if status not in {"approved", "replan_required", "rejected"}:
        return (False, "Review decision status must be approved, replan_required, or rejected.")
    for field in ("blocking_issues", "warnings", "replan_instructions"):
        if field in mapping and not isinstance(mapping[field], list):
            return (False, f"Review decision field '{field}' must be a list.")
    if not isinstance(mapping.get("writer_ready_summary"), str):
        return (False, "Review decision must include writer_ready_summary string.")
    return (True, mapping)


def artifact_envelope_basic(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (False, "Artifact output must include top-level 'meta' and 'data' objects.")
    return (True, mapping)


def artifact_meta_data_present(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    if not isinstance(meta, dict):
        return (False, "Artifact output missing meta object.")
    required = ("artifact_type", "schema_id")
    missing = [field for field in required if not meta.get(field)]
    if missing:
        return (False, f"Artifact meta missing required fields: {', '.join(missing)}")
    if not isinstance(mapping.get("data"), dict):
        return (False, "Artifact output missing data object.")
    return (True, mapping)


@lru_cache(maxsize=1)
def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(SCHEMA_DIR)


def artifact_schema_valid(result: Any) -> GuardrailResult:
    """Validate a persisted artifact output against its canonical JSON Schema."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Artifact output must decode to a JSON object.")
    meta = mapping.get("meta")
    if not isinstance(meta, dict):
        return (False, "Artifact output missing meta object.")
    artifact_type_raw = str(meta.get("artifact_type") or "").strip().upper()
    if not artifact_type_raw:
        return (False, "Artifact meta missing artifact_type.")
    try:
        artifact_type = ArtifactType(artifact_type_raw)
    except ValueError:
        return (False, f"Unknown artifact_type for schema validation: {artifact_type_raw}.")
    schema_file = ARTIFACT_SCHEMA_FILE.get(artifact_type)
    if not schema_file:
        return (False, f"No JSON schema mapping registered for artifact_type {artifact_type_raw}.")
    try:
        validator = _schema_registry().validator_for(schema_file)
        validate_or_raise(validator, mapping)
    except SchemaValidationError as exc:
        details = "; ".join(exc.errors[:8])
        if len(exc.errors) > 8:
            details += f"; ... and {len(exc.errors) - 8} more"
        return (False, f"Artifact schema validation failed for {schema_file}: {details}")
    except Exception as exc:
        return (False, f"Artifact schema validation failed for {schema_file}: {exc}")
    return (True, mapping)


def season_scenario_selection_shape(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Scenario selection output must decode to an object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (False, "Scenario selection must include meta and data objects.")
    if meta.get("artifact_type") != "SEASON_SCENARIO_SELECTION":
        return (False, "Scenario selection meta.artifact_type must be SEASON_SCENARIO_SELECTION.")
    if data.get("selected_scenario_id") not in {"A", "B", "C"}:
        return (False, "Scenario selection selected_scenario_id must be A, B, or C.")
    if not isinstance(data.get("season_scenarios_ref"), str) or not data.get("season_scenarios_ref"):
        return (False, "Scenario selection must include season_scenarios_ref.")
    forbidden_keys = {"phases", "agenda", "workouts", "weekly_kj_bands"}
    if any(key in data for key in forbidden_keys):
        return (False, "Scenario selection must not contain season, phase, week, or workout planning payloads.")
    return (True, mapping)


def season_phase_coverage_and_cadence(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season output must decode to an object.")
    candidate_document = mapping.get("candidate_document")
    candidate_map = candidate_document if isinstance(candidate_document, dict) else {}
    data = mapping.get("data") if "data" in mapping else candidate_map.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        return (False, "Season plan must include at least one phase.")
    seen_ranges: set[str] = set()
    parsed_ranges = []
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            return (False, f"Season phase {idx} must be an object.")
        range_key = phase.get("iso_week_range")
        if not isinstance(range_key, str) or not range_key:
            return (False, f"Season phase {idx} missing iso_week_range.")
        if range_key in seen_ranges:
            return (False, f"Duplicate season phase iso_week_range: {range_key}.")
        seen_ranges.add(range_key)
        parsed = parse_iso_week_range(range_key)
        if parsed is None:
            return (False, f"Season phase {idx} has invalid iso_week_range: {range_key}.")
        parsed_ranges.append((range_key, parsed))
        if not isinstance(phase.get("deload"), bool):
            return (False, f"Season phase {range_key} must include boolean deload.")
        rationale = phase.get("deload_rationale")
        if phase.get("deload") is True and (not isinstance(rationale, str) or not rationale.strip()):
            return (False, f"Season phase {range_key} deload requires non-empty deload_rationale.")
    for previous, current in zip(parsed_ranges, parsed_ranges[1:], strict=False):
        previous_range = previous[1]
        current_range = current[1]
        expected_next = _next_iso_week(previous_range.end)
        if current_range.start != expected_next:
            return (
                False,
                "Season phases must be continuous and non-overlapping; "
                f"{current[0]} should start at {expected_next.year:04d}-{expected_next.week:02d}.",
            )
    return (True, mapping)


def season_cycle_ordering(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Season output must decode to an object.")
    candidate_document = mapping.get("candidate_document")
    candidate_map = candidate_document if isinstance(candidate_document, dict) else {}
    data = mapping.get("data") if "data" in mapping else candidate_map.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    phases = data.get("phases")
    if not isinstance(phases, list):
        return (True, mapping)
    allowed = {"Base", "Build", "Peak", "Transition"}
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        cycle = phase.get("cycle")
        if cycle not in allowed:
            return (False, f"Season phase cycle must be one of {sorted(allowed)}; got {cycle!r}.")
    return (True, mapping)


def phase_s5_band_match(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase guardrails output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    load_guardrails = data.get("load_guardrails")
    if not isinstance(load_guardrails, dict):
        return (True, mapping)
    bands = load_guardrails.get("weekly_kj_bands")
    if not isinstance(bands, list) or not bands:
        return (False, "Phase guardrails must include weekly_kj_bands.")
    for entry in bands:
        if not isinstance(entry, dict):
            return (False, "Each weekly_kj_bands entry must be an object.")
        band = entry.get("band")
        if not isinstance(band, dict):
            return (False, "Each weekly_kj_bands entry must include band object.")
        min_value = band.get("min")
        max_value = band.get("max")
        if not isinstance(min_value, (int, float)) or not isinstance(max_value, (int, float)):
            return (False, "Each weekly_kj_bands band must include numeric min and max.")
        if float(min_value) > float(max_value):
            return (False, "weekly_kj_bands min must not exceed max.")
        expected = _extract_expected_s5_band(str(band.get("notes") or ""))
        if expected and (round(float(min_value)) != expected[0] or round(float(max_value)) != expected[1]):
            return (
                False,
                f"weekly_kj_bands[{entry.get('week')}] does not match deterministic S5 band {expected[0]}-{expected[1]}.",
            )
    return (True, mapping)


def phase_weeks_match_range(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase structure output must decode to an object.")
    meta = mapping.get("meta")
    data = mapping.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        return (True, mapping)
    phase_range = parse_iso_week_range(meta.get("iso_week_range"))
    if phase_range is None:
        return (True, mapping)
    expected_weeks = [_iso_week_key(week) for week in _weeks_in_range(phase_range)]
    observed_weeks: set[str] = set()
    load_ranges = data.get("load_ranges")
    if isinstance(load_ranges, dict):
        for entry in load_ranges.get("weekly_kj_bands") or []:
            if isinstance(entry, dict):
                week_key = _coerce_week_key(entry.get("week"))
                if week_key:
                    observed_weeks.add(week_key)
    skeleton = data.get("week_skeleton_logic")
    if isinstance(skeleton, dict):
        roles = skeleton.get("week_roles")
        roles_map = roles if isinstance(roles, dict) else {}
        for entry in roles_map.get("week_roles") or []:
            if isinstance(entry, dict):
                week_key = _coerce_week_key(entry.get("week"))
                if week_key:
                    observed_weeks.add(week_key)
    if not observed_weeks:
        return (True, mapping)
    expected_set = set(expected_weeks)
    missing = [week for week in expected_weeks if week not in observed_weeks]
    extra = sorted(observed_weeks - expected_set)
    if missing or extra:
        return (
            False,
            "Phase structure weeks must match meta.iso_week_range exactly; "
            f"missing={missing or []}, extra={extra or []}.",
        )
    return (True, mapping)


def _extract_expected_s5_band(notes: str) -> tuple[int, int] | None:
    match = re.search(r"S5(?: deterministic)? band(?: is|=|:)?\s*(\d+)\s*(?:-|/|to)\s*(\d+)", notes, re.I)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _iso_week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


def _next_iso_week(week: IsoWeek) -> IsoWeek:
    monday = date.fromisocalendar(week.year, week.week, 1)
    next_monday = monday + timedelta(days=7)
    iso_year, iso_week, _ = next_monday.isocalendar()
    return IsoWeek(iso_year, iso_week)


def _weeks_in_range(range_spec) -> list[IsoWeek]:
    cursor = date.fromisocalendar(range_spec.start.year, range_spec.start.week, 1)
    end = date.fromisocalendar(range_spec.end.year, range_spec.end.week, 1)
    weeks: list[IsoWeek] = []
    while cursor <= end:
        iso_year, iso_week, _ = cursor.isocalendar()
        weeks.append(IsoWeek(iso_year, iso_week))
        cursor += timedelta(days=7)
    return weeks


def _coerce_week_key(value: Any) -> str | None:
    week = parse_iso_week(value)
    if week is None:
        return None
    return _iso_week_key(week)


def week_corridor_and_capacity_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    summary = data.get("week_summary")
    if not isinstance(summary, dict):
        return (True, mapping)
    planned = summary.get("planned_weekly_load_kj")
    corridor = summary.get("weekly_load_corridor_kj") or summary.get("weekly_load_corridor")
    if not isinstance(planned, (int, float)) or not isinstance(corridor, dict):
        return (True, mapping)
    min_value = corridor.get("min")
    max_value = corridor.get("max")
    if isinstance(min_value, (int, float)) and float(planned) < float(min_value):
        return (False, "Week planned_weekly_load_kj is below weekly load corridor.")
    if isinstance(max_value, (int, float)) and float(planned) > float(max_value):
        return (False, "Week planned_weekly_load_kj exceeds weekly load corridor.")
    return (True, mapping)


def week_recovery_day_load_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    for entry in data.get("agenda") or []:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("day_role") or "").upper()
        planned = entry.get("planned_kj")
        workout_id = entry.get("workout_id")
        planned_value = float(planned) if isinstance(planned, (int, float)) else 0.0
        if role in {"REST", "OFF_BIKE"} and (planned_value > 0 or workout_id):
            return (False, f"{role} day {entry.get('day')} must not carry planned load or a workout_id.")
    return (True, mapping)


def week_daily_availability_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    context = _GUARDRAIL_CONTEXT.get({})
    availability_payload = context.get("availability_payload")
    if not isinstance(availability_payload, dict):
        return (True, mapping)
    target_week = context.get("target_week")
    if isinstance(target_week, dict):
        year = target_week.get("year")
        week = target_week.get("week")
        target_week = IsoWeek(int(year), int(week)) if isinstance(year, int) and isinstance(week, int) else None
    try:
        from rps.planning.week_availability import validate_week_plan_daily_availability

        issues = validate_week_plan_daily_availability(
            week_plan_payload=mapping,
            availability_payload=availability_payload,
            target_week=target_week if isinstance(target_week, IsoWeek) else None,
        )
    except Exception as exc:
        return (False, f"Week daily availability check failed: {exc}")
    if issues:
        return (False, "; ".join(issue.format() for issue in issues[:5]))
    return (True, mapping)


def week_exportability_check(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Week plan output must decode to an object.")
    try:
        from rps.workouts.validator import collect_week_plan_export_issues

        issues = collect_week_plan_export_issues(mapping)
    except Exception as exc:
        return (False, f"Week exportability check failed: {exc}")
    if issues:
        return (False, "; ".join(issue.format() for issue in issues[:5]))
    return (True, mapping)


def des_diagnostic_only(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "DES report output must decode to an object.")
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    recommendation = data.get("recommendation")
    if not isinstance(recommendation, dict):
        return (True, mapping)
    if recommendation.get("type") not in (None, "advisory"):
        return (False, "DES recommendation type must remain advisory.")
    if recommendation.get("scope") not in (None, "Season-Planner"):
        return (False, "DES recommendation scope must remain Season-Planner.")
    explicitly_not = recommendation.get("explicitly_not")
    if isinstance(explicitly_not, list):
        missing = {"direct_phase_change", "weekly_intervention"} - {str(item) for item in explicitly_not}
        if missing:
            return (False, "DES recommendation must explicitly exclude direct_phase_change and weekly_intervention.")
    return (True, mapping)


REGISTRY: dict[str, GuardrailFn] = {
    "typed_output_present": typed_output_present,
    "coaching_recommendation_text_present": coaching_recommendation_text_present,
    "adjustment_intent_has_preview_message": adjustment_intent_has_preview_message,
    "coach_preview_summary_complete": coach_preview_summary_complete,
    "pending_resolution_summary_present": pending_resolution_summary_present,
    "audit_lists_are_lists": audit_lists_are_lists,
    "phase_bundle_integrity": phase_bundle_integrity,
    "season_bundle_integrity": season_bundle_integrity,
    "week_bundle_integrity": week_bundle_integrity,
    "review_decision_integrity": review_decision_integrity,
    "artifact_envelope_basic": artifact_envelope_basic,
    "artifact_meta_data_present": artifact_meta_data_present,
    "artifact_schema_valid": artifact_schema_valid,
    "season_scenario_selection_shape": season_scenario_selection_shape,
    "season_phase_coverage_and_cadence": season_phase_coverage_and_cadence,
    "season_cycle_ordering": season_cycle_ordering,
    "phase_s5_band_match": phase_s5_band_match,
    "phase_weeks_match_range": phase_weeks_match_range,
    "week_corridor_and_capacity_check": week_corridor_and_capacity_check,
    "week_recovery_day_load_check": week_recovery_day_load_check,
    "week_daily_availability_check": week_daily_availability_check,
    "week_exportability_check": week_exportability_check,
    "des_diagnostic_only": des_diagnostic_only,
}


def resolve_guardrail(name: str) -> GuardrailFn:
    """Return a registered guardrail callable by symbolic name."""

    try:
        return REGISTRY[name]
    except KeyError as exc:  # pragma: no cover - config validation catches this in tests
        raise ValueError(f"Unknown CrewAI guardrail: {name}") from exc


def resolve_task_policy(task_blueprint: Any, task_policies: JsonMap) -> TaskExecutionPolicy:
    """Resolve the merged task execution policy from config defaults and overrides."""

    defaults = task_policies.get("defaults") or {}
    kind_defaults = defaults.get(task_blueprint.config.get("kind") or "") or {}
    task_overrides = (task_policies.get("tasks") or {}).get(task_blueprint.name) or {}

    output_mode = str(task_overrides.get("output_mode") or kind_defaults.get("output_mode") or "pydantic")
    guardrails_raw = task_overrides.get("guardrails")
    if guardrails_raw is None:
        guardrails_raw = kind_defaults.get("guardrails") or []
    guardrails = tuple(str(item) for item in guardrails_raw)
    guardrail_max_retries = int(
        task_overrides.get("guardrail_max_retries")
        or kind_defaults.get("guardrail_max_retries")
        or 3
    )
    return TaskExecutionPolicy(
        output_mode=output_mode,
        guardrails=guardrails,
        guardrail_max_retries=guardrail_max_retries,
    )


def build_task_guardrail_kwargs(task_blueprint: Any, task_policies: JsonMap) -> JsonMap:
    """Return CrewAI Task kwargs for guardrails and output-mode policy."""

    policy = resolve_task_policy(task_blueprint, task_policies)
    kwargs: JsonMap = {"guardrail_max_retries": policy.guardrail_max_retries}
    if policy.guardrails:
        guardrail_fns = [
            _with_guardrail_telemetry(task_blueprint.name, name, resolve_guardrail(name))
            for name in policy.guardrails
        ]
        if len(guardrail_fns) == 1:
            kwargs["guardrail"] = guardrail_fns[0]
        else:
            kwargs["guardrails"] = guardrail_fns
    kwargs["_resolved_output_mode"] = policy.output_mode
    return kwargs


def _with_guardrail_telemetry(task_name: str, guardrail_name: str, guardrail_fn: GuardrailFn) -> GuardrailFn:
    """Wrap one guardrail so failures become compact retry-relevant runtime events."""

    def _wrapped(result: Any):
        ok, payload = guardrail_fn(result)
        if not ok:
            context = _GUARDRAIL_CONTEXT.get({})
            emit_runtime_event(
                root=context.get("root"),
                athlete_id=context.get("athlete_id"),
                run_id=context.get("run_id"),
                event_type="CREW_TASK_GUARDRAIL_FAILED",
                component=context.get("component") or f"task:{task_name}",
                task=task_name,
                guardrail=guardrail_name,
                reason=str(payload)[:500],
            )
        return (ok, payload)

    return cast(GuardrailFn, _wrapped)
