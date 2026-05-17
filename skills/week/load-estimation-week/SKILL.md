---
name: load-estimation-week
description: Translate the active weekly corridor into day and workout load targets conservatively.
metadata:
  author: rps
  version: "8.0"
---
Translate a weekly corridor into executable week targets.

Method:
1. Start from the active phase/S5 corridor, capacity context, and phase intent.
2. Use `Deterministic Week Calendar and Availability Context` for the exact Mon-Sun dates, fixed rest days, day availability, logistics, events, and active S5 band.
3. Use `Deterministic Workout Load Estimation Context` for code-owned per-hour mechanical/governance load calibration.
4. Allocate load to structurally important days first: key sessions, durable endurance, and protected recovery.
5. Reconcile residual load with duration-first adjustments before any intensity escalation.
6. Use add-on aerobic load before changing workout classification or intensity domain.
7. Keep the final week structurally coherent even if the corridor is not hit perfectly.

Distribution rules:
- key load belongs on role-consistent key days first
- recovery days are protected before residual load is distributed elsewhere
- long endurance load should stay durable rather than becoming disguised quality work
- slightly under target with explanation is safer than structurally incoherent precision

Reconciliation rules:
- first adjust duration within the day-role intent
- then use aerobic add-ons where appropriate
- avoid intensity inflation that exists only to satisfy a weekly number
- if a week remains slightly low after safe reconciliation, preserve safety and explain the miss
- if under target, explain the safety decision before increasing intensity
- never compress load onto recovery days or fixed-rest days

Progressive-overload execution:
- execute the active phase/week role; do not select a new cadence in Week planning
- load weeks progress primarily through time/kJ, not intensity density
- deload, mini-reset, reload, and re-entry weeks preserve their role even if the corridor midpoint is higher
- default re-entry target is `BL_kJ * 0.90 to 1.00`; high fatigue uses `0.85 to 0.95`; robust/fresh uses `0.95 to 1.05` only without spike/dominance warnings
- for `3:1`, apply W1/W2/W3 intent as `BL * 1.00-1.05`, `W1 * 1.08-1.12`, `W2 * 1.06-1.10`
- for `2:1`, apply W1/W2 intent as `BL * 1.00-1.05`, `W1 * 1.08-1.15`
- for `2:1:1`, apply W1/W2/MR/W4 intent as `BL * 1.00-1.05`, `W1 * 1.08-1.12`, `W2 * 0.80-0.90`, `W2 * 0.95-1.05`

Load semantics:
- work from governance load (`planned_weekly_load_kj`) when matching the corridor
- `week_summary.planned_weekly_load_kj` must remain inside the active Phase/S5 band unless a guarded replan is requested
- `week_summary.weekly_load_corridor_kj` mirrors the active Phase/S5 `weekly_kj_bands[w]`
- preserve the distinction between corridor compliance and raw mechanical work
- when a workout estimate is weak, expose fallback assumptions instead of pretending precision
- use injected deterministic S5/capacity values directly; do not recompute or widen them
- workout `planned_kj` remains mechanical work; do not compare raw `planned_kj` totals against governance corridors without applying the approved load-estimation method
- use injected domain-hourly estimates for rough planning; exact workout text is checked by code-owned segment parsing after output
- segment parsing applies `%FTP`/range/ramp targets, loop repeats, `r_i` clamping, final-only rounding, and IF-direct fallback only for unparseable/intent-only workouts

Week STOP/replan triggers:
- active `weekly_kj_bands` missing
- target week infeasible under availability/capacity context
- forbidden intensity domain requested
- fixed rest day or recovery day is used as a load catch-up bucket
- KPI gating is active but required body-mass context is missing

Hard rules:
- no intensity inflation purely to hit corridor numbers
- no stealth load compression onto recovery days
- preserve recovery protection and key role logic
- preserve phase intent even when the corridor is tight
- a week outside the Phase/S5 band must be rejected or sent to replan, not stored silently
- day dates and fixed-rest-day handling must match the deterministic day matrix
