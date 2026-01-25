---
Type: Policy
Policy-For: LOAD_DISTRIBUTION
Policy-ID: LoadDistributionPolicy
Version: 1.0

Scope: Shared
Authority: Informational

Applies-To:
  - Micro-Planner
  - Workout-Builder

Notes: >
  Optional, non-binding guidance for distributing weekly planned_Load_kJ
  across days. This policy MUST NOT override governance bands or block intent.
---

# Load Distribution Policy (Optional)

## Purpose

Provide a deterministic, optional method to distribute weekly
**planned_Load_kJ** across days without altering governance or intent.

This policy is **advisory**. It is used only when explicitly referenced
by a prompt or operator. Governance bands always override.

---

## Weekly target selection (optional)

If a weekly target is needed for distribution, choose a value **within**
the weekly_kj_bands (planned_Load_kJ).

Default (optional):
- `weekly_target = min + 0.67 × (max - min)` (upper-third)

If availability constraints prevent hitting this target, the planner may
shift downward within the band and record the reason.

---

## Day-weighting defaults (optional)

Suggested default weights (sum = 1.0):

| Day | Weight |
| --- | ---: |
| Mon | 0.08 |
| Tue | 0.12 |
| Wed | 0.12 |
| Thu | 0.12 |
| Fri | 0.06 |
| Sat | 0.25 |
| Sun | 0.25 |

These reflect a weekend-heavy endurance emphasis. Adjust only if
availability or governance requires it.

---

## Reconciliation (optional)

After workouts are drafted:
1) Recompute planned_Load_kJ per day.
2) If weekly total is outside the band, adjust **duration only** for
   flexible endurance sessions (not quality sessions).
3) Recompute until within band or availability prevents compliance.

If compliance cannot be achieved, stop and escalate to Meso/Macro.

## Rounding & residuals (optional)

When distributing a weekly target to days:
1) Compute float day targets.
2) Round to integers.
3) Allocate any residual difference using **largest remainder** to the
   most flexible days (typically Sat/Sun, then ENDURANCE days).

---

## Non-Override Rules

- Never change block intent or quality density.
- Never increase intensity solely to hit the band.
- Use duration/volume adjustments first.

---

## End of LoadDistributionPolicy (Optional)
