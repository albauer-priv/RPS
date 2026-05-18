"""Deterministic workout-load estimation for WEEK_PLAN validation and context.

The functions here implement the per-workout part of LoadEstimationSpec without
changing persisted WEEK_PLAN schemas. They parse the project workout-text subset
where possible and expose calibration context for prompts and tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rps.planning.load_bands import (
    ALPHA,
    default_if_for_domain,
    extract_ftp_watts,
    resolve_if_ref_load,
)
from rps.workouts.week_plan_consistency import derive_workout_duration_seconds

JsonMap = dict[str, Any]

_SECTION_HEADERS = {
    "Warmup",
    "#### Activation",
    "Main Set",
    "#### Add-On",
    "#### Z2 Add-On",
    "Cooldown",
}
_LOOP_RE = re.compile(r"^(?P<count>\d+)[xX]$")
_STEP_RE = re.compile(
    r"^- "
    r"(?:(?P<duration>(?:\d+(?:\.\d+)?(?:s|m|h)|\d+m\d+|\d+h\d+m)) )?"
    r"(?:(?P<ramp>ramp \d+(?:\.\d+)?%(?:-\d+(?:\.\d+)?%)?)|(?P<target>\d+(?:\.\d+)?%(?:-\d+(?:\.\d+)?%)?)) "
    r"(?P<cadence>\d+(?:-\d+)?rpm)"
    r"(?: (?P<flags>intensity=(?:warmup|recovery|interval|cooldown)))?"
    r"$"
)
_PERCENT_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)%")


@dataclass(frozen=True)
class WorkoutLoadEstimate:
    """Estimated mechanical and governance load for a planned workout."""

    planned_kj: int
    planned_if: float
    planned_load_kj: int
    duration_seconds: int
    segment_parse_status: str
    used_fallback_if_direct: bool
    if_ref_load: float
    if_ref_load_source: str
    warnings: tuple[str, ...]

    def as_dict(self) -> JsonMap:
        """Return a JSON-serializable estimate."""

        return {
            "planned_kj": self.planned_kj,
            "planned_if": self.planned_if,
            "planned_load_kj": self.planned_load_kj,
            "duration_seconds": self.duration_seconds,
            "segment_parse_status": self.segment_parse_status,
            "used_fallback_IF_direct": self.used_fallback_if_direct,
            "IF_ref_load": self.if_ref_load,
            "IF_ref_load_source": self.if_ref_load_source,
            "warnings": list(self.warnings),
        }


def estimate_workout_load(
    *,
    workout: JsonMap,
    agenda_entry: JsonMap | None = None,
    zone_model_payload: JsonMap | None = None,
    athlete_profile_payload: JsonMap | None = None,
    domain_hint: str | None = None,
) -> WorkoutLoadEstimate:
    """Estimate one workout's planned mechanical and governance load.

    Inputs:
        workout: WEEK_PLAN workout object with `workout_text` and metadata.
        agenda_entry: optional matching agenda row used for fallback duration
            and day-role domain hints.
        zone_model_payload: Zone Model envelope containing `ftp_watts`.
        athlete_profile_payload: Athlete Profile envelope for `IF_ref_load`.
        domain_hint: optional explicit intensity-domain fallback.

    Returns:
        WorkoutLoadEstimate with final-rounded values and trace flags.

    Errors:
        Raises ValueError for missing/invalid FTP or negative parsed duration.
    """

    ftp = extract_ftp_watts(zone_model_payload or {})
    if ftp is None:
        raise ValueError("missing_or_invalid_ftp")
    if_ref = resolve_if_ref_load(
        athlete_profile_payload=athlete_profile_payload,
        zone_model_payload=zone_model_payload,
    )
    workout_text = str(workout.get("workout_text") or "")
    segments = _parse_segments(workout_text)
    warnings: list[str] = []
    if segments:
        total_seconds = sum(duration for duration, _factor in segments)
        if total_seconds < 0:
            raise ValueError("negative_duration")
        if total_seconds == 0:
            return _zero_estimate(if_ref.value, if_ref.source)
        r_mean = sum(duration * factor for duration, factor in segments) / total_seconds
        r_eq = (sum(duration * (_clamp(factor, 0.0, 1.5) ** 4) for duration, factor in segments) / total_seconds) ** 0.25
        planned_if_raw = _clamp(r_eq, 0.0, 1.3)
        planned_kj_raw = ftp * r_mean * total_seconds / 1000.0
        planned_load_raw = planned_kj_raw * ((planned_if_raw / if_ref.value) ** ALPHA)
        return WorkoutLoadEstimate(
            planned_kj=int(round(planned_kj_raw)),
            planned_if=round(planned_if_raw, 3),
            planned_load_kj=int(round(planned_load_raw)),
            duration_seconds=int(round(total_seconds)),
            segment_parse_status="OK",
            used_fallback_if_direct=False,
            if_ref_load=if_ref.value,
            if_ref_load_source=if_ref.source,
            warnings=tuple(warnings),
        )

    fallback_seconds = _fallback_duration_seconds(workout, agenda_entry)
    if fallback_seconds < 0:
        raise ValueError("negative_duration")
    if fallback_seconds == 0:
        return _zero_estimate(if_ref.value, if_ref.source)
    domain = _domain_from_inputs(domain_hint=domain_hint, workout=workout, agenda_entry=agenda_entry)
    default_if = default_if_for_domain(domain, zone_model_payload or {})
    planned_if_raw = _clamp(default_if, 0.0, 1.3)
    planned_kj_raw = ftp * planned_if_raw * fallback_seconds / 1000.0
    planned_load_raw = planned_kj_raw * ((planned_if_raw / if_ref.value) ** ALPHA)
    warnings.append("used_IF_direct_fallback")
    return WorkoutLoadEstimate(
        planned_kj=int(round(planned_kj_raw)),
        planned_if=round(planned_if_raw, 3),
        planned_load_kj=int(round(planned_load_raw)),
        duration_seconds=int(round(fallback_seconds)),
        segment_parse_status="FAIL",
        used_fallback_if_direct=True,
        if_ref_load=if_ref.value,
        if_ref_load_source=if_ref.source,
        warnings=tuple(warnings),
    )


def estimate_week_plan_load(
    *,
    week_plan_payload: JsonMap,
    zone_model_payload: JsonMap | None = None,
    athlete_profile_payload: JsonMap | None = None,
) -> JsonMap:
    """Estimate deterministic workout loads for every workout in a WEEK_PLAN."""

    data = _as_map(week_plan_payload.get("data"))
    agenda = [_as_map(item) for item in _as_list(data.get("agenda"))]
    workouts = [_as_map(item) for item in _as_list(data.get("workouts"))]
    agenda_by_id = {
        str(row.get("workout_id")): row
        for row in agenda
        if row.get("workout_id") not in (None, "")
    }
    estimates: list[JsonMap] = []
    warnings: list[str] = []
    mechanical_total = 0
    governance_total = 0
    for workout in workouts:
        workout_id = str(workout.get("workout_id") or "")
        try:
            estimate = estimate_workout_load(
                workout=workout,
                agenda_entry=agenda_by_id.get(workout_id),
                zone_model_payload=zone_model_payload,
                athlete_profile_payload=athlete_profile_payload,
            )
        except ValueError as exc:
            warnings.append(f"{workout_id or 'UNKNOWN'}:{exc}")
            continue
        estimate_map = {"workout_id": workout_id, **estimate.as_dict()}
        estimates.append(estimate_map)
        mechanical_total += estimate.planned_kj
        governance_total += estimate.planned_load_kj
    summary = _as_map(data.get("week_summary"))
    planned = _as_float(summary.get("planned_weekly_load_kj"))
    return {
        "workouts": estimates,
        "mechanical_total_kj": mechanical_total,
        "estimated_planned_weekly_load_kj": governance_total,
        "declared_planned_weekly_load_kj": planned,
        "delta_to_declared_planned_weekly_load_kj": None if planned is None else int(round(governance_total - planned)),
        "warnings": warnings,
    }


def build_workout_load_method_context(
    *,
    athlete_profile_payload: JsonMap | None = None,
    zone_model_payload: JsonMap | None = None,
    allowed_intensity_domains: list[str] | None = None,
) -> JsonMap:
    """Build deterministic per-hour load calibration for prompt injection."""

    ftp = extract_ftp_watts(zone_model_payload or {})
    if_ref = resolve_if_ref_load(
        athlete_profile_payload=athlete_profile_payload,
        zone_model_payload=zone_model_payload,
    )
    domains = [str(item).strip().upper() for item in allowed_intensity_domains or [] if str(item).strip()]
    if not domains:
        domains = ["RECOVERY", "ENDURANCE", "TEMPO"]
    rows: list[JsonMap] = []
    warnings: list[str] = []
    if ftp is None:
        warnings.append("missing_or_invalid_ftp")
    else:
        for domain in domains:
            intensity = _clamp(default_if_for_domain(domain, zone_model_payload or {}), 0.0, 1.3)
            duration_seconds = 3600.0
            mechanical = ftp * intensity * duration_seconds / 1000.0
            governance = mechanical * ((intensity / if_ref.value) ** ALPHA) if if_ref.value > 0 else 0.0
            rows.append(
                {
                    "domain": domain,
                    "IF_default": round(intensity, 3),
                    "mechanical_kj_per_hour": int(round(mechanical)),
                    "governance_load_kj_per_hour": int(round(governance)),
                }
            )
    return {
        "unit_semantics": {
            "planned_kj": "mechanical_kj",
            "planned_weekly_load_kj": "governance_load_kj",
        },
        "ftp_watts": ftp,
        "IF_ref_load": if_ref.value,
        "IF_ref_load_source": if_ref.source,
        "alpha": ALPHA,
        "domain_hourly_estimates": rows,
        "warnings": warnings,
    }


def render_workout_load_method_context_block(context: JsonMap) -> str:
    """Render workout-load calibration context for planner prompts."""

    if not context:
        return ""
    lines = [
        "**Deterministic Workout Load Estimation Context**",
        "Use this code-owned calibration when assigning workout durations and loads. Do not invent separate kJ/load-kJ semantics.",
        f"ftp_watts: {context.get('ftp_watts')}",
        f"IF_ref_load: {context.get('IF_ref_load')} ({context.get('IF_ref_load_source')})",
        f"alpha: {context.get('alpha')}",
        "unit_semantics: planned_kj=mechanical_kj, planned_weekly_load_kj=governance_load_kj",
    ]
    rows = [_as_map(item) for item in _as_list(context.get("domain_hourly_estimates"))]
    if rows:
        lines.append("domain_hourly_estimates:")
        for row in rows:
            lines.append(
                f"- {row.get('domain')}: IF {row.get('IF_default')}, "
                f"mechanical {row.get('mechanical_kj_per_hour')} kJ/h, "
                f"governance {row.get('governance_load_kj_per_hour')} load-kJ/h"
            )
    warnings = [str(item) for item in _as_list(context.get("warnings")) if str(item).strip()]
    if warnings:
        lines.append("workout_load_warnings:")
        lines.extend(f"- {item}" for item in warnings)
    return "\n".join(lines) + "\n"


def _parse_segments(text: str) -> list[tuple[float, float]]:
    segments: list[tuple[float, float]] = []
    repeat = 1
    repeat_active = False
    for raw_line in (text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            if repeat_active:
                repeat = 1
                repeat_active = False
            continue
        if stripped in _SECTION_HEADERS:
            repeat = 1
            repeat_active = False
            continue
        loop_match = _LOOP_RE.fullmatch(stripped)
        if loop_match:
            repeat = int(loop_match.group("count"))
            repeat_active = True
            continue
        match = _STEP_RE.fullmatch(stripped)
        if not match:
            continue
        duration = match.group("duration")
        if not duration:
            continue
        factor = _target_factor(match.group("ramp") or match.group("target") or "")
        if factor is None:
            continue
        segments.append((_duration_token_to_seconds(duration) * max(repeat, 1), factor))
    return segments


def _target_factor(target: str) -> float | None:
    values = [float(match.group("value")) / 100.0 for match in _PERCENT_RE.finditer(target or "")]
    if not values:
        return None
    return sum(values) / len(values)


def _duration_token_to_seconds(token: str) -> float:
    if re.fullmatch(r"\d+m\d+", token):
        minutes, seconds = token.split("m", 1)
        return float(minutes) * 60.0 + float(seconds)
    total = 0.0
    hours_match = re.search(r"(?P<hours>\d+(?:\.\d+)?)h", token)
    if hours_match:
        total += float(hours_match.group("hours")) * 3600.0
    minutes_match = re.search(r"(?P<minutes>\d+(?:\.\d+)?)m", token)
    if minutes_match:
        total += float(minutes_match.group("minutes")) * 60.0
    seconds_match = re.search(r"(?P<seconds>\d+(?:\.\d+)?)s", token)
    if seconds_match:
        total += float(seconds_match.group("seconds"))
    return total


def _fallback_duration_seconds(workout: JsonMap, agenda_entry: JsonMap | None) -> int:
    text_seconds = derive_workout_duration_seconds(str(workout.get("workout_text") or ""))
    if text_seconds > 0:
        return text_seconds
    workout_seconds = _hhmmss_to_seconds(str(workout.get("duration") or ""))
    if workout_seconds > 0:
        return workout_seconds
    return _hhmm_to_seconds(str(_as_map(agenda_entry).get("planned_duration") or ""))


def _domain_from_inputs(*, domain_hint: str | None, workout: JsonMap, agenda_entry: JsonMap | None) -> str:
    candidates = [
        domain_hint,
        _as_map(agenda_entry).get("day_role"),
        workout.get("notes"),
        workout.get("title"),
    ]
    text = " ".join(str(item or "") for item in candidates).upper()
    if "RECOVERY" in text or "REST" in text:
        return "RECOVERY"
    if "TEMPO" in text:
        return "TEMPO"
    if "SWEET" in text:
        return "SWEET_SPOT"
    if "THRESHOLD" in text:
        return "THRESHOLD"
    if "VO2" in text:
        return "VO2MAX"
    if "ANAEROBIC" in text:
        return "ANAEROBIC"
    if "QUALITY" in text:
        return "TEMPO"
    if "ENDURANCE" in text:
        return "ENDURANCE"
    return "ENDURANCE"


def _zero_estimate(if_ref_load: float, if_ref_load_source: str) -> WorkoutLoadEstimate:
    return WorkoutLoadEstimate(
        planned_kj=0,
        planned_if=0.0,
        planned_load_kj=0,
        duration_seconds=0,
        segment_parse_status="OK",
        used_fallback_if_direct=False,
        if_ref_load=if_ref_load,
        if_ref_load_source=if_ref_load_source,
        warnings=(),
    )


def _hhmmss_to_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = [int(part) for part in parts]
    except ValueError:
        return 0
    return max(0, hours * 3600 + minutes * 60 + seconds)


def _hhmm_to_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        return 0
    try:
        hours, minutes = [int(part) for part in parts]
    except ValueError:
        return 0
    return max(0, (hours * 60 + minutes) * 60)


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
