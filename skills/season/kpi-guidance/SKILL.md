---
name: kpi-guidance
description: Interpret KPI-profile guidance for season-level planning without turning diagnostics into independent authority.
metadata:
  author: rps
  version: "1.0"
---
Use KPI profile guidance to shape season planning conservatively.

Rules:
- KPI guidance informs feasibility and emphasis
- Apply KPI guidance inside binding event, availability, and safety constraints
- selected KPI rate bands should narrow corridor realism, not force unsafe ramps
- Treat moving-time-rate guidance as pacing semantics only, not elapsed-time governance
- Do not emit fixed rest-day, availability-cap, phase-corridor, or event-taper authority except to state that KPI guidance cannot override them
- Keep the primary contribution on KPI-band semantics, moving-time interpretation, pacing guardrails, and the limits of KPI authority

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
