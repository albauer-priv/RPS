---
name: blueprint-bound-writing
description: Constrain artifact writing to approved blueprints and deterministic context.
---
# Blueprint-Bound Writing

Artifact writers serialize approved planning decisions. They do not create new planning decisions.

Rules:

1. Use approved bundle blueprints as the write source.
2. Use deterministic context for dates, ranges, roles, load bands, availability, event implications, and syntax constraints.
3. Do not use CrewAI memory, advisory memory, or narrative recollection for structural fields.
4. Preserve schema validity and runtime-owned metadata boundaries.
5. If a required blueprint field is missing, return a blocker rather than filling by guess.
6. Writers do not perform primary semantic repair. If bundle semantics still need reinterpretation, approval was upstream-incorrect and the output is not writer-ready.

Output expectation:

- Final JSON must be schema-valid and contract-consistent.
- Narrative text may explain the approved blueprint but must not alter it.
