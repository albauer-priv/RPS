"""Phase-artifact CrewAI guardrails enforcing ADR-035 authority boundaries."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from rps.crewai_runtime.guardrails_context import GuardrailResult, JsonMap
from rps.crewai_runtime.guardrails_utilities import (
    _as_float,
    _as_list,
    _as_map,
    _coerce_mapping,
    _phase_execution_context,
)
from rps.planning.contracts import (
    blocking_messages,
    validate_phase_against_execution_context,
    validate_phase_bundle_review_readiness,
    validate_phase_s5_bands_against_context,
)
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week, parse_iso_week_range


def phase_bundle_integrity(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    required = ("phase_range", "week_blueprints", "guardrails", "structure", "preview", "constraint_audit", "load_governance_audit")
    missing = [field for field in required if field not in mapping]
    if missing:
        return (False, f"Phase bundle missing required keys: {', '.join(missing)}")
    week_blueprints = mapping.get("week_blueprints")
    if not isinstance(week_blueprints, list) or not week_blueprints:
        return (False, "Phase bundle must include at least one week blueprint.")
    return (True, mapping)


def phase_bundle_matches_context(result: Any) -> GuardrailResult:
    """Validate internal Phase bundle week blueprints against execution context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    context = _phase_execution_context()
    if not context:
        return (True, mapping)
    blueprints = [_as_map(item) for item in _as_list(mapping.get("week_blueprints"))]
    if not blueprints:
        return (False, "Phase bundle must include week_blueprints for contract validation.")
    inherited_contract = _as_map(context.get("inherited_scenario_contract"))
    phase_payload = {
        "data": {
            "load_ranges": {
                "weekly_kj_bands": [
                    {
                        "week": item.get("week"),
                        "band": {"min": item.get("s5_band_min"), "max": item.get("s5_band_max")},
                    }
                    for item in blueprints
                ]
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": item.get("week"), "role": item.get("week_role")}
                        for item in blueprints
                    ]
                }
            },
        }
    }
    if inherited_contract:
        phase_payload["data"]["inherited_scenario_contract"] = inherited_contract
        if _as_map(_as_map(phase_payload.get("data")).get("inherited_scenario_contract")) != inherited_contract:
            return (False, "Synthetic Phase candidate missing deterministic inherited_scenario_contract.")
    issues = validate_phase_against_execution_context(
        phase_payload=phase_payload,
        phase_execution_context=context,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def phase_s5_band_match(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase guardrails output must decode to an object.")
    context = _phase_execution_context()
    if context:
        issues = validate_phase_s5_bands_against_context(
            phase_payload=mapping,
            phase_execution_context=context,
        )
        messages = blocking_messages(issues)
        if messages:
            return (False, "; ".join(messages[:5]))
        return (True, mapping)
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


def phase_bundle_review_readiness(result: Any) -> GuardrailResult:
    """Ensure a normalized phase bundle is review-ready before review runs."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase bundle must decode to an object.")
    issues = validate_phase_bundle_review_readiness(phase_bundle_payload=mapping)
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
    return (True, mapping)


def phase_execution_context_match(result: Any) -> GuardrailResult:
    """Validate Phase artifact structure and bands against phase execution context."""

    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase output must decode to an object.")
    context = _phase_execution_context()
    if not context:
        return (True, mapping)
    issues = validate_phase_against_execution_context(
        phase_payload=mapping,
        phase_execution_context=context,
    )
    messages = blocking_messages(issues)
    if messages:
        return (False, "; ".join(messages[:5]))
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


def phase_week_role_load_coherence(result: Any) -> GuardrailResult:
    mapping = _coerce_mapping(result)
    if not isinstance(mapping, dict):
        return (False, "Phase output must decode to an object.")
    if "week_blueprints" in mapping:
        blueprints = mapping.get("week_blueprints")
        if not isinstance(blueprints, list) or not blueprints:
            return (False, "Phase week_blueprints must be non-empty.")
        ok, message = _check_role_band_sequence(
            [
                {
                    "week": item.get("week"),
                    "role": item.get("week_role"),
                    "min": item.get("s5_band_min"),
                    "max": item.get("s5_band_max"),
                    "notes": " ".join(str(warn) for warn in item.get("warnings") or []),
                }
                for item in blueprints
                if isinstance(item, dict)
            ]
        )
        return (ok, mapping if ok else message)
    data = mapping.get("data")
    if not isinstance(data, dict):
        return (True, mapping)
    bands_by_week: dict[str, JsonMap] = {}
    load_ranges = data.get("load_ranges")
    if isinstance(load_ranges, dict):
        for entry in load_ranges.get("weekly_kj_bands") or []:
            if not isinstance(entry, dict):
                continue
            week = _coerce_week_key(entry.get("week"))
            band = entry.get("band")
            if week and isinstance(band, dict):
                bands_by_week[week] = band
    skeleton = data.get("week_skeleton_logic")
    roles_map = skeleton.get("week_roles") if isinstance(skeleton, dict) else {}
    role_entries = roles_map.get("week_roles") if isinstance(roles_map, dict) else []
    sequence = []
    for entry in role_entries or []:
        if not isinstance(entry, dict):
            continue
        week = _coerce_week_key(entry.get("week"))
        band = bands_by_week.get(week or "")
        if not week or not band:
            continue
        sequence.append(
            {
                "week": week,
                "role": entry.get("role"),
                "min": band.get("min"),
                "max": band.get("max"),
                "notes": band.get("notes"),
            }
        )
    if not sequence:
        return (True, mapping)
    ok, message = _check_role_band_sequence(sequence)
    return (ok, mapping if ok else message)


def _extract_expected_s5_band(notes: str) -> tuple[int, int] | None:
    match = re.search(r"S5(?: deterministic)? band(?: is|=|:)?\s*(\d+)\s*(?:-|/|to)\s*(\d+)", notes, re.I)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _check_role_band_sequence(sequence: list[JsonMap]) -> GuardrailResult:
    previous_load_max: float | None = None
    previous_load_role = ""
    for entry in sequence:
        role = str(entry.get("role") or "").upper()
        max_value = _as_float(entry.get("max"))
        notes = str(entry.get("notes") or "").lower()
        if max_value is None:
            continue
        fallback_allows_flat = "fallback_level 4" in notes or "fallback_level 5" in notes or "s5 fallback" in notes
        if role in {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"} and previous_load_max is not None:
            required_factor = 0.92 if role in {"MINI_RESET", "SHORTENED_MINI_RESET"} else 0.82
            if max_value >= previous_load_max * required_factor and not fallback_allows_flat:
                return (
                    False,
                    f"{entry.get('week')} {role} band must reduce materially versus prior load role {previous_load_role}.",
                )
        if role in {"RELOAD", "SHORTENED_RELOAD"} and previous_load_max is not None:
            if max_value > previous_load_max * 1.13 and not fallback_allows_flat:
                return (False, f"{entry.get('week')} {role} band reload exceeds progressive-overload bounds.")
        if role.startswith("LOAD") or role in {"RELOAD", "SHORTENED_CONSOLIDATION", "SHORTENED_RELOAD"}:
            previous_load_max = max_value
            previous_load_role = role
    return (True, sequence)


def _iso_week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


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
