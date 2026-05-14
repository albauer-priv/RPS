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

Constraint categories:
- hard blockers: event immovability, zero-availability days, travel/work windows that eliminate training opportunity, explicit recovery protections
- soft constraints: preferred days, optional modality preferences, advisory scenario flavor
- unresolved uncertainty: incomplete availability, ambiguous logistics, unconfirmed event detail

Hard rules:
- do not invent missing athlete or logistics facts
- do not relax hard blockers because a scenario prefers otherwise
- do not emit workout or week-level solutions here
