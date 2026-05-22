---
name: constraint-synthesis
description: Preserve athlete, availability, logistics, and event constraints in season planning and review.
metadata:
  author: rps
  version: "3.0"
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
- hard blockers: event immovability, zero-availability days, travel/work windows that eliminate training opportunity, explicit recovery protections
- soft constraints: preferred days, optional modality preferences, advisory scenario flavor
- unresolved uncertainty: incomplete availability, ambiguous logistics, unconfirmed event detail

Hard rules:
- use explicit athlete and logistics facts from upstream context
- keep hard blockers authoritative over scenario preference
- emit season-level constraint synthesis only
- do not make KPI semantics, historical continuity, or cadence/load philosophy the main output unless they directly prove or constrain a hard boundary
- keep event findings tied to actual planning events; event-free windows do not need synthetic negative findings

Retrieval policy:
- Use `workspace_get_input` for athlete-managed inputs such as `planning_events`, `athlete_profile`, `availability`, and `logistics`.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots.
- Use `workspace_get_version` only when the task explicitly requires a week-sensitive historical artefact version.

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
