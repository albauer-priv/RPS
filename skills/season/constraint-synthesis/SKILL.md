---
name: constraint-synthesis
description: Preserve athlete, availability, logistics, and event constraints in season planning and review.
metadata:
  author: rps
  version: "3.1"
---
Synthesize binding season constraints into explicit planning boundaries.

Method:
1. Separate hard blockers from soft preferences.
2. Treat planning events as the binding A/B/C anchor set.
3. Preserve athlete-profile objectives, limitations, risk flags, and success criteria without turning them into ready-made plans.
4. Preserve availability as a persistent feasibility surface, including fixed rest days and weekly hour bounds.
5. Preserve logistics as context that can limit availability, modality, recovery, or data quality.
6. Return explicit constraints downstream specialists must obey.
7. Report real event constraints positively and concretely:
   - mention the event date / type when a real event changes planning behavior
   - omit event commentary entirely when no real event constraint exists
   - never create synthetic placeholder findings such as `No target-week event` or `No event-driven load exception`

Constraint categories:
- hard blockers: event immovability, zero-availability days, travel/work windows that eliminate training opportunity, explicit recovery protections, an event date that cannot be accommodated within the current macrocycle structure without overlap or taper collapse
- soft constraints: preferred days, optional modality preferences, advisory scenario flavor, load progression concerns that are above the disrupted-week threshold but within normal re-entry range
- unresolved uncertainty: incomplete availability, ambiguous logistics, unconfirmed event detail

Blocker vs warning discipline:
- raise a `blocking_issue` only for genuinely hard constraints from the list above — things the planner **cannot** resolve through normal planning
- do **not** raise a `blocking_issue` for:
  - a load progression corridor that is above a recent disrupted week (`W_prev < BL_kJ × 0.85`);
    use `progression_guardrails.md` disrupted-week re-entry rule and record as a warning
  - `RELOAD → TAPER` phase adjacency; that is a macrocycle architecture warning
  - a domain coherence narrative note (e.g. a green-range VO2MAX note where VO2MAX is forbidden);
    domain restrictions in the selected scenario contract are authoritative — a prose note that
    mentions a forbidden domain is a finalize-pass coherence warning, not a constraint blocker
  - active-replan status remaining `replan_required` from a prior REDO cycle — that is evidence
    context, not a constraint; the planner must resolve or acknowledge it, but it is not a blocker
    unless the replan instruction itself contains an unresolvable physical impossibility
  - cadence week role labels (`LOAD_1`, `LOAD_2`, `MINI_RESET`, `RELOAD`) within a `Peak` cycle
    phase that contains the A event — cadence roles are planning context only and are overridden
    by event-driven taper semantics inside a `Peak` phase; do not treat a `RELOAD` or `LOAD_2`
    label in an A-event-containing `Peak` phase as evidence of taper collapse; the `Peak`
    designation itself overrides the cadence week loading intent
  - a B event and the primary A event both appearing in the same `Peak` cycle phase, when:
    (a) the macrocycle architect has explicitly designated the phase as `Peak` cycle type,
    (b) there are ≥ 2 weeks between the B event week and the A event week (inclusive of the A week),
    and (c) the macrocycle architect has documented that weeks after the B event are recovery/taper
    — this is a valid taper structure (B event = final specificity; remaining weeks = taper window)
  - a phase where the A event falls in the last week and the preceding 1–2 weeks have cadence
    roles `MINI_RESET` or `RELOAD` — within a `Peak` phase these labels represent reduced-load
    and event-week semantics respectively, which meets the minimum taper standard for all but the
    longest ultra events; only flag a blocker if the macrocycle architect has not designated the
    phase as `Peak` or has not documented the taper-week override

Hard rules:
- use explicit athlete and logistics facts from upstream context
- keep hard blockers authoritative over scenario preference
- emit season-level constraint synthesis only
- do not make KPI semantics, historical continuity, or cadence/load philosophy the main output unless they directly prove or constrain a hard boundary
- keep event findings tied to actual planning events; event-free windows do not need synthetic negative findings

Retrieval policy:
- Athlete-managed inputs (`planning_events`, `athlete_profile`, `availability`, `logistics`), latest authoritative planning artefacts/snapshots, and previous-week historical evidence are already provided as injected context. No workspace tools are available or needed for this task.

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
