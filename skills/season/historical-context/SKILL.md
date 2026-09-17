---
name: historical-context
description: Interpret recent load, recovery, and tolerance history for season planning.
metadata:
  author: rps
  version: "1.0"
---
Summarize recent athlete history as season-planning context.

Focus on:
- recent load tolerance
- recovery reliability
- re-entry needs after disruption
- signs that aggressive progression or long build strings are unsafe

Disrupted-week classification:
- When the most recent completed week load (`W_prev_actual`) is materially below the deterministic
  baseline (`W_prev_actual < BL_kJ × 0.85`), explicitly classify that week as **DISRUPTED**
  in the output — caused by illness, travel, vacation, or other transient factor.
- State clearly that downstream load governance must use `BL_kJ` (historical baseline) as the
  re-entry anchor, **not** `W_prev_actual`.
- A season corridor starting at `BL_kJ × 0.90–1.00` is valid re-entry even if it is substantially
  above `W_prev_actual`; the gap is explained by the disrupted week, not by planning overreach.
- Do not advise downstream agents to "stay conservative relative to last week's actual load" when
  last week was a disrupted week — that recommendation would propagate an incorrect anchor.
- Reference: `skills/season/load-governance/references/progression_guardrails.md`
  §"Disrupted week re-entry".

Hard rules:
- stay evidence-led and recent-history-led
- do not restate fixed rest days, availability caps, phase corridors, event taper handling, or KPI pacing semantics as the main conclusion unless the historical record directly constrains them
- when classifying a disrupted week, name the disrupted-week status explicitly so that the
  `season_evidence_alignment` specialist and the load-governance specialist can both apply
  the correct re-entry anchor

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
