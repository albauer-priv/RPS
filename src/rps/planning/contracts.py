"""Deterministic planning-contract validators.

The functions in this module compare model-authored planning artefacts with
code-owned runtime contracts. They deliberately return structured issues
instead of raising so callers can decide whether to block, warn, or attach
review instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from rps.workspace.intensity_domains import normalize_intensity_domain_list
from rps.workspace.iso_helpers import IsoWeekRange, parse_iso_week, parse_iso_week_range
from rps.workspace.phase_intents import (
    normalize_phase_intent,
    normalize_phase_type,
    normalize_season_archetype,
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


def _candidate_or_document(mapping: JsonMap) -> JsonMap:
    candidate = mapping.get("candidate_document")
    return candidate if isinstance(candidate, dict) else mapping


def derive_expected_average_weekly_kj_range(*, season_plan_payload: JsonMap) -> JsonMap | None:
    """Derive the weighted expected average weekly kJ range from phase corridors."""

    document = _candidate_or_document(season_plan_payload)
    phases = _phase_data(document)
    total_weeks = 0
    weighted_min = 0.0
    weighted_max = 0.0
    for phase in phases:
        weeks = _range_week_count(phase.get("iso_week_range"))
        weekly_kj = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
        min_value = _as_float(weekly_kj.get("min"))
        max_value = _as_float(weekly_kj.get("max"))
        if weeks is None or weeks <= 0 or min_value is None or max_value is None:
            return None
        total_weeks += weeks
        weighted_min += min_value * weeks
        weighted_max += max_value * weeks
    if total_weeks <= 0:
        return None
    return {
        "min": int(round(weighted_min / total_weeks)),
        "max": int(round(weighted_max / total_weeks)),
    }


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
) -> list[PlanningContractIssue]:
    """Validate Season Plan strategic corridors against deterministic phase load context."""

    document = _candidate_or_document(season_plan_payload)
    phases = _phase_data(document)
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
    build_max_values: list[float] = []
    peak_max_values: list[tuple[str, float]] = []
    phase_allowed_domain_sets: list[tuple[str, list[str]]] = []
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
        if allowed_domains:
            phase_allowed_domain_sets.append((phase_id or path, allowed_domains))
            outside = sorted(set(allowed_domains) - set(season_allowed_domains)) if season_allowed_domains else []
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
    expected_envelope = derive_expected_average_weekly_kj_range(season_plan_payload=season_plan_payload)
    actual_envelope = _as_map(_as_map(document.get("data")).get("season_load_envelope")).get("expected_average_weekly_kj_range")
    actual_envelope_map = _as_map(actual_envelope)
    actual_min = _as_float(actual_envelope_map.get("min"))
    actual_max = _as_float(actual_envelope_map.get("max"))
    if expected_envelope and None not in {actual_min, actual_max}:
        if round(actual_min) != expected_envelope["min"] or round(actual_max) != expected_envelope["max"]:
            issues.append(
                PlanningContractIssue(
                    "season_load_envelope_mismatch",
                    (
                        f"expected_average_weekly_kj_range is {actual_min:g}-{actual_max:g}, "
                        f"expected weighted phase-derived {expected_envelope['min']}-{expected_envelope['max']}."
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
    """Validate phase weekly load bands directly against deterministic S5 context."""

    expected: dict[str, JsonMap] = {}
    for entry in _as_list(phase_execution_context.get("phase_s5_bands")):
        entry_map = _as_map(entry)
        week = _week_key(entry_map.get("week"))
        band = _as_map(entry_map.get("band"))
        if week and band:
            expected[week] = band
    if not expected:
        return [
            PlanningContractIssue(
                "phase_s5_context_missing",
                "Deterministic phase S5 bands are missing.",
                path="phase_execution_context.phase_s5_bands",
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
        if None not in {observed_min, observed_max, expected_min, expected_max} and (
            round(observed_min) != round(expected_min) or round(observed_max) != round(expected_max)
        ):
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
    if not expected_roles:
        issues.append(
            PlanningContractIssue(
                "phase_week_role_context_missing",
                "Deterministic week_role_by_iso_week is missing.",
                path="phase_execution_context.week_role_by_iso_week",
            )
        )
        return issues
    data = _as_map(phase_payload.get("data"))
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
        if None not in {observed_min, observed_max, expected_min, expected_max} and (
            observed_min != expected_min or observed_max != expected_max
        ):
            issues.append(
                PlanningContractIssue(
                    "week_corridor_active_band_mismatch",
                    f"Week corridor {observed_min:g}-{observed_max:g}, expected active band {expected_min:g}-{expected_max:g}.",
                    path="data.week_summary.weekly_load_corridor_kj",
                )
            )
        planned = _as_float(summary.get("planned_weekly_load_kj"))
        if None not in {planned, expected_min, expected_max} and not (expected_min <= planned <= expected_max):
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
        context = {"week_role_by_iso_week": expected_roles, "phase_s5_bands": []}
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
