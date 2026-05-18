"""Deterministic load-band calculations for planning guardrails.

This module implements the code-owned parts of `LoadEstimationSpec` used by
Season, Phase, and Week planning. It treats `planned_kJ` as mechanical work and
`planned_weekly_load_kj` as the governance load metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import inf
from typing import Any

from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange, parse_iso_week_range, range_contains
from rps.workspace.phase_resolution import date_to_iso_week

JsonMap = dict[str, Any]

ALPHA = 1.3
DEFAULT_IF_REF_LOAD = 0.68
DEFAULT_DOMAIN_IF: dict[str, float] = {
    "REST": 0.0,
    "OFF": 0.0,
    "NONE": 0.0,
    "RECOVERY": 0.55,
    "ENDURANCE": 0.70,
    "TEMPO": 0.80,
    "SWEET_SPOT": 0.90,
    "THRESHOLD": 1.00,
    "VO2MAX": 1.10,
    "ANAEROBIC": 1.15,
}
LOGISTICS_LOAD_IMPACTS = {"AVAILABILITY", "MISSED_SESSION", "MODALITY", "RECOVERY", "DATA_QUALITY"}


class LoadBandError(ValueError):
    """Raised when deterministic load-band derivation cannot continue."""


@dataclass(frozen=True)
class NumberBand:
    """Numeric min/max band used for load calculations."""

    min: float
    max: float

    def as_dict(self) -> JsonMap:
        """Return a JSON-serializable representation."""

        return {"min": self.min, "max": self.max}


@dataclass(frozen=True)
class IfRefLoad:
    """Resolved athlete-aware IF normalization constant."""

    value: float
    source: str


@dataclass(frozen=True)
class S5BandResult:
    """Final S5 band plus trace data."""

    band: NumberBand
    trace: JsonMap


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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def default_if_for_domain(domain: str, zone_model_payload: JsonMap | None = None) -> float:
    """Return deterministic IF for an intensity domain.

    Zone-model values are used when a recognizable endurance/tempo/threshold
    zone is available; otherwise the project fallback table is used.
    """

    normalized = str(domain or "").strip().upper().replace(" ", "_")
    zone_if = _zone_model_if_for_domain(normalized, zone_model_payload or {})
    if zone_if is not None:
        return zone_if
    return DEFAULT_DOMAIN_IF.get(normalized, DEFAULT_DOMAIN_IF["ENDURANCE"])


def _zone_model_if_for_domain(domain: str, zone_model_payload: JsonMap) -> float | None:
    data = _as_map(zone_model_payload.get("data"))
    zones = _as_list(data.get("zones"))
    preferred_zone_ids = {
        "RECOVERY": ("Z1",),
        "ENDURANCE": ("Z2", "Z3"),
        "TEMPO": ("Z3",),
        "SWEET_SPOT": ("SS",),
        "THRESHOLD": ("Z4",),
        "VO2MAX": ("Z5",),
    }.get(domain, ())
    for zone_id in preferred_zone_ids:
        for zone in zones:
            zone_map = _as_map(zone)
            if str(zone_map.get("zone_id") or "").upper() != zone_id:
                continue
            typical_if = _as_float(zone_map.get("typical_if"))
            if typical_if is not None and typical_if >= 0:
                return typical_if
    return None


def resolve_if_ref_load(
    *,
    athlete_profile_payload: JsonMap | None = None,
    zone_model_payload: JsonMap | None = None,
) -> IfRefLoad:
    """Resolve `IF_ref_load` according to `LoadEstimationSpec`.

    Inputs are full artifact envelopes. The function prefers athlete
    `endurance_anchor_w / ftp_watts`, then zone-model Z2/endurance typical IF,
    then the constant fallback.
    """

    zone_payload = zone_model_payload or {}
    ftp = extract_ftp_watts(zone_payload)
    profile_data = _as_map((athlete_profile_payload or {}).get("data"))
    profile = _as_map(profile_data.get("profile"))
    anchor = _as_float(profile.get("endurance_anchor_w"))
    if anchor is not None and ftp is not None and ftp > 0:
        return IfRefLoad(_clamp(anchor / ftp, 0.55, 0.80), "ATHLETE_PROFILE_ANCHOR")

    zone_if = _zone_model_if_for_domain("ENDURANCE", zone_payload)
    if zone_if is not None:
        return IfRefLoad(_clamp(zone_if, 0.55, 0.80), "ZONEMODEL_ENDURANCE_TYPICAL")

    return IfRefLoad(DEFAULT_IF_REF_LOAD, "FALLBACK_CONST")


def extract_ftp_watts(zone_model_payload: JsonMap | None) -> float | None:
    """Extract `ftp_watts` from a zone-model envelope."""

    data = _as_map((zone_model_payload or {}).get("data"))
    metadata = _as_map(data.get("model_metadata"))
    ftp = _as_float(metadata.get("ftp_watts"))
    return ftp if ftp is not None and ftp > 0 else None


def calculate_availability_feasible_band(
    *,
    availability_hours: float,
    ftp_watts: float,
    allowed_intensity_domains: list[str],
    if_ref_load: float,
    zone_model_payload: JsonMap | None = None,
    utilization_min: float = 0.0,
    utilization_max: float = 1.0,
) -> NumberBand:
    """Calculate the feasible `planned_weekly_load_kj` band from availability."""

    if ftp_watts <= 0:
        raise LoadBandError("missing_or_invalid_ftp")
    if availability_hours < 0:
        raise LoadBandError("negative_availability")
    domains = [str(item).strip().upper() for item in allowed_intensity_domains if str(item).strip()]
    if not domains:
        raise LoadBandError("missing_allowed_intensity_domains")
    if if_ref_load <= 0:
        raise LoadBandError("missing_or_invalid_if_ref_load")

    if_values = [default_if_for_domain(domain, zone_model_payload) for domain in domains]
    if_min = max(min(if_values), 0.0)
    if_max = min(max(if_values), 1.3)
    t_cap_sec = availability_hours * 3600.0
    t_min = t_cap_sec * utilization_min
    t_max = t_cap_sec * utilization_max
    norm = if_ref_load**ALPHA
    exponent = ALPHA + 1.0
    feasible_min = (ftp_watts * t_min / 1000.0) * (if_min**exponent) / norm
    feasible_max = (ftp_watts * t_max / 1000.0) * (if_max**exponent) / norm
    if feasible_min < 0 or feasible_max < 0 or feasible_min > feasible_max:
        raise LoadBandError("feasible_band_empty")
    return NumberBand(feasible_min, feasible_max)


def calculate_kpi_capacity_band(
    *,
    kpi_rate_band: JsonMap,
    body_mass_kg: float | None,
    availability_hours: float,
    if_ref_load: float,
    if_ref_week: float | None = None,
    utilization_max: float = 1.0,
) -> NumberBand:
    """Map KPI kJ/kg/h guidance into governance load space."""

    if body_mass_kg is None or body_mass_kg <= 0:
        raise LoadBandError("missing_body_mass_for_kpi_rate")
    kj_range = _as_map(kpi_rate_band.get("kj_per_kg_per_hour"))
    band_min = _as_float(kj_range.get("min"))
    band_max = _as_float(kj_range.get("max"))
    if band_min is None or band_max is None or band_min < 0 or band_max < band_min:
        raise LoadBandError("invalid_kpi_rate_band")
    ref_week = if_ref_week if if_ref_week is not None and if_ref_week > 0 else if_ref_load
    moving_time_capacity_hours = availability_hours * utilization_max
    kpi_kj_min = band_min * body_mass_kg * moving_time_capacity_hours
    kpi_kj_max = band_max * body_mass_kg * moving_time_capacity_hours
    factor = (ref_week / if_ref_load) ** ALPHA
    return NumberBand(kpi_kj_min * factor, kpi_kj_max * factor)


def calculate_progression_band(
    *,
    previous_load_kj: float | None,
    max_weekly_increase_pct: float = 0.12,
    max_weekly_decrease_pct: float = 0.40,
) -> NumberBand | None:
    """Return an optional progression overlay band."""

    if previous_load_kj is None or previous_load_kj <= 0:
        return None
    return NumberBand(
        previous_load_kj * (1.0 - max_weekly_decrease_pct),
        previous_load_kj * (1.0 + max_weekly_increase_pct),
    )


def selected_kpi_rate_band_from_selection(selection_payload: JsonMap | None) -> JsonMap | None:
    """Return selected KPI moving-time-rate guidance from scenario selection.

    The returned object is the code-owned input for KPI capacity mapping. It is
    absent unless the selection carries a complete mechanical kJ/kg/h band.
    """

    data = _as_map((selection_payload or {}).get("data"))
    selected = _as_map(data.get("kpi_moving_time_rate_guidance_selection"))
    if not selected:
        return None
    kj_range = _as_map(selected.get("kj_per_kg_per_hour"))
    if _as_float(kj_range.get("min")) is None or _as_float(kj_range.get("max")) is None:
        return None
    return selected


def derive_phase_s5_band(
    *,
    season_band: NumberBand,
    feasible_band: NumberBand,
    kpi_band: NumberBand | None = None,
    progression_band: NumberBand | None = None,
    kpi_selector_used: str | None = None,
    kpi_escalation_bands: dict[str, NumberBand] | None = None,
    kpi_escalation_order: list[str] | None = None,
    kpi_utilization_override_band: NumberBand | None = None,
) -> S5BandResult:
    """Derive the final S5 phase band and trace fallback behavior."""

    active_kpi_band = kpi_band or NumberBand(0.0, inf)
    base = _intersect_bands(season_band, feasible_band, active_kpi_band)
    with_progression = _intersect_bands(base, progression_band) if progression_band else base
    trace: JsonMap = {
        "season_band": season_band.as_dict(),
        "feasible_band": feasible_band.as_dict(),
        "kpi_band": None if kpi_band is None else kpi_band.as_dict(),
        "progression_band": None if progression_band is None else progression_band.as_dict(),
        "kpi_rate_band_selector_used": kpi_selector_used,
    }
    if _valid_band(with_progression):
        return _s5_result(with_progression, trace, 0, "normal_intersection")

    if progression_band is not None and _valid_band(base):
        return _s5_result(base, trace, 1, "dropped_progression_overlay")

    escalated = _try_kpi_escalation(
        season_band=season_band,
        feasible_band=feasible_band,
        progression_band=progression_band,
        kpi_escalation_bands=kpi_escalation_bands or {},
        kpi_escalation_order=kpi_escalation_order,
        current_selector=kpi_selector_used,
        trace=trace,
    )
    if escalated is not None:
        return escalated

    if kpi_utilization_override_band is not None:
        override_base = _intersect_bands(season_band, feasible_band, kpi_utilization_override_band)
        override_progression = _intersect_bands(override_base, progression_band) if progression_band else override_base
        if _valid_band(override_progression):
            trace["kpi_utilization_override_band"] = kpi_utilization_override_band.as_dict()
            return _s5_result(override_progression, trace, 3, "kpi_utilization_override")
        if _valid_band(override_base):
            trace["kpi_utilization_override_band"] = kpi_utilization_override_band.as_dict()
            return _s5_result(override_base, trace, 3, "kpi_utilization_override_without_progression")

    hard_band = _intersect_bands(feasible_band, active_kpi_band)
    if _valid_band(hard_band):
        if season_band.max < hard_band.min:
            degenerate = NumberBand(hard_band.min, hard_band.min)
            return _s5_result(degenerate, trace, 5, "season_corridor_infeasible_override")
        if season_band.min > hard_band.max:
            degenerate = NumberBand(hard_band.max, hard_band.max)
            return _s5_result(degenerate, trace, 5, "season_corridor_infeasible_override")
        degenerate = NumberBand(hard_band.max, hard_band.max)
        return _s5_result(degenerate, trace, 4, "degenerate_band_at_hard_max")

    if season_band.max < feasible_band.min:
        closest = feasible_band.min
    elif season_band.min > feasible_band.max:
        closest = feasible_band.max
    else:
        raise LoadBandError("s5_override_band_empty")
    degenerate = NumberBand(closest, closest)
    return _s5_result(degenerate, trace, 5, "season_corridor_infeasible_override")


def _try_kpi_escalation(
    *,
    season_band: NumberBand,
    feasible_band: NumberBand,
    progression_band: NumberBand | None,
    kpi_escalation_bands: dict[str, NumberBand],
    kpi_escalation_order: list[str] | None,
    current_selector: str | None,
    trace: JsonMap,
) -> S5BandResult | None:
    order = tuple(kpi_escalation_order or ("LOW", "MID", "HIGH"))
    current = str(current_selector or "").upper()
    lookup = {str(key).upper(): key for key in kpi_escalation_bands}
    start = order.index(current) + 1 if current in order else 0
    for selector in order[start:]:
        key = lookup.get(str(selector).upper(), selector)
        kpi_band = kpi_escalation_bands.get(key)
        if kpi_band is None:
            continue
        base = _intersect_bands(season_band, feasible_band, kpi_band)
        candidate = _intersect_bands(base, progression_band) if progression_band else base
        if _valid_band(candidate):
            escalated_trace = {**trace, "kpi_band": kpi_band.as_dict(), "kpi_rate_band_selector_used": key}
            return _s5_result(candidate, escalated_trace, 2, f"kpi_rate_band_escalation_{key}")
        if _valid_band(base):
            escalated_trace = {**trace, "kpi_band": kpi_band.as_dict(), "kpi_rate_band_selector_used": key}
            return _s5_result(base, escalated_trace, 2, f"kpi_rate_band_escalation_{key}_without_progression")
    return None


def _intersect_bands(*bands: NumberBand | None) -> NumberBand:
    valid = [band for band in bands if band is not None]
    if not valid:
        return NumberBand(0.0, inf)
    return NumberBand(max(band.min for band in valid), min(band.max for band in valid))


def _valid_band(band: NumberBand) -> bool:
    return band.min <= band.max and band.max >= 0


def _s5_result(band: NumberBand, trace: JsonMap, fallback_level: int, fallback_reason: str) -> S5BandResult:
    final = NumberBand(float(round(band.min)), float(round(band.max)))
    final_trace = {
        **trace,
        "fallback_level": fallback_level,
        "fallback_reason": fallback_reason,
        "final_band": final.as_dict(),
    }
    return S5BandResult(final, final_trace)


def build_load_capacity_context(
    *,
    target_week: IsoWeek | None = None,
    phase_range: IsoWeekRange | None = None,
    athlete_profile_payload: JsonMap | None = None,
    availability_payload: JsonMap | None = None,
    logistics_payload: JsonMap | None = None,
    zone_model_payload: JsonMap | None = None,
    season_plan_payload: JsonMap | None = None,
    phase_guardrails_payload: JsonMap | None = None,
    wellness_payload: JsonMap | None = None,
    kpi_profile_payload: JsonMap | None = None,
    kpi_rate_band: JsonMap | None = None,
    previous_load_kj: float | None = None,
) -> JsonMap:
    """Build deterministic load-capacity and S5 context for planner prompts."""

    if_ref = resolve_if_ref_load(
        athlete_profile_payload=athlete_profile_payload,
        zone_model_payload=zone_model_payload,
    )
    ftp = extract_ftp_watts(zone_model_payload or {})
    availability_hours = _availability_hours(availability_payload or {})
    table_hours = _availability_table_weekly_hours(availability_payload or {})
    effective_hours = _effective_availability_hours(availability_hours, table_hours)
    allowed_domains = _allowed_domains(
        target_week=target_week,
        phase_range=phase_range,
        season_plan_payload=season_plan_payload or {},
        phase_guardrails_payload=phase_guardrails_payload or {},
    )
    logistics_constraints = _logistics_constraints(
        logistics_payload or {},
        target_week=target_week,
        phase_range=phase_range,
    )
    result: JsonMap = {
        "unit_semantics": "planned_weekly_load_kj",
        "if_ref_load": if_ref.value,
        "if_ref_load_source": if_ref.source,
        "ftp_watts": ftp,
        "allowed_intensity_domains": allowed_domains,
        "availability_weekly_hours": availability_hours,
        "availability_table_weekly_hours": table_hours,
        "availability_hours_source": effective_hours["source"],
        "logistics_constraints": logistics_constraints,
        "availability_load_capacity_kj": None,
        "s5_bands": [],
        "warnings": [],
    }
    if ftp is None:
        result["warnings"].append("missing_or_invalid_ftp")
        return result
    try:
        result["availability_load_capacity_kj"] = _capacity_for_hour_buckets(
            availability_hours=availability_hours,
            effective_availability_hours=effective_hours["hours"],
            ftp_watts=ftp,
            allowed_domains=allowed_domains,
            if_ref_load=if_ref.value,
            zone_model_payload=zone_model_payload or {},
        )
    except LoadBandError as exc:
        result["warnings"].append(str(exc))

    season_band = _season_band_for_context(
        target_week=target_week,
        phase_range=phase_range,
        season_plan_payload=season_plan_payload or {},
    )
    weeks = _weeks_for_context(target_week=target_week, phase_range=phase_range)
    if season_band is not None:
        body_mass = _body_mass_kg(athlete_profile_payload or {}, wellness_payload or {})
        kpi_band = None
        kpi_escalation_bands: dict[str, NumberBand] = {}
        kpi_escalation_order: list[str] = []
        kpi_utilization_override_band = None
        kpi_error: str | None = None
        typical_hours = _as_float(_as_map(effective_hours["hours"]).get("typical")) or 0.0
        try:
            if kpi_rate_band:
                kpi_band = calculate_kpi_capacity_band(
                    kpi_rate_band=kpi_rate_band,
                    body_mass_kg=body_mass,
                    availability_hours=typical_hours,
                    if_ref_load=if_ref.value,
                )
                kpi_escalation_bands, kpi_escalation_order = _kpi_escalation_band_context(
                    kpi_profile_payload=kpi_profile_payload or {},
                    body_mass_kg=body_mass,
                    availability_hours=typical_hours,
                    if_ref_load=if_ref.value,
                )
                if _kpi_utilization_override_allowed(kpi_profile_payload or {}):
                    kpi_utilization_override_band = calculate_kpi_capacity_band(
                        kpi_rate_band=kpi_rate_band,
                        body_mass_kg=body_mass,
                        availability_hours=typical_hours,
                        if_ref_load=if_ref.value,
                        utilization_max=1.0,
                    )
        except LoadBandError as exc:
            result["warnings"].append(str(exc))
            kpi_error = str(exc)
        progression_band = calculate_progression_band(previous_load_kj=previous_load_kj)
        for week in weeks:
            if kpi_error is not None:
                result["s5_bands"].append({"week": _week_key(week), "error": kpi_error})
                continue
            try:
                feasible = calculate_availability_feasible_band(
                    availability_hours=typical_hours,
                    ftp_watts=ftp,
                    allowed_intensity_domains=allowed_domains,
                    if_ref_load=if_ref.value,
                    zone_model_payload=zone_model_payload or {},
                )
                s5 = derive_phase_s5_band(
                    season_band=season_band,
                    feasible_band=feasible,
                    kpi_band=kpi_band,
                    progression_band=progression_band,
                    kpi_selector_used=str(kpi_rate_band.get("segment")) if isinstance(kpi_rate_band, dict) else None,
                    kpi_escalation_bands=kpi_escalation_bands,
                    kpi_escalation_order=kpi_escalation_order,
                    kpi_utilization_override_band=kpi_utilization_override_band,
                )
            except LoadBandError as exc:
                result["s5_bands"].append({"week": _week_key(week), "error": str(exc)})
                continue
            result["s5_bands"].append(
                {
                    "week": _week_key(week),
                    "band": {"min": int(s5.band.min), "max": int(s5.band.max)},
                    "trace": s5.trace,
                }
            )
    return result


def render_load_capacity_context_block(context: JsonMap) -> str:
    """Render deterministic load context as a planner prompt block."""

    if not context:
        return ""
    lines = [
        "**Deterministic Load Capacity Context**",
        "These values are code-owned. Use them directly; do not recompute, widen, or override S5/availability load bands in agent reasoning.",
        f"unit_semantics: {context.get('unit_semantics')}",
        f"ftp_watts: {context.get('ftp_watts')}",
        f"IF_ref_load: {context.get('if_ref_load')} ({context.get('if_ref_load_source')})",
        "allowed_intensity_domains: " + ", ".join(str(x) for x in _as_list(context.get("allowed_intensity_domains"))),
    ]
    hours = _as_map(context.get("availability_weekly_hours"))
    if hours:
        lines.append(
            f"availability_weekly_hours: min {hours.get('min')}, typical {hours.get('typical')}, max {hours.get('max')}"
        )
    table_hours = _as_map(context.get("availability_table_weekly_hours"))
    if table_hours:
        totals = _as_map(table_hours.get("hours"))
        lines.append(
            "availability_table_weekly_hours: "
            f"min {totals.get('min')}, typical {totals.get('typical')}, max {totals.get('max')}, "
            f"complete {table_hours.get('complete')}"
        )
    if context.get("availability_hours_source"):
        lines.append(f"availability_hours_source: {context.get('availability_hours_source')}")
    capacity = _as_map(context.get("availability_load_capacity_kj"))
    if capacity:
        lines.append(
            "availability_load_capacity_kj: "
            f"min {capacity.get('min')}, typical {capacity.get('typical')}, max {capacity.get('max')}"
        )
    s5_bands = _as_list(context.get("s5_bands"))
    if s5_bands:
        lines.append("deterministic_s5_bands:")
        for entry in s5_bands:
            entry_map = _as_map(entry)
            band = _as_map(entry_map.get("band"))
            trace = _as_map(entry_map.get("trace"))
            if band:
                lines.append(
                    f"- {entry_map.get('week')}: min {band.get('min')}, max {band.get('max')}, "
                    f"fallback_level {trace.get('fallback_level')}, fallback_reason {trace.get('fallback_reason')}"
                )
            elif entry_map.get("error"):
                lines.append(f"- {entry_map.get('week')}: ERROR {entry_map.get('error')}")
    constraints = [str(item) for item in _as_list(context.get("logistics_constraints")) if str(item).strip()]
    if constraints:
        lines.append("logistics_constraints:")
        lines.extend(f"- {item}" for item in constraints)
    warnings = [str(item) for item in _as_list(context.get("warnings")) if str(item).strip()]
    if warnings:
        lines.append("load_context_warnings:")
        lines.extend(f"- {item}" for item in warnings)
    return "\n".join(lines) + "\n"


def _capacity_for_hour_buckets(
    *,
    availability_hours: dict[str, float],
    effective_availability_hours: JsonMap,
    ftp_watts: float,
    allowed_domains: list[str],
    if_ref_load: float,
    zone_model_payload: JsonMap,
) -> JsonMap:
    capacity: JsonMap = {
        "unit_semantics": "planned_weekly_load_kj",
        "source": "AVAILABILITY.weekly_hours + ZONE_MODEL.ftp_watts",
    }
    selected_hours = {
        key: _as_float(effective_availability_hours.get(key)) or availability_hours.get(key, 0.0)
        for key in ("min", "typical", "max")
    }
    for key in ("min", "typical", "max"):
        band = calculate_availability_feasible_band(
            availability_hours=selected_hours.get(key, 0.0),
            ftp_watts=ftp_watts,
            allowed_intensity_domains=allowed_domains,
            if_ref_load=if_ref_load,
            zone_model_payload=zone_model_payload,
        )
        capacity[key] = int(round(band.max))
    return capacity


def _availability_hours(availability_payload: JsonMap) -> dict[str, float]:
    data = _as_map(availability_payload.get("data"))
    weekly = _as_map(data.get("weekly_hours"))
    return {
        "min": _as_float(weekly.get("min")) or 0.0,
        "typical": _as_float(weekly.get("typical")) or 0.0,
        "max": _as_float(weekly.get("max")) or 0.0,
    }


def _availability_table_weekly_hours(availability_payload: JsonMap) -> JsonMap:
    data = _as_map(availability_payload.get("data"))
    rows = _as_list(data.get("availability_table"))
    fixed_rest = {str(item)[:3].title() for item in _as_list(data.get("fixed_rest_days"))}
    totals = {"min": 0.0, "typical": 0.0, "max": 0.0}
    covered_days: set[str] = set()
    missing_values: list[str] = []
    for row in rows:
        row_map = _as_map(row)
        day = str(row_map.get("day") or row_map.get("weekday") or "").strip()[:3].title()
        if not day:
            continue
        covered_days.add(day)
        if day in fixed_rest:
            continue
        values = {
            "min": _as_float(row_map.get("hours_min") or row_map.get("min_hours") or row_map.get("min")),
            "typical": _as_float(row_map.get("hours_typical") or row_map.get("typical_hours") or row_map.get("typical")),
            "max": _as_float(row_map.get("hours_max") or row_map.get("max_hours") or row_map.get("max")),
        }
        for key, value in values.items():
            if value is None:
                missing_values.append(f"{day}.{key}")
                continue
            totals[key] += value
    complete = len(covered_days) >= 7 and not missing_values
    return {
        "hours": totals,
        "covered_days": sorted(covered_days),
        "complete": complete,
        "source": "AVAILABILITY.availability_table",
        "missing_values": missing_values,
    }


def _effective_availability_hours(weekly_hours: dict[str, float], table_hours: JsonMap) -> JsonMap:
    if table_hours.get("complete") is True:
        return {"source": "AVAILABILITY.availability_table", "hours": _as_map(table_hours.get("hours"))}
    return {"source": "AVAILABILITY.weekly_hours", "hours": weekly_hours}


def _body_mass_kg(athlete_profile_payload: JsonMap, wellness_payload: JsonMap) -> float | None:
    profile = _as_map(_as_map(athlete_profile_payload.get("data")).get("profile"))
    profile_mass = _as_float(profile.get("body_mass_kg"))
    if profile_mass is not None and profile_mass > 0:
        return profile_mass
    wellness_data = _as_map(wellness_payload.get("data"))
    wellness_mass = _as_float(wellness_data.get("body_mass_kg"))
    return wellness_mass if wellness_mass is not None and wellness_mass > 0 else None


def _kpi_escalation_band_context(
    *,
    kpi_profile_payload: JsonMap,
    body_mass_kg: float | None,
    availability_hours: float,
    if_ref_load: float,
) -> tuple[dict[str, NumberBand], list[str]]:
    data = _as_map(kpi_profile_payload.get("data"))
    durability = _as_map(data.get("durability"))
    guidance = _as_map(durability.get("moving_time_rate_guidance"))
    candidates: list[tuple[float, str, NumberBand]] = []
    for row in _as_list(guidance.get("bands")):
        row_map = _as_map(row)
        segment = str(row_map.get("segment") or "").strip()
        if not segment:
            continue
        kj_range = _as_map(row_map.get("kj_per_kg_per_hour"))
        band_min = _as_float(kj_range.get("min"))
        if band_min is None:
            continue
        band = calculate_kpi_capacity_band(
            kpi_rate_band=row_map,
            body_mass_kg=body_mass_kg,
            availability_hours=availability_hours,
            if_ref_load=if_ref_load,
        )
        candidates.append((band_min, segment, band))
    candidates.sort(key=lambda item: item[0])
    return ({segment: band for _rank, segment, band in candidates}, [segment for _rank, segment, _band in candidates])


def _kpi_utilization_override_allowed(kpi_profile_payload: JsonMap) -> bool:
    data = _as_map(kpi_profile_payload.get("data"))
    durability = _as_map(data.get("durability"))
    guidance = _as_map(durability.get("moving_time_rate_guidance"))
    return bool(
        data.get("kpi_mapping_utilization_override_allowed")
        or durability.get("kpi_mapping_utilization_override_allowed")
        or guidance.get("kpi_mapping_utilization_override_allowed")
    )


def _allowed_domains(
    *,
    target_week: IsoWeek | None,
    phase_range: IsoWeekRange | None,
    season_plan_payload: JsonMap,
    phase_guardrails_payload: JsonMap,
) -> list[str]:
    guardrails_data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(guardrails_data.get("allowed_forbidden_semantics"))
    domains = [str(item).strip().upper() for item in _as_list(semantics.get("allowed_intensity_domains")) if str(item).strip()]
    if domains:
        return domains
    phase = _season_phase_for_context(
        target_week=target_week,
        phase_range=phase_range,
        season_plan_payload=season_plan_payload,
    )
    phase_semantics = _as_map(phase.get("allowed_forbidden_semantics"))
    domains = [
        str(item).strip().upper()
        for item in _as_list(phase_semantics.get("allowed_intensity_domains"))
        if str(item).strip()
    ]
    if domains:
        return domains
    season_phases = _as_list(_as_map(season_plan_payload.get("data")).get("phases"))
    if phase_range is None and not season_phases:
        return ["ENDURANCE"]
    return []


def _season_band_for_context(
    *,
    target_week: IsoWeek | None,
    phase_range: IsoWeekRange | None,
    season_plan_payload: JsonMap,
) -> NumberBand | None:
    phase = _season_phase_for_context(
        target_week=target_week,
        phase_range=phase_range,
        season_plan_payload=season_plan_payload,
    )
    weekly_kj = _as_map(_as_map(phase.get("weekly_load_corridor")).get("weekly_kj"))
    min_value = _as_float(weekly_kj.get("min"))
    max_value = _as_float(weekly_kj.get("max"))
    if min_value is None or max_value is None or min_value < 0 or max_value < min_value:
        return None
    return NumberBand(min_value, max_value)


def _season_phase_for_context(
    *,
    target_week: IsoWeek | None,
    phase_range: IsoWeekRange | None,
    season_plan_payload: JsonMap,
) -> JsonMap:
    data = _as_map(season_plan_payload.get("data"))
    for phase in _as_list(data.get("phases")):
        phase_map = _as_map(phase)
        parsed = parse_iso_week_range(phase_map.get("iso_week_range"))
        if parsed is None:
            continue
        if phase_range is not None and parsed.key == phase_range.key:
            return phase_map
        if target_week is not None and range_contains(parsed, target_week):
            return phase_map
    return {}


def _weeks_for_context(*, target_week: IsoWeek | None, phase_range: IsoWeekRange | None) -> list[IsoWeek]:
    if phase_range is None:
        return [target_week] if target_week is not None else []
    weeks: list[IsoWeek] = []
    cursor = date.fromisocalendar(phase_range.start.year, phase_range.start.week, 1)
    end = date.fromisocalendar(phase_range.end.year, phase_range.end.week, 1)
    while cursor <= end:
        iso_year, iso_week, _ = cursor.isocalendar()
        weeks.append(IsoWeek(iso_year, iso_week))
        cursor += timedelta(days=7)
    return weeks


def _logistics_constraints(
    logistics_payload: JsonMap,
    *,
    target_week: IsoWeek | None,
    phase_range: IsoWeekRange | None,
) -> list[str]:
    data = _as_map(logistics_payload.get("data"))
    events = _as_list(data.get("events"))
    constraints: list[str] = []
    for event in events:
        event_map = _as_map(event)
        impact = str(event_map.get("impact") or "").upper()
        if impact not in LOGISTICS_LOAD_IMPACTS:
            continue
        raw_date = event_map.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            event_week = date_to_iso_week(date.fromisoformat(raw_date))
        except ValueError:
            continue
        if target_week is not None and event_week != target_week:
            if phase_range is None or not range_contains(phase_range, event_week):
                continue
        elif phase_range is not None and not range_contains(phase_range, event_week):
            continue
        constraints.append(
            f"{raw_date} ({_week_key(event_week)}) {event_map.get('event_type')} impact {impact}: {event_map.get('description')}"
        )
    return constraints


def _week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"
