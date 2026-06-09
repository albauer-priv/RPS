"""Deterministic planning-contract validators.

The functions in this module compare model-authored planning artefacts with
code-owned runtime contracts. They deliberately return structured issues
instead of raising so callers can decide whether to block, warn, or attach
review instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from rps.planning.deterministic_context import build_effective_week_constraints_block
from rps.planning.phase_authority import (
    format_role_week_load_bands,
    normalize_role_week_load_bands,
    role_week_band_by_week,
)
from rps.workspace.intensity_domains import normalize_intensity_domain_list
from rps.workspace.iso_helpers import IsoWeekRange, parse_iso_week, parse_iso_week_range
from rps.workspace.phase_intents import (
    normalize_phase_intent,
    normalize_phase_type,
    normalize_season_archetype,
    semantic_allowed_intensity_domains,
    semantic_allowed_load_modalities,
    semantic_forbidden_intensity_domains,
    validate_phase_semantics,
)

JsonMap = dict[str, Any]
Severity = Literal["blocker", "warning"]


@dataclass(frozen=True)
class PlanningContractIssue:
    """One deterministic planning-contract issue."""

    code: str
    message: str
    severity: Severity = "blocker"
    path: str | None = None

    def format(self) -> str:
        """Return a compact human/actionable issue string."""

        prefix = f"{self.path}: " if self.path else ""
        return f"{self.severity.upper()} {self.code}: {prefix}{self.message}"


def blocking_messages(issues: list[PlanningContractIssue]) -> list[str]:
    """Return formatted blocker messages from a contract issue list."""

    return [issue.format() for issue in issues if issue.severity == "blocker"]


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _shared_contract_fields(candidate: JsonMap, authority: JsonMap) -> list[str]:
    """Return shared keys between candidate and authority sorted for stable checks."""

    return sorted(set(candidate) & set(authority))


def _compare_contract_subset(
    *,
    candidate: JsonMap,
    authority: JsonMap,
    path: str,
    code: str,
    label: str,
) -> list[PlanningContractIssue]:
    """Return mismatch issues for a shared candidate/authority contract subset."""

    issues: list[PlanningContractIssue] = []
    if authority and not candidate:
        return [
            PlanningContractIssue(
                f"{code}_missing",
                f"{label} is missing.",
                path=path,
            )
        ]
    for field in _shared_contract_fields(candidate, authority):
        if candidate.get(field) != authority.get(field):
            issues.append(
                PlanningContractIssue(
                    code,
                    f"{label}.{field} is {candidate.get(field)!r}, expected {authority.get(field)!r}.",
                    path=f"{path}.{field}",
                )
            )
    return issues


def _week_key(value: object) -> str | None:
    week = parse_iso_week(value)
    if week is None:
        return None
    return f"{week.year:04d}-{week.week:02d}"


def _range_week_count(range_key: object) -> int | None:
    parsed = parse_iso_week_range(range_key)
    if parsed is None:
        return None
    return _range_week_count_parsed(parsed)


def _range_week_count_parsed(range_spec: IsoWeekRange) -> int:
    return (range_spec.end.year * 60 + range_spec.end.week) - (range_spec.start.year * 60 + range_spec.start.week) + 1


def _phase_data(document: JsonMap) -> list[JsonMap]:
    return [_as_map(item) for item in _as_list(_as_map(document.get("data")).get("phases"))]


def _normalize_modalities(values: object) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in _as_list(values):
        normalized = str(value or "").strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _format_role_week_bands(entries: object) -> list[str]:
    return format_role_week_load_bands(entries)


def _extract_km_values(text: object) -> list[int]:
    values: list[int] = []
    for match in re.finditer(r"(\d{2,4})(?:\s*[-/]\s*(\d{2,4}))?\s*km", str(text or ""), flags=re.IGNORECASE):
        values.append(int(match.group(1)))
        if match.group(2) is not None:
            values.append(int(match.group(2)))
    return values


def _has_positive_forbidden_domain_mention(text: object, domain: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    token = str(domain or "").strip().lower()
    if token not in normalized:
        return False
    negative_cues = (
        f"{token} remains excluded",
        f"{token} is excluded",
        f"{token} remains forbidden",
        f"{token} is forbidden",
        f"no {token}",
        f"without {token}",
        f"{token} suppressed",
        f"{token} remains suppressed",
        f"{token} excluded",
        f"{token} forbidden",
    )
    if any(cue in normalized for cue in negative_cues):
        return False
    positive_cues = (
        f"{token} appears",
        f"{token} support",
        f"{token} remains secondary",
        f"{token} kept secondary",
        f"controlled {token}",
        f"{token}-led",
        f"{token} maintenance",
    )
    return any(cue in normalized for cue in positive_cues)


def _candidate_or_document(mapping: JsonMap) -> JsonMap:
    candidate = mapping.get("candidate_document")
    return candidate if isinstance(candidate, dict) else mapping


def derive_expected_average_weekly_kj_range(*, season_plan_payload: JsonMap) -> JsonMap | None:
    """Derive the authoritative average weekly kJ range from role-week load bands."""

    document = _candidate_or_document(season_plan_payload)
    phases = _phase_data(document)
    total_weeks = 0
    total_min = 0.0
    total_max = 0.0
    for phase in phases:
        role_week_load_bands = normalize_role_week_load_bands(phase.get("role_week_load_bands"))
        if not role_week_load_bands:
            weekly_kj = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
            role_week_load_bands = normalize_role_week_load_bands(weekly_kj.get("notes"))
        if not role_week_load_bands:
            return None
        for entry in role_week_load_bands:
            band = _as_map(entry.get("band"))
            min_value = _as_float(band.get("min"))
            max_value = _as_float(band.get("max"))
            if min_value is None or max_value is None:
                return None
            total_weeks += 1
            total_min += min_value
            total_max += max_value
    if total_weeks <= 0:
        return None
    return {
        "min": int(round(total_min / total_weeks)),
        "max": int(round(total_max / total_weeks)),
    }


def validate_season_bundle_semantics(*, season_bundle_payload: JsonMap) -> list[PlanningContractIssue]:
    """Validate structured Season bundle semantics before review and writing."""

    issues: list[PlanningContractIssue] = []
    season_domains = normalize_intensity_domain_list(_as_map(season_bundle_payload).get("season_allowed_domains"))
    season_load_envelope = _as_map(season_bundle_payload.get("season_load_envelope"))
    envelope_range = _as_map(season_load_envelope.get("expected_average_weekly_kj_range"))
    if not season_load_envelope or _as_float(envelope_range.get("min")) is None or _as_float(envelope_range.get("max")) is None:
        issues.append(
            PlanningContractIssue(
                "season_bundle_load_envelope_missing",
                "Season bundle must include deterministic season_load_envelope.expected_average_weekly_kj_range.",
                path="season_load_envelope.expected_average_weekly_kj_range",
            )
        )
    notes = [str(item).strip() for item in _as_list(season_bundle_payload.get("season_semantic_notes")) if str(item).strip()]
    if not notes:
        issues.append(
            PlanningContractIssue(
                "season_bundle_semantic_notes_missing",
                "Season bundle must include season_semantic_notes for writer-safe framing.",
                path="season_semantic_notes",
            )
        )
    for idx, phase in enumerate(_as_list(season_bundle_payload.get("phase_blueprints"))):
        phase_map = _as_map(phase)
        path = f"phase_blueprints[{idx}]"
        errors = validate_phase_semantics(
            phase_type=phase_map.get("phase_type"),
            phase_intent=phase_map.get("phase_intent"),
            build_subtype=phase_map.get("build_subtype"),
        )
        for error in errors:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_phase_semantics_invalid",
                    error,
                    path=path,
                )
            )
        taxonomy_version = str(phase_map.get("phase_taxonomy_version") or "").strip()
        if not taxonomy_version:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_phase_taxonomy_version_missing",
                    "Season phase blueprints must include phase_taxonomy_version.",
                    path=f"{path}.phase_taxonomy_version",
                )
            )
        allowed_domains = normalize_intensity_domain_list(phase_map.get("allowed_domains"))
        semantic_max = semantic_allowed_intensity_domains(phase_map.get("phase_intent"))
        if allowed_domains and semantic_max:
            outside = sorted(set(allowed_domains) - set(semantic_max))
            if outside:
                issues.append(
                    PlanningContractIssue(
                        "season_bundle_phase_domains_outside_semantic_contract",
                        "Phase blueprint uses domains outside the code-owned semantic profile: " + ", ".join(outside) + ".",
                        path=f"{path}.allowed_domains",
                    )
                )
        if season_domains and allowed_domains:
            outside_season = sorted(set(allowed_domains) - (set(season_domains) | {"RECOVERY"}))
            if outside_season:
                issues.append(
                    PlanningContractIssue(
                        "season_bundle_phase_domains_outside_season_authority",
                        "Phase blueprint uses domains outside season authority: " + ", ".join(outside_season) + ".",
                        path=f"{path}.allowed_domains",
                    )
                )
        forbidden_domains = normalize_intensity_domain_list(phase_map.get("forbidden_domains"))
        allowed_modalities = _normalize_modalities(phase_map.get("allowed_load_modalities"))
        expected_modalities = _normalize_modalities(semantic_allowed_load_modalities(phase_map.get("phase_intent")))
        if allowed_modalities != expected_modalities:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_phase_modalities_mismatch",
                    f"Phase blueprint allowed_load_modalities {allowed_modalities!r} do not match the canonical semantic profile {expected_modalities!r}.",
                    path=f"{path}.allowed_load_modalities",
                )
            )
        semantic_forbidden = semantic_forbidden_intensity_domains(phase_map.get("phase_intent"))
        if semantic_forbidden:
            missing_forbidden = sorted(set(semantic_forbidden) - set(forbidden_domains))
            if missing_forbidden:
                issues.append(
                    PlanningContractIssue(
                        "season_bundle_phase_forbidden_domains_missing",
                        "Phase blueprint is missing forbidden domains required by the semantic profile: " + ", ".join(missing_forbidden) + ".",
                        path=f"{path}.forbidden_domains",
                    )
                )
        semantic_contract = _as_map(phase_map.get("semantic_contract"))
        if not semantic_contract:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_phase_semantic_contract_missing",
                    "Season phase blueprints must include semantic_contract.",
                    path=f"{path}.semantic_contract",
                )
            )
            continue
        for field in ("methodology_family", "threshold_role", "event_load_policy", "taper_policy"):
            if not str(semantic_contract.get(field) or "").strip():
                issues.append(
                    PlanningContractIssue(
                        "season_bundle_phase_semantic_contract_incomplete",
                        f"semantic_contract.{field} must be populated.",
                        path=f"{path}.semantic_contract.{field}",
                    )
                )
        if not [str(item).strip() for item in _as_list(semantic_contract.get("writer_semantic_notes")) if str(item).strip()]:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_phase_writer_notes_missing",
                    "semantic_contract.writer_semantic_notes must include at least one note.",
                    path=f"{path}.semantic_contract.writer_semantic_notes",
                )
            )
    return issues


def validate_season_bundle_review_readiness(*, season_bundle_payload: JsonMap) -> list[PlanningContractIssue]:
    """Validate that a normalized season bundle is ready for review and writing."""

    issues: list[PlanningContractIssue] = []
    top_level_blockers = [str(item).strip() for item in _as_list(season_bundle_payload.get("blocking_issues")) if str(item).strip()]
    if top_level_blockers:
        issues.append(
            PlanningContractIssue(
                "season_bundle_blocking_issues_present",
                "Season finalize bundle still contains blocking_issues and is not review-ready.",
                path="blocking_issues",
            )
        )
    for idx, audit in enumerate(_as_list(season_bundle_payload.get("constraints"))):
        blocking = [str(item).strip() for item in _as_list(_as_map(audit).get("blocking_issues")) if str(item).strip()]
        if blocking:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_constraint_blockers_present",
                    "Constraint audit still contains blocking issues: " + "; ".join(blocking[:3]),
                    path=f"constraints[{idx}].blocking_issues",
                )
            )
    for idx, audit in enumerate(_as_list(season_bundle_payload.get("load_governance"))):
        blocking = [str(item).strip() for item in _as_list(_as_map(audit).get("blocking_issues")) if str(item).strip()]
        if blocking:
            issues.append(
                PlanningContractIssue(
                    "season_bundle_governance_blockers_present",
                    "Load-governance audit still contains blocking issues: " + "; ".join(blocking[:3]),
                    path=f"load_governance[{idx}].blocking_issues",
                )
            )
    phantom_markers = (
        "no target-week event",
        "no logistics exception",
        "no event-driven load exception",
        "no target week event",
    )
    for idx, blueprint in enumerate(_as_list(season_bundle_payload.get("phase_blueprints"))):
        event_constraints = [str(item).strip() for item in _as_list(_as_map(blueprint).get("event_constraints")) if str(item).strip()]
        if any(any(marker in item.lower() for marker in phantom_markers) for item in event_constraints):
            issues.append(
                PlanningContractIssue(
                    "season_bundle_phantom_event_constraint",
                    "Season finalize bundle still carries synthetic no-event semantics in phase blueprint event_constraints.",
                    path=f"phase_blueprints[{idx}].event_constraints",
                )
            )
    return issues


def validate_phase_bundle_review_readiness(*, phase_bundle_payload: JsonMap) -> list[PlanningContractIssue]:
    """Validate that a normalized phase bundle is ready for review and writing."""

    issues: list[PlanningContractIssue] = []
    top_level_blockers = [str(item).strip() for item in _as_list(phase_bundle_payload.get("blocking_issues")) if str(item).strip()]
    if top_level_blockers:
        issues.append(
            PlanningContractIssue(
                "phase_bundle_blocking_issues_present",
                "Phase finalize bundle still contains blocking_issues and is not review-ready.",
                path="blocking_issues",
            )
        )
    for field in ("constraint_audit", "load_governance_audit"):
        audit = _as_map(phase_bundle_payload.get(field))
        blocking = [str(item).strip() for item in _as_list(audit.get("blocking_issues")) if str(item).strip()]
        if blocking:
            issues.append(
                PlanningContractIssue(
                    "phase_bundle_audit_blockers_present",
                    f"{field} still contains blocking issues: " + "; ".join(blocking[:3]),
                    path=f"{field}.blocking_issues",
                )
            )
    phase_intent = str(phase_bundle_payload.get("phase_intent") or "").strip()
    for field in ("guardrails", "structure", "preview"):
        nested = _as_map(phase_bundle_payload.get(field))
        nested_intent = str(nested.get("phase_intent") or "").strip()
        if phase_intent and nested_intent and nested_intent != phase_intent:
            issues.append(
                PlanningContractIssue(
                    "phase_bundle_nested_intent_mismatch",
                    f"{field}.phase_intent {nested_intent!r} does not match bundle phase_intent {phase_intent!r}.",
                    path=f"{field}.phase_intent",
                )
            )
    if not [str(item).strip() for item in _as_list(_as_map(phase_bundle_payload.get("guardrails")).get("phase_summary")) if str(item).strip()]:
        issues.append(
            PlanningContractIssue(
                "phase_bundle_guardrails_summary_missing",
                "Phase finalize bundle must provide guardrails.phase_summary before review.",
                path="guardrails.phase_summary",
            )
        )
    if not [str(item).strip() for item in _as_list(_as_map(phase_bundle_payload.get("preview")).get("phase_intent_summary")) if str(item).strip()]:
        issues.append(
            PlanningContractIssue(
                "phase_bundle_preview_summary_missing",
                "Phase finalize bundle must provide preview.phase_intent_summary before review.",
                path="preview.phase_intent_summary",
            )
        )
    return issues


def validate_week_bundle_review_readiness(*, week_bundle_payload: JsonMap) -> list[PlanningContractIssue]:
    """Validate that a week bundle is ready for review and writing."""

    issues: list[PlanningContractIssue] = []
    top_level_blockers = [str(item).strip() for item in _as_list(week_bundle_payload.get("blocking_issues")) if str(item).strip()]
    if top_level_blockers:
        issues.append(
            PlanningContractIssue(
                "week_bundle_blocking_issues_present",
                "Week finalize bundle still contains blocking_issues and is not review-ready.",
                path="blocking_issues",
            )
        )
    for idx, day in enumerate(_as_list(week_bundle_payload.get("day_blueprints"))):
        day_map = _as_map(day)
        if day_map.get("fixed_rest_day") is True:
            planned_duration = _as_int(day_map.get("planned_duration_minutes")) or 0
            planned_kj = _as_int(day_map.get("planned_kj")) or 0
            workout_id = str(day_map.get("workout_id") or "").strip()
            if planned_duration > 0 or planned_kj > 0 or workout_id:
                issues.append(
                    PlanningContractIssue(
                        "week_bundle_fixed_rest_day_loaded",
                        "Fixed rest day still carries duration, kJ, or workout assignment.",
                        path=f"day_blueprints[{idx}]",
                    )
                )
    for idx, workout in enumerate(_as_list(week_bundle_payload.get("workout_blueprints"))):
        workout_map = _as_map(workout)
        legality = str(workout_map.get("phase_legality_status") or "").strip().lower()
        exportability = str(workout_map.get("exportability_status") or "").strip().lower()
        if legality == "illegal":
            issues.append(
                PlanningContractIssue(
                    "week_bundle_illegal_workout_blueprint",
                    "Week finalize bundle still contains a phase-illegal workout blueprint.",
                    path=f"workout_blueprints[{idx}].phase_legality_status",
                )
            )
        if exportability == "invalid":
            issues.append(
                PlanningContractIssue(
                    "week_bundle_invalid_exportability_status",
                    "Week finalize bundle still contains an export-invalid workout blueprint.",
                    path=f"workout_blueprints[{idx}].exportability_status",
                )
            )
    return issues


def validate_snapshot_freshness(
    *,
    snapshot_payload: JsonMap,
    expected_source_versions: JsonMap,
    authoritative: bool = True,
    snapshot_label: str = "snapshot",
) -> list[PlanningContractIssue]:
    """Validate snapshot source versions against currently loaded authority inputs."""

    issues: list[PlanningContractIssue] = []
    observed = _as_map(_as_map(snapshot_payload.get("data")).get("source_versions"))
    severity: Severity = "blocker" if authoritative else "warning"
    if not observed and expected_source_versions:
        return [
            PlanningContractIssue(
                "snapshot_source_versions_missing",
                f"{snapshot_label} has no source_versions.",
                severity=severity,
                path="data.source_versions",
            )
        ]
    for key, expected in expected_source_versions.items():
        if expected in (None, ""):
            continue
        observed_value = observed.get(str(key))
        if observed_value != expected:
            issues.append(
                PlanningContractIssue(
                    "snapshot_stale_source_version",
                    f"{snapshot_label} source {key!s} is {observed_value!r}, expected {expected!r}.",
                    severity=severity,
                    path=f"data.source_versions.{key}",
                )
            )
    return issues


def validate_season_plan_against_phase_slots(
    *,
    season_plan_payload: JsonMap,
    phase_slot_context: JsonMap,
) -> list[PlanningContractIssue]:
    """Validate final Season Plan phases against deterministic scenario slots."""

    document = _candidate_or_document(season_plan_payload)
    phases = _phase_data(document)
    slots = [_as_map(item) for item in _as_list(phase_slot_context.get("phase_slots"))]
    issues: list[PlanningContractIssue] = []
    if not slots:
        return [
            PlanningContractIssue(
                "phase_slot_context_missing",
                "Deterministic phase slot context is missing; Season Plan cannot be checked.",
            )
        ]
    if len(phases) != len(slots):
        issues.append(
            PlanningContractIssue(
                "season_phase_count_mismatch",
                f"Season Plan has {len(phases)} phases, expected {len(slots)} from selected scenario.",
                path="data.phases",
            )
        )
        return issues
    for idx, (phase, slot) in enumerate(zip(phases, slots, strict=True), start=1):
        path = f"data.phases[{idx - 1}]"
        for field in ("phase_id", "iso_week_range"):
            if str(phase.get(field) or "") != str(slot.get(field) or ""):
                issues.append(
                    PlanningContractIssue(
                        "season_phase_slot_mismatch",
                        f"{field} is {phase.get(field)!r}, expected {slot.get(field)!r}.",
                        path=f"{path}.{field}",
                    )
                )
        expected_len = _as_float(slot.get("length_weeks"))
        observed_len = _range_week_count(phase.get("iso_week_range"))
        if expected_len is not None and observed_len is not None and int(expected_len) != observed_len:
            issues.append(
                PlanningContractIssue(
                    "season_phase_length_mismatch",
                    f"Phase length is {observed_len} weeks, expected {int(expected_len)}.",
                    path=f"{path}.iso_week_range",
                )
            )
        observed_intent = normalize_phase_intent(phase.get("phase_intent"))
        expected_intent = normalize_phase_intent(slot.get("phase_intent"))
        if expected_intent and observed_intent != expected_intent:
            issues.append(
                PlanningContractIssue(
                    "season_phase_intent_mismatch",
                    f"phase_intent is {phase.get('phase_intent')!r}, expected {expected_intent!r}.",
                    path=f"{path}.phase_intent",
                )
            )
    if phase_slot_context.get("coverage_matches_horizon") is False:
        issues.append(
            PlanningContractIssue(
                "phase_slot_coverage_invalid",
                "Selected scenario phase slots do not cover the planning horizon exactly.",
                path="phase_slot_context.coverage_matches_horizon",
            )
        )
    return issues


def validate_season_plan_against_phase_load_context(
    *,
    season_plan_payload: JsonMap,
    season_phase_load_context: JsonMap,
    include_narrative_semantics: bool = True,
) -> list[PlanningContractIssue]:
    """Validate Season Plan strategic corridors against deterministic phase load context."""

    document = _candidate_or_document(season_plan_payload)
    phases = _phase_data(document)
    selected_scenario_contract = _as_map(_as_map(document.get("data")).get("selected_scenario_contract"))
    authority_selected_contract = _as_map(season_phase_load_context.get("selected_scenario_contract"))
    context_by_phase = {
        str(_as_map(item).get("phase_id") or ""): _as_map(item)
        for item in _as_list(season_phase_load_context.get("phases"))
    }
    season_allowed_domains = normalize_intensity_domain_list(
        season_phase_load_context.get("season_allowed_intensity_domains")
    )
    issues: list[PlanningContractIssue] = []
    if not context_by_phase:
        return [
            PlanningContractIssue(
                "season_phase_load_context_missing",
                "Deterministic season phase load context is missing; Season Plan cannot be checked.",
            )
        ]
    if authority_selected_contract:
        issues.extend(
            _compare_contract_subset(
                candidate=selected_scenario_contract,
                authority=authority_selected_contract,
                path="data.selected_scenario_contract",
                code="season_selected_scenario_contract_mismatch",
                label="selected_scenario_contract",
            )
        )
    body_metadata = _as_map(_as_map(document.get("data")).get("body_metadata"))
    data = _as_map(document.get("data"))
    if not str(body_metadata.get("phase_taxonomy_version") or "").strip():
        issues.append(
            PlanningContractIssue(
                "season_phase_taxonomy_version_missing",
                "Season Plan body_metadata.phase_taxonomy_version must be populated.",
                path="data.body_metadata.phase_taxonomy_version",
            )
        )
    build_max_values: list[float] = []
    peak_max_values: list[tuple[str, float]] = []
    phase_allowed_domain_sets: list[tuple[str, list[str]]] = []
    expected_events: set[tuple[str, str]] = set()
    observed_events: set[tuple[str, str]] = set()
    a_events: list[JsonMap] = []
    season_archetype = normalize_season_archetype(season_phase_load_context.get("season_archetype"))
    for idx, phase in enumerate(phases):
        phase_id = str(phase.get("phase_id") or "")
        ctx = context_by_phase.get(phase_id)
        path = f"data.phases[{idx}]"
        if not ctx:
            issues.append(
                PlanningContractIssue(
                    "season_phase_load_context_phase_missing",
                    f"No deterministic phase load context for {phase_id or 'unknown phase'}.",
                    path=path,
                )
            )
            continue
        planned = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
        planned_min = _as_float(planned.get("min"))
        planned_max = _as_float(planned.get("max"))
        rec = _as_map(ctx.get("recommended_phase_corridor"))
        rec_min = _as_float(rec.get("min"))
        rec_max = _as_float(rec.get("max"))
        if None not in {planned_min, planned_max, rec_min, rec_max}:
            assert planned_min is not None and planned_max is not None
            assert rec_min is not None and rec_max is not None
            if planned_min < rec_min or planned_max > rec_max:
                issues.append(
                    PlanningContractIssue(
                        "season_phase_corridor_outside_contract",
                        f"Corridor {planned_min:g}-{planned_max:g} outside deterministic {rec_min:g}-{rec_max:g}.",
                        path=f"{path}.weekly_load_corridor.weekly_kj",
                    )
                )
        phase_type = normalize_phase_type(phase.get("phase_type") or phase.get("cycle") or ctx.get("phase_type") or ctx.get("phase_cycle") or "")
        observed_intent = normalize_phase_intent(phase.get("phase_intent"))
        expected_intent = normalize_phase_intent(ctx.get("phase_intent"))
        semantic_errors = validate_phase_semantics(
            phase_type=phase.get("phase_type") or phase.get("cycle") or ctx.get("phase_type") or ctx.get("phase_cycle"),
            phase_intent=phase.get("phase_intent") or ctx.get("phase_intent"),
            build_subtype=phase.get("build_subtype"),
        )
        for error in semantic_errors:
            issues.append(
                PlanningContractIssue(
                    "season_phase_semantics_invalid",
                    error,
                    path=path,
                )
            )
        if expected_intent and observed_intent != expected_intent:
            issues.append(
                PlanningContractIssue(
                    "season_phase_intent_outside_contract",
                    f"phase_intent {observed_intent!r} does not match deterministic intent {expected_intent!r}.",
                    path=f"{path}.phase_intent",
                )
            )
        phase_semantics = _as_map(phase.get("allowed_forbidden_semantics"))
        allowed_domains = normalize_intensity_domain_list(phase_semantics.get("allowed_intensity_domains"))
        forbidden_domains = normalize_intensity_domain_list(phase_semantics.get("forbidden_intensity_domains"))
        allowed_modalities = _normalize_modalities(phase_semantics.get("allowed_load_modalities"))
        expected_modalities = _normalize_modalities(semantic_allowed_load_modalities(observed_intent))
        semantic_max = semantic_allowed_intensity_domains(observed_intent)
        if semantic_max and allowed_domains:
            outside_semantic = sorted(set(allowed_domains) - set(semantic_max))
            if outside_semantic:
                issues.append(
                    PlanningContractIssue(
                        "season_phase_domains_outside_semantic_contract",
                        "Phase uses intensity domains outside the semantic contract for its intent: "
                        + ", ".join(outside_semantic)
                        + ".",
                        path=f"{path}.allowed_forbidden_semantics.allowed_intensity_domains",
                    )
                )
        semantic_forbidden = semantic_forbidden_intensity_domains(observed_intent)
        if semantic_forbidden:
            missing_forbidden = sorted(set(semantic_forbidden) - set(forbidden_domains))
            if missing_forbidden:
                issues.append(
                    PlanningContractIssue(
                        "season_phase_forbidden_domains_missing",
                        "Phase is missing forbidden intensity domains required by its semantic contract: "
                        + ", ".join(missing_forbidden)
                        + ".",
                        path=f"{path}.allowed_forbidden_semantics.forbidden_intensity_domains",
                    )
                )
        if expected_modalities and allowed_modalities != expected_modalities:
            issues.append(
                PlanningContractIssue(
                    "season_phase_modalities_mismatch",
                    f"allowed_load_modalities {allowed_modalities!r} do not match the canonical semantic profile {expected_modalities!r}.",
                    path=f"{path}.allowed_forbidden_semantics.allowed_load_modalities",
                )
            )
        if allowed_domains:
            phase_allowed_domain_sets.append((phase_id or path, allowed_domains))
            outside = sorted(set(allowed_domains) - (set(season_allowed_domains) | {"RECOVERY"})) if season_allowed_domains else []
            if outside:
                issues.append(
                    PlanningContractIssue(
                        "season_phase_intensity_domain_outside_authority",
                        "Phase uses intensity domains outside selected season authority: " + ", ".join(outside) + ".",
                        path=f"{path}.allowed_forbidden_semantics.allowed_intensity_domains",
                    )
                )
        if observed_intent in {"shortened_re_entry", "preparation_re_entry", "transition_recovery"}:
            if "VO2MAX" in allowed_domains:
                issues.append(
                    PlanningContractIssue(
                        "season_phase_intent_vo2max_conflict",
                        "Recovery/re-entry/consolidation intents must not allow VO2MAX.",
                        path=f"{path}.allowed_forbidden_semantics.allowed_intensity_domains",
                    )
                )
        if observed_intent == "taper_freshening" and "VO2MAX" in allowed_domains:
            issues.append(
                PlanningContractIssue(
                    "season_peak_taper_vo2max_conflict",
                    "Taper intent must not expose VO2MAX as a general allowed domain.",
                    path=f"{path}.allowed_forbidden_semantics.allowed_intensity_domains",
                )
            )
        if observed_intent == "specificity_build" and phase_type not in {"BUILD", "PEAK"}:
            issues.append(
                PlanningContractIssue(
                    "season_specificity_build_cycle_conflict",
                    "specificity_build must live in Build or late Peak-adjacent structure.",
                    path=f"{path}.phase_type",
                )
            )
        overview = _as_map(phase.get("overview"))
        structural_emphasis = _as_map(phase.get("structural_emphasis"))
        justification = {}
        for entry in _as_list(_as_map(data.get("justification")).get("phase_justifications")):
            entry_map = _as_map(entry)
            if str(entry_map.get("phase_id") or "") == phase_id:
                justification = entry_map
                break
        if include_narrative_semantics:
            narrative_fields = [
                phase.get("narrative"),
                overview.get("metabolic_focus"),
                structural_emphasis.get("typical_focus"),
                justification.get("intensity_distribution"),
                *[str(item) for item in _as_list(overview.get("expected_adaptations"))],
                *[str(item) for item in _as_list(overview.get("non_negotiables"))],
            ]
            for forbidden_domain in forbidden_domains:
                if any(_has_positive_forbidden_domain_mention(text, forbidden_domain) for text in narrative_fields):
                    issues.append(
                        PlanningContractIssue(
                            "season_phase_forbidden_domain_positive_narrative",
                            f"{forbidden_domain} is forbidden for this phase but is described positively in season-plan narrative text.",
                            path=path,
                        )
                    )
                    break
        if observed_intent and "VO2MAX" in forbidden_domains and observed_intent == "vo2_build" and season_archetype == "ceiling_first_durability":
            issues.append(
                PlanningContractIssue(
                    "season_ceiling_support_vo2max_forbidden",
                    "vo2_build under ceiling_first_durability should not forbid VO2MAX outright when early VO2 is permitted.",
                    severity="warning",
                    path=f"{path}.allowed_forbidden_semantics.forbidden_intensity_domains",
                )
            )
        if phase_type == "BUILD" and planned_max is not None:
            build_max_values.append(planned_max)
        event_trace = _as_map(ctx.get("event_taper_trace"))
        expected_role_week_bands = _format_role_week_bands(ctx.get("role_week_load_bands"))
        expected_role_week_sentence_parts = [item for item in expected_role_week_bands if item]
        observed_structured_role_week_bands = normalize_role_week_load_bands(phase.get("role_week_load_bands"))
        expected_structured_role_week_bands = normalize_role_week_load_bands(ctx.get("role_week_load_bands"))
        if expected_structured_role_week_bands and observed_structured_role_week_bands != expected_structured_role_week_bands:
            issues.append(
                PlanningContractIssue(
                    "season_phase_role_week_bands_mismatch",
                    "phase.role_week_load_bands must match deterministic persisted phase week-band authority exactly.",
                    path=f"{path}.role_week_load_bands",
                )
            )
        weekly_kj_notes = str(planned.get("notes") or "")
        if expected_role_week_sentence_parts and not all(item in weekly_kj_notes for item in expected_role_week_sentence_parts):
            issues.append(
                PlanningContractIssue(
                    "season_phase_role_week_guardrails_missing",
                    "weekly_load_corridor.weekly_kj.notes must materialize deterministic role-week guardrails for auditability.",
                    path=f"{path}.weekly_load_corridor.weekly_kj.notes",
                )
            )
        expected_phase_events: set[tuple[str, str]] = set()
        for event in _as_list(event_trace.get("events")):
            event_map = _as_map(event)
            event_date = str(event_map.get("date") or "").strip()
            event_type = str(event_map.get("type") or "").strip().upper()
            if event_date and event_type in {"A", "B", "C"}:
                expected_phase_events.add((event_date, event_type))
                expected_events.add((event_date, event_type))
                if event_type == "A":
                    a_events.append(event_map)
        observed_phase_events = [_as_map(item) for item in _as_list(phase.get("events_constraints"))]
        for event in observed_phase_events:
            event_date = str(event.get("window") or "").strip()
            event_type = str(event.get("type") or "").strip().upper()
            if event_date and event_type in {"A", "B", "C"}:
                observed_events.add((event_date, event_type))
        unexpected_events = sorted(
            (str(event.get("window") or "").strip(), str(event.get("type") or "").strip().upper())
            for event in observed_phase_events
            if (
                str(event.get("window") or "").strip(),
                str(event.get("type") or "").strip().upper(),
            )
            not in expected_phase_events
        )
        if unexpected_events:
            issues.append(
                PlanningContractIssue(
                    "season_phase_unexpected_event_constraints",
                    "events_constraints contains entries that do not match deterministic planning events for this season phase.",
                    path=f"{path}.events_constraints",
                )
            )
        if (phase_type in {"PEAK", "TAPER"} or event_trace.get("has_a_event")) and planned_max is not None:
            peak_max_values.append((phase_id, planned_max))
        if event_trace.get("has_b_event") and phase_type == "PEAK" and not event_trace.get("has_a_event"):
            issues.append(
                PlanningContractIssue(
                    "b_event_full_peak_not_allowed",
                    "B event phase must remain rehearsal/minor adjustment, not a standalone Peak.",
                    path=f"{path}.phase_type",
                )
            )
    if build_max_values and peak_max_values:
        build_ceiling = max(build_max_values)
        for phase_id, peak_max in peak_max_values:
            if peak_max >= build_ceiling:
                issues.append(
                    PlanningContractIssue(
                        "a_event_peak_taper_not_reduced",
                        f"Peak/A-event phase {phase_id} max {peak_max:g} is not reduced below Build max {build_ceiling:g}.",
                    )
                )
    if season_allowed_domains:
        scenario_quality_domains = {domain for domain in season_allowed_domains if domain not in {"ENDURANCE"}}
        if not phase_allowed_domain_sets:
            issues.append(
                PlanningContractIssue(
                    "season_phase_intensity_domains_missing",
                    "Season phases are missing allowed_intensity_domains despite selected season authority.",
                    path="data.phases",
                )
            )
        if scenario_quality_domains and phase_allowed_domain_sets:
            quality_present = any(
                scenario_quality_domains.intersection(set(domains))
                for _phase_id, domains in phase_allowed_domain_sets
            )
            collapsed_to_endurance_only = all(domains == ["ENDURANCE"] for _phase_id, domains in phase_allowed_domain_sets)
            if collapsed_to_endurance_only or not quality_present:
                issues.append(
                    PlanningContractIssue(
                        "season_intensity_domains_collapsed_to_endurance_only",
                        "Selected season authority permits additional intensity domains, but the Season Plan never carries them into any phase.",
                        path="data.phases",
                    )
                )
    missing_events = sorted(expected_events - observed_events)
    if missing_events:
        issues.append(
            PlanningContractIssue(
                "season_event_constraints_missing",
                "Season Plan is missing planning events in phase events_constraints: "
                + ", ".join(f"{date} {event_type}" for date, event_type in missing_events)
                + ".",
                path="data.phases[].events_constraints",
            )
        )
    objective = _as_map(data.get("season_intent_principles")).get("season_objective")
    objective_km = _extract_km_values(objective)
    if objective_km and a_events:
        highest_a_event = max(
            a_events,
            key=lambda item: (
                str(item.get("date") or ""),
                str(item.get("week") or ""),
                str(item.get("name") or ""),
            ),
        )
        event_label = " ".join(
            str(part).strip()
            for part in (highest_a_event.get("name"), highest_a_event.get("date"))
            if str(part or "").strip()
        ).strip()
        event_km = _extract_km_values(event_label)
        if event_km and not any(abs(event_distance - objective_distance) <= 25 for event_distance in event_km for objective_distance in objective_km):
            issues.append(
                PlanningContractIssue(
                    "season_objective_event_mismatch_warning",
                    "Primary season objective distance does not align with the highest in-horizon A-event anchor; surface this as a user-visible warning and keep finalization non-blocking.",
                    severity="warning",
                    path="data.season_intent_principles.season_objective",
                )
            )
    expected_envelope = derive_expected_average_weekly_kj_range(season_plan_payload=season_plan_payload)
    actual_envelope = _as_map(_as_map(document.get("data")).get("season_load_envelope")).get("expected_average_weekly_kj_range")
    actual_envelope_map = _as_map(actual_envelope)
    actual_min = _as_float(actual_envelope_map.get("min"))
    actual_max = _as_float(actual_envelope_map.get("max"))
    if expected_envelope and None not in {actual_min, actual_max}:
        assert actual_min is not None and actual_max is not None
        if round(actual_min) != expected_envelope["min"] or round(actual_max) != expected_envelope["max"]:
            issues.append(
                PlanningContractIssue(
                    "season_load_envelope_mismatch",
                    (
                        f"expected_average_weekly_kj_range is {actual_min:g}-{actual_max:g}, "
                        f"expected authoritative role-week-band-derived {expected_envelope['min']}-{expected_envelope['max']}."
                    ),
                    path="data.season_load_envelope.expected_average_weekly_kj_range",
                )
            )
    return issues


def validate_phase_s5_bands_against_context(
    *,
    phase_payload: JsonMap,
    phase_execution_context: JsonMap,
) -> list[PlanningContractIssue]:
    """Validate phase weekly load bands against exact deterministic phase week-band authority."""

    expected = role_week_band_by_week(phase_execution_context.get("phase_role_week_load_bands"))
    source_path = "phase_execution_context.phase_role_week_load_bands"
    if not expected:
        for entry in _as_list(phase_execution_context.get("phase_s5_bands")):
            entry_map = _as_map(entry)
            week = _week_key(entry_map.get("week"))
            band = _as_map(entry_map.get("band"))
            if week and band:
                expected[week] = band
        source_path = "phase_execution_context.phase_s5_bands"
    if not expected:
        return [
            PlanningContractIssue(
                "phase_s5_context_missing",
                "Deterministic phase weekly band authority is missing.",
                path=source_path,
            )
        ]
    issues: list[PlanningContractIssue] = []
    data = _as_map(phase_payload.get("data"))
    load_guardrails = _as_map(data.get("load_guardrails") or data.get("load_ranges"))
    observed_entries = _as_list(load_guardrails.get("weekly_kj_bands"))
    if not observed_entries:
        return [
            PlanningContractIssue(
                "phase_weekly_bands_missing",
                "Phase artifact does not include weekly_kj_bands.",
                path="data.load_guardrails.weekly_kj_bands",
            )
        ]
    for entry in observed_entries:
        entry_map = _as_map(entry)
        week = _week_key(entry_map.get("week"))
        band = _as_map(entry_map.get("band"))
        if not week or not band:
            continue
        expected_band = expected.get(week)
        if not expected_band:
            issues.append(
                PlanningContractIssue(
                    "phase_week_outside_context",
                    f"Week {week} is not part of deterministic phase S5 context.",
                    path="data.load_guardrails.weekly_kj_bands",
                )
            )
            continue
        observed_min = _as_float(band.get("min"))
        observed_max = _as_float(band.get("max"))
        expected_min = _as_float(expected_band.get("min"))
        expected_max = _as_float(expected_band.get("max"))
        if None not in {observed_min, observed_max, expected_min, expected_max}:
            assert observed_min is not None and observed_max is not None
            assert expected_min is not None and expected_max is not None
            if round(observed_min) != round(expected_min) or round(observed_max) != round(expected_max):
                issues.append(
                    PlanningContractIssue(
                        "phase_s5_band_mismatch",
                        f"{week} band {observed_min:g}-{observed_max:g} does not match deterministic {expected_min:g}-{expected_max:g}.",
                        path="data.load_guardrails.weekly_kj_bands",
                    )
                )
    return issues


def validate_phase_against_execution_context(
    *,
    phase_payload: JsonMap,
    phase_execution_context: JsonMap,
) -> list[PlanningContractIssue]:
    """Validate phase structure roles and weeks against phase execution context."""

    expected_roles = {
        str(key): str(value)
        for key, value in _as_map(phase_execution_context.get("week_role_by_iso_week")).items()
    }
    issues: list[PlanningContractIssue] = []
    data = _as_map(phase_payload.get("data"))
    issues.extend(
        _compare_contract_subset(
            candidate=_as_map(data.get("inherited_scenario_contract")),
            authority=_as_map(phase_execution_context.get("inherited_scenario_contract")),
            path="data.inherited_scenario_contract",
            code="phase_inherited_scenario_contract_mismatch",
            label="inherited_scenario_contract",
        )
    )
    expected_allowed_domains = normalize_intensity_domain_list(
        phase_execution_context.get("phase_allowed_intensity_domains")
    )
    expected_forbidden_domains = normalize_intensity_domain_list(
        phase_execution_context.get("phase_forbidden_intensity_domains")
    )
    expected_modalities = _normalize_modalities(
        phase_execution_context.get("phase_allowed_load_modalities")
    )
    if expected_allowed_domains or expected_forbidden_domains or expected_modalities:
        observed_semantics = _as_map(data.get("allowed_forbidden_semantics"))
        if observed_semantics:
            observed_allowed_domains = normalize_intensity_domain_list(
                observed_semantics.get("allowed_intensity_domains")
            )
            observed_forbidden_domains = normalize_intensity_domain_list(
                observed_semantics.get("forbidden_intensity_domains")
            )
            observed_modalities = _normalize_modalities(
                observed_semantics.get("allowed_load_modalities")
            )
            if expected_allowed_domains and observed_allowed_domains != expected_allowed_domains:
                issues.append(
                    PlanningContractIssue(
                        "phase_allowed_domains_mismatch",
                        "Phase allowed_intensity_domains must match exact persisted phase legality.",
                        path="data.allowed_forbidden_semantics.allowed_intensity_domains",
                    )
                )
            if expected_forbidden_domains and observed_forbidden_domains != expected_forbidden_domains:
                issues.append(
                    PlanningContractIssue(
                        "phase_forbidden_domains_mismatch",
                        "Phase forbidden_intensity_domains must match exact persisted phase legality.",
                        path="data.allowed_forbidden_semantics.forbidden_intensity_domains",
                    )
                )
            if expected_modalities and observed_modalities != expected_modalities:
                issues.append(
                    PlanningContractIssue(
                        "phase_allowed_modalities_mismatch",
                        "Phase allowed_load_modalities must match exact persisted phase legality.",
                        path="data.allowed_forbidden_semantics.allowed_load_modalities",
                    )
                )
        observed_structural = _as_map(data.get("structural_phase_elements"))
        if observed_structural:
            observed_structural_domains = normalize_intensity_domain_list(
                observed_structural.get("allowed_intensity_domains")
            )
            observed_structural_modalities = _normalize_modalities(
                observed_structural.get("allowed_load_modalities")
            )
            if expected_allowed_domains and observed_structural_domains != expected_allowed_domains:
                issues.append(
                    PlanningContractIssue(
                        "phase_structural_allowed_domains_mismatch",
                        "Phase structure allowed_intensity_domains must match exact persisted phase legality.",
                        path="data.structural_phase_elements.allowed_intensity_domains",
                    )
                )
            if expected_modalities and observed_structural_modalities != expected_modalities:
                issues.append(
                    PlanningContractIssue(
                        "phase_structural_allowed_modalities_mismatch",
                        "Phase structure allowed_load_modalities must match exact persisted phase legality.",
                        path="data.structural_phase_elements.allowed_load_modalities",
                    )
                )
    expected_primary_objective = str(phase_execution_context.get("phase_primary_objective") or "").strip()
    if expected_primary_objective:
        observed_primary_objective = ""
        if isinstance(data.get("phase_summary"), dict):
            observed_primary_objective = str(_as_map(data.get("phase_summary")).get("primary_objective") or "").strip()
        if not observed_primary_objective and isinstance(data.get("upstream_intent"), dict):
            observed_primary_objective = str(_as_map(data.get("upstream_intent")).get("primary_objective") or "").strip()
        if not observed_primary_objective and isinstance(data.get("phase_intent_summary"), dict):
            observed_primary_objective = str(_as_map(data.get("phase_intent_summary")).get("primary_objective") or "").strip()
        if observed_primary_objective and observed_primary_objective != expected_primary_objective:
            issues.append(
                PlanningContractIssue(
                    "phase_primary_objective_mismatch",
                    "Phase primary objective must match the exact persisted Season phase objective.",
                    path="data.phase_primary_objective",
                )
            )
    if not expected_roles:
        issues.append(
            PlanningContractIssue(
                "phase_week_role_context_missing",
                "Deterministic week_role_by_iso_week is missing.",
                path="phase_execution_context.week_role_by_iso_week",
            )
        )
        return issues
    skeleton = _as_map(data.get("week_skeleton_logic"))
    roles_map = _as_map(skeleton.get("week_roles"))
    observed_entries = [_as_map(item) for item in _as_list(roles_map.get("week_roles"))]
    observed_roles: dict[str, str] = {}
    for entry in observed_entries:
        week = _week_key(entry.get("week"))
        role = str(entry.get("role") or entry.get("week_role") or "")
        if week and role:
            observed_roles[week] = role
    if observed_roles:
        for week, expected_role in expected_roles.items():
            observed_role = observed_roles.get(week)
            if observed_role != expected_role:
                issues.append(
                    PlanningContractIssue(
                        "phase_week_role_mismatch",
                        f"{week} role {observed_role!r}, expected {expected_role!r}.",
                        path="data.week_skeleton_logic.week_roles",
                    )
                )
        extra = sorted(set(observed_roles) - set(expected_roles))
        if extra:
            issues.append(
                PlanningContractIssue(
                    "phase_extra_week_roles",
                    f"Phase structure contains roles outside exact phase range: {', '.join(extra)}.",
                    path="data.week_skeleton_logic.week_roles",
                )
            )
    issues.extend(validate_phase_s5_bands_against_context(phase_payload=phase_payload, phase_execution_context=phase_execution_context))
    return issues


def validate_week_plan_against_week_context(
    *,
    week_plan_payload: JsonMap,
    week_calendar_context: JsonMap,
) -> list[PlanningContractIssue]:
    """Validate a Week Plan against active deterministic week context."""

    data = _as_map(week_plan_payload.get("data"))
    summary = _as_map(data.get("week_summary"))
    agenda = [_as_map(item) for item in _as_list(data.get("agenda"))]
    issues: list[PlanningContractIssue] = []
    issues.extend(
        _compare_contract_subset(
            candidate=_as_map(data.get("inherited_planning_posture")),
            authority=_as_map(week_calendar_context.get("inherited_planning_posture")),
            path="data.inherited_planning_posture",
            code="week_inherited_planning_posture_mismatch",
            label="inherited_planning_posture",
        )
    )
    issues.extend(
        _compare_contract_subset(
            candidate=_as_map(data.get("effective_week_constraints")),
            authority=build_effective_week_constraints_block(week_calendar_context),
            path="data.effective_week_constraints",
            code="week_effective_constraints_mismatch",
            label="effective_week_constraints",
        )
    )
    active_band = _as_map(
        week_calendar_context.get("active_weekly_kj_band")
        or week_calendar_context.get("phase_weekly_kj_band")
        or week_calendar_context.get("active_s5_band")
    )
    if not active_band:
        issues.append(
            PlanningContractIssue(
                "week_active_band_missing",
                "Deterministic active weekly band is missing.",
                path="week_calendar_context.active_weekly_kj_band",
            )
        )
    else:
        corridor = _as_map(summary.get("weekly_load_corridor_kj") or summary.get("weekly_load_corridor"))
        observed_min = _as_float(corridor.get("min"))
        observed_max = _as_float(corridor.get("max"))
        expected_min = _as_float(active_band.get("min"))
        expected_max = _as_float(active_band.get("max"))
        if None not in {observed_min, observed_max, expected_min, expected_max}:
            assert observed_min is not None and observed_max is not None
            assert expected_min is not None and expected_max is not None
            if observed_min != expected_min or observed_max != expected_max:
                issues.append(
                    PlanningContractIssue(
                        "week_corridor_active_band_mismatch",
                        f"Week corridor {observed_min:g}-{observed_max:g}, expected active band {expected_min:g}-{expected_max:g}.",
                        path="data.week_summary.weekly_load_corridor_kj",
                    )
                )
        planned = _as_float(summary.get("planned_weekly_load_kj"))
        if None not in {planned, expected_min, expected_max} and not (expected_min <= planned <= expected_max):
            assert planned is not None
            assert expected_min is not None and expected_max is not None
            issues.append(
                PlanningContractIssue(
                    "week_planned_load_outside_active_band",
                    f"planned_weekly_load_kj {planned:g} outside active band {expected_min:g}-{expected_max:g}.",
                    path="data.week_summary.planned_weekly_load_kj",
                )
            )
    expected_days = [
        (str(row.get("day") or ""), str(row.get("date") or ""))
        for row in _as_list(week_calendar_context.get("day_matrix"))
        if isinstance(row, dict)
    ]
    if expected_days and len(agenda) != len(expected_days):
        issues.append(
            PlanningContractIssue(
                "week_agenda_length_mismatch",
                f"Agenda has {len(agenda)} days, expected {len(expected_days)}.",
                path="data.agenda",
            )
        )
    for idx, expected in enumerate(expected_days):
        if idx >= len(agenda):
            continue
        row = agenda[idx]
        expected_day, expected_date = expected
        if row.get("day") != expected_day or row.get("date") != expected_date:
            issues.append(
                PlanningContractIssue(
                    "week_agenda_calendar_mismatch",
                    f"Row {idx + 1} is {row.get('day')} {row.get('date')}, expected {expected_day} {expected_date}.",
                    path=f"data.agenda[{idx}]",
                )
            )
    target_skeleton = _as_map(week_calendar_context.get("target_week_skeleton"))
    if target_skeleton:
        expected_roles_by_day = {
            str(_as_map(item).get("day_of_week") or "").strip(): str(_as_map(item).get("day_role") or "").strip()
            for item in _as_list(target_skeleton.get("days"))
            if str(_as_map(item).get("day_of_week") or "").strip() and str(_as_map(item).get("day_role") or "").strip()
        }
        for row in agenda:
            day = str(row.get("day") or "").strip()
            expected_role = expected_roles_by_day.get(day)
            observed_role = str(row.get("day_role") or "").strip()
            if expected_role and observed_role != expected_role:
                issues.append(
                    PlanningContractIssue(
                        "week_day_role_skeleton_mismatch",
                        f"{day} day_role {observed_role!r} does not match shared skeleton role {expected_role!r}.",
                        path="data.agenda",
                    )
                )
    week_role = str(week_calendar_context.get("phase_week_role") or "").upper()
    if week_role in {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"}:
        quality_days = [row for row in agenda if str(row.get("day_role") or "").upper() == "QUALITY"]
        if quality_days:
            issues.append(
                PlanningContractIssue(
                    "week_recovery_role_quality_day",
                    f"{week_role} week must not contain QUALITY days.",
                    path="data.agenda",
                )
            )
    return issues


def validate_writer_output_against_blueprints(
    *,
    scope: Literal["season", "phase", "week"],
    artifact_payload: JsonMap,
    blueprints: list[JsonMap],
) -> list[PlanningContractIssue]:
    """Validate writer output against approved internal blueprints."""

    if not blueprints:
        return [
            PlanningContractIssue(
                "blueprints_missing",
                f"No approved {scope} blueprints available for writer-output comparison.",
            )
        ]
    if scope == "season":
        context = {"phase_slots": [{"phase_id": bp.get("phase_id"), "iso_week_range": bp.get("iso_week_range")} for bp in blueprints]}
        return validate_season_plan_against_phase_slots(season_plan_payload=artifact_payload, phase_slot_context=context)
    if scope == "phase":
        expected_roles = {
            str(bp.get("week")): str(bp.get("week_role"))
            for bp in blueprints
            if bp.get("week") and bp.get("week_role")
        }
        context: JsonMap = {"week_role_by_iso_week": expected_roles, "phase_s5_bands": []}
        for bp in blueprints:
            week = bp.get("week")
            band_min = bp.get("s5_band_min")
            band_max = bp.get("s5_band_max")
            if week and band_min is not None and band_max is not None:
                context["phase_s5_bands"].append({"week": week, "band": {"min": band_min, "max": band_max}})
        return validate_phase_against_execution_context(phase_payload=artifact_payload, phase_execution_context=context)
    agenda = [_as_map(item) for item in _as_list(_as_map(artifact_payload.get("data")).get("agenda"))]
    issues: list[PlanningContractIssue] = []
    day_blueprints = [bp for bp in blueprints if bp.get("day")]
    if day_blueprints and len(agenda) != len(day_blueprints):
        issues.append(
            PlanningContractIssue(
                "week_day_blueprint_agenda_count_mismatch",
                f"Agenda has {len(agenda)} days, expected {len(day_blueprints)} day blueprints.",
                path="data.agenda",
            )
        )
    for idx, bp in enumerate(day_blueprints):
        if idx >= len(agenda):
            continue
        row = agenda[idx]
        for field, blueprint_field in (
            ("day", "day"),
            ("date", "date"),
            ("day_role", "day_role"),
            ("planned_kj", "planned_kj"),
        ):
            if row.get(field) != bp.get(blueprint_field):
                issues.append(
                    PlanningContractIssue(
                        "week_day_blueprint_mismatch",
                        f"{field} is {row.get(field)!r}, expected {bp.get(blueprint_field)!r}.",
                        path=f"data.agenda[{idx}].{field}",
                    )
                )
    return issues
