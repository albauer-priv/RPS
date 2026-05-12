---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Agents / Orchestrator
---
# ADR-038: CrewAI Advisory Flows and True Hierarchical Crews

## Context
Season/Phase outer flows are already in place, but Week/report/feed-forward orchestration still uses direct RPS helper calls and inner Season/Phase specialist execution still runs through repeated one-task crews instead of one true hierarchical CrewAI crew.

## Decision
- Move outer Week / Report / Feed-Forward orchestration to CrewAI Flow wrappers.
- Replace serial specialist-task execution for Season and Phase with one real hierarchical CrewAI crew per run.

## Alternatives Considered
- Keep advisory/week orchestration direct and only change inner crews.
- Defer all remaining flow work until a later larger rewrite.

## Consequences
- The runtime becomes more consistently CrewAI-owned.
- Public artefact contracts remain unchanged.
- Coach orchestration remains a separate follow-up step.
