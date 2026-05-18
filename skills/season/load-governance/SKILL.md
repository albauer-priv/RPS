---
name: load-governance
description: Season-level corridor derivation and progression governance under durability-first rules.
metadata:
  author: rps
  version: "7.0"
---
Author season load governance as sustainable corridor and progression authority.

Method:
1. Start from athlete robustness, availability pressure, selected KPI guidance, event ambition, and the injected deterministic load-capacity context.
2. Treat `availability_load_capacity_kj` as a hard plausibility boundary for repeated weekly governance load.
3. Set a sustainable season weekly corridor that can realistically be repeated and progressed without repeated catch-up weeks.
4. Choose progression framing and cadence ownership at season level; lower layers may apply but not reinvent it.
5. Prefer feasible corridors over aspirational overload and protect `A` event clarity inside schema-valid cycle values.

Deterministic load context:
- use the injected `availability_load_capacity_kj` min/typical/max directly
- use the injected `IF_ref_load` and source for explanation only
- treat logistics as risk and planning constraints; reduce hours numerically only when explicit hour fields exist
- if a season corridor sits above capacity, flag review/replan pressure instead of normalizing it silently
- agents explain and apply code-owned deterministic S5/availability bands exactly as injected
- season corridors are expressed in `planned_weekly_load_kj/week`, even when upstream wording says `weekly_kJ`
- Season sets strategic corridors; Phase applies deterministic feasibility and S5 intersection once a concrete phase range and allowed domains exist
- use `ambition_if_range` to shape QUALITY intent while preserving segment-derived IF and code-owned load math

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

Hard rules:
- keep event ambition inside safe ramp limits
- set season corridors that remain achievable without repeated catch-up weeks
- model multiple `A` events with explicit macrocycle or peak-window logic
- if robustness is doubtful, narrow progression rather than widen intensity
- season load governance must remain explicit enough that phase planning can inherit it deterministically
- `self_check.every_phase_maps_to_cycle_and_deload_intent` may be true only after coverage, cycle, cadence, and deload intent are checked

Output format:
- Return the task expected_output with load bands, progression notes, assumptions, and STOP or warning states separated clearly.
- Use injected code-owned capacity/S5 values where present and explain how the task applies them.
- Include trace cues for availability, phase/week corridor, deload, re-entry, and progression logic.
