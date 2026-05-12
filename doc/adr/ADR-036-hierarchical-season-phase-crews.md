---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime / Planning
---
# ADR-036: Hierarchical Season and Phase Crew Execution

## Context

The CrewAI cutover established typed persisted artefact execution and a specialist foundation for Season and Phase, but actual runtime execution still behaved like one final task per artefact. This left the internal specialist split unused.

Season and Phase are the two planning steps with enough internal reasoning complexity to justify specialized CrewAI subtasks while keeping the external persistence boundary stable.

## Decision

Implement internal hierarchical execution for:

1. `SEASON_PLAN`
   - run specialist subtasks first
   - pass their structured findings to the Season manager
   - persist only the manager-authored `SEASON_PLAN`

2. `PHASE_GUARDRAILS` / `PHASE_STRUCTURE` / `PHASE_PREVIEW`
   - run specialist subtasks and audits first
   - finalize an internal `PhaseBundle`
   - deterministically select the requested nested phase document from the bundle
   - persist only the requested public phase artefact

Do not change outer orchestrators or public artefact schemas in this decision.

## Consequences

Positive:

- Season/Phase specialist roles now have real runtime meaning.
- Public contracts stay stable.
- Internal bundle/audit models are exercised in code, not only in docs.

Tradeoffs:

- Outer Flow ownership is still deferred.
- Internal specialists currently reuse top-level prompt families via prompt-agent mapping.
- `PhaseBundle` is internal only, so bundle state is not visible as a stored artefact.

## Alternatives Considered

### Keep direct single-task execution

Rejected because it leaves the specialist split unused and undermines the intended CrewAI architecture.

### Introduce full Flow migration first

Deferred because it is larger and not required to start using the specialist split safely.
