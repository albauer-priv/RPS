"""Strict binding resolution for Season Scenario Selection against latest scenarios."""

from __future__ import annotations

from typing import Any

from rps.planning.season_structure import (
    build_selected_scenario_contract_context,
    build_selected_scenario_structure_context,
    render_selected_scenario_contract_block,
    render_selected_scenario_structure_block,
)

JsonMap = dict[str, Any]

REASON_SELECTION_MISSING = "selection_missing"
REASON_SCENARIOS_MISSING = "scenarios_missing"
REASON_SELECTION_STALE = "selection_stale_vs_scenarios"
REASON_SELECTED_SCENARIO_UNRESOLVED = "selected_scenario_unresolved"
REASON_SELECTED_SCENARIO_CONTRACT_INCOMPLETE = "selected_scenario_contract_incomplete"
REASON_SELECTED_SCENARIO_STRUCTURE_MISSING = "selected_scenario_structure_missing"

CONTRACT_REQUIRED_FIELDS = (
    "selected_scenario_id",
    "scenario_name",
    "selection_source",
    "selection_rationale",
    "load_posture",
    "recovery_margin",
    "fatigue_exposure",
    "specificity_density",
    "load_philosophy",
    "risk_profile",
    "constraint_summary",
    "event_alignment_notes",
    "risk_flags",
    "kpi_guardrail_notes",
    "decision_notes",
    "season_archetype",
    "allowed_intensity_domains",
    "forbidden_intensity_domains",
    "deload_cadence",
)

CONTRACT_NONEMPTY_FIELDS = (
    "selected_scenario_id",
    "scenario_name",
    "selection_source",
    "load_posture",
    "recovery_margin",
    "fatigue_exposure",
    "specificity_density",
    "load_philosophy",
    "risk_profile",
    "season_archetype",
    "deload_cadence",
)

STRUCTURE_REQUIRED_FIELDS = (
    "selected_scenario_id",
    "scenario_name",
    "planning_horizon_weeks",
    "deload_cadence",
    "phase_length_weeks",
    "phase_count_expected",
    "allowed_intensity_domains",
    "forbidden_intensity_domains",
    "season_archetype",
)


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_str(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _version_key(payload: JsonMap | None) -> str:
    return _as_str(_as_map(payload).get("meta", {}).get("version_key"))


def _run_id(payload: JsonMap | None) -> str:
    return _as_str(_as_map(payload).get("meta", {}).get("run_id"))


def _resolve_selected_id(selection_payload: JsonMap | None, explicit_selected_scenario_id: str | None) -> str:
    explicit = _as_str(explicit_selected_scenario_id)
    if explicit:
        return explicit
    return _as_str(_as_map(selection_payload).get("data", {}).get("selected_scenario_id"))


def _scenario_exists(scenarios_payload: JsonMap | None, selected_scenario_id: str) -> bool:
    scenarios = _as_list(_as_map(_as_map(scenarios_payload).get("data")).get("scenarios"))
    return any(_as_str(_as_map(item).get("scenario_id")) == selected_scenario_id for item in scenarios)


def _selection_binds_to_scenarios(selection_payload: JsonMap | None, scenarios_payload: JsonMap | None) -> bool:
    selection_meta = _as_map(_as_map(selection_payload).get("meta"))
    selection_data = _as_map(_as_map(selection_payload).get("data"))
    scenarios_meta = _as_map(_as_map(scenarios_payload).get("meta"))
    scenarios_version_key = _as_str(scenarios_meta.get("version_key"))
    if not scenarios_version_key:
        return False

    for entry in _as_list(selection_meta.get("trace_upstream")):
        entry_map = _as_map(entry)
        if _as_str(entry_map.get("artifact")) != "SEASON_SCENARIOS":
            continue
        if _as_str(entry_map.get("version_key")) == scenarios_version_key:
            return True
        if _as_str(entry_map.get("version")) == scenarios_version_key:
            return True

    return _as_str(selection_data.get("season_scenarios_ref")) == scenarios_version_key


def _contract_missing_fields(contract: JsonMap) -> list[str]:
    missing: list[str] = []
    list_fields = {
        "constraint_summary",
        "event_alignment_notes",
        "risk_flags",
        "kpi_guardrail_notes",
        "decision_notes",
        "allowed_intensity_domains",
        "forbidden_intensity_domains",
    }
    for field in CONTRACT_REQUIRED_FIELDS:
        if field not in contract:
            missing.append(field)
            continue
        value = contract.get(field)
        if field in CONTRACT_NONEMPTY_FIELDS:
            if isinstance(value, str) and not value.strip():
                missing.append(field)
            elif value is None:
                missing.append(field)
        elif field in list_fields:
            if not isinstance(value, list):
                missing.append(field)
                continue
            if field == "constraint_summary" and not [item for item in value if isinstance(item, str) and item.strip()]:
                missing.append(field)
    return missing


def _structure_missing_fields(structure: JsonMap) -> list[str]:
    missing: list[str] = []
    for field in STRUCTURE_REQUIRED_FIELDS:
        value = structure.get(field)
        if field in {"allowed_intensity_domains", "forbidden_intensity_domains"}:
            if not isinstance(value, list):
                missing.append(field)
            continue
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    return missing


def resolve_bound_season_selection(
    *,
    season_scenarios_payload: JsonMap | None,
    selection_payload: JsonMap | None,
    selected_scenario_id: str | None = None,
) -> JsonMap:
    """Return strict latest-selection binding verdict plus derived season context when valid."""

    scenarios = _as_map(season_scenarios_payload)
    selection = _as_map(selection_payload)
    scenarios_version_key = _version_key(scenarios)
    selection_version_key = _version_key(selection)
    explicit_selected = _as_str(selected_scenario_id)

    base: JsonMap = {
        "ok": False,
        "reason_code": "",
        "reason_message": "",
        "selected_scenario_id": "",
        "selection_version_key": selection_version_key,
        "scenarios_version_key": scenarios_version_key,
        "selection_run_id": _run_id(selection),
        "scenarios_run_id": _run_id(scenarios),
        "selection_payload": selection,
        "scenarios_payload": scenarios,
        "selected_scenario_structure_context": {},
        "selected_scenario_contract": {},
        "selected_scenario_structure_markdown": "",
        "selected_scenario_contract_markdown": "",
    }

    if not scenarios:
        base["reason_code"] = REASON_SCENARIOS_MISSING
        base["reason_message"] = "Latest Season Scenarios artifact is missing."
        return base
    if not selection:
        base["reason_code"] = REASON_SELECTION_MISSING
        base["reason_message"] = "Latest Selected Scenario artifact is missing."
        return base
    if not _selection_binds_to_scenarios(selection, scenarios):
        base["reason_code"] = REASON_SELECTION_STALE
        base["reason_message"] = "Selected Scenario references an older Season Scenarios version. Reselect required."
        return base

    resolved_selected_id = _resolve_selected_id(selection, explicit_selected)
    base["selected_scenario_id"] = resolved_selected_id
    if not resolved_selected_id:
        base["reason_code"] = REASON_SELECTED_SCENARIO_UNRESOLVED
        base["reason_message"] = "Selected Scenario could not be resolved in the latest Season Scenarios."
        return base
    if not _scenario_exists(scenarios, resolved_selected_id):
        base["reason_code"] = REASON_SELECTED_SCENARIO_UNRESOLVED
        base["reason_message"] = "Selected Scenario could not be resolved in the latest Season Scenarios."
        return base

    structure = build_selected_scenario_structure_context(
        season_scenarios_payload=scenarios,
        selection_payload=selection,
        selected_scenario_id=resolved_selected_id,
    )
    if not structure:
        base["reason_code"] = REASON_SELECTED_SCENARIO_STRUCTURE_MISSING
        base["reason_message"] = "Selected Scenario structure context could not be derived from the latest Season Scenarios."
        return base
    missing_structure_fields = _structure_missing_fields(structure)
    if missing_structure_fields:
        base["reason_code"] = REASON_SELECTED_SCENARIO_STRUCTURE_MISSING
        base["reason_message"] = (
            "Selected Scenario structure context is incomplete for season planning. "
            f"Missing fields: {', '.join(missing_structure_fields)}."
        )
        base["selected_scenario_structure_context"] = structure
        base["selected_scenario_structure_markdown"] = render_selected_scenario_structure_block(structure)
        return base

    contract = build_selected_scenario_contract_context(
        season_scenarios_payload=scenarios,
        selection_payload=selection,
        selected_scenario_id=resolved_selected_id,
    )
    if not contract:
        base["reason_code"] = REASON_SELECTED_SCENARIO_CONTRACT_INCOMPLETE
        base["reason_message"] = "Selected Scenario contract could not be derived from the latest Season Scenarios."
        base["selected_scenario_structure_context"] = structure
        base["selected_scenario_structure_markdown"] = render_selected_scenario_structure_block(structure)
        return base

    missing_fields = _contract_missing_fields(contract)
    if missing_fields:
        base["reason_code"] = REASON_SELECTED_SCENARIO_CONTRACT_INCOMPLETE
        base["reason_message"] = (
            "Selected Scenario is present but incomplete for season planning. "
            f"Missing fields: {', '.join(missing_fields)}."
        )
        base["selected_scenario_structure_context"] = structure
        base["selected_scenario_contract"] = contract
        base["selected_scenario_structure_markdown"] = render_selected_scenario_structure_block(structure)
        base["selected_scenario_contract_markdown"] = render_selected_scenario_contract_block(contract)
        return base

    base["ok"] = True
    base["reason_code"] = "ready"
    base["reason_message"] = "Selected Scenario is valid and bound to the latest Season Scenarios."
    base["selected_scenario_structure_context"] = structure
    base["selected_scenario_contract"] = contract
    base["selected_scenario_structure_markdown"] = render_selected_scenario_structure_block(structure)
    base["selected_scenario_contract_markdown"] = render_selected_scenario_contract_block(contract)
    return base
