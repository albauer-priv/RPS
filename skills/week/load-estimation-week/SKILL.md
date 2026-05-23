---
name: load-estimation-week
description: Translate the active weekly corridor into day and workout load targets conservatively.
metadata:
  author: rps
  version: "9.0"
---
Translate a weekly corridor into executable week targets.

Definitions:
- `planned_kj`: mechanical work estimate at workout/day level
- `planned_weekly_load_kj`: governance week-load metric used for week-corridor compliance
- `active_weekly_kj_band`: binding target-week governance-load band from deterministic week context
- `active_s5_band`: fallback/background governance band only when no week-specific band is present
- `BL_kJ`: baseline weekly governance-load anchor used for overload, deload, and re-entry interpretation
- `prior_week_kJ`: previous comparable build-week governance load
- `DL_kJ`: deload governance-load target
- `RE_kJ`: re-entry governance-load target
- `MR_kJ`: mini-reset governance-load target
- `W1_kJ`, `W2_kJ`, `W3_kJ`, `W4_kJ`: cadence-step governance-load targets used to interpret the active week role
- `phase_role`: active deterministic phase role
- `week_role`: active deterministic week role
- `IF_ref_load`: deterministic normalization reference from the shared load-estimation method

Authority / injected sources:
- `active_weekly_kj_band`, `active_s5_band`, fixed rest days, day availability, events, `phase_role`, and `week_role` come from `Deterministic Week Calendar and Availability Context`
- load-estimation math and `IF_ref_load` come from `skills/shared/load-estimation-core/SKILL.md`
- this layer translates weekly governance load into safe day/workout targets; it must not invent new cadence families or break phase/workout legality

Method:
1. Start from the binding active weekly corridor, capacity context, and phase intent.
2. Use `Deterministic Week Calendar and Availability Context` for exact Mon-Sun dates, phase role, active phase week role, fixed rest days, day availability, logistics, events, and the binding `active_weekly_kj_band`. Treat `active_s5_band` as fallback/background only when no week-specific band is present.
3. Use `Deterministic Workout Load Estimation Context` for code-owned per-hour mechanical/governance load calibration.
4. Allocate load to structurally important days first: key sessions, durable endurance, and protected recovery.
5. Reconcile residual load with duration-first adjustments before any intensity escalation.
6. Use add-on aerobic load before changing workout classification or intensity domain.
7. Keep the final week structurally coherent even if the corridor is not hit perfectly.

Distribution rules:
- key load belongs on role-consistent key days first
- recovery days are protected before residual load is distributed elsewhere
- fixed rest days always stay `00:00`, `0 kJ`, and `workout_id null`
- no day may exceed its deterministic availability cap
- long endurance load should stay durable rather than becoming disguised quality work
- slightly under target with explanation is safer than structurally incoherent precision

Progression axes:
- duration / total governance work
- frequency when the active week shape supports it
- density / complexity
- intensity last

Reconciliation rules:
- first adjust duration within the day-role intent
- then use aerobic add-ons where appropriate
- keep intensity changes tied to phase intent rather than weekly-number chasing
- if a week remains slightly low after safe reconciliation, preserve safety and explain the miss
- if under target, explain the safety decision before increasing intensity
- keep recovery days and fixed-rest days protected from load compression
- progress at most one overload axis per step: duration/kJ, frequency, density/complexity, or intensity
- use intensity as the last overload lever, not the first reconciliation tool

Progressive-overload execution:
- execute the active phase/week role and preserve cadence selected upstream
- load weeks progress primarily through time/kJ, not intensity density
- `LOAD_*` weeks may carry role-consistent key work only within the active phase quality cap
- `DELOAD`, `MINI_RESET`, and `SHORTENED_MINI_RESET` weeks must show real load and quality reduction
- `RELOAD` weeks rebuild conservatively without exceeding progressive-overload intent
- event weeks use event-specific execution and must not become generic quality weeks
- deload, mini-reset, reload, and re-entry weeks preserve their role even if the corridor midpoint is higher
- default re-entry target is `BL_kJ * 0.90 to 1.00`; high fatigue uses `0.85 to 0.95`; robust/fresh uses `0.95 to 1.05` only without spike/dominance warnings
- for `3:1`, apply W1/W2/W3 intent as `BL * 1.00-1.05`, `W1 * 1.08-1.12`, `W2 * 1.06-1.10`
- for `2:1`, apply W1/W2 intent as `BL * 1.00-1.05`, `W1 * 1.08-1.15`
- for `2:1:1`, apply W1/W2/MR/W4 intent as `BL * 1.00-1.05`, `W1 * 1.08-1.12`, `W2 * 0.80-0.90`, `W2 * 0.95-1.05`
- if poor readiness turns a nominal reload into a baseline-anchored week, treat it as re-entry in the week reasoning

Durability-first execution:
- missed or constrained load is not debt to be repaid later in the week
- when compressed, remove lower-priority stress before weakening recovery structure
- choose the week shape the athlete can likely repeat, not the one that cosmetically centers the corridor
- long endurance load must remain durable rather than mutating into disguised threshold or VO2 work

Load semantics:
- work from governance load (`planned_weekly_load_kj`) when matching the corridor
- `week_summary.planned_weekly_load_kj` must remain inside the binding active weekly band unless a guarded replan is requested
- `week_summary.weekly_load_corridor_kj` mirrors the binding active weekly band for the target week
- when availability cannot support the active band, stop or mark replan; do not add intensity to force the number
- preserve the distinction between corridor compliance and raw mechanical work
- when a workout estimate is weak, expose fallback assumptions instead of pretending precision
- use injected deterministic week-band/capacity values directly and preserve their exact bounds
- treat workout `planned_kj` as mechanical work and compare week totals to governance corridors through the approved load-estimation method
- use injected domain-hourly estimates for rough planning; exact workout text is checked by code-owned segment parsing after output
- segment parsing applies `%FTP`/range/ramp targets, loop repeats, `r_i` clamping, final-only rounding, and IF-direct fallback only for unparseable/intent-only workouts

Week STOP/replan triggers:
- active `weekly_kj_bands` missing
- target week infeasible under availability/capacity context
- requested intensity domain sits outside the allowed domain set
- fixed rest day or recovery day is used as a load catch-up bucket
- KPI gating is active but required body-mass context is missing

Hard rules:
- use duration and aerobic add-ons before considering intensity changes, and keep intensity tied to phase intent
- keep recovery days protected from load compression
- preserve recovery protection and key role logic
- preserve phase intent even when the corridor is tight
- keep workout construction subordinate to workout-policy legality and export-safe subset rules
- a week outside the binding active weekly band must be rejected or sent to replan, not stored silently
- day dates and fixed-rest-day handling must match the deterministic day matrix

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output with load bands, progression notes, assumptions, and STOP or warning states separated clearly.
- Use injected code-owned capacity/S5 values where present and explain how the task applies them.
- Include trace cues for availability, phase/week corridor, deload, re-entry, and progression logic.
