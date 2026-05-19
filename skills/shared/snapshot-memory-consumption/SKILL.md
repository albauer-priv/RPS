---
name: snapshot-memory-consumption
description: Consume code-owned snapshot memory while keeping CrewAI memory non-binding.
---
# Snapshot Memory Consumption

Snapshot artifacts are code-owned derived context. CrewAI memory is assistive only.

Rules:

1. `ATHLETE_STATE_SNAPSHOT` and `PLANNING_CONTEXT_SNAPSHOT` are authoritative derived context only when fresh for the current run.
2. `ADVISORY_MEMORY` is non-binding narrative context.
3. CrewAI memory is non-binding and must never override artifacts, deterministic contracts, schemas, or snapshot source versions.
4. If snapshot source versions conflict with loaded authority artifacts, stop or request replan.
5. Prefer injected fresh snapshot blocks before using tools to rediscover the same resolved facts.

Output expectation:

- Cite snapshot refs as derived context when used.
- Mark advisory/CrewAI memory as non-binding when it influences narrative only.
