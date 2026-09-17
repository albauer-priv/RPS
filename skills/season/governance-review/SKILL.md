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
- phase corridors above the deterministic `availability_load_capacity_kj` **max cap** are blocked unless explicitly marked as an exception; corridors between typical and max are valid with progression rationale
- Base, Build, Peak, Transition, shortened/re-entry, B-event rehearsal, and A-event taper phases show distinct load semantics
- Deload, mini-reset, reload, re-entry, and taper behavior are numerically visible in phase and role-week bands
- durability-first keeps `RECOVERY` and dominant `ENDURANCE`, with targeted `TEMPO` or scenario-permitted quality only when coherent
- season authority for intensity domains comes from the selected scenario and deterministic season context; downstream phase restrictions must not be used to narrow the season bundle retroactively

Blocker vs warning discipline:
- raise a `blocking_issue` only for:
  - a phase corridor that materially exceeds the athlete's demonstrated historical maximum
  - a corridor that exceeds the deterministic `availability_load_capacity_kj` **max cap**
  - a missing or zero baseline that makes corridor derivation impossible
  - a structurally undefined cadence or phase-role assignment
- do **not** raise a `blocking_issue` for:
  - a corridor that is above a recent disrupted week's actual load — when the most recent week
    `W_prev_actual < BL_kJ × 0.85`, the disrupted-week rule applies: use `BL_kJ` as anchor;
    a corridor at `BL_kJ × 0.85–1.05` is valid re-entry, not overreach
  - a standard re-entry corridor within `BL_kJ × 0.85–1.05`
  - a corridor between typical and max availability capacity when progression rationale is given
  - `RELOAD → TAPER` phase adjacency — that is a structural warning; recommend restructuring the
    preceding phase's final week but do not block unless the taper window is shorter than the
    minimum effective window (2–3 weeks including event week for events > 12 hours)
  - a domain coherence narrative note (e.g. a forbidden domain mentioned in prose) — that is a
    finalize-pass coherence warning, not a governance blocker
- use `warnings` (not `blocking_issues`) for concerns the review crew should see but that do not
  prevent a valid plan from being submitted

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
