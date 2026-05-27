"""Deterministic season-scenario recommendation helpers."""

from __future__ import annotations

import math
from datetime import date
from statistics import mean
from typing import Any

JsonMap = dict[str, Any]

_SUPPORTED_CADENCES = {"2:1", "3:1", "2:1:1"}


def _data(payload: JsonMap | None) -> JsonMap:
    if not isinstance(payload, dict):
        return {}
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _numbers(values: list[object]) -> list[float]:
    return [number for value in values if (number := _as_float(value)) is not None]


def _average(values: list[object]) -> float | None:
    numbers = _numbers(values)
    return mean(numbers) if numbers else None


def _coefficient_of_variation(values: list[object]) -> float | None:
    numbers = _numbers(values)
    if len(numbers) < 2:
        return None
    avg = mean(numbers)
    if avg <= 0:
        return None
    variance = sum((value - avg) ** 2 for value in numbers) / len(numbers)
    return math.sqrt(variance) / avg


def _recent_weeks(activities_trend_payload: JsonMap | None, count: int) -> list[JsonMap]:
    data = _data(activities_trend_payload)
    weeks = data.get("weekly_trends")
    if not isinstance(weeks, list):
        return []
    dict_weeks = [week for week in weeks if isinstance(week, dict)]
    dict_weeks.sort(key=lambda item: (int(item.get("year") or 0), int(item.get("iso_week") or 0)))
    return dict_weeks[-count:]


def _weekly_kj(week: JsonMap) -> float | None:
    aggregates = week.get("weekly_aggregates")
    if not isinstance(aggregates, dict):
        return None
    return _as_float(aggregates.get("work_kj"))


def _metric(week: JsonMap, section: str, key: str) -> float | None:
    section_value = week.get(section)
    if not isinstance(section_value, dict):
        return None
    return _as_float(section_value.get(key))


def _availability_summary(availability_payload: JsonMap | None) -> JsonMap:
    data = _data(availability_payload)
    weekly = data.get("weekly_hours")
    weekly = weekly if isinstance(weekly, dict) else {}
    fixed_rest_days = data.get("fixed_rest_days")
    table = data.get("availability_table")
    travel_risk_days = 0
    if isinstance(table, list):
        for row in table:
            if isinstance(row, dict) and str(row.get("travel_risk", "")).upper() in {"MED", "HIGH"}:
                travel_risk_days += 1
    return {
        "weekly_hours_min": _as_float(weekly.get("min")),
        "weekly_hours_typical": _as_float(weekly.get("typical")),
        "weekly_hours_max": _as_float(weekly.get("max")),
        "fixed_rest_days": fixed_rest_days if isinstance(fixed_rest_days, list) else [],
        "travel_risk_days": travel_risk_days,
    }


def _athlete_summary(athlete_profile_payload: JsonMap | None) -> JsonMap:
    data = _data(athlete_profile_payload)
    profile = data.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    limitations = data.get("limitations")
    limitations_text = " ".join(str(item) for item in limitations) if isinstance(limitations, list) else ""
    objectives = data.get("objectives")
    objectives_text = str(objectives) if objectives else ""
    return {
        "age": _as_float(profile.get("age")),
        "training_age_years": _as_float(profile.get("training_age_years")),
        "body_mass_kg": _as_float(profile.get("body_mass_kg")),
        "limitations_text": limitations_text,
        "objectives_text": objectives_text,
    }


def _baseline_summary(historical_baseline_payload: JsonMap | None) -> JsonMap:
    data = _data(historical_baseline_payload)
    metrics = data.get("metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    yearly = data.get("yearly_summary")
    year_count = len(yearly) if isinstance(yearly, list) else 0
    return {
        "kj_per_year": _as_float(metrics.get("kj_per_year")),
        "kj_per_hour": _as_float(metrics.get("kj_per_hour")),
        "year_count": year_count,
    }


def _season_start_date(season_scenarios_payload: JsonMap | None) -> str:
    meta = season_scenarios_payload.get("meta") if isinstance(season_scenarios_payload, dict) else None
    if not isinstance(meta, dict):
        return ""
    temporal_scope = meta.get("temporal_scope")
    if not isinstance(temporal_scope, dict):
        return ""
    value = temporal_scope.get("from")
    return value if isinstance(value, str) else ""


def _parse_iso_date(raw: object) -> date | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def filter_future_planning_events_payload(
    planning_events_payload: JsonMap | None,
    *,
    as_of_date: str,
    until_date: str | None = None,
) -> JsonMap:
    """Return a planning-events payload filtered to future events in the active horizon."""

    if not isinstance(planning_events_payload, dict):
        return {}
    target_start = _parse_iso_date(as_of_date)
    target_end = _parse_iso_date(until_date)
    if target_start is None:
        return planning_events_payload
    data = _data(planning_events_payload)
    events = data.get("events")
    filtered_events: list[JsonMap] = []
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict):
            continue
        parsed = _parse_iso_date(event.get("date"))
        if parsed is None or parsed < target_start:
            continue
        if target_end is not None and parsed > target_end:
            continue
        filtered_events.append(dict(event))
    filtered_data = dict(data)
    filtered_data["events"] = filtered_events
    filtered_payload = dict(planning_events_payload)
    filtered_payload["data"] = filtered_data
    return filtered_payload


def _event_summary(planning_events_payload: JsonMap | None, *, as_of_date: str = "") -> JsonMap:
    data = _data(planning_events_payload)
    events = data.get("events")
    if not isinstance(events, list):
        return {"future_a_events": 0, "future_b_events": 0}
    future_events = [
        event
        for event in events
        if isinstance(event, dict) and (not as_of_date or str(event.get("date", "")) >= as_of_date)
    ]
    return {
        "future_a_events": sum(1 for event in future_events if event.get("type") == "A"),
        "future_b_events": sum(1 for event in future_events if event.get("type") == "B"),
    }


def _scenario_items(season_scenarios_payload: JsonMap | None) -> list[JsonMap]:
    data = _data(season_scenarios_payload)
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list):
        return []
    return [scenario for scenario in scenarios if isinstance(scenario, dict)]


def _score_for_cadence(cadence: str, features: JsonMap) -> tuple[float, list[str], list[str]]:
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []
    volatility = bool(features.get("load_volatility_high"))
    recent_gap = bool(features.get("recent_load_gap"))
    robust_base = bool(features.get("robust_base"))
    competitive = bool(features.get("competitive_objective"))
    masters = bool(features.get("masters_athlete"))
    travel_or_fixed = bool(features.get("travel_or_fixed_rest_constraint"))
    drift_risk = bool(features.get("drift_or_durability_risk"))
    availability_ok = bool(features.get("availability_typical_ok"))
    b_event = bool(features.get("has_future_b_event"))

    if cadence == "2:1":
        score += 2.0
        reasons.append("frequent recovery fits durability-first planning")
        if volatility or recent_gap:
            score += 2.0
            reasons.append("recent load volatility or low-load week favors protected rebuilding")
        if masters or travel_or_fixed:
            score += 1.0
            reasons.append("masters profile and fixed constraints benefit from frequent reset weeks")
        if robust_base and competitive:
            score -= 1.2
            warnings.append("may be conservative for the competitive objective if readiness improves")
    elif cadence == "3:1":
        score += 1.0
        reasons.append("classic longer build block can sharpen fitness when stable")
        if robust_base:
            score += 1.5
            reasons.append("historical base supports longer loading blocks")
        if competitive and availability_ok:
            score += 1.0
            reasons.append("competitive objective and availability can support bigger build blocks")
        if not volatility and not recent_gap and not drift_risk:
            score += 1.5
            reasons.append("stable recent load and durability markers support a classic build cadence")
        if volatility:
            score -= 2.0
            warnings.append("recent weekly load volatility makes long uninterrupted builds riskier")
        if recent_gap:
            score -= 1.5
            warnings.append("latest low-load week argues against an aggressive 3:1 restart")
        if masters or travel_or_fixed or drift_risk:
            score -= 1.2
            warnings.append("masters/travel/durability markers require tighter fatigue control")
    elif cadence == "2:1:1":
        score += 2.0
        reasons.append("two load weeks plus mini-reset/reload balances adaptation and control")
        if robust_base:
            score += 1.0
            reasons.append("historical base is strong enough to use reload weeks productively")
        if volatility or recent_gap:
            score += 1.5
            reasons.append("adaptive reset/reload semantics fit variable recent load")
        if competitive:
            score += 0.8
            reasons.append("keeps a performance path without committing to a full 3:1 risk profile")
        if availability_ok:
            score += 0.5
            reasons.append("typical availability can support controlled load weeks")
        if b_event:
            score += 0.5
            reasons.append("future B event can be handled as rehearsal/minor adjustment")
        if drift_risk:
            score += 0.3
            reasons.append("mini-reset protects against accumulating durability drift")
        if not volatility and not recent_gap and not drift_risk:
            score -= 1.0
            warnings.append("less necessary when recent load and durability markers are stable")
    else:
        warnings.append(f"unsupported cadence {cadence!r}")

    return score, reasons, warnings


def build_scenario_recommendation_context(
    *,
    season_scenarios_payload: JsonMap | None,
    athlete_profile_payload: JsonMap | None = None,
    kpi_profile_payload: JsonMap | None = None,
    availability_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    historical_baseline_payload: JsonMap | None = None,
    activities_trend_payload: JsonMap | None = None,
    wellness_payload: JsonMap | None = None,
) -> JsonMap:
    """Return a code-owned advisory scenario recommendation.

    Inputs are workspace artefact payloads. The result is not a persisted
    contract; it is deterministic context for scenario generation and UI
    selection support.
    """

    del kpi_profile_payload, wellness_payload
    scenarios = _scenario_items(season_scenarios_payload)
    recent4 = _recent_weeks(activities_trend_payload, 4)
    recent8 = _recent_weeks(activities_trend_payload, 8)
    recent12 = _recent_weeks(activities_trend_payload, 12)
    recent4_kj = [_weekly_kj(week) for week in recent4]
    recent8_kj = [_weekly_kj(week) for week in recent8]
    recent12_kj = [_weekly_kj(week) for week in recent12]
    avg4_kj = _average(recent4_kj)
    avg8_kj = _average(recent8_kj)
    avg12_kj = _average(recent12_kj)
    last_kj = _weekly_kj(recent8[-1]) if recent8 else None
    cv8 = _coefficient_of_variation(recent8_kj)
    avg8_di = _average([_metric(week, "intensity_load_metrics", "durability_index") for week in recent8])
    avg8_decoupling = _average([_metric(week, "intensity_load_metrics", "decoupling_percent") for week in recent8])
    avg8_tsb = _average([_metric(week, "metrics", "tsb_today") for week in recent8])
    avg8_hours = _average([_metric(week, "metrics", "weekly_moving_time_total_min") for week in recent8])
    if avg8_hours is not None:
        avg8_hours = avg8_hours / 60.0

    availability = _availability_summary(availability_payload)
    athlete = _athlete_summary(athlete_profile_payload)
    baseline = _baseline_summary(historical_baseline_payload)
    events = _event_summary(planning_events_payload, as_of_date=_season_start_date(season_scenarios_payload))
    objectives_text = str(athlete.get("objectives_text", "")).lower()
    limitations_text = str(athlete.get("limitations_text", "")).lower()
    age = _as_float(athlete.get("age"))
    typical_hours = _as_float(availability.get("weekly_hours_typical"))
    kj_per_year = _as_float(baseline.get("kj_per_year"))

    features: JsonMap = {
        "robust_base": bool((kj_per_year or 0) >= 180000 or (avg8_kj or 0) >= 6000),
        "competitive_objective": "top 20" in objectives_text or "competitive" in objectives_text,
        "masters_athlete": bool(age is not None and age >= 50),
        "travel_or_fixed_rest_constraint": bool(
            availability.get("travel_risk_days") or availability.get("fixed_rest_days") or "travel" in limitations_text
        ),
        "availability_typical_ok": bool((typical_hours or 0) >= 12),
        "load_volatility_high": bool(cv8 is not None and cv8 >= 0.45),
        "recent_load_gap": bool(last_kj is not None and avg8_kj is not None and last_kj < avg8_kj * 0.5),
        "drift_or_durability_risk": bool(
            (avg8_di is not None and avg8_di < 0.96)
            or (avg8_decoupling is not None and avg8_decoupling > 5.0)
        ),
        "has_future_b_event": bool(events.get("future_b_events")),
    }

    ranked: list[JsonMap] = []
    warnings: list[str] = []
    for scenario in scenarios:
        guidance = scenario.get("scenario_guidance")
        guidance = guidance if isinstance(guidance, dict) else {}
        cadence = str(guidance.get("deload_cadence") or "")
        scenario_id = str(scenario.get("scenario_id") or "")
        if cadence not in _SUPPORTED_CADENCES:
            warnings.append(f"Scenario {scenario_id or '?'} has unsupported or missing cadence.")
            continue
        score, reasons, score_warnings = _score_for_cadence(cadence, features)
        ranked.append(
            {
                "scenario_id": scenario_id,
                "name": scenario.get("name"),
                "deload_cadence": cadence,
                "score": round(score, 2),
                "reasons": reasons[:4],
                "warnings": score_warnings[:4],
            }
        )
    ranked.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    best = ranked[0] if ranked else {}

    confidence = "LOW"
    if len(recent8) >= 6 and scenarios:
        confidence = "MEDIUM"
    if len(recent8) >= 8 and baseline.get("year_count", 0) and typical_hours is not None:
        confidence = "HIGH"
    if warnings:
        confidence = "MEDIUM" if confidence == "HIGH" else confidence

    evidence = {
        "recent_4w_avg_kj": round(avg4_kj, 1) if avg4_kj is not None else None,
        "recent_8w_avg_kj": round(avg8_kj, 1) if avg8_kj is not None else None,
        "recent_12w_avg_kj": round(avg12_kj, 1) if avg12_kj is not None else None,
        "latest_week_kj": round(last_kj, 1) if last_kj is not None else None,
        "recent_8w_load_cv": round(cv8, 2) if cv8 is not None else None,
        "recent_8w_avg_hours": round(avg8_hours, 2) if avg8_hours is not None else None,
        "recent_8w_avg_durability_index": round(avg8_di, 3) if avg8_di is not None else None,
        "recent_8w_avg_decoupling_percent": round(avg8_decoupling, 2) if avg8_decoupling is not None else None,
        "recent_8w_avg_tsb": round(avg8_tsb, 1) if avg8_tsb is not None else None,
        "historical_kj_per_year": round(kj_per_year, 1) if kj_per_year is not None else None,
        "availability_typical_hours": typical_hours,
        "availability_max_hours": availability.get("weekly_hours_max"),
        "fixed_rest_days": availability.get("fixed_rest_days"),
        "future_a_events": events.get("future_a_events"),
        "future_b_events": events.get("future_b_events"),
        "age": age,
        "training_age_years": athlete.get("training_age_years"),
    }
    recommended_id = best.get("scenario_id") if best else None
    summary = ""
    if recommended_id:
        summary = (
            f"Recommend Scenario {recommended_id} ({best.get('deload_cadence')}) because it best balances "
            "historical capacity, recent load volatility, availability, event timing, and durability risk."
        )
    else:
        summary = "No scenario recommendation available because no valid scenario cadence was found."

    return {
        "recommended_scenario_id": recommended_id,
        "recommended_scenario_name": best.get("name") if best else None,
        "recommended_cadence": best.get("deload_cadence") if best else None,
        "confidence": confidence,
        "summary": summary,
        "evidence": evidence,
        "features": features,
        "ranking": ranked,
        "warnings": warnings,
    }


def render_scenario_recommendation_block(context: JsonMap) -> str:
    """Render recommendation context for prompt injection."""

    if not context:
        return ""
    lines = ["\n**Deterministic Season Scenario Recommendation Context**"]
    lines.append(f"recommended_scenario_id: {context.get('recommended_scenario_id') or 'n/a'}")
    lines.append(f"recommended_cadence: {context.get('recommended_cadence') or 'n/a'}")
    lines.append(f"confidence: {context.get('confidence') or 'n/a'}")
    lines.append(f"summary: {context.get('summary') or 'n/a'}")
    evidence = context.get("evidence")
    if isinstance(evidence, dict):
        lines.append("evidence:")
        for key in sorted(evidence):
            lines.append(f"- {key}: {evidence.get(key)}")
    ranking = context.get("ranking")
    if isinstance(ranking, list):
        lines.append("ranking:")
        for item in ranking:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- "
                f"{item.get('scenario_id')}: score {item.get('score')} "
                f"cadence {item.get('deload_cadence')} reasons {item.get('reasons')}"
            )
    warnings = context.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append("warnings:")
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append(
        "Use this recommendation as advisory evidence in scenario notes and decision notes; "
        "do not auto-select a scenario."
    )
    return "\n".join(lines) + "\n"
