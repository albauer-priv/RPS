---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-14
Owner: Architecture
---
# ADR-048: Skills-First Multi-Crew Planning Runtime

## Context

RPS has already moved toward a skills-first methodology layer, but the planning runtime still compresses planning, review, and writing into overly broad managers and thin single-task flows. The knowledge migration is incomplete, and several skills still point to minimal placeholders rather than the real planning rules.

## Decision

Adopt a skills-first, multi-crew planning runtime for Season, Phase, Week, and Report.

The standard planning topology becomes:
- Planning Crew
- Review Crew
- Writer Crew
- Outer Flow Router with bounded replan rounds

Additional decisions:
- skills are the canonical planning knowledge layer
- contracts and schemas remain explicit machine-layer artifacts
- managers coordinate but do not absorb holistic review as a side responsibility
- writers only serialize approved outputs
- Coach and Workout Editor reuse the Week specialist family instead of maintaining separate knowledge systems

## Alternatives considered

### Keep one crew and overload the manager
Rejected because it preserves hidden role blending and prevents skill-pure specialization.

### Keep planning knowledge mainly in legacy specs and only link from skills
Rejected because it leaves the runtime dependent on non-canonical prose outside the skill system.

## Consequences

Positive:
- clearer skill boundaries
- cleaner agent/task ownership
- explicit review and replan semantics
- better reuse between planning surfaces and conversational surfaces

Negative:
- more runtime/config complexity
- more internal models and tasks to maintain
- migration cost for knowledge references

## Follow-up requirements

- migrate substantive planning knowledge into skill references
- add internal bundle/review/replan models
- recut agents, tasks, and bundles
- update flow wrappers to multi-crew routing
