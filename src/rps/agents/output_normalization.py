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
from rps.workspace.intensity_domains import normalize_intensity_domain_list

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
_DISALLOWED_AVOID_DOMAINS = {"NONE", "RECOVERY"}


def normalize_workout_percent_ranges(text: str) -> str:
    """Normalize malformed power ranges like ``68-72%`` to ``68%-72%``."""

    return re.sub(
        r"(?<![%\d])(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)%(?!\S)",
        r"\1%-\2%",
        text,
    )


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


def _normalize_trace_entries(value: object, *, allowed: set[str]) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        artifact = str(item.get("artifact") or "").strip().upper()
        if artifact not in allowed:
            continue
        version = str(item.get("version") or "").strip() or "1.0"
        run_id = str(item.get("run_id") or "").strip()
        if not run_id:
            continue
        token = (artifact, version, run_id)
        if token in seen:
            continue
        seen.add(token)
        normalized.append({"artifact": artifact, "version": version, "run_id": run_id})
    return normalized


def normalize_phase_guardrails_document(document: dict[str, Any]) -> dict[str, Any]:
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

    document["data"] = data
    return document


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
    meta["trace_events"] = _normalize_trace_entries(meta.get("trace_events"), allowed=_SEASON_SCENARIO_TRACE_EVENT_ARTIFACTS)
    meta["trace_data"] = _normalize_trace_entries(meta.get("trace_data"), allowed=_SEASON_SCENARIO_TRACE_DATA_ARTIFACTS)

    data = document.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    allowed_data_keys = {"kpi_profile_ref", "athlete_profile_ref", "planning_horizon_weeks", "scenarios", "notes"}
    data = {key: value for key, value in data.items() if key in allowed_data_keys}
    data.setdefault("notes", [])

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
        for scenario in scenarios:
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
                "scenario_guidance",
            }
            scenario = {key: value for key, value in scenario.items() if key in allowed_scenario_keys}
            guidance = scenario.get("scenario_guidance") or {}
            if not isinstance(guidance, dict):
                guidance = {}
            allowed_guidance_keys = {
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
                "intensity_guidance",
                "assumptions",
                "unknowns",
            }
            guidance = {key: value for key, value in guidance.items() if key in allowed_guidance_keys}
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

            guidance.setdefault("event_alignment_notes", [])
            guidance.setdefault("risk_flags", [])
            guidance.setdefault("fixed_rest_days", [])
            guidance.setdefault("constraint_summary", [])
            guidance.setdefault("kpi_guardrail_notes", [])
            guidance.setdefault("decision_notes", [])
            guidance.setdefault("assumptions", [])
            guidance.setdefault("unknowns", [])
            intensity_guidance = guidance.get("intensity_guidance")
            if not isinstance(intensity_guidance, dict):
                intensity_guidance = {}
            allowed_domains = normalize_intensity_domain_list(intensity_guidance.get("allowed_domains"))
            avoid_domains = normalize_intensity_domain_list(intensity_guidance.get("avoid_domains"))
            if not allowed_domains:
                allowed_domains = ["ENDURANCE_LOW"]
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
