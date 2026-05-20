"""Derive protocol progression signatures from persisted week-plan workouts."""

from __future__ import annotations

import re
from typing import Any

from rps.workouts.structured import WorkoutLoop, WorkoutSection, WorkoutStep, parse_workout_text

JsonMap = dict[str, Any]


def extract_progression_signatures_from_week_plan(week_plan_payload: JsonMap) -> list[JsonMap]:
    """Return inferred progression signatures from a persisted WEEK_PLAN payload."""

    data = week_plan_payload.get("data")
    if not isinstance(data, dict):
        return []
    workouts = data.get("workouts")
    if not isinstance(workouts, list):
        return []
    signatures: list[JsonMap] = []
    for item in workouts:
        if not isinstance(item, dict):
            continue
        signature = _infer_signature(item)
        if signature:
            signatures.append(signature)
    return signatures


def match_progression_signature(
    *,
    signatures: list[JsonMap],
    protocol_type: str,
    protocol_variant: str,
    workout_family: str,
    day_role: str,
) -> JsonMap | None:
    """Return the best-matching prior progression signature for a new workout blueprint."""

    variant = protocol_variant.strip().upper()
    ptype = protocol_type.strip().upper()
    family = workout_family.strip().upper()
    role = day_role.strip().upper()
    best: tuple[int, JsonMap] | None = None
    for candidate in signatures:
        score = 0
        if str(candidate.get("protocol_type") or "").upper() != ptype:
            continue
        if str(candidate.get("day_role") or "").upper() == role:
            score += 1
        if str(candidate.get("workout_family") or "").upper() == family:
            score += 2
        if str(candidate.get("protocol_variant_guess") or "").upper() == variant:
            score += 5
        if variant.startswith("VO2_") and str(candidate.get("protocol_variant_guess") or "").upper().startswith("VO2_"):
            score += 2
        if "SWEET_SPOT" in variant and "SWEET_SPOT" in str(candidate.get("protocol_variant_guess") or "").upper():
            score += 2
        if "TEMPO" in variant and "TEMPO" in str(candidate.get("protocol_variant_guess") or "").upper():
            score += 2
        if "THRESHOLD" in variant and "THRESHOLD" in str(candidate.get("protocol_variant_guess") or "").upper():
            score += 2
        if best is None or score > best[0]:
            best = (score, candidate)
    return dict(best[1]) if best and best[0] > 0 else None


def _infer_signature(workout: JsonMap) -> JsonMap | None:
    title = str(workout.get("title") or "")
    notes = str(workout.get("notes") or "")
    text = str(workout.get("workout_text") or "").strip()
    day_role = _infer_day_role(title=title, notes=notes)
    if not text:
        return None
    try:
        structure = parse_workout_text(text, context_text=f"{title}\n{notes}")
    except Exception:
        return None
    main = _find_section(structure.sections, "Main Set")
    if main is None:
        return None
    title_key = f"{title}\n{notes}".upper()
    if any(isinstance(block, WorkoutLoop) and _loop_is_microburst(block) for block in main.blocks):
        loops = [block for block in main.blocks if isinstance(block, WorkoutLoop) and _loop_is_microburst(block)]
        first = loops[0]
        work_seconds = _duration_seconds(first.steps[0].duration)
        recovery_seconds = _duration_seconds(first.steps[1].duration)
        reps = [block.count for block in loops]
        return {
            "protocol_type": "MICROBURST_SETS",
            "protocol_variant_guess": _microburst_variant_guess(work_seconds, recovery_seconds),
            "workout_family": "VO2MAX",
            "day_role": day_role,
            "set_count": len(reps),
            "reps_per_set": reps,
            "work_duration_seconds": work_seconds,
            "recovery_duration_seconds": recovery_seconds,
            "total_reps": sum(reps),
            "tiz_minutes": int(round(sum(reps) * work_seconds / 60.0)),
        }
    if any(isinstance(block, WorkoutLoop) and _loop_is_over_under(block) for block in main.blocks) or "OVER/UNDER" in title_key:
        loop = next((block for block in main.blocks if isinstance(block, WorkoutLoop) and _loop_is_over_under(block)), None)
        if loop is None:
            return None
        under = _duration_minutes(loop.steps[0].duration)
        over = _duration_minutes(loop.steps[1].duration)
        return {
            "protocol_type": "OVER_UNDER_INTERVALS",
            "protocol_variant_guess": "TEMPO_OVER_UNDER",
            "workout_family": "TEMPO",
            "day_role": day_role,
            "oscillation_count": loop.count,
            "under_duration_minutes": under,
            "over_duration_minutes": over,
            "tiz_minutes": loop.count * (under + over),
        }
    if any(isinstance(block, WorkoutLoop) for block in main.blocks):
        loop = next(block for block in main.blocks if isinstance(block, WorkoutLoop))
        work = _duration_minutes(loop.steps[0].duration)
        recovery = _duration_minutes(loop.steps[1].duration) if len(loop.steps) > 1 else 0
        cadence = loop.steps[0].cadence
        family = _family_guess(title_key, loop.steps[0].target, cadence)
        protocol_type = "STRENGTH_ENDURANCE_INTERVALS" if family == "K3" else "CLASSIC_INTERVALS"
        return {
            "protocol_type": protocol_type,
            "protocol_variant_guess": _classic_variant_guess(title_key, family),
            "workout_family": "ENDURANCE" if family == "K3" else family,
            "day_role": day_role,
            "set_count": loop.count,
            "work_duration_minutes": work,
            "recovery_duration_minutes": recovery,
            "tiz_minutes": loop.count * work,
        }
    step_blocks = [block for block in main.blocks if isinstance(block, WorkoutStep)]
    if len(step_blocks) >= 2:
        first_target = _target_midpoint(step_blocks[0].target)
        second_target = _target_midpoint(step_blocks[1].target)
        if second_target > first_target:
            return {
                "protocol_type": "FATIGUE_FINISH",
                "protocol_variant_guess": "ENDURANCE_PREFATIGUE_FINISH" if "PRE-FATIGUE" in title_key else "ENDURANCE_FATIGUE_FINISH",
                "workout_family": "ENDURANCE",
                "day_role": day_role,
                "preload_minutes": _duration_minutes(step_blocks[0].duration),
                "finish_minutes": _duration_minutes(step_blocks[1].duration),
                "tiz_minutes": _duration_minutes(step_blocks[1].duration),
            }
    if len(step_blocks) == 1:
        return {
            "protocol_type": "LONG_STEADY",
            "protocol_variant_guess": _long_steady_variant_guess(title_key, step_blocks[0].target),
            "workout_family": _family_guess(title_key, step_blocks[0].target, step_blocks[0].cadence),
            "day_role": day_role,
            "main_duration_minutes": _duration_minutes(step_blocks[0].duration),
            "tiz_minutes": _duration_minutes(step_blocks[0].duration),
        }
    return None


def _find_section(sections: tuple[WorkoutSection, ...], name: str) -> WorkoutSection | None:
    for section in sections:
        if section.name == name:
            return section
    return None


def _infer_day_role(*, title: str, notes: str) -> str:
    text = f"{title}\n{notes}".upper()
    if "RECOVERY" in text:
        return "RECOVERY"
    if any(token in text for token in ("SWEET SPOT", "TEMPO", "THRESHOLD", "VO2", "K3", "QUALITY")):
        return "QUALITY"
    return "ENDURANCE"


def _loop_is_microburst(loop: WorkoutLoop) -> bool:
    return len(loop.steps) == 2 and all(_is_seconds(step.duration) for step in loop.steps)


def _loop_is_over_under(loop: WorkoutLoop) -> bool:
    return (
        len(loop.steps) == 2
        and all(not _is_seconds(step.duration) for step in loop.steps)
        and _target_midpoint(loop.steps[1].target) > _target_midpoint(loop.steps[0].target)
        and _target_midpoint(loop.steps[0].target) >= 0.9
    )


def _classic_variant_guess(title_key: str, family: str) -> str:
    if family == "THRESHOLD":
        return "THRESHOLD_CLASSIC"
    if family == "SWEET_SPOT":
        return "SWEET_SPOT_CLASSIC"
    if family == "K3":
        return "K3_CLASSIC"
    if family == "VO2MAX":
        return "VO2_LONG_INTERVALS"
    return "TEMPO_CLASSIC"


def _long_steady_variant_guess(title_key: str, target: str) -> str:
    if "TEMPO STEADY" in title_key or "BREVET" in title_key:
        return "TEMPO_STEADY_BREVET"
    if "LOW-END" in title_key or _target_midpoint(target) <= 0.65:
        return "ENDURANCE_LOW"
    if "LONG ENDURANCE" in title_key or "ANCHOR" in title_key:
        return "ENDURANCE_LONG_STEADY"
    return "ENDURANCE_STEADY"


def _microburst_variant_guess(work_seconds: int, recovery_seconds: int) -> str:
    if work_seconds == 20 and recovery_seconds == 10:
        return "VO2_20_10"
    if work_seconds == 40 and recovery_seconds == 20:
        return "VO2_40_20"
    return "VO2_30_15"


def _family_guess(title_key: str, target: str, cadence: str) -> str:
    if "THRESHOLD" in title_key or _target_midpoint(target) >= 0.95:
        return "THRESHOLD"
    if "SWEET SPOT" in title_key or 0.88 <= _target_midpoint(target) <= 0.94:
        return "SWEET_SPOT"
    if "VO2" in title_key or _target_midpoint(target) >= 1.05:
        return "VO2MAX"
    if "K3" in title_key or _cadence_min(cadence) <= 60:
        return "K3"
    if "TEMPO" in title_key or 0.8 <= _target_midpoint(target) < 0.88:
        return "TEMPO"
    return "ENDURANCE"


def _duration_minutes(token: str) -> int:
    return int(round(_duration_seconds(token) / 60.0))


def _duration_seconds(token: str) -> int:
    total = 0.0
    for value, suffix in re.findall(r"(\d+(?:\.\d+)?)([hms])", token):
        scalar = float(value)
        if suffix == "h":
            total += scalar * 3600.0
        elif suffix == "m":
            total += scalar * 60.0
        else:
            total += scalar
    return int(round(total))


def _is_seconds(token: str) -> bool:
    return token.endswith("s") and "m" not in token and "h" not in token


def _target_midpoint(target: str) -> float:
    values = [float(value) / 100.0 for value in re.findall(r"(\d+(?:\.\d+)?)%", target)]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _cadence_min(cadence: str) -> int:
    match = re.match(r"(?P<low>\d+)(?:-\d+)?rpm", cadence)
    return int(match.group("low")) if match else 999
