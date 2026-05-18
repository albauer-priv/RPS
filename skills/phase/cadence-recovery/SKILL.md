---
name: cadence-recovery
description: Apply season-owned cadence, deload, and re-entry rules inside an exact phase range.
metadata:
  author: rps
  version: "5.0"
---
Apply cadence as a constrained translation problem.

Method:
1. Confirm the season-compatible cadence family: `3:1`, `2:1`, or `2:1:1`.
2. Place build, deload, and mini-reset weeks so the exact phase range stays coherent.
3. Define deload magnitude and re-entry load from the selected baseline.
4. Favor the shorter fatigue wave whenever tolerance or logistics are uncertain.

Selection rules:
- `2:1` for fragile recovery, life stress, masters profiles, injury/illness sensitivity, or repeated build-week collapse
- `3:1` only with stable robustness and evidence that three progressive weeks are sustainable
- `2:1:1` when two build weeks are tolerated but a full third build week is consistently too much

Deload and re-entry:
- deload must reduce meaningful weekly load, not merely relabel intensity
- baseline-anchored deload: `DL_kJ = BL_kJ * 0.60 to 0.80`
- last-build anchored deload: `DL_kJ = prior_week_kJ * 0.55 to 0.75`
- default re-entry: `RE_kJ = BL_kJ * 0.90 to 1.00`
- high-fatigue re-entry: `RE_kJ = BL_kJ * 0.85 to 0.95`
- robust/fresh re-entry, only without spike or dominance warnings: `RE_kJ = BL_kJ * 0.95 to 1.05`
- when fatigue remains high, re-entry should be lower rather than forcing the old build target

Cadence target math:
- `3:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `W3 = W2 * 1.06-1.10`, then deload
- `2:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.15`, then deload
- `2:1:1`: `W1 = BL * 1.00-1.05`, `W2 = W1 * 1.08-1.12`, `MR = W2 * 0.80-0.90`, `W4 = W2 * 0.95-1.05`
- if `2:1:1` fatigue is high in W2 or readiness is poor in W3, replace `MR` with true deload and treat W4 as re-entry
- after a clean `2:1:1`, update next baseline conservatively as `BL_kJ_next = mean(W2_kJ, W4_kJ)` or use rolling `CH_kJ`

Hard rules:
- use the cadence allowed by season logic
- re-entry ramps gradually back toward normal build load
- deloads and mini-resets must remain visible in the phase structure
- a phase structure must show which weeks are build, deload, mini-reset, reload, or re-entry
- use cadence logic to constrain structure while preserving explicit season authority

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
