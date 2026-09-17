---
name: evidence-alignment
description: Convert historical baseline plus exact previous-week activity evidence into early season-planning implications.
metadata:
  author: rps
  version: "1.0"
---
Interpret season evidence before synthesis.

Inputs:
- `historical_baseline`
- exact previous-week `activities_actual`
- exact previous-week `activities_trend`
- selected scenario posture and deterministic season context

Return:
- continuity/disruption signal
- load tolerance / durability / recovery caution
- compact planning implications
- prohibited overreach

Hard rules:
- use only previous-week weekly evidence, never target-week evidence
- evidence shapes season conservatism and realism only
- do not rewrite deterministic legality, selected-scenario authority, or exact season phase-load authority
- this task is not the final season planner and not a late reviewer

Good implication examples:
- `Recent continuity is disrupted; keep cadence and ramp assumptions conservative until load tolerance restabilizes.`
- `Baseline supports sustained long-event continuity, but recent trend still argues against aggressive early build compression.`
- `Recent activity evidence does not justify widening quality density beyond the selected scenario posture.`
- `W_prev was disrupted (W_prev_actual = X kJ < BL_kJ × 0.85 = Y kJ); downstream load governance must use BL_kJ as the re-entry anchor; a season corridor at BL_kJ × 0.90–1.00 is valid re-entry — the gap above W_prev_actual is explained by the disrupted week, not by planning overreach.`

Prohibited implication examples:
- Do NOT emit: `Plan must remain conservative relative to last week's actual load of X kJ` when that
  week was disrupted — this instructs load governance to use the wrong anchor.
- Do NOT emit: `Overreach risk: plan exceeds recent actual load` for a corridor within BL_kJ × 0.85–1.05
  when the gap is explained by a disrupted week.

Disrupted-week detection:
- check `W_prev_actual` against `BL_kJ` from `HISTORICAL_BASELINE`
- if `W_prev_actual < BL_kJ × 0.85`: classify as disrupted week; state the disrupted-week
  implication from the template above; reference `progression_guardrails.md` §"Disrupted week re-entry"
- if `W_prev_actual ≥ BL_kJ × 0.85`: normal re-entry; standard conservatism still applies
