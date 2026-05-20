# Week Load Estimation

Week planning turns corridor logic into executable day and workout targets.

Use:
- active weekly corridor
- phase intent and week role structure
- durable distribution across key sessions, endurance, and recovery

The target is a realistic week, not mathematical perfection.

## Progressive-overload execution boundaries

Sources: `ProgressiveOverloadPolicy`, `DurabilityFirstPrinciples`.

Week planning does not select the season cadence. It executes the active phase/week role.

Rules:

- `week_summary.planned_weekly_load_kj` must remain inside the binding active weekly band.
- `week_summary.weekly_load_corridor_kj` must mirror the binding active weekly band for the target ISO week.
- Workout-level `planned_kj` is mechanical work; corridor compliance uses governance load.
- If the week is a load week, use volume/work and durable duration before intensity.
- If the week is deload, mini-reset, or re-entry, preserve that role even if the corridor midpoint looks attractive.
- Do not use a recovery/fixed-rest day as a load bucket.
- Do not compensate missed sessions by compressing load later in the week.
- If exact corridor centering would require intensity inflation or unsafe day density, stay safer and explain the under-target outcome or request replan.

STOP or request bounded replan when:

- active `weekly_kj_bands` are missing
- the target week is infeasible under the injected availability/capacity context
- a forbidden domain is needed to hit the target
- KPI gating is active but required body-mass context is missing

Cadence-derived week targets from ProgressiveOverloadPolicy:

- `3:1`
  - W1: `BL_kJ * 1.00 to 1.05`
  - W2: `W1_kJ * 1.08 to 1.12`
  - W3: `W2_kJ * 1.06 to 1.10`
  - Deload: `BL_kJ * 0.60 to 0.80` or `prior_week_kJ * 0.55 to 0.75`
- `2:1`
  - W1: `BL_kJ * 1.00 to 1.05`
  - W2: `W1_kJ * 1.08 to 1.15`
  - Deload: `BL_kJ * 0.60 to 0.80` or `prior_week_kJ * 0.55 to 0.75`
- `2:1:1`
  - W1: `BL_kJ * 1.00 to 1.05`
  - W2: `W1_kJ * 1.08 to 1.12`
  - Mini-reset: `W2_kJ * 0.80 to 0.90`
  - Reload/consolidation: `W2_kJ * 0.95 to 1.05`

Re-entry:

- Default: `BL_kJ * 0.90 to 1.00`
- High fatigue: `BL_kJ * 0.85 to 0.95`
- Fresh/robust with no warnings: `BL_kJ * 0.95 to 1.05`
