---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Agents / Orchestrator
---
# ADR-037: CrewAI Flow Outer Orchestration

## Context
Season and Phase inner typed CrewAI execution already exists, but outer orchestration is still mostly RPS-first and scoped Phase runs can recompute the same internal bundle multiple times. Specialist agents also still reuse planner-level prompts.

## Decision
- Use CrewAI Flows as the outer execution wrappers for Season and Phase orchestration.
- Persist requested Phase public artefacts from one internal `PhaseBundle` per scoped Phase run.
- Give Season and Phase specialists dedicated prompt slices instead of top-level prompt reuse.

## Alternatives Considered
- Keep current orchestrators and only optimize Phase batching.
- Convert every remaining planning and advisory chain to CrewAI Flows immediately.

## Consequences
- Season/Phase execution becomes closer to the target Flow-first outer architecture.
- Public artefact contracts stay unchanged.
- Week/report/feed-forward remain separate follow-up work.
