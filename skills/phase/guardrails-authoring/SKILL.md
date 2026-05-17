---
name: guardrails-authoring
description: Author exact-range phase guardrails as weekly bands plus execution boundaries.
metadata:
  author: rps
  version: "8.0"
---
Author guardrails for one exact phase range.

Method:
1. Consume the injected deterministic S5 bands for the exact phase range.
2. Consume `Deterministic Phase Execution Context` for required ISO weeks, phase length, week index, cycle, and deload intent.
3. Resolve a deterministic baseline week from the recent history when baseline-based progression logic is needed.
4. Copy each code-owned S5 band and trace into `phase_guardrails.load_guardrails.weekly_kj_bands`.
5. If S5 reports STOP/fallback status, expose the status and request bounded replan rather than widening the band.
6. Express execution boundaries that later structure and week planning must respect.
7. Encode what is allowed, suppressed, or protected in this phase.

Baseline selection:
- use the recent `6-8` week lookback, default `8`
- compute `MED_kJ = median(Work (kJ))` and `MED_time = median(Weekly Moving Time Total (min))`
- exclude disrupted/deload weeks where `Work (kJ) < 0.80 * MED_kJ`
- exclude spike/peak weeks where `Work (kJ) > 1.15 * MED_kJ`
- exclude sparse weeks where `# Activities < 4`
- require at least `2 of 3` quality gates:
  - aerobic structure: `Z2 Share (Power) >= 60%`
  - stability: `DI >= 0.95`, or valid Z2 drift flag and `Decoupling <= 5%`
  - execution: `# Activities >= 4`, `Work >= 0.85 * MED_kJ`, and `Weekly Moving Time Total >= 0.85 * MED_time`
- choose the most recent structurally valid week that passes exclusions and at least `2/3` gates
- if no week qualifies, use `BL_kJ = MED_kJ` with low baseline confidence

Feasible-band logic:
- S5 is code-owned truth for weekly governance-load bands
- interpret S5 in governance-load space, not raw mechanical work
- if the season corridor is infeasible for this exact phase, surface the fallback/STOP trace rather than silently pushing overload downstream
- do not recompute, broaden, or override injected S5 values in agent reasoning
- `weekly_kj_bands[w]` always refers to `planned_weekly_load_kj` for ISO week `w`
- feasible bands require valid FTP, non-negative availability, and at least one allowed intensity domain
- KPI capacity bands are active only when selected KPI moving-time-rate guidance is present; if active, `body_mass_kg` is mandatory
- progression overlay uses prior `planned_weekly_load_kj` only when a valid previous value exists

S5 fallback semantics:
- Level 0: normal season/feasible/KPI/progression intersection
- Level 1: progression overlay dropped
- Level 2: KPI rate-band escalation `LOW -> MID -> HIGH` if available
- Level 3: KPI utilization override only if explicitly allowed
- Level 4: degenerate band at hard max
- Level 5: season-corridor infeasible override to closest feasible point
- STOP instead of emitting a band for missing/invalid FTP, negative availability, no allowed domains, empty feasible band, KPI-active missing body mass, or empty Level 5 override

Execution boundaries:
- specify what intensity domains are allowed, suppressed, or only touched sparingly
- make recovery protection explicit where cadence or event context requires it
- keep exact-range traceability visible in every guardrail result

Hard rules:
- guardrails are binding for downstream structure and week planning
- exact range must stay traceable and must not drift
- emitted weeks must match `Deterministic Phase Execution Context.required_phase_weeks`
- do not hide unrealistic load pressure behind wide bands
- do not let execution rules contradict season-owned cadence or taper logic
- `weekly_kj_bands` must match injected deterministic S5 bands
- no load compression onto recovery days or fixed-rest days
