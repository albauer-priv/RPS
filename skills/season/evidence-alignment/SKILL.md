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
