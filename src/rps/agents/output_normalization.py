"""Deterministic artifact normalization shared by CrewAI-backed planner flows."""

from __future__ import annotations

import datetime
import json
import logging
import math
import re
from pathlib import Path
from typing import Any

from rps.agents.tasks import AgentTask
from rps.planning.phase_authority import (
    build_week_skeleton_for_phase,
    normalize_role_week_load_bands,
    persisted_phase_weekly_kj_bands,
)
from rps.workspace.artifact_metadata import normalize_trace_reference
from rps.workspace.intensity_domains import normalize_intensity_domain_list
from rps.workspace.iso_helpers import parse_iso_week_range

logger = logging.getLogger(__name__)
_KNOWLEDGE_SOURCE_ROOT = Path(__file__).resolve().parents[3] / "specs" / "knowledge" / "_shared" / "sources"
_CADENCE_PHASE_LENGTHS = {
    "3:1": 4,
    "2:1": 3,
    "2:1:1": 4,
}
_MIN_SHORTENED_PHASE_LENGTH = 2
_SEASON_SCENARIO_TRACE_EVENT_ARTIFACTS = {"PLANNING_EVENTS"}
_SEASON_SCENARIO_TRACE_DATA_ARTIFACTS = {
    "ATHLETE_PROFILE",
    "LOGISTICS",
    "KPI_PROFILE",
    "AVAILABILITY",
    "WELLNESS",
}
_SEASON_SCENARIO_TRACE_UPSTREAM_ARTIFACTS = _SEASON_SCENARIO_TRACE_EVENT_ARTIFACTS | _SEASON_SCENARIO_TRACE_DATA_ARTIFACTS | {
    "ATHLETE_STATE_SNAPSHOT",
    "PLANNING_CONTEXT_SNAPSHOT",
}
_PHASE_TRACE_UPSTREAM_ARTIFACTS = {
    "SEASON_PLAN",
    "SEASON_SCENARIO_SELECTION",
    "SEASON_SCENARIOS",
    "PHASE_GUARDRAILS",
    "PHASE_STRUCTURE",
}
_DISALLOWED_AVOID_DOMAINS = {"NONE", "RECOVERY"}
_SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$")
_META_SCOPES = {"Shared", "Season", "Phase", "Week", "Context"}
_SCENARIO_IDS = ("A", "B", "C")


def _as_map(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []
_INLINE_LOOP_STEP_RE = re.compile(
    r"^(?P<indent>\s*)-\s*(?P<count>\d+)[xX]\s+(?P<step>(?:\d+(?:\.\d+)?(?:s|m|h)|\d+m\d+|\d+h\d+m).*)$"
)


def normalize_workout_percent_ranges(text: str) -> str:
    """Normalize malformed power ranges like ``68-72%`` to ``68%-72%``."""

    return re.sub(
        r"(?<![%\d])(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)%(?!\S)",
        r"\1%-\2%",
        text,
    )


def normalize_workout_inline_loop_headers(text: str) -> str:
    """Normalize inline loop shorthand like ``- 3x 12m 80%-84% 88rpm`` to a standalone loop header."""

    normalized_lines: list[str] = []
    changed = False
    for raw_line in text.splitlines():
        match = _INLINE_LOOP_STEP_RE.fullmatch(raw_line)
        if not match:
            normalized_lines.append(raw_line)
            continue
        indent = match.group("indent")
        count = match.group("count")
        step = match.group("step")
        normalized_lines.append(f"{indent}{count}x")
        normalized_lines.append(f"{indent}- {step}")
        changed = True
    if not changed:
        return text
    return "\n".join(normalized_lines)


def _as_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _as_non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _normalize_semver(value: object, *, default: str = "1.0") -> str:
    rendered = str(value or "").strip()
    if _SEMVER_PATTERN.fullmatch(rendered):
        return rendered
    return default


def _normalize_meta_scope(value: object, *, default: str = "Season") -> str:
    rendered = str(value or "").strip()
    return rendered if rendered in _META_SCOPES else default


def _text_value(value: object, *, fallback: str = "Not specified.") -> str:
    if isinstance(value, str):
        rendered = value.strip()
    elif isinstance(value, list):
        rendered = " | ".join(str(item).strip() for item in value if str(item).strip())
    elif isinstance(value, dict):
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif value is None:
        rendered = ""
    else:
        rendered = str(value).strip()
    return rendered or fallback


def _text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        rendered = value.strip()
        return [rendered] if rendered else []
    if value is None:
        return []
    rendered = str(value).strip()
    return [rendered] if rendered else []


def _iso_week_range_weeks(range_str: object) -> int | None:
    if not isinstance(range_str, str) or "--" not in range_str:
        return None
    start_str, end_str = range_str.split("--", 1)
    try:
        sy, sw = (int(part) for part in start_str.split("-", 1))
        ey, ew = (int(part) for part in end_str.split("-", 1))
        start_date = datetime.date.fromisocalendar(sy, sw, 1)
        end_date = datetime.date.fromisocalendar(ey, ew, 7)
    except ValueError:
        return None
    return ((end_date - start_date).days // 7) + 1


def extract_planning_events_document(raw: object) -> dict[str, Any] | None:
    """Return parsed planning_events content from a read result or raw mapping."""

    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        return raw
    if isinstance(raw, dict) and raw.get("ok") is True:
        content = raw.get("content")
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
    return None


def extract_loaded_document(raw: object) -> dict[str, Any] | None:
    """Return a parsed document from a workspace tool result or raw mapping."""

    if isinstance(raw, dict) and isinstance(raw.get("document"), dict):
        return raw["document"]
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        return raw
    if isinstance(raw, dict) and raw.get("ok") is True:
        content = raw.get("content")
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
    return None


def _merge_unique_strings(existing: list[str], required: list[str]) -> list[str]:
    """Append missing stripped strings while preserving order."""

    merged = [item.strip() for item in existing if item and item.strip()]
    seen = {item for item in merged}
    for item in required:
        stripped = str(item).strip()
        if stripped and stripped not in seen:
            merged.append(stripped)
            seen.add(stripped)
    return merged


def _canonical_quality_intent(*, phase_type: object, phase_intent: object, current: object) -> str | None:
    """Return the canonical quality-intent token for supported phase semantics."""

    phase_type_token = str(phase_type or "").strip().upper()
    phase_intent_token = str(phase_intent or "").strip().lower()
    if phase_type_token == "BASE" and phase_intent_token in {"shortened_re_entry", "shortened_consolidation", "re_entry"}:
        return "Stabilization"
    rendered_current = str(current or "").strip()
    return rendered_current or None


def _trace_entry_from_document(
    document: dict[str, Any] | None,
    *,
    expected_artifact: str,
    version_key: str | None = None,
) -> dict[str, str] | None:
    """Return one canonical trace reference from a stored artifact document."""

    if not isinstance(document, dict):
        return None
    meta = _as_map(document.get("meta"))
    run_id = str(meta.get("run_id") or "").strip()
    resolved_version_key = str(version_key or meta.get("version_key") or "").strip()
    if not run_id or not resolved_version_key:
        return None
    reference = normalize_trace_reference(
        {
            "artifact": expected_artifact,
            "version": _normalize_semver(meta.get("version")),
            "schema_version": meta.get("schema_version"),
            "version_key": resolved_version_key,
            "run_id": run_id,
        }
    )
    if reference is None:
        return None
    return {key: str(value) for key, value in reference.items()}


def _parse_compact_event_window(value: object) -> tuple[str, str] | None:
    """Return `(date, type)` when a planned-event window carries a concrete date marker."""

    rendered = str(value or "").strip()
    match = re.search(
        r"(\d{4}-\d{2}-\d{2})\s*(?:\((A|B|C)\)|([ABC])\b)",
        rendered,
        re.IGNORECASE,
    )
    if match is None:
        return None
    event_type = (match.group(2) or match.group(3) or "").upper()
    if not event_type:
        return None
    return match.group(1), event_type


def _project_phase_guardrails_season_constraints(
    document: dict[str, Any],
    *,
    season_plan_document: dict[str, Any] | None,
) -> dict[str, Any]:
    """Deterministically propagate required season constraints into PHASE_GUARDRAILS."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    if str(meta.get("artifact_type", "")).upper() != "PHASE_GUARDRAILS":
        return document
    if not isinstance(season_plan_document, dict):
        return document
    season_data = season_plan_document.get("data")
    if not isinstance(season_data, dict):
        return document
    global_constraints = season_data.get("global_constraints")
    if not isinstance(global_constraints, dict):
        return document
    data = document.get("data")
    if not isinstance(data, dict):
        return document

    phase_summary = data.get("phase_summary")
    if not isinstance(phase_summary, dict):
        phase_summary = {}
    non_negotiables = _merge_unique_strings(
        _text_list(phase_summary.get("non_negotiables")),
        _text_list(global_constraints.get("availability_assumptions")),
    )
    key_risks = _merge_unique_strings(
        _text_list(phase_summary.get("key_risks_warnings")),
        _text_list(global_constraints.get("risk_constraints")),
    )
    passthrough_event_windows = [
        item
        for item in _text_list(global_constraints.get("planned_event_windows"))
        if _parse_compact_event_window(item) is None
    ]
    phase_summary["non_negotiables"] = _merge_unique_strings(non_negotiables, passthrough_event_windows)
    phase_summary["key_risks_warnings"] = key_risks
    data["phase_summary"] = phase_summary

    execution_non_negotiables = data.get("execution_non_negotiables")
    if not isinstance(execution_non_negotiables, dict):
        execution_non_negotiables = {}
    recovery_rules = _text_value(
        execution_non_negotiables.get("recovery_protection_rules"),
        fallback="",
    )
    recovery_notes: list[str] = []
    recovery_protection = global_constraints.get("recovery_protection")
    if isinstance(recovery_protection, dict):
        recovery_notes = _text_list(recovery_protection.get("notes"))
    recovery_parts = [recovery_rules] if recovery_rules else []
    for item in recovery_notes:
        if item not in recovery_rules:
            recovery_parts.append(item)
    if recovery_parts:
        execution_non_negotiables["recovery_protection_rules"] = " | ".join(
            part for part in recovery_parts if part
        )
    data["execution_non_negotiables"] = execution_non_negotiables

    events_constraints = data.get("events_constraints")
    if not isinstance(events_constraints, dict):
        events_constraints = {}
    events = events_constraints.get("events")
    if not isinstance(events, list):
        events = []
    existing_pairs = {
        (str(entry.get("date") or "").strip(), str(entry.get("type") or "").strip().upper())
        for entry in events
        if isinstance(entry, dict)
    }
    for item in _text_list(global_constraints.get("planned_event_windows")):
        parsed = _parse_compact_event_window(item)
        if parsed is None or parsed in existing_pairs:
            continue
        event_date, event_type = parsed
        try:
            parsed_date = datetime.date.fromisoformat(event_date)
            iso_year, iso_week, _ = parsed_date.isocalendar()
        except ValueError:
            continue
        events.append(
            {
                "date": event_date,
                "week": f"{iso_year:04d}-{iso_week:02d}",
                "type": event_type,
                "constraint": f"Planned season event window preserved from season_plan: {item}",
            }
        )
        existing_pairs.add(parsed)
    events_constraints["events"] = events
    data["events_constraints"] = events_constraints
    document["data"] = data
    return document


def normalize_phase_structure_document(
    document: dict[str, Any],
    *,
    season_plan_document: dict[str, Any] | None = None,
    phase_guardrails_document: dict[str, Any] | None = None,
    phase_guardrails_version_key: str | None = None,
    phase_execution_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically project required season and guardrails constraints into PHASE_STRUCTURE."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    artifact_type = str(meta.get("artifact_type", "")).upper()
    if artifact_type and artifact_type != "PHASE_STRUCTURE":
        return document
    data = document.get("data")
    if not isinstance(data, dict):
        return document
    execution_context = _as_map(phase_execution_context)

    upstream_intent = data.get("upstream_intent")
    if not isinstance(upstream_intent, dict):
        upstream_intent = {}
    upstream_constraints = _text_list(upstream_intent.get("constraints"))
    if isinstance(season_plan_document, dict):
        season_data = season_plan_document.get("data")
        if isinstance(season_data, dict):
            global_constraints = season_data.get("global_constraints")
            if isinstance(global_constraints, dict):
                recovery_notes: list[str] = []
                recovery_protection = global_constraints.get("recovery_protection")
                if isinstance(recovery_protection, dict):
                    recovery_notes = _text_list(recovery_protection.get("notes"))
                required_constraints = (
                    _text_list(global_constraints.get("availability_assumptions"))
                    + _text_list(global_constraints.get("risk_constraints"))
                    + recovery_notes
                    + _text_list(global_constraints.get("planned_event_windows"))
                )
                upstream_intent["constraints"] = _merge_unique_strings(
                    upstream_constraints,
                    required_constraints,
                )
                upstream_constraints = upstream_intent["constraints"]
    data["upstream_intent"] = upstream_intent

    inherited_scenario_contract = _as_map(execution_context.get("inherited_scenario_contract"))
    if inherited_scenario_contract:
        data["inherited_scenario_contract"] = inherited_scenario_contract
    elif isinstance(phase_guardrails_document, dict):
        guardrails_data = phase_guardrails_document.get("data")
        if isinstance(guardrails_data, dict):
            inherited_contract = guardrails_data.get("inherited_scenario_contract")
            if isinstance(inherited_contract, dict):
                data["inherited_scenario_contract"] = inherited_contract
    if isinstance(phase_guardrails_document, dict):
        guardrails_data = phase_guardrails_document.get("data")
        if isinstance(guardrails_data, dict):
            load_guardrails = guardrails_data.get("load_guardrails")
            if isinstance(load_guardrails, dict):
                weekly_kj_bands = load_guardrails.get("weekly_kj_bands")
                load_ranges = data.get("load_ranges")
                if not isinstance(load_ranges, dict):
                    load_ranges = {}
                if isinstance(weekly_kj_bands, list):
                    load_ranges["weekly_kj_bands"] = weekly_kj_bands
                if phase_guardrails_version_key:
                    load_ranges["source"] = f"phase_guardrails_{phase_guardrails_version_key}.json"
                data["load_ranges"] = load_ranges
    season_phase = _season_phase_for_range(season_plan_document, meta.get("iso_week_range"))
    if season_phase:
        semantics = _as_map(season_phase.get("allowed_forbidden_semantics"))
        if semantics:
            structural_phase_elements = data.get("structural_phase_elements")
            if not isinstance(structural_phase_elements, dict):
                structural_phase_elements = {}
            structural_phase_elements["allowed_intensity_domains"] = list(
                semantics.get("allowed_intensity_domains") or []
            )
            structural_phase_elements["allowed_load_modalities"] = list(
                semantics.get("allowed_load_modalities") or []
            )
            data["structural_phase_elements"] = structural_phase_elements
            execution_principles = data.get("execution_principles")
            if not isinstance(execution_principles, dict):
                execution_principles = {}
            load_intensity_handling = execution_principles.get("load_intensity_handling")
            if not isinstance(load_intensity_handling, dict):
                load_intensity_handling = {}
            load_intensity_handling["forbidden_intensity_domains"] = list(
                semantics.get("forbidden_intensity_domains") or []
            )
            canonical_quality_intent = _canonical_quality_intent(
                phase_type=upstream_intent.get("phase_type"),
                phase_intent=upstream_intent.get("phase_intent"),
                current=load_intensity_handling.get("quality_intent"),
            )
            if canonical_quality_intent:
                load_intensity_handling["quality_intent"] = canonical_quality_intent
            execution_principles["load_intensity_handling"] = load_intensity_handling
            data["execution_principles"] = execution_principles
        overview = _as_map(season_phase.get("overview"))
        phase_goals = _as_map(overview.get("phase_goals"))
        primary_objective = str(phase_goals.get("primary") or "").strip()
        if primary_objective:
            upstream_intent["primary_objective"] = primary_objective

    trace_upstream = meta.get("trace_upstream")
    phase_guardrails_ref = _trace_entry_from_document(
        phase_guardrails_document,
        expected_artifact="PHASE_GUARDRAILS",
        version_key=phase_guardrails_version_key,
    )
    trace_upstream = _replace_canonical_direct_trace_entry(
        trace_upstream,
        replacement=phase_guardrails_ref,
    )
    meta["trace_upstream"] = _normalize_trace_entries(
        trace_upstream,
        allowed=_PHASE_TRACE_UPSTREAM_ARTIFACTS,
    )
    document["meta"] = meta

    document["data"] = data
    return document


def normalize_phase_structure_document_from_execution_context(
    document: dict[str, Any],
    *,
    phase_execution_context: dict[str, Any] | None,
    phase_guardrails_document: dict[str, Any] | None = None,
    phase_guardrails_version_key: str | None = None,
    season_plan_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project exact PHASE_STRUCTURE authority from deterministic phase execution context."""

    context = _as_map(phase_execution_context)
    normalized = normalize_phase_structure_document(
        document,
        season_plan_document=season_plan_document,
        phase_guardrails_document=phase_guardrails_document,
        phase_guardrails_version_key=phase_guardrails_version_key,
        phase_execution_context=context,
    )
    if not isinstance(normalized, dict):
        return normalized
    data = normalized.get("data")
    if not isinstance(data, dict):
        return normalized
    context = _as_map(phase_execution_context)
    if not context:
        return normalized
    inherited_scenario_contract = _as_map(context.get("inherited_scenario_contract"))
    if not inherited_scenario_contract:
        raise ValueError(
            "PHASE_STRUCTURE pre-guardrail normalization requires phase_execution_context.inherited_scenario_contract."
        )
    data["inherited_scenario_contract"] = inherited_scenario_contract

    structural_phase_elements = data.get("structural_phase_elements")
    if not isinstance(structural_phase_elements, dict):
        structural_phase_elements = {}
    allowed_domains = _text_list(context.get("phase_allowed_intensity_domains"))
    if allowed_domains:
        structural_phase_elements["allowed_intensity_domains"] = allowed_domains
    allowed_modalities = _text_list(context.get("phase_allowed_load_modalities"))
    if allowed_modalities:
        structural_phase_elements["allowed_load_modalities"] = allowed_modalities
    if structural_phase_elements:
        data["structural_phase_elements"] = structural_phase_elements

    execution_principles = data.get("execution_principles")
    if not isinstance(execution_principles, dict):
        execution_principles = {}
    load_intensity_handling = execution_principles.get("load_intensity_handling")
    if not isinstance(load_intensity_handling, dict):
        load_intensity_handling = {}
    forbidden_domains = _text_list(context.get("phase_forbidden_intensity_domains"))
    if forbidden_domains:
        load_intensity_handling["forbidden_intensity_domains"] = forbidden_domains
    canonical_quality_intent = _canonical_quality_intent(
        phase_type=context.get("phase_type"),
        phase_intent=context.get("phase_intent"),
        current=load_intensity_handling.get("quality_intent"),
    )
    if canonical_quality_intent:
        load_intensity_handling["quality_intent"] = canonical_quality_intent
    if load_intensity_handling:
        execution_principles["load_intensity_handling"] = load_intensity_handling
    if execution_principles:
        data["execution_principles"] = execution_principles

    upstream_intent = data.get("upstream_intent")
    if not isinstance(upstream_intent, dict):
        upstream_intent = {}
    primary_objective = str(context.get("phase_primary_objective") or "").strip()
    if primary_objective:
        upstream_intent["primary_objective"] = primary_objective
    if upstream_intent:
        data["upstream_intent"] = upstream_intent

    normalized["data"] = data
    return normalized


def normalize_phase_guardrails_document_from_execution_context(
    document: dict[str, Any],
    *,
    phase_execution_context: dict[str, Any] | None,
    season_plan_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project exact PHASE_GUARDRAILS authority from deterministic phase execution context."""

    context = _as_map(phase_execution_context)
    if not normalize_role_week_load_bands(context.get("phase_role_week_load_bands")):
        raise ValueError(
            "PHASE_GUARDRAILS pre-guardrail normalization requires phase_execution_context.phase_role_week_load_bands."
        )
    return normalize_phase_guardrails_document(
        document,
        season_plan_document=season_plan_document,
        phase_execution_context=context,
    )


def _season_phase_for_range(
    season_plan_document: dict[str, Any] | None,
    range_key: object,
) -> dict[str, Any]:
    """Return the matching persisted Season phase for one phase-range key."""

    if not isinstance(season_plan_document, dict):
        return {}
    data = season_plan_document.get("data")
    if not isinstance(data, dict):
        return {}
    expected = str(range_key or "").strip()
    for phase in data.get("phases") or []:
        phase_map = phase if isinstance(phase, dict) else {}
        if str(phase_map.get("iso_week_range") or "").strip() == expected:
            return phase_map
    return {}


def _season_phase_role_week_load_bands(phase_map: dict[str, Any]) -> list[dict[str, Any]]:
    """Return exact structured week bands from persisted phase or legacy notes."""

    entries = normalize_role_week_load_bands(phase_map.get("role_week_load_bands"))
    if entries:
        return entries
    weekly_kj = _as_map(_as_map(phase_map.get("weekly_load_corridor")).get("weekly_kj"))
    return normalize_role_week_load_bands(weekly_kj.get("notes"))


def _phase_preview_shared_skeleton(
    *,
    expected_range: object,
    structure_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build deterministic shared preview/week skeleton from stored phase structure."""

    week_roles_map = _as_map(_as_map(structure_data.get("week_skeleton_logic")).get("week_roles"))
    week_role_by_iso_week = {
        str(_as_map(entry).get("week") or "").strip(): str(_as_map(entry).get("role") or "").strip()
        for entry in _as_list(week_roles_map.get("week_roles"))
        if str(_as_map(entry).get("week") or "").strip() and str(_as_map(entry).get("role") or "").strip()
    }
    week_keys = list(week_role_by_iso_week)
    if not week_keys:
        parsed = parse_iso_week_range(expected_range)
        if parsed is not None:
            week_keys = []
            cursor = parsed.start
            while True:
                week_keys.append(f"{cursor.year:04d}-{cursor.week:02d}")
                if cursor == parsed.end:
                    break
                if cursor.week == 52:
                    cursor = type(cursor)(cursor.year + 1, 1)
                else:
                    cursor = type(cursor)(cursor.year, cursor.week + 1)
    structural_phase_elements = _as_map(structure_data.get("structural_phase_elements"))
    execution_principles = _as_map(structure_data.get("execution_principles"))
    load_intensity = _as_map(execution_principles.get("load_intensity_handling"))
    recovery_protection = _as_map(execution_principles.get("recovery_protection"))
    upstream_intent = _as_map(structure_data.get("upstream_intent"))
    return build_week_skeleton_for_phase(
        week_keys=week_keys,
        week_role_by_iso_week=week_role_by_iso_week,
        fixed_rest_days=_text_list(recovery_protection.get("fixed_non_training_days")),
        allowed_day_roles=_text_list(structural_phase_elements.get("allowed_day_roles")),
        allowed_intensity_domains=_text_list(structural_phase_elements.get("allowed_intensity_domains")),
        allowed_load_modalities=_text_list(structural_phase_elements.get("allowed_load_modalities")),
        quality_cap=load_intensity.get("max_quality_days_per_week") if isinstance(load_intensity.get("max_quality_days_per_week"), int) else None,
        phase_intent=str(upstream_intent.get("phase_intent") or "").strip(),
    )


def normalize_phase_preview_document(
    document: dict[str, Any],
    *,
    phase_structure_document: dict[str, Any] | None = None,
    phase_structure_version_key: str | None = None,
) -> dict[str, Any]:
    """Repair derived PHASE_PREVIEW fields using stored structure authority."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    artifact_type = str(meta.get("artifact_type", "")).upper()
    if artifact_type and artifact_type != "PHASE_PREVIEW":
        return document
    if meta.get("authority") != "Informational":
        meta["authority"] = "Informational"
    data = document.get("data")
    if not isinstance(data, dict):
        return document

    traceability = data.get("traceability")
    if not isinstance(traceability, dict):
        traceability = {}
    derived_from = _text_list(traceability.get("derived_from"))
    if phase_structure_version_key:
        derived_from = _merge_unique_strings(
            derived_from,
            [f"phase_structure_{phase_structure_version_key}.json"],
        )
    if derived_from:
        traceability["derived_from"] = derived_from
    data["traceability"] = traceability

    if not isinstance(phase_structure_document, dict):
        document["data"] = data
        return document

    structure_data = phase_structure_document.get("data")
    if not isinstance(structure_data, dict):
        document["data"] = data
        return document

    phase_structure_ref = _trace_entry_from_document(
        phase_structure_document,
        expected_artifact="PHASE_STRUCTURE",
        version_key=phase_structure_version_key,
    )
    trace_upstream = [phase_structure_ref] if phase_structure_ref is not None else []
    meta["trace_upstream"] = _normalize_trace_entries(
        trace_upstream,
        allowed=_PHASE_TRACE_UPSTREAM_ARTIFACTS,
    )
    document["meta"] = meta

    structural_phase_elements = structure_data.get("structural_phase_elements")
    execution_principles = structure_data.get("execution_principles")
    upstream_intent = structure_data.get("upstream_intent")
    if not isinstance(structural_phase_elements, dict):
        structural_phase_elements = {}
    if not isinstance(execution_principles, dict):
        execution_principles = {}
    if not isinstance(upstream_intent, dict):
        upstream_intent = {}
    load_intensity = execution_principles.get("load_intensity_handling")
    recovery_protection = execution_principles.get("recovery_protection")
    if not isinstance(load_intensity, dict):
        load_intensity = {}
    if not isinstance(recovery_protection, dict):
        recovery_protection = {}

    allowed_intensity_domains = set(_text_list(structural_phase_elements.get("allowed_intensity_domains")))
    fixed_non_training_days = set(_text_list(recovery_protection.get("fixed_non_training_days")))
    quality_cap = load_intensity.get("max_quality_days_per_week")
    quality_cap = quality_cap if isinstance(quality_cap, int) else None

    fallback_training_domain = "ENDURANCE"
    if fallback_training_domain not in allowed_intensity_domains:
        for candidate in _text_list(structural_phase_elements.get("allowed_intensity_domains")):
            if candidate not in {"NONE", "RECOVERY"}:
                fallback_training_domain = candidate
                break

    weekly_agenda_preview = data.get("weekly_agenda_preview")
    if not isinstance(weekly_agenda_preview, list):
        document["data"] = data
        return document

    phase_intent_summary = data.get("phase_intent_summary")
    if not isinstance(phase_intent_summary, dict):
        phase_intent_summary = {}
    primary_objective = str(upstream_intent.get("primary_objective") or "").strip()
    if primary_objective:
        phase_intent_summary["primary_objective"] = primary_objective
    data["phase_intent_summary"] = phase_intent_summary

    week_to_week_narrative = data.get("week_to_week_narrative")
    if not isinstance(week_to_week_narrative, dict):
        week_to_week_narrative = {}
    rendered_not_change = str(week_to_week_narrative.get("what_will_not_change") or "").strip().lower()
    if not rendered_not_change or "stay fixed" in rendered_not_change or "will not change" in rendered_not_change:
        week_to_week_narrative["what_will_not_change"] = (
            "The preview reflects the current phase-derived skeleton: fixed rest days, "
            "recovery semantics, and allowed day-role/domain shape stay aligned unless an explicit replan changes upstream phase authority."
        )
    if not str(week_to_week_narrative.get("what_is_flexible") or "").strip():
        week_to_week_narrative["what_is_flexible"] = (
            "Week planning may add concrete workout detail and bounded within-guardrail adjustments "
            "without changing the inherited day-role/domain skeleton."
        )
    data["week_to_week_narrative"] = week_to_week_narrative

    shared_skeleton = _phase_preview_shared_skeleton(
        expected_range=meta.get("iso_week_range"),
        structure_data=structure_data,
    )
    shared_by_week = {
        str(_as_map(entry).get("week") or "").strip(): _as_map(entry)
        for entry in shared_skeleton
        if str(_as_map(entry).get("week") or "").strip()
    }
    expected_week_keys = [
        str(_as_map(entry).get("week") or "").strip()
        for entry in shared_skeleton
        if str(_as_map(entry).get("week") or "").strip()
    ]
    if expected_week_keys and len(weekly_agenda_preview) != len(expected_week_keys):
        raise ValueError(
            "PHASE_PREVIEW weekly_agenda_preview must match exact shared skeleton week coverage."
        )

    for index, week_entry in enumerate(weekly_agenda_preview):
        if not isinstance(week_entry, dict):
            continue
        expected_week_key = expected_week_keys[index] if index < len(expected_week_keys) else ""
        if expected_week_key:
            week_entry["week"] = expected_week_key
        week_key = str(week_entry.get("week") or "").strip()
        days = week_entry.get("days")
        if not isinstance(days, list):
            continue
        skeleton_days = {
            str(_as_map(day).get("day_of_week") or "").strip(): _as_map(day)
            for day in _as_list(_as_map(shared_by_week.get(week_key)).get("days"))
            if str(_as_map(day).get("day_of_week") or "").strip()
        }
        quality_days_seen = 0
        for day in days:
            if not isinstance(day, dict):
                continue
            day_of_week = str(day.get("day_of_week") or "").strip()
            day_role = str(day.get("day_role") or "").strip()
            skeleton_day = skeleton_days.get(day_of_week)
            if skeleton_day:
                day["day_role"] = skeleton_day.get("day_role")
                day["intensity_domain"] = skeleton_day.get("intensity_domain")
                day["load_modality"] = skeleton_day.get("load_modality")
                day_role = str(day.get("day_role") or "").strip()
            if day_of_week in fixed_non_training_days:
                day["day_role"] = "REST"
                day["intensity_domain"] = "NONE"
                day["load_modality"] = "NONE"
                continue
            if day_role == "RECOVERY":
                day["intensity_domain"] = "RECOVERY"
                day["load_modality"] = "NONE"
                continue
            if day_role == "QUALITY":
                quality_days_seen += 1
                if quality_cap is not None and quality_days_seen > quality_cap:
                    day["day_role"] = "ENDURANCE"
                    day["intensity_domain"] = fallback_training_domain
                    day["load_modality"] = "NONE"
        week_entry["days"] = days

    data["weekly_agenda_preview"] = weekly_agenda_preview
    document["data"] = data
    return document


def _derive_planning_horizon_from_events(
    meta: dict[str, Any],
    planning_events_document: dict[str, Any] | None,
) -> tuple[str, dict[str, str], int] | None:
    if not isinstance(planning_events_document, dict):
        return None
    data = planning_events_document.get("data")
    if not isinstance(data, dict):
        data = planning_events_document
    events = data.get("events")
    if not isinstance(events, list):
        return None

    last_event_date: datetime.date | None = None
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type") or "").strip().upper()
        if event_type not in {"A", "B", "C"}:
            continue
        raw_date = event.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            parsed_date = datetime.date.fromisoformat(raw_date)
        except ValueError:
            continue
        if last_event_date is None or parsed_date > last_event_date:
            last_event_date = parsed_date

    start_week = str(meta.get("iso_week") or "").strip()
    if not start_week or last_event_date is None:
        return None
    try:
        start_year, start_iso_week = (int(part) for part in start_week.split("-", 1))
        start_date = datetime.date.fromisocalendar(start_year, start_iso_week, 1)
    except ValueError:
        return None

    end_year, end_iso_week, _ = last_event_date.isocalendar()
    end_date = datetime.date.fromisocalendar(end_year, end_iso_week, 7)
    if end_date < start_date:
        end_date = start_date + datetime.timedelta(days=6)
        end_year, end_iso_week, _ = end_date.isocalendar()
    planning_horizon_weeks = ((end_date - start_date).days // 7) + 1
    range_key = f"{start_year:04d}-{start_iso_week:02d}--{end_year:04d}-{end_iso_week:02d}"
    temporal_scope = {"from": start_date.isoformat(), "to": end_date.isoformat()}
    return range_key, temporal_scope, planning_horizon_weeks


def _normalized_phase_length(guidance: dict[str, Any]) -> int:
    cadence = str(guidance.get("deload_cadence") or "").strip()
    mapped = _CADENCE_PHASE_LENGTHS.get(cadence)
    if mapped is not None:
        return mapped
    return _as_positive_int(guidance.get("phase_length_weeks")) or 4


def _build_phase_plan_summary(
    planning_horizon_weeks: int,
    phase_length_weeks: int,
    max_shortened_phases: int,
) -> tuple[int, int, list[dict[str, int]]]:
    phase_count = math.ceil(planning_horizon_weeks / phase_length_weeks)
    shortening_budget = max(0, (phase_count * phase_length_weeks) - planning_horizon_weeks)
    if shortening_budget == 0:
        return phase_count, 0, []

    max_supported_shortened = min(2, phase_count)
    max_reduction_per_shortened = max(1, phase_length_weeks - _MIN_SHORTENED_PHASE_LENGTH)
    required_shortened = math.ceil(shortening_budget / max_reduction_per_shortened)
    shortened_count = min(
        max_supported_shortened,
        max(max(1, max_shortened_phases), required_shortened),
    )
    base_reduction = shortening_budget // shortened_count
    remainder = shortening_budget % shortened_count
    reductions = [base_reduction + (1 if idx < remainder else 0) for idx in range(shortened_count)]

    shortened_lengths: dict[int, int] = {}
    for reduction in reductions:
        length = max(_MIN_SHORTENED_PHASE_LENGTH, phase_length_weeks - reduction)
        shortened_lengths[length] = shortened_lengths.get(length, 0) + 1

    shortened_phases = [
        {"len": length, "count": count}
        for length, count in sorted(shortened_lengths.items(), reverse=True)
    ]
    full_phases = phase_count - shortened_count
    return full_phases, shortening_budget, shortened_phases


def _trace_entry_from_string(value: str, *, allowed: set[str]) -> dict[str, str] | None:
    raw = value.strip()
    if not raw:
        return None
    artifact_token = raw.split(".", 1)[0]
    lowered = artifact_token.lower()
    artifact = ""
    for candidate in sorted(allowed, key=len, reverse=True):
        if lowered.startswith(candidate.lower()):
            artifact = candidate
            break
    if not artifact:
        return None
    run_id = raw.split(".", 1)[1].strip() if "." in raw else raw
    run_id = run_id.removesuffix(".json").strip()
    if not run_id:
        return None
    return {
        "artifact": artifact,
        "version": "1.0",
        "schema_version": "1.0",
        "version_key": _canonical_trace_version_key(artifact, run_id),
        "run_id": run_id,
    }


def _canonical_trace_version_key(artifact: str, version_key: object) -> str:
    """Return a canonical version_key for phase/season artifact lineage."""

    rendered = str(version_key or "").strip()
    if not rendered:
        return rendered
    canonical = rendered.removesuffix(".json")
    prefix = f"{artifact.lower()}_"
    if canonical.lower().startswith(prefix):
        canonical = canonical[len(prefix) :]
    return canonical


def _normalize_trace_entries(value: object, *, allowed: set[str]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized_by_key: dict[tuple[str, str], dict[str, str]] = {}
    ordered_keys: list[tuple[str, str]] = []

    def _score(entry: dict[str, str]) -> tuple[int, int]:
        run_id = entry["run_id"].strip().lower()
        version_key = entry["version_key"].strip().lower()
        return (
            0 if run_id in {"runtime-owned", "unknown"} else 1,
            0 if version_key.endswith(".json") else 1,
        )

    for item in value:
        if isinstance(item, str):
            entry = _trace_entry_from_string(item, allowed=allowed)
            if entry is None:
                continue
        elif isinstance(item, dict):
            artifact = str(item.get("artifact") or "").strip().upper()
            if artifact not in allowed:
                continue
            version = _normalize_semver(item.get("version"))
            run_id = str(item.get("run_id") or "").strip()
            if not run_id:
                continue
            reference = normalize_trace_reference(
                {
                    "artifact": artifact,
                    "version": version,
                    "schema_version": item.get("schema_version"),
                    "version_key": _canonical_trace_version_key(artifact, item.get("version_key")),
                    "run_id": run_id,
                }
            )
            if reference is None:
                continue
            entry = {key: str(value) for key, value in reference.items()}
        else:
            continue
        token = (entry["artifact"], entry["version_key"])
        existing = normalized_by_key.get(token)
        if existing is None:
            normalized_by_key[token] = entry
            ordered_keys.append(token)
            continue
        if _score(entry) > _score(existing):
            normalized_by_key[token] = entry
    return [normalized_by_key[token] for token in ordered_keys]


def _replace_canonical_direct_trace_entry(
    entries: object,
    *,
    replacement: dict[str, str] | None,
) -> list[dict[str, Any] | str]:
    """Replace direct-upstream lineage for one artifact/version pair with a canonical entry."""

    normalized_entries = list(entries) if isinstance(entries, list) else []
    if replacement is None:
        return [item for item in normalized_entries if isinstance(item, (dict, str))]

    target_artifact = replacement["artifact"].strip().upper()
    target_version_key = _canonical_trace_version_key(target_artifact, replacement["version_key"])
    filtered: list[dict[str, Any] | str] = []
    for item in normalized_entries:
        if isinstance(item, str):
            filtered.append(item)
            continue
        if not isinstance(item, dict):
            continue
        artifact = str(item.get("artifact") or "").strip().upper()
        version_key = _canonical_trace_version_key(artifact, item.get("version_key"))
        if artifact == target_artifact and version_key == target_version_key:
            continue
        filtered.append(item)
    filtered.append(replacement)
    return filtered


def normalize_phase_guardrails_document(
    document: dict[str, Any],
    *,
    season_plan_document: dict[str, Any] | None = None,
    phase_execution_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize PHASE_GUARDRAILS shape quirks before validation."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    if str(meta.get("artifact_type", "")).upper() != "PHASE_GUARDRAILS":
        return document
    data = document.get("data")
    if not isinstance(data, dict):
        return document
    execution_non_negotiables = data.get("execution_non_negotiables")
    if isinstance(execution_non_negotiables, dict):
        recovery_rules = execution_non_negotiables.get("recovery_protection_rules")
        if isinstance(recovery_rules, list):
            normalized_rules = [str(item).strip() for item in recovery_rules if str(item).strip()]
            execution_non_negotiables["recovery_protection_rules"] = " | ".join(normalized_rules)
        data["execution_non_negotiables"] = execution_non_negotiables
    load_guardrails = data.get("load_guardrails")
    if not isinstance(load_guardrails, dict):
        document["data"] = data
        return document

    def _widen_band(entry: dict[str, Any]) -> None:
        band = entry.get("band")
        if not isinstance(band, dict):
            return
        min_val = band.get("min")
        max_val = band.get("max")
        if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            band["min"] = float(min_val)
            band["max"] = float(max_val)

    rows = load_guardrails.get("weekly_kj_bands")
    if isinstance(rows, list):
        for entry in rows:
            if isinstance(entry, dict):
                _widen_band(entry)

    context = _as_map(phase_execution_context)
    phase_bands = persisted_phase_weekly_kj_bands(context.get("phase_role_week_load_bands"))
    if phase_bands:
        load_guardrails["weekly_kj_bands"] = phase_bands

    season_data = season_plan_document.get("data") if isinstance(season_plan_document, dict) else None
    if isinstance(season_data, dict):
        inherited_contract = season_data.get("selected_scenario_contract")
        if isinstance(inherited_contract, dict):
            data["inherited_scenario_contract"] = inherited_contract
        season_phase = _season_phase_for_range(season_plan_document, meta.get("iso_week_range"))
        if season_phase:
            phase_summary = data.get("phase_summary")
            if not isinstance(phase_summary, dict):
                phase_summary = {}
            overview = _as_map(season_phase.get("overview"))
            phase_goals = _as_map(overview.get("phase_goals"))
            if not str(phase_summary.get("primary_objective") or "").strip():
                primary_objective = str(phase_goals.get("primary") or "").strip()
                if primary_objective:
                    phase_summary["primary_objective"] = primary_objective
            data["phase_summary"] = phase_summary
            semantics = _as_map(season_phase.get("allowed_forbidden_semantics"))
            if semantics:
                allowed_forbidden = data.get("allowed_forbidden_semantics")
                if not isinstance(allowed_forbidden, dict):
                    allowed_forbidden = {}
                if not _text_list(allowed_forbidden.get("allowed_intensity_domains")):
                    allowed_forbidden["allowed_intensity_domains"] = list(
                        semantics.get("allowed_intensity_domains") or []
                    )
                if not _text_list(allowed_forbidden.get("allowed_load_modalities")):
                    allowed_forbidden["allowed_load_modalities"] = list(
                        semantics.get("allowed_load_modalities") or []
                    )
                if not _text_list(allowed_forbidden.get("forbidden_intensity_domains")):
                    allowed_forbidden["forbidden_intensity_domains"] = list(
                        semantics.get("forbidden_intensity_domains") or []
                    )
                data["allowed_forbidden_semantics"] = allowed_forbidden
            exact_bands = persisted_phase_weekly_kj_bands(_season_phase_role_week_load_bands(season_phase))
            if exact_bands and not phase_bands:
                load_guardrails["weekly_kj_bands"] = exact_bands

    phase_summary = data.get("phase_summary")
    if not isinstance(phase_summary, dict):
        phase_summary = {}
    primary_objective = str(context.get("phase_primary_objective") or "").strip()
    if primary_objective:
        phase_summary["primary_objective"] = primary_objective
    if phase_summary:
        data["phase_summary"] = phase_summary

    allowed_forbidden = data.get("allowed_forbidden_semantics")
    if not isinstance(allowed_forbidden, dict):
        allowed_forbidden = {}
    allowed_domains = _text_list(context.get("phase_allowed_intensity_domains"))
    if allowed_domains:
        allowed_forbidden["allowed_intensity_domains"] = allowed_domains
    forbidden_domains = _text_list(context.get("phase_forbidden_intensity_domains"))
    if forbidden_domains:
        allowed_forbidden["forbidden_intensity_domains"] = forbidden_domains
    allowed_modalities = _text_list(context.get("phase_allowed_load_modalities"))
    if allowed_modalities:
        allowed_forbidden["allowed_load_modalities"] = allowed_modalities
    quality_density = allowed_forbidden.get("quality_density")
    if not isinstance(quality_density, dict):
        quality_density = {}
    canonical_quality_intent = _canonical_quality_intent(
        phase_type=context.get("phase_type") or _as_map(data.get("body_metadata")).get("phase_type"),
        phase_intent=context.get("phase_intent") or _as_map(data.get("body_metadata")).get("phase_intent"),
        current=quality_density.get("quality_intent"),
    )
    if canonical_quality_intent:
        quality_density["quality_intent"] = canonical_quality_intent
    if quality_density:
        allowed_forbidden["quality_density"] = quality_density
    if allowed_forbidden:
        data["allowed_forbidden_semantics"] = allowed_forbidden

    document["data"] = data
    return _project_phase_guardrails_season_constraints(
        document,
        season_plan_document=season_plan_document,
    )


def normalize_season_scenarios_document(
    document: dict[str, Any],
    *,
    planning_events_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize season scenario horizon and phase math before validation."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    artifact_type = str(meta.get("artifact_type", "")).upper()
    if artifact_type == "SEASON_SCENARIO_SELECTION":
        meta["version"] = _normalize_semver(meta.get("version"))
        meta["scope"] = _normalize_meta_scope(meta.get("scope"))
        if meta.get("authority") != "Informational":
            meta["authority"] = "Informational"
        if meta.get("owner_agent") != "Season-Scenario-Agent":
            meta["owner_agent"] = "Season-Scenario-Agent"
        if meta.get("schema_id") != "SeasonScenarioSelectionInterface":
            meta["schema_id"] = "SeasonScenarioSelectionInterface"
        if meta.get("schema_version") != "1.0":
            meta["schema_version"] = "1.0"
        if "notes" not in meta:
            meta["notes"] = ""
        else:
            notes_value = meta.get("notes")
            if isinstance(notes_value, list):
                meta["notes"] = " ".join(str(item) for item in notes_value if item is not None)
        meta["trace_upstream"] = _normalize_trace_entries(
            meta.get("trace_upstream"),
            allowed=_SEASON_SCENARIO_TRACE_UPSTREAM_ARTIFACTS,
        )
        meta["trace_events"] = _normalize_trace_entries(
            meta.get("trace_events"),
            allowed=_SEASON_SCENARIO_TRACE_EVENT_ARTIFACTS,
        )
        meta["trace_data"] = _normalize_trace_entries(
            meta.get("trace_data"),
            allowed=_SEASON_SCENARIO_TRACE_DATA_ARTIFACTS,
        )
        document["meta"] = meta
        data = document.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("selection_rationale", "")
        data.setdefault("notes", [])
        document["data"] = data
        return document
    if artifact_type != "SEASON_SCENARIOS":
        return document

    meta["version"] = _normalize_semver(meta.get("version"))
    meta["scope"] = _normalize_meta_scope(meta.get("scope"))
    if meta.get("authority") != "Informational":
        meta["authority"] = "Informational"
    if meta.get("owner_agent") != "Season-Scenario-Agent":
        meta["owner_agent"] = "Season-Scenario-Agent"
    if meta.get("schema_id") != "SeasonScenariosInterface":
        meta["schema_id"] = "SeasonScenariosInterface"
    if meta.get("schema_version") != "1.0":
        meta["schema_version"] = "1.0"
    if "notes" not in meta:
        meta["notes"] = ""
    else:
        notes_value = meta.get("notes")
        if isinstance(notes_value, list):
            meta["notes"] = " ".join(str(item) for item in notes_value if item is not None)
    meta["trace_upstream"] = _normalize_trace_entries(
        meta.get("trace_upstream"),
        allowed=_SEASON_SCENARIO_TRACE_UPSTREAM_ARTIFACTS,
    )
    meta["trace_events"] = _normalize_trace_entries(meta.get("trace_events"), allowed=_SEASON_SCENARIO_TRACE_EVENT_ARTIFACTS)
    meta["trace_data"] = _normalize_trace_entries(meta.get("trace_data"), allowed=_SEASON_SCENARIO_TRACE_DATA_ARTIFACTS)

    data = document.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    allowed_data_keys = {"kpi_profile_ref", "athlete_profile_ref", "planning_horizon_weeks", "scenarios", "notes"}
    data = {key: value for key, value in data.items() if key in allowed_data_keys}
    data["kpi_profile_ref"] = _text_value(data.get("kpi_profile_ref"), fallback="kpi_profile.latest")
    data["athlete_profile_ref"] = _text_value(data.get("athlete_profile_ref"), fallback="athlete_profile.latest")
    data["notes"] = _text_list(data.get("notes"))

    previous_range = meta.get("iso_week_range")
    previous_horizon = data.get("planning_horizon_weeks")
    planning_horizon_weeks: int | None = None
    derived_horizon = _derive_planning_horizon_from_events(meta, planning_events_document)
    if derived_horizon is not None:
        range_key, temporal_scope, planning_horizon_weeks = derived_horizon
        meta["iso_week_range"] = range_key
        meta["temporal_scope"] = temporal_scope
        data["planning_horizon_weeks"] = planning_horizon_weeks
        if previous_range != range_key or previous_horizon != planning_horizon_weeks:
            logger.info(
                "Season scenarios horizon normalized from range=%s horizon=%s to range=%s horizon=%s",
                previous_range,
                previous_horizon,
                range_key,
                planning_horizon_weeks,
            )
    else:
        planning_horizon_weeks = _as_positive_int(data.get("planning_horizon_weeks"))
        if planning_horizon_weeks is None:
            planning_horizon_weeks = _as_positive_int(_iso_week_range_weeks(meta.get("iso_week_range")))
        if planning_horizon_weeks is not None:
            data["planning_horizon_weeks"] = planning_horizon_weeks

    scenarios = data.get("scenarios") or []
    cleaned_scenarios: list[dict[str, Any]] = []
    if isinstance(scenarios, list):
        for idx, scenario in enumerate(scenarios[:3]):
            if not isinstance(scenario, dict):
                continue
            allowed_scenario_keys = {
                "scenario_id",
                "name",
                "core_idea",
                "load_philosophy",
                "risk_profile",
                "key_differences",
                "best_suited_if",
                "typical_week_feel",
                "main_payoff",
                "main_cost",
                "what_gets_prioritized",
                "what_gets_de_emphasized",
                "scenario_guidance",
            }
            scenario = {key: value for key, value in scenario.items() if key in allowed_scenario_keys}
            scenario_id = str(scenario.get("scenario_id") or "").strip().upper()
            if scenario_id not in _SCENARIO_IDS:
                scenario_id = _SCENARIO_IDS[idx] if idx < len(_SCENARIO_IDS) else "C"
            scenario["scenario_id"] = scenario_id
            for key in (
                "name",
                "core_idea",
                "load_philosophy",
                "risk_profile",
                "key_differences",
                "best_suited_if",
            ):
                scenario[key] = _text_value(scenario.get(key))
            scenario["typical_week_feel"] = _text_value(
                scenario.get("typical_week_feel"),
                fallback="Typical weeks should feel coherent with the scenario's load, recovery, and specificity tradeoffs.",
            )
            scenario["main_payoff"] = _text_value(
                scenario.get("main_payoff"),
                fallback="The scenario provides a distinct training benefit relative to the other options.",
            )
            scenario["main_cost"] = _text_value(
                scenario.get("main_cost"),
                fallback="The scenario gives up some margin, sharpness, or robustness relative to the other options.",
            )
            scenario["what_gets_prioritized"] = _text_value(
                scenario.get("what_gets_prioritized"),
                fallback="The scenario emphasizes the most important adaptation or execution priority.",
            )
            scenario["what_gets_de_emphasized"] = _text_value(
                scenario.get("what_gets_de_emphasized"),
                fallback="The scenario intentionally downplays lower-priority training elements.",
            )
            guidance = scenario.get("scenario_guidance") or {}
            if not isinstance(guidance, dict):
                guidance = {}
            allowed_guidance_keys = {
                "recovery_margin",
                "fatigue_exposure",
                "specificity_density",
                "deload_cadence",
                "phase_length_weeks",
                "phase_count_expected",
                "max_shortened_phases",
                "shortening_budget_weeks",
                "phase_plan_summary",
                "event_alignment_notes",
                "risk_flags",
                "fixed_rest_days",
                "constraint_summary",
                "kpi_guardrail_notes",
                "decision_notes",
                "season_archetype",
                "season_archetype_rationale",
                "intensity_guidance",
                "assumptions",
                "unknowns",
            }
            guidance = {key: value for key, value in guidance.items() if key in allowed_guidance_keys}
            guidance["recovery_margin"] = _text_value(guidance.get("recovery_margin"))
            guidance["fatigue_exposure"] = _text_value(guidance.get("fatigue_exposure"))
            guidance["specificity_density"] = _text_value(guidance.get("specificity_density"))
            cadence = str(guidance.get("deload_cadence") or "").strip()
            if cadence not in _CADENCE_PHASE_LENGTHS:
                cadence = "3:1"
            guidance["deload_cadence"] = cadence
            phase_length_weeks = _normalized_phase_length(guidance)
            guidance["phase_length_weeks"] = phase_length_weeks

            if planning_horizon_weeks is not None:
                max_shortened_phases = _as_non_negative_int(guidance.get("max_shortened_phases"))
                if max_shortened_phases is None:
                    max_shortened_phases = 2
                full_phases, shortening_budget_weeks, shortened_phases = _build_phase_plan_summary(
                    planning_horizon_weeks,
                    phase_length_weeks,
                    max_shortened_phases,
                )
                guidance["phase_count_expected"] = math.ceil(planning_horizon_weeks / phase_length_weeks)
                guidance["shortening_budget_weeks"] = shortening_budget_weeks
                guidance["max_shortened_phases"] = (
                    max(max_shortened_phases, sum(item["count"] for item in shortened_phases))
                    if shortening_budget_weeks > 0
                    else 0
                )
                guidance["phase_plan_summary"] = {
                    "full_phases": full_phases,
                    "shortened_phases": shortened_phases,
                }
            else:
                guidance["phase_count_expected"] = _as_positive_int(guidance.get("phase_count_expected")) or 1
                guidance["max_shortened_phases"] = _as_non_negative_int(guidance.get("max_shortened_phases")) or 2
                guidance["shortening_budget_weeks"] = _as_non_negative_int(guidance.get("shortening_budget_weeks")) or 0
                guidance["phase_plan_summary"] = {
                    "full_phases": guidance["phase_count_expected"],
                    "shortened_phases": [],
                }

            for key in (
                "event_alignment_notes",
                "risk_flags",
                "fixed_rest_days",
                "constraint_summary",
                "kpi_guardrail_notes",
                "decision_notes",
                "season_archetype_rationale",
                "assumptions",
                "unknowns",
            ):
                guidance[key] = _text_list(guidance.get(key))
            season_archetype = str(guidance.get("season_archetype") or "").strip()
            if season_archetype not in {"none", "ceiling_first_durability"}:
                season_archetype = "none"
            guidance["season_archetype"] = season_archetype
            if season_archetype == "none" and not guidance["season_archetype_rationale"]:
                guidance["season_archetype_rationale"] = []
            intensity_guidance = guidance.get("intensity_guidance")
            if not isinstance(intensity_guidance, dict):
                intensity_guidance = {}
            allowed_domains = normalize_intensity_domain_list(intensity_guidance.get("allowed_domains"))
            avoid_domains = normalize_intensity_domain_list(intensity_guidance.get("avoid_domains"))
            if not allowed_domains:
                allowed_domains = ["ENDURANCE"]
            avoid_domains = [
                domain
                for domain in avoid_domains
                if domain not in set(allowed_domains) and domain not in _DISALLOWED_AVOID_DOMAINS
            ]
            intensity_guidance["allowed_domains"] = allowed_domains
            intensity_guidance["avoid_domains"] = avoid_domains
            guidance["intensity_guidance"] = intensity_guidance
            scenario["scenario_guidance"] = guidance
            cleaned_scenarios.append(scenario)
    data["scenarios"] = cleaned_scenarios
    document["meta"] = meta
    document["data"] = data
    return document


def load_shared_knowledge_source(relative_dir: str, filename: str) -> str | None:
    """Return a shared knowledge source file content when it exists."""

    path = _KNOWLEDGE_SOURCE_ROOT / relative_dir / filename
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def injection_mode_for_tasks(tasks: list[AgentTask]) -> str | None:
    """Resolve a single injection mode from the requested task list."""

    mapping = {
        AgentTask.CREATE_SEASON_SCENARIOS: "scenario",
        AgentTask.CREATE_SEASON_SCENARIO_SELECTION: "scenario",
        AgentTask.CREATE_SEASON_PLAN: "season_plan",
        AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD: "feed_forward",
        AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
        AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
        AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
        AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
        AgentTask.CREATE_WEEK_PLAN: "week_plan",
        AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
    }
    modes = {mapping[task] for task in tasks if task in mapping}
    if len(modes) != 1:
        return None
    return next(iter(modes))
