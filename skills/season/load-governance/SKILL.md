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
- logistics constraints are risk and planning constraints; do not numerically reduce hours unless explicit hour fields exist
- if a season corridor sits above capacity, flag review/replan pressure instead of normalizing it silently
- agents may explain code-owned values, but must not recompute, widen, or overwrite deterministic S5/availability bands
- season corridors are expressed in `planned_weekly_load_kj/week`, even when upstream wording says `weekly_kJ`
- Season may set strategic corridors, but must not perform exact feasibility/S5 narrowing; Phase owns deterministic feasibility and S5 intersection once a concrete phase range and allowed domains exist
- `ambition_if_range` may shape QUALITY intent, but it must not override segment-derived IF or code-owned load math

Progression guardrails:
- standard week-over-week ramp: `+8%` to `+12%`
- conservative ramp: `+5%` to `+8%`
- aggressive ramp: `+12%` to `+18%` only in rare robust cases
- avoid sustained ramps above `15%` outside explicit special cases
- do not simultaneously use the top of the kJ ramp range and increase intensity density
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
- re-entry must not snap back to peak build week
- every deload phase or week-level deload intent needs a cadence-based rationale

Cadence-specific load targets:
- `3:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `W3 = W2 * 1.06-1.10`, then deload
- `2:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.15`, then deload
- `2:1:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `MR = W2 * 0.80-0.90`, `W4 = W2 * 0.95-1.05`
- if `2:1:1` mini-reset becomes a true deload, treat the reload week as re-entry and baseline-anchor it

Hard rules:
- no unsafe ramp just to satisfy event ambition
- no season corridor that requires repeated catch-up weeks
- no implicit double-peak logic for multiple `A` events
- if robustness is doubtful, narrow progression rather than widen intensity
- season load governance must remain explicit enough that phase planning can inherit it deterministically
- `self_check.every_phase_maps_to_cycle_and_deload_intent` may be true only after coverage, cycle, cadence, and deload intent are checked
