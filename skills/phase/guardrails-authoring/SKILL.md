---
name: guardrails-authoring
description: Author exact-range phase guardrails as weekly bands plus execution boundaries.
metadata:
  author: rps
  version: "9.0"
---
Author guardrails for one exact phase range.

Definitions:
- `weekly_kj_bands[w]`: exact-range governance-load band for ISO week `w`, expressed in `planned_weekly_load_kj`
- `planned_kj`: mechanical workout/day work estimate; not the guardrail corridor metric
- `planned_weekly_load_kj`: governance week-load metric used for guardrail/band compliance
- `BL_kJ`: baseline weekly governance-load anchor used when baseline-based progression interpretation is needed
- `MED_kJ`: recent median weekly work used in deterministic baseline selection support
- `MED_time`: recent median weekly moving time used in deterministic baseline selection support
- `phase_role`: deterministic exact-range phase role
- `week_role`: deterministic inherited role for a specific ISO week
- `build_subtype`: canonical build intent for `BUILD` phases

Authority / injected sources:
- `weekly_kj_bands[w]`, `phase_role`, `week_role`, and S5 traces come from deterministic phase execution/S5 context
- baseline support comes from the exact-range baseline-selection method already defined in this skill
- this layer authorizes guardrails and role-aware boundaries; it does not invent cadence families or workout-level load math

Method:
1. Consume the injected deterministic S5 bands for the exact phase range.
2. Consume `Deterministic Phase Execution Context` for required ISO weeks, phase length, week index, cycle, phase role, inherited week roles, scenario cadence, and deload intent.
2a. Treat inherited canonical phase semantics from deterministic phase execution context as binding authority:
   - `phase_type`
   - `phase_intent`
   - `build_subtype` when `phase_type = BUILD`
   Use them for domain narrowing, recovery protection, and VO2/taper handling.
3. Treat `phase_cadence_week_roles` and `week_role_by_iso_week` as binding; do not invent week roles or replace the selected scenario cadence.
4. Resolve a deterministic baseline week from the recent history when baseline-based progression logic is needed.
5. Copy each code-owned role-aware S5 band and trace into `phase_guardrails.load_guardrails.weekly_kj_bands`.
   Band notes must preserve S5 band, phase role, week role, role progression band, and availability feasibility trace.
5a. Treat the persisted Season phase authority as the exact binding band source. Copy exact week bands from injected deterministic authority; do not narrow or recompute them from S5 prose.
6. If S5 reports STOP/fallback status, expose the status and request bounded replan rather than widening the band.
7. Express execution boundaries that later structure and week planning must respect.
8. Encode what is allowed, suppressed, or protected in this phase.

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
- when zero weeks qualify, use `BL_kJ = MED_kJ` with low baseline confidence

Progression axes:
- duration / governance work
- frequency when inherited structure allows it
- density / complexity
- intensity last

Progression rule:
- guardrails must never imply multi-axis hidden escalation by keeping load, density, and intensity all rising together without explicit bounded justification

Feasible-band logic:
- S5 is code-owned truth for weekly governance-load bands
- interpret S5 in governance-load space, not raw mechanical work
- if the season corridor is infeasible for this exact phase, surface the fallback/STOP trace rather than silently pushing overload downstream
- copy injected S5 values exactly and explain their application
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
- emit STOP status for missing/invalid FTP, negative availability, empty domain sets, empty feasible bands, KPI-active missing body mass, or empty Level 5 override

Execution boundaries:
- specify what intensity domains are allowed, suppressed, or only touched sparingly
- make recovery protection explicit where cadence or event context requires it
- keep exact-range traceability visible in every guardrail result
- inherited overload policy must be visible in the guardrails, not buried in prose
- distinguish build, deload, mini-reset, reload, and re-entry weeks where the policy requires different behavior
- if inherited governance suppresses a defining domain, do not author a phase-execution frame that still behaves like that intent
- make `allowed_forbidden_semantics` match canonical `phase_type` / `phase_intent` / `build_subtype`
  - `vo2_build`: optional sparse fresh `VO2MAX` only when scenario authority permits it
  - `threshold_build`: threshold-oriented, not a new VO2 block
  - `sst_build`: extensive moderate work with density control
  - `durability_build`: fatigue-resistant specificity, duration/kJ first
  - `specificity_build`: event-near pacing/fueling/terrain/logistics realism without full taper semantics
  - `vlamax_lowering`: efficiency-oriented, no anaerobic drift
  - `peak_sharpening` / `taper_freshening`: freshness-sensitive narrowing, no accumulation drift
  - `race_execution`: protect event execution and recovery runway

Operational overload-policy translation into guardrails:
- for `3:1`, guardrails should make three progressive load opportunities visible before the deload week
- for `2:1`, guardrails should make two progressive load opportunities visible before the deload week
- for `2:1:1`, guardrails should make:
  - two progressive load opportunities
  - one mini-reset week with a clear reduction
  - one reload week near W2 load
- if fallback conditions are present, guardrails must allow:
  - mini-reset -> true deload
  - reload -> re-entry
- use these reference reductions when expressing notes and review pressure:
  - deload from baseline: `BL * 0.60-0.80`
  - deload from prior build: `prior * 0.55-0.75`
  - re-entry: `BL * 0.90-1.00`
  - high-fatigue re-entry: `BL * 0.85-0.95`

Intent-domain translation rules:
- `threshold_build` is legal only when `THRESHOLD` is allowed upstream
- if `THRESHOLD` is suppressed upstream, author `durability_build`, `sst_build`, or `specificity_build` style execution boundaries according to the inherited intent, not threshold-shaped boundaries by implication

Hard rules:
- guardrails are binding for downstream structure and week planning
- keep the exact range traceable and stable
- emitted weeks must match `Deterministic Phase Execution Context.required_phase_weeks`
- emitted week bands must preserve the injected phase role and week role for every ISO week
- deload, mini-reset, re-entry, reload, and taper weeks must be numerically visible unless S5 fallback trace explains why not
- do not let week-role/load-shape drift away from inherited overload policy
- keep threshold-shaped execution semantics out of phases where `THRESHOLD` is suppressed upstream
- surface unrealistic load pressure explicitly in review/replan guidance
- align execution rules with season-owned cadence and taper logic
- `weekly_kj_bands` must match injected deterministic S5 bands
- Treat inherited scenario contract as season posture ceiling only; do not narrow it to phase-local legality
- phase legality fields must stay separate from the scenario ceiling
- freeze `inherited_scenario_contract` exactly from injected deterministic authority; do not summarize, paraphrase, compress, or rewrite nested `inherited_scenario_contract` fields such as `constraint_summary` or `risk_flags`
- for `BASE / shortened_re_entry`, canonical `quality_intent` is `Stabilization`
- keep recovery days and fixed-rest days protected from load compression
- emit `body_metadata.phase_type`, `body_metadata.phase_intent`, and `body_metadata.phase_taxonomy_version` explicitly and keep them identical to upstream authority
- emit `body_metadata.build_subtype` explicitly for `BUILD` phases and keep it identical to upstream authority

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
