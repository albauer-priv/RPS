---
name: domain-glossary
description: Shared RPS domain vocabulary — use these definitions consistently across coach, planning, and review layers.
metadata:
  author: rps
  version: "1.0"
---
Use these term definitions exactly. Do not redefine or rename these concepts in output. This vocabulary is the shared semantic layer between the coach conversation and all planning and review agents.

## Load units

- `kJ` (kilojoule): the governance-load unit for all planning and review decisions. This is NOT raw mechanical work (watts × seconds) but the normalized governance metric derived from workout data. All corridors, baselines, and thresholds are in kJ unless explicitly stated otherwise.
- `BL_kJ`: the deterministic baseline anchor — the athlete's established typical weekly governance-load. Use as the re-entry anchor after any disruption. Never substitute W_prev_actual for BL_kJ when the most recent week was disrupted.
- `W_prev_actual`: the measured governance-load of the most recent completed week. Valid as a progression anchor only when the week was uninterrupted (W_prev_actual ≥ BL_kJ × 0.85).
- `availability_load_capacity_kj`: the deterministic upper bound per week derived from the athlete's stated availability. Corridors above this cap require explicit rationale.

## Disrupted week

A week is **disrupted** when `W_prev_actual < BL_kJ × 0.85` (illness, travel, vacation, or other transient factor).
- Re-entry after a disrupted week: `RE_kJ = BL_kJ × 0.90–1.00` is valid even when it substantially exceeds `W_prev_actual`.
- Do not anchor re-entry to `W_prev_actual` when the week was disrupted — that propagates an artificially low baseline.

## Phase cycles (schema-valid values only)

- `Base`: aerobic foundation, durability, repeatability, low-risk volume development.
- `Build`: progressive event-relevant load within durability-first ramp limits.
- `Peak`: final event-specific sharpening and taper behavior. Taper is expressed inside `Peak`, not as a separate cycle.
- `Transition`: recovery, re-entry, reset, or post-event restoration.
- `Specificity` and `Taper` are **not** valid cycle values in RPS artifacts.

## Event priority

- `A` event: the primary performance objective. Receives a dedicated peak window and taper. Defines macrocycle structure.
- `B` event: secondary and subordinate. Minor load adjustment only — no independent taper, no full peak.
- `C` event: training participation. No structural adjustment, no taper, no recovery debt carried forward.

## Cadence families

- `3:1`: three progressive build weeks, then one deload. For athletes with stable robustness only.
- `2:1`: two progressive build weeks, then one deload. Default for masters athletes, fragile recovery, or high life stress.
- `2:1:1`: two build weeks, one mini-reset, one return-to-build. When a third build week consistently overloads.
- Season cadence is selected once and does not change locally unless the season review layer authorizes it.

## Durability-first

Durability-first means `RECOVERY` and dominant `ENDURANCE` protect repeatability. It is **not** intensity-free: `TEMPO` or other scenario-permitted quality is valid as tightly bounded phase intent when recovery and event specificity justify it. A plan that suppresses all intensity including scenario-permitted domains is not durability-first — it is a planning error.

## Blocking issue vs warning

- `blocking_issue`: a hard failure that prevents plan submission. Raise only for genuine structural impossibilities or safety violations. The test: "can any valid plan proceed from here?" If yes → warning, not blocker.
- `warning`: a concern that reviewers should see but that does not prevent submission. Use for suboptimal choices that do not make the plan structurally invalid.
- When in doubt: warning, not blocking_issue. Incorrect blockers are worse than missed warnings because they prevent valid plans from advancing.
