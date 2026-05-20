"""Protocol-driven deterministic workout solving and rendering helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from rps.workouts.structured import WorkoutLoop, WorkoutSection, WorkoutStep, WorkoutStructure

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class SolvedWorkout:
    """Solved protocol instance ready for export rendering."""

    title: str
    notes: str
    structure: WorkoutStructure


def solve_protocol_workout(spec: Any) -> SolvedWorkout:
    """Solve one concrete workout protocol instance from blueprint render metadata."""

    protocol_type = str(spec.protocol_type or "").upper()
    if protocol_type == "LONG_STEADY":
        return _solve_long_steady(spec)
    if protocol_type == "CLASSIC_INTERVALS":
        return _solve_classic_intervals(spec)
    if protocol_type == "MICROBURST_SETS":
        return _solve_microburst_sets(spec)
    if protocol_type == "OVER_UNDER_INTERVALS":
        return _solve_over_under_intervals(spec)
    if protocol_type == "STRENGTH_ENDURANCE_INTERVALS":
        return _solve_strength_endurance(spec)
    if protocol_type == "FATIGUE_FINISH":
        return _solve_fatigue_finish(spec)
    if protocol_type == "RAMP_INTERVALS":
        return _solve_ramp_intervals(spec)
    if protocol_type == "DAY_TYPE_ONLY":
        raise ValueError(f"Protocol '{spec.protocol_variant or spec.workout_id}' is a day-type-only definition and cannot render workout_text.")
    raise ValueError(f"Unsupported protocol_type '{protocol_type}' for {spec.workout_id}.")


def _solve_long_steady(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or (6 if spec.low_end_endurance else 8))
    cool = int(params.get("cooldown_minutes") or 8)
    total = max(spec.planned_duration_minutes, warm + cool + 10)
    main = max(total - warm - cool, 10)
    structure = WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-75%" if warm >= 10 else "ramp 50%-65%", "85-95rpm"),)),
            WorkoutSection("Main Set", (WorkoutStep(_minutes_token(main), str(params.get("main_target") or ("60%-65%" if spec.low_end_endurance else "68%-72%")), str(params.get("main_cadence") or "85-90rpm")),)),
            WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)),
        )
    )
    return SolvedWorkout(
        title=_title_for_protocol(spec),
        notes=_notes_for_protocol(spec),
        structure=structure,
    )


def _solve_classic_intervals(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or 10)
    cool = int(params.get("cooldown_minutes") or 8)
    activation_profile = str(params.get("activation_profile") or "").strip().upper()
    activation_minutes = 3 if activation_profile else 0
    target_tiz = int(spec.primary_tiz_target_min or params.get("tiz_min_minutes") or 0)
    work_min, recovery_min, sets = _solve_classic_interval_distribution(
        target_tiz=max(target_tiz, 1),
        set_count_min=int(params.get("set_count_min") or 1),
        set_count_max=int(params.get("set_count_max") or 5),
        work_duration_min=int(params.get("work_duration_min_minutes") or 1),
        work_duration_max=int(params.get("work_duration_max_minutes") or 60),
        recovery_duration=int(params.get("recovery_duration_minutes") or 3),
        preferred_primary_axis=str(spec.progression_state.get("primary_axis") or ""),
        preferred_secondary_axis=str(spec.progression_state.get("secondary_axis") or ""),
        previous_signature=_previous_signature(spec),
    )
    main_blocks: list[WorkoutLoop | WorkoutStep] = [
        WorkoutLoop(
            sets,
            (
                WorkoutStep(f"{work_min}m", str(params.get("work_target") or "88%-92%"), str(params.get("work_cadence") or "85-90rpm")),
                WorkoutStep(f"{recovery_min}m", str(params.get("recovery_target") or "60%-65%"), str(params.get("recovery_cadence") or "85-90rpm")),
            ),
        )
    ]
    primary_used = sets * work_min + sets * recovery_min
    addon_minutes = _solve_addon_minutes(spec=spec, primary_minutes=primary_used + warm + cool + activation_minutes)
    sections: list[WorkoutSection] = [WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-75%", "85-95rpm"),))]
    if activation_profile:
        sections.append(_activation_section(activation_profile))
    sections.append(WorkoutSection("Main Set", tuple(main_blocks)))
    if addon_minutes > 0:
        sections.append(_z2_addon_section(spec=spec, addon_minutes=addon_minutes))
    sections.append(WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)))
    return SolvedWorkout(title=_title_for_protocol(spec), notes=_notes_for_protocol(spec), structure=WorkoutStructure(tuple(sections)))


def _solve_strength_endurance(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or 10)
    cool = int(params.get("cooldown_minutes") or 8)
    target_tiz = int(spec.primary_tiz_target_min or params.get("tiz_min_minutes") or 24)
    work_min, recovery_min, sets = _solve_classic_interval_distribution(
        target_tiz=target_tiz,
        set_count_min=int(params.get("set_count_min") or 3),
        set_count_max=int(params.get("set_count_max") or 5),
        work_duration_min=int(params.get("work_duration_min_minutes") or 6),
        work_duration_max=int(params.get("work_duration_max_minutes") or 10),
        recovery_duration=int(params.get("recovery_duration_minutes") or 3),
        preferred_primary_axis="work_duration",
        preferred_secondary_axis="set_count",
        previous_signature=_previous_signature(spec),
    )
    primary_used = sets * work_min + sets * recovery_min
    addon_minutes = _solve_addon_minutes(spec=spec, primary_minutes=primary_used + warm + cool)
    sections = [
        WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-75%", "85-95rpm"),)),
        WorkoutSection(
            "Main Set",
            (
                WorkoutLoop(
                    sets,
                    (
                        WorkoutStep(f"{work_min}m", str(params.get("work_target") or "85%-90%"), str(params.get("work_cadence") or "50-60rpm")),
                        WorkoutStep(f"{recovery_min}m", str(params.get("recovery_target") or "55%-60%"), str(params.get("recovery_cadence") or "85rpm")),
                    ),
                ),
            ),
        ),
    ]
    if addon_minutes > 0:
        sections.append(_z2_addon_section(spec=spec, addon_minutes=addon_minutes))
    sections.append(WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)))
    return SolvedWorkout(title=_title_for_protocol(spec), notes=_notes_for_protocol(spec), structure=WorkoutStructure(tuple(sections)))


def _solve_over_under_intervals(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or 8)
    cool = int(params.get("cooldown_minutes") or 8)
    under_minutes = int(params.get("under_duration_minutes") or 3)
    over_minutes = int(params.get("over_duration_minutes") or 1)
    oscillation_min = int(params.get("oscillation_count_min") or 4)
    oscillation_max = int(params.get("oscillation_count_max") or 8)
    target_tiz = int(spec.primary_tiz_target_min or params.get("tiz_min_minutes") or ((under_minutes + over_minutes) * oscillation_min))
    per_oscillation = max(under_minutes + over_minutes, 1)
    previous = _previous_signature(spec)
    oscillations = min(oscillation_max, max(oscillation_min, (target_tiz + per_oscillation - 1) // per_oscillation))
    previous_oscillations = int(previous.get("oscillation_count") or 0)
    previous_tiz = int(previous.get("tiz_minutes") or 0)
    if previous_oscillations and target_tiz >= previous_tiz:
        oscillations = max(oscillations, previous_oscillations)
        while oscillations < oscillation_max and oscillations * per_oscillation < target_tiz:
            oscillations += 1
    primary_used = warm + cool + oscillations * per_oscillation
    addon_minutes = _solve_addon_minutes(spec=spec, primary_minutes=primary_used)
    sections: list[WorkoutSection] = [
        WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-75%", "85-95rpm"),)),
        WorkoutSection(
            "Main Set",
            (
                WorkoutLoop(
                    oscillations,
                    (
                        WorkoutStep(f"{under_minutes}m", str(params.get("under_target") or "95%"), str(params.get("under_cadence") or "85-90rpm")),
                        WorkoutStep(f"{over_minutes}m", str(params.get("over_target") or "105%"), str(params.get("over_cadence") or "90rpm")),
                    ),
                ),
            ),
        ),
    ]
    if addon_minutes > 0:
        sections.append(_z2_addon_section(spec=spec, addon_minutes=addon_minutes))
    sections.append(WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)))
    return SolvedWorkout(title=_title_for_protocol(spec), notes=_notes_for_protocol(spec), structure=WorkoutStructure(tuple(sections)))


def _solve_microburst_sets(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or 10)
    cool = int(params.get("cooldown_minutes") or 8)
    activation_profile = str(params.get("activation_profile") or "VO2_STANDARD").strip().upper()
    activation_minutes = 3 if activation_profile else 0
    work_seconds = int(params.get("work_duration_seconds") or 30)
    recovery_seconds = int(params.get("recovery_duration_seconds") or 15)
    target_tiz = int(spec.primary_tiz_target_min or params.get("tiz_min_minutes") or 12)
    total_reps = max(1, int(round(target_tiz * 60 / work_seconds)))
    previous = _previous_signature(spec)
    set_count, reps_per_set = _solve_microburst_distribution(
        total_reps=total_reps,
        set_count_min=int(params.get("set_count_min") or 2),
        set_count_max=int(params.get("set_count_max") or 4),
        reps_per_set_min=int(params.get("reps_per_set_min") or 8),
        reps_per_set_max=int(params.get("reps_per_set_max") or 15),
        preferred_set_count=len(list(params.get("work_target_by_set") or [])) or None,
        previous_signature=previous,
        preferred_primary_axis=str(spec.progression_state.get("primary_axis") or ""),
        preferred_secondary_axis=str(spec.progression_state.get("secondary_axis") or ""),
        protocol_variant=str(spec.protocol_variant or ""),
        work_seconds=work_seconds,
        recovery_seconds=recovery_seconds,
    )
    blocks: list[WorkoutLoop | WorkoutStep] = []
    target_by_set = list(params.get("work_target_by_set") or [])
    work_target = str(params.get("work_target") or "115%")
    for idx in range(set_count):
        target = str(target_by_set[idx]) if idx < len(target_by_set) else work_target
        blocks.append(
            WorkoutLoop(
                reps_per_set[idx],
                (
                    WorkoutStep(f"{work_seconds}s", target, str(params.get("work_cadence") or "92-95rpm")),
                    WorkoutStep(f"{recovery_seconds}s", str(params.get("recovery_target") or "50%"), str(params.get("recovery_cadence") or "85rpm")),
                ),
            )
        )
        if idx < set_count - 1:
            blocks.append(
                WorkoutStep(
                    f"{int(params.get('between_set_recovery_minutes') or 3)}m",
                    str(params.get("between_set_recovery_target") or "55%"),
                    str(params.get("between_set_recovery_cadence") or "85rpm"),
                )
            )
    primary_minutes = sum(reps_per_set) * (work_seconds + recovery_seconds) / 60
    primary_minutes += (set_count - 1) * int(params.get("between_set_recovery_minutes") or 3)
    addon_minutes = _solve_addon_minutes(spec=spec, primary_minutes=int(round(primary_minutes)) + warm + cool + activation_minutes)
    sections = [WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-75%", "85-95rpm"),))]
    if activation_profile:
        sections.append(_activation_section(activation_profile))
    sections.append(WorkoutSection("Main Set", tuple(blocks)))
    if addon_minutes > 0:
        sections.append(_z2_addon_section(spec=spec, addon_minutes=addon_minutes))
    sections.append(WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)))
    return SolvedWorkout(title=_title_for_protocol(spec), notes=_notes_for_protocol(spec), structure=WorkoutStructure(tuple(sections)))


def _solve_ramp_intervals(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or 8)
    cool = int(params.get("cooldown_minutes") or 8)
    work_min, recovery_min, sets = _solve_classic_interval_distribution(
        target_tiz=int(spec.primary_tiz_target_min or params.get("tiz_min_minutes") or 16),
        set_count_min=int(params.get("set_count_min") or 3),
        set_count_max=int(params.get("set_count_max") or 5),
        work_duration_min=int(params.get("work_duration_min_minutes") or 6),
        work_duration_max=int(params.get("work_duration_max_minutes") or 8),
        recovery_duration=int(params.get("recovery_duration_minutes") or 3),
        preferred_primary_axis="set_count",
        preferred_secondary_axis="work_duration",
        previous_signature=_previous_signature(spec),
    )
    structure = WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-75%", "85-95rpm"),)),
            WorkoutSection(
                "Main Set",
                (
                    WorkoutLoop(
                        sets,
                        (
                            WorkoutStep(f"{work_min}m", str(params.get("work_target") or "ramp 95%-112%"), str(params.get("work_cadence") or "90-95rpm")),
                            WorkoutStep(f"{recovery_min}m", str(params.get("recovery_target") or "55%"), str(params.get("recovery_cadence") or "85rpm")),
                        ),
                    ),
                ),
            ),
            WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)),
        )
    )
    return SolvedWorkout(title=_title_for_protocol(spec), notes=_notes_for_protocol(spec), structure=structure)


def _solve_fatigue_finish(spec: Any) -> SolvedWorkout:
    params = spec.progression_parameters
    warm = int(params.get("warmup_minutes") or 8)
    cool = int(params.get("cooldown_minutes") or 8)
    preload_min = int(params.get("preload_min_minutes") or 120)
    finish_min = int(params.get("finish_min_minutes") or 20)
    finish_max = int(params.get("finish_max_minutes") or 60)
    usable = max(spec.planned_duration_minutes - warm - cool, preload_min + finish_min)
    finish = min(finish_max, max(finish_min, usable - preload_min))
    preload = max(usable - finish, preload_min)
    structure = WorkoutStructure(
        sections=(
            WorkoutSection("Warmup", (WorkoutStep(f"{warm}m", "ramp 50%-65%", "85-95rpm"),)),
            WorkoutSection(
                "Main Set",
                (
                    WorkoutStep(_minutes_token(preload), str(params.get("preload_target") or "68%-72%"), str(params.get("preload_cadence") or "85-90rpm")),
                    WorkoutStep(_minutes_token(finish), str(params.get("finish_target") or "82%-88%"), str(params.get("finish_cadence") or "88rpm")),
                ),
            ),
            WorkoutSection("Cooldown", (WorkoutStep(f"{cool}m", "ramp 60%-45%", "80-85rpm"),)),
        )
    )
    return SolvedWorkout(title=_title_for_protocol(spec), notes=_notes_for_protocol(spec), structure=structure)


def _solve_classic_interval_distribution(
    *,
    target_tiz: int,
    set_count_min: int,
    set_count_max: int,
    work_duration_min: int,
    work_duration_max: int,
    recovery_duration: int,
    preferred_primary_axis: str,
    preferred_secondary_axis: str,
    previous_signature: JsonMap | None,
) -> tuple[int, int, int]:
    previous = previous_signature or {}
    previous_sets = int(previous.get("set_count") or 0)
    previous_work = int(previous.get("work_duration_minutes") or 0)
    previous_tiz = int(previous.get("tiz_minutes") or 0)
    if previous_sets and previous_work:
        previous_sets = min(max(previous_sets, set_count_min), set_count_max)
        previous_work = min(max(previous_work, work_duration_min), work_duration_max)
        if target_tiz > previous_tiz and preferred_primary_axis == "work_duration":
            work = previous_work
            while work < work_duration_max and previous_sets * work < target_tiz:
                work += 1
            if previous_sets * work >= target_tiz:
                return work, recovery_duration, previous_sets
            if preferred_secondary_axis in {"set_redistribution", "set_count"}:
                progressed = _redistribute_sets_for_tiz(
                    target_tiz=target_tiz,
                    current_sets=previous_sets,
                    set_count_max=set_count_max,
                    work_duration_min=work_duration_min,
                    work_duration_max=work_duration_max,
                )
                if progressed is not None:
                    progressed_work, progressed_sets = progressed
                    return progressed_work, recovery_duration, progressed_sets
        if (
            target_tiz == previous_tiz
            and preferred_secondary_axis == "set_redistribution"
            and previous_work >= work_duration_max
            and previous_sets < set_count_max
        ):
            redistributed_sets = previous_sets + 1
            redistributed_work = min(work_duration_max, max(work_duration_min, math.ceil(target_tiz / redistributed_sets)))
            return redistributed_work, recovery_duration, redistributed_sets
    best: tuple[int, int, int, int] | None = None
    for sets in range(set_count_min, set_count_max + 1):
        for work in range(work_duration_min, work_duration_max + 1):
            tiz = sets * work
            if tiz < target_tiz:
                continue
            score = (tiz - target_tiz) * 100
            if preferred_primary_axis == "work_duration":
                score += abs(work - min(work_duration_max, max(work_duration_min, target_tiz // max(sets, 1))))
            if preferred_secondary_axis == "set_redistribution":
                score += sets * 2
            elif preferred_secondary_axis == "set_count":
                score += sets
            total = sets * (work + recovery_duration)
            candidate = (score, total, work, sets)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        sets = set_count_max
        work = work_duration_max
    else:
        _, _, work, sets = best
    return work, recovery_duration, sets


def _solve_microburst_distribution(
    *,
    total_reps: int,
    set_count_min: int,
    set_count_max: int,
    reps_per_set_min: int,
    reps_per_set_max: int,
    preferred_set_count: int | None,
    previous_signature: JsonMap | None,
    preferred_primary_axis: str,
    preferred_secondary_axis: str,
    protocol_variant: str,
    work_seconds: int,
    recovery_seconds: int,
) -> tuple[int, list[int]]:
    previous = previous_signature or {}
    previous_reps_raw = previous.get("reps_per_set")
    previous_reps = [int(item) for item in previous_reps_raw] if isinstance(previous_reps_raw, list) and previous_reps_raw else []
    if (
        previous_reps
        and int(previous.get("work_duration_seconds") or 0) == work_seconds
        and int(previous.get("recovery_duration_seconds") or 0) == recovery_seconds
    ):
        progressed = _progress_microburst_from_previous(
            previous_reps=previous_reps,
            target_total_reps=total_reps,
            set_count_min=set_count_min,
            set_count_max=set_count_max,
            reps_per_set_min=reps_per_set_min,
            reps_per_set_max=reps_per_set_max,
            preferred_primary_axis=preferred_primary_axis,
            preferred_secondary_axis=preferred_secondary_axis,
            protocol_variant=protocol_variant,
        )
        if progressed is not None:
            return len(progressed), progressed
    best: tuple[int, int, int] | None = None
    best_distribution: list[int] = []
    for set_count in range(set_count_min, set_count_max + 1):
        base = total_reps // set_count
        remainder = total_reps % set_count
        reps = [base + (1 if idx < remainder else 0) for idx in range(set_count)]
        if any(rep < reps_per_set_min or rep > reps_per_set_max for rep in reps):
            continue
        spread = max(reps) - min(reps)
        preference_penalty = abs(set_count - preferred_set_count) if preferred_set_count is not None else 0
        score = (preference_penalty, spread, set_count, max(reps))
        if best is None or score < best:
            best = score
            best_distribution = reps
    if not best_distribution:
        set_count = min(max(set_count_min, (total_reps + reps_per_set_max - 1) // reps_per_set_max), set_count_max)
        base = total_reps // max(set_count, 1)
        remainder = total_reps % max(set_count, 1)
        best_distribution = [min(reps_per_set_max, base + (1 if idx < remainder else 0)) for idx in range(set_count)]
        return set_count, best_distribution
    return len(best_distribution), best_distribution


def _solve_addon_minutes(*, spec: Any, primary_minutes: int) -> int:
    params = spec.progression_parameters
    addon_policy = str(spec.addon_policy or "NONE").upper()
    if addon_policy == "NONE":
        return 0
    total = max(spec.planned_duration_minutes, primary_minutes)
    remaining = total - primary_minutes
    if remaining <= 0:
        return 0
    min_block = int(params.get("addon_min_block_minutes") or 10)
    step = int(params.get("addon_step_minutes") or 5)
    max_share = float(params.get("addon_max_share_of_session") or 0.45)
    max_allowed = int(total * max_share)
    return max(0, min((remaining // step) * step, max_allowed, int(params.get("addon_max_block_minutes") or remaining), max(remaining, 0))) if remaining >= min_block else 0


def _z2_addon_section(*, spec: Any, addon_minutes: int) -> WorkoutSection:
    params = spec.progression_parameters
    target = str(params.get("addon_target") or "68%-72%")
    cadence = str(params.get("addon_cadence") or "85-95rpm")
    return WorkoutSection("#### Z2 Add-On", (WorkoutStep(_minutes_token(addon_minutes), target, cadence),))


def _previous_signature(spec: Any) -> JsonMap:
    payload = spec.progression_state.get("previous_signature")
    return payload if isinstance(payload, dict) else {}


def _redistribute_sets_for_tiz(
    *,
    target_tiz: int,
    current_sets: int,
    set_count_max: int,
    work_duration_min: int,
    work_duration_max: int,
) -> tuple[int, int] | None:
    next_sets = current_sets + 1
    if next_sets > set_count_max:
        return None
    work = math.ceil(target_tiz / next_sets)
    if work_duration_min <= work <= work_duration_max:
        return work, next_sets
    return None


def _progress_microburst_from_previous(
    *,
    previous_reps: list[int],
    target_total_reps: int,
    set_count_min: int,
    set_count_max: int,
    reps_per_set_min: int,
    reps_per_set_max: int,
    preferred_primary_axis: str,
    preferred_secondary_axis: str,
    protocol_variant: str,
) -> list[int] | None:
    reps = list(previous_reps)
    previous_total = sum(reps)
    practical_reps_ceiling = min(reps_per_set_max, 13 if "VO2_40_20" in protocol_variant.upper() or "VO2_30_15" in protocol_variant.upper() else reps_per_set_max)
    if target_total_reps > previous_total and preferred_primary_axis == "reps":
        while sum(reps) < target_total_reps and max(reps) < practical_reps_ceiling:
            for idx in range(len(reps)):
                if reps[idx] >= practical_reps_ceiling or sum(reps) >= target_total_reps:
                    continue
                reps[idx] += 1
        if sum(reps) >= target_total_reps:
            return reps
        if preferred_secondary_axis == "sets" and len(reps) < set_count_max:
            preferred_sets = len(reps) + 1
            return _balanced_reps_distribution(
                total_reps=max(target_total_reps, previous_total),
                set_count=max(set_count_min, preferred_sets),
                reps_per_set_min=reps_per_set_min,
                reps_per_set_max=reps_per_set_max,
            )
    if (
        target_total_reps == previous_total
        and preferred_secondary_axis == "sets"
        and len(reps) < set_count_max
        and max(previous_reps) >= practical_reps_ceiling
    ):
        return _balanced_reps_distribution(
            total_reps=target_total_reps,
            set_count=max(set_count_min, len(reps) + 1),
            reps_per_set_min=reps_per_set_min,
            reps_per_set_max=reps_per_set_max,
        )
    return None


def _balanced_reps_distribution(
    *,
    total_reps: int,
    set_count: int,
    reps_per_set_min: int,
    reps_per_set_max: int,
) -> list[int] | None:
    base = total_reps // set_count
    remainder = total_reps % set_count
    reps = [base + (1 if idx < remainder else 0) for idx in range(set_count)]
    if any(rep < reps_per_set_min or rep > reps_per_set_max for rep in reps):
        return None
    return reps


def _activation_section(profile: str) -> WorkoutSection:
    if profile in {"VO2_STANDARD", "SWEET_SPOT_STANDARD", "THRESHOLD_STANDARD"}:
        return WorkoutSection(
            "#### Activation",
            (
                WorkoutLoop(
                    3,
                    (
                        WorkoutStep("20s", "120%", "95rpm"),
                        WorkoutStep("40s", "60%", "85rpm"),
                    ),
                ),
            ),
        )
    return WorkoutSection(
        "#### Activation",
        (
            WorkoutLoop(
                3,
                (
                    WorkoutStep("20s", "120%", "95rpm"),
                    WorkoutStep("40s", "60%", "85rpm"),
                ),
            ),
        ),
    )


def _title_for_protocol(spec: Any) -> str:
    variant = str(spec.protocol_variant or spec.protocol_type or spec.workout_family).upper()
    if variant.startswith("VO2_20_10"):
        return "VO2max 20/10 Microbursts"
    if variant.startswith("VO2_40_20"):
        return "VO2max 40/20 Microbursts"
    if variant.startswith("VO2_30_15"):
        return "VO2max 30/15 Microbursts"
    if "VO2_LONG" in variant:
        return "VO2max Long Intervals"
    if "THRESHOLD" in variant:
        return "Threshold Intervals"
    if "OVER_UNDER" in variant:
        return "Tempo Over/Under"
    if "SWEET_SPOT_EXTENSIVE" in variant:
        return "Sweet Spot Extensive"
    if "SWEET_SPOT" in variant:
        return "Sweet Spot Intervals"
    if "TEMPO_STEADY_BREVET" in variant:
        return "Tempo Steady State"
    if "TEMPO" in variant:
        return "Tempo Intervals"
    if "K3" in variant:
        return "K3 Strength Endurance"
    if "PREFATIGUE_FINISH" in variant:
        return "Endurance Pre-Fatigue Finish"
    if "FATIGUE_FINISH" in variant:
        return "Endurance Fatigue Finish"
    if "BACK_TO_BACK" in variant:
        return "Endurance Back-to-Back Load"
    if "ENDURANCE_LONG" in variant:
        return "Long Endurance Anchor"
    if spec.low_end_endurance:
        return "Low-End Endurance Support"
    return "Aerobic Endurance Support"


def _notes_for_protocol(spec: Any) -> str:
    variant = str(spec.protocol_variant or spec.protocol_type or spec.workout_family).replace("_", " ").title()
    return f"Deterministic {variant} workout generated from the approved week blueprint."


def _minutes_token(total_minutes: int) -> str:
    total_minutes = max(int(total_minutes), 1)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h{minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"
