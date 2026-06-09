---
name: load-governance
description: Season-level corridor derivation and progression governance under durability-first rules.
metadata:
  author: rps
  version: "8.0"
---
Author season load governance as sustainable corridor and progression authority.

Definitions:
- `planned_kj`: mechanical work estimate at workout/day level; never use it directly for season corridor compliance
- `planned_weekly_load_kj`: governance week-load metric used for season corridor and band compliance
- `availability_load_capacity_kj`: deterministic season-level governance-load capacity context for a phase or week-role slice
- `LR_share`: long-ride share of total planned weekly time/work from injected deterministic context when such a share is available; use it only as a conservative dominance signal, never as a value to invent from prose
- `phase_role`: deterministic season role for a slot, such as Base, Build, Peak, or Transition-like re-entry behavior
- `cadence_week_roles`: inherited cadence-owned role sequence within a slot, such as `LOAD_1`, `LOAD_2`, `MINI_RESET`, `RELOAD`
- `BL_kJ`: baseline weekly governance-load anchor used for overload, deload, and re-entry decisions in this layer
- `prior_week_kJ`: immediately preceding comparable build-week governance load used for last-build anchored deload logic
- `DL_kJ`: governance-load target for a deload week
- `RE_kJ`: governance-load target for a re-entry week
- `MR_kJ`: governance-load target for a mini-reset week
- `W1_kJ`, `W2_kJ`, `W3_kJ`, `W4_kJ`: cadence-step governance-load targets for progressive overload interpretation
- `BL_kJ_next`: conservative next-baseline anchor after a completed cadence cycle
- `IF_ref_load`: deterministic normalization reference from the active load-estimation method; do not redefine it here

Authority / injected sources:
- `availability_load_capacity_kj`, `phase_role`, `cadence_week_roles`, baseline hints, and progression trace come from `Deterministic Season Phase Load Context`
- `LR_share`, when available, must come from deterministic historical/context blocks already injected for this run; if it is absent, omit the long-ride dominance inference rather than inventing it
- load-estimation math and `IF_ref_load` semantics come from `skills/shared/load-estimation-core/SKILL.md`
- when `BL_kJ` is not directly injected, derive it only from the deterministic baseline/progression context already present in the season load context; do not invent it from prose
- this layer must not compute workout-level segment math

Method:
1. Start from athlete robustness, availability pressure, selected KPI guidance, event ambition, and the injected deterministic load-capacity context.
2. Treat `availability_load_capacity_kj` as a hard plausibility boundary for repeated weekly governance load.
3. Use `Deterministic Season Phase Load Context` to set each phase corridor from phase role, inherited week roles, availability cap, baseline, and progression trace.
4. Set sustainable phase corridors that can realistically be repeated and progressed without repeated catch-up weeks; do not copy availability capacity min/typical/max as every phase's target corridor.
5. Choose progression framing and cadence ownership at season level; lower layers may apply but not reinvent it.
6. Prefer feasible corridors over aspirational overload and protect `A` event clarity inside schema-valid cycle values.
7. Treat selected-scenario intensity domains as season authority. Phase Guardrails may narrow them downstream, but must not be used to reconstruct season authority backward.

Operational decision order:
1. Determine baseline and feasibility from the injected deterministic context.
2. Choose cadence-family interpretation from robustness, recovery, and risk context.
3. Choose ramp class:
   - conservative `+5%` to `+8%`
   - standard `+8%` to `+12%`
   - aggressive `+12%` to `+18%` only in rare robust cases
4. Define how deload, mini-reset, reload, and re-entry work across the season.
5. Decide whether early Build entry must stay at lower-corridor values because preceding context is shortened/base/re-entry.
6. Expose fallback behavior when the nominal cadence no longer matches tolerance.

Progression axes:
- duration / total work (`planned_weekly_load_kj`)
- frequency only when the surrounding structure explicitly permits it
- density / complexity of quality distribution
- intensity last

Progression rules:
- advance only one overload axis per step unless an explicit bounded exception is stated
- do not use intensity first to rescue a weak corridor
- do not combine top-of-range kJ progression with simultaneous density escalation unless recovery margin remains explicit

Deterministic load context:
- use the injected `availability_load_capacity_kj` min/typical/max directly
- explain when a corridor is below capacity because of re-entry, mini-reset, reload, event rehearsal, or taper semantics
- use the injected `IF_ref_load` and source for explanation only
- treat logistics as risk and planning constraints; reduce hours numerically only when explicit hour fields exist
- if a season corridor sits above capacity, flag review/replan pressure instead of normalizing it silently
- if a season corridor equals availability capacity across unrelated phases, flag review pressure because sustainable progression/taper semantics may have been lost
- a phase corridor must fit the injected phase-role feasibility band; 12,000 kJ is invalid when the available time cannot support it
- agents explain and apply code-owned deterministic S5/availability bands exactly as injected
- season corridors are expressed in `planned_weekly_load_kj/week`, even when upstream wording says `weekly_kJ`
- Season sets strategic corridors; Phase applies deterministic feasibility and S5 intersection once a concrete phase range and allowed domains exist
- Season phase role modulates corridor meaning before Phase runs: Base stabilizes, Build progresses, Peak tapers/sharpens, Transition re-enters/consolidates
- use `ambition_if_range` to shape QUALITY intent while preserving segment-derived IF and code-owned load math
- durability-first means dominant `ENDURANCE`, not `ENDURANCE only`
- `TEMPO` and, when scenario-permitted, `SWEET_SPOT` can be season-valid especially in later Base, Build, or rehearsal-oriented build
- `THRESHOLD` and `VO2MAX` may remain narrower or excluded by scenario/phase context; do not widen them heuristically

Progression guardrails:
- standard week-over-week ramp: `+8%` to `+12%`
- conservative ramp: `+5%` to `+8%`
- aggressive ramp: `+12%` to `+18%` only in rare robust cases
- keep sustained ramps at or below `15%` except in explicit special cases
- choose either top-of-range kJ progression or increased intensity density, with recovery margin preserved
- if time metrics exist, repeated `LR_share > 0.50` means long-ride dominance and should push cadence/ramp more conservative

Cadence framing:
- `3:1` means three load weeks followed by one deload in a four-week phase
- `2:1` means two load weeks followed by one deload in a three-week phase
- `2:1:1` means two load weeks, one mini-reset, and one reload in a four-week phase
- prefer `2:1` for fragile recovery, high life stress, masters profiles, or repeated breakdown in week 3
- prefer `3:1` only with stable robustness and clear recovery capacity
- prefer `2:1:1` when two build weeks are tolerated but a full third build week is too risky

Cadence fallback and adjustment rules:
- if `2:1:1` mini-reset becomes a true deload because fatigue remains high or readiness is poor, treat the following week as baseline-anchored re-entry rather than normal reload
- if `3:1` repeatedly collapses in week 3, move to a more conservative cadence such as `2:1` or `2:1:1`
- if `2:1` repeatedly over-recovers, makes deload unnecessary, or stalls baseline development without clear fatigue pressure, consider whether `3:1` or `2:1:1` is more appropriate
- if Build-entry follows shortened, base, or re-entry structure, the first Build week must be readiness-gated and may need to start at the lower edge of the available corridor
- large jumps into Build are exceptions that require explicit robustness/readiness rationale rather than silent acceptance

Deload and re-entry framing:
- deload should usually reduce meaningfully relative to baseline or last build week
- baseline-anchored deload target: `DL_kJ = BL_kJ * 0.60 to 0.80`
- last-build anchored deload target: `DL_kJ = prior_week_kJ * 0.55 to 0.75`
- default re-entry: `RE_kJ = BL_kJ * 0.90 to 1.00`
- high-fatigue re-entry: `RE_kJ = BL_kJ * 0.85 to 0.95`
- robust/fresh re-entry, only without spike or dominance warnings: `RE_kJ = BL_kJ * 0.95 to 1.05`
- re-entry progresses gradually from reduced load toward normal build load
- every deload phase or week-level deload intent needs a cadence-based rationale

Cadence-specific load targets:
- `3:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `W3 = W2 * 1.06-1.10`, then deload
- `2:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.15`, then deload
- `2:1:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `MR = W2 * 0.80-0.90`, `W4 = W2 * 0.95-1.05`
- if `2:1:1` mini-reset becomes a true deload, treat the reload week as re-entry and baseline-anchor it
- inherited cadence comes from the selected Scenario; Season Plan may interpret and explain the cadence but must not replace it

Baseline update rules:
- next baseline must be conservative; do not anchor future progression to the single highest visible week
- after a clean `2:1:1`, `BL_next` may be approximated from `mean(W2, W4)` or a comparable conservative rolling anchor
- after high fatigue, fallback, or shortened re-entry context, bias the next baseline downward rather than carrying peak build assumptions forward

Season-level overload-policy translation:
- `3:1` should usually appear in season logic only when the athlete can absorb three progressive build exposures before a clear deload
- `2:1` should usually appear when recovery risk is high enough that the third build week would be speculative
- `2:1:1` should usually appear when two build exposures are productive but a full third build week is not
- do not describe `2:1:1` as generic deload cadence; it is two load weeks, one mini-reset, one reload unless fallback explicitly changes that
- when fallback changes semantics, the season notes should say so plainly:
  - mini-reset became true deload
  - reload became re-entry

Hard rules:
- keep event ambition inside safe ramp limits
- set season corridors that remain achievable without repeated catch-up weeks
- model multiple `A` events with explicit macrocycle or peak-window logic
- if robustness is doubtful, narrow progression rather than widen intensity
- keep reload and re-entry semantically distinct whenever the policy treats them differently
- make cadence, fallback, baseline, and Build-entry readiness logic visible enough that Phase can inherit them deterministically
- season load governance must remain explicit enough that phase planning can inherit it deterministically
- final `A` event taper corridors must show meaningful load reduction versus Build unless a documented review rationale proves otherwise
- `self_check.every_phase_maps_to_cycle_and_deload_intent` may be true only after coverage, cycle, cadence, and deload intent are checked
- do not let a downstream `PHASE_GUARDRAILS`-style `ENDURANCE`-only restriction erase broader season authority when the selected scenario permits targeted quality domains

Output format:
- Return the task expected_output with load bands, progression notes, assumptions, and STOP or warning states separated clearly.
- Use injected code-owned capacity/S5 values where present and explain how the task applies them.
- Include trace cues for availability, phase/week corridor, deload, re-entry, and progression logic.
