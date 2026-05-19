---
name: governance-review
description: Review season corridor realism, progression safety, and macrocycle load governance.
metadata:
  author: rps
  version: "1.0"
---
Review the season candidate for governance realism.

Checklist:
- corridor logic is feasible for the athlete context
- progression and cadence remain sustainable
- cadence is inherited from the selected Scenario and has not been replaced by Season Plan reasoning
- `cadence_week_roles` are represented in phase blueprints and in writer-ready rationale
- phase role in the season macrocycle is represented in every phase blueprint and modulates the load corridor
- role-week load bands from `Deterministic Season Phase Load Context` are represented in every phase blueprint
- taper and peak logic remain inside realistic overload limits
- final `A` event taper corridors are lower than Build/re-entry corridors unless the candidate gives a specific accepted rationale
- `B` events receive only rehearsal/minor-load-adjustment treatment, not full taper or peak treatment
- season-level load framing stays durability-first
- availability capacity is used as a boundary, not copied as the target corridor for every phase
- phase corridors above typical availability capacity are blocked unless explicitly marked as an exception and still below max capacity
- Base, Build, Peak, Transition, shortened/re-entry, B-event rehearsal, and A-event taper phases show distinct load semantics
- Deload, mini-reset, reload, re-entry, and taper behavior are numerically visible in phase and role-week bands
- durability-first keeps `RECOVERY` and dominant `ENDURANCE`, with targeted `TEMPO` or scenario-permitted quality only when coherent
- season authority for intensity domains comes from the selected scenario and deterministic season context; downstream phase restrictions must not be used to narrow the season bundle retroactively

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
