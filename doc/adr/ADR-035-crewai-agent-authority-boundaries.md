---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime / Planning
---
# ADR-035: CrewAI Agent Authority Boundaries

## Context

After the hard CrewAI cutover, runtime execution was unified, but authority boundaries were still partly blurred across docs, YAML config, and output normalization. The largest inconsistencies were:

- `SEASON_PHASE_FEED_FORWARD` still appeared in some places as if it were a `Performance-Analyst` output.
- Phase responsibility wording risked implying that cadence selection belonged to `Phase-Architect`.
- CrewAI config still reflected only coarse top-level agents, without the internal specialist split already established in architecture discussions.

The binding repo contracts and principles already define a stricter ownership model.

## Decision

Adopt these authority boundaries:

1. `Season-Scenario-Agent` is advisory only.
2. `Season-Planner` is the first binding planning authority.
3. `Season-Planner` owns `SEASON_PLAN` and `SEASON_PHASE_FEED_FORWARD`.
4. `Phase-Architect` owns `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, `PHASE_PREVIEW`, and `PHASE_FEED_FORWARD`.
5. `Week-Planner` is strict executor only.
6. `Performance-Analyst` is diagnostic only and owns `DES_ANALYSIS_REPORT` only.
7. `Coach` is an orchestration surface, not an artefact-authoring planning authority.
8. Cadence selection belongs to Scenario/Season, with Season as the binding decision point; Phase may only apply season-selected cadence.

Also adopt the internal CrewAI foundation split:

- Season specialist roles: scenario interpretation, event anchors, macrocycle architecture, load governance, constraints, historical context, KPI guidance, and season audit.
- Phase specialist roles: guardrails, structure, cadence/recovery integration, intensity distribution, preview synthesis, constraint audit, and load-governance audit.

These internal roles do not introduce new persisted artefact authorities by themselves.

## Consequences

Positive:

- Persisted artefact ownership now matches binding contracts.
- Docs and runtime metadata are aligned.
- Future hierarchical Crew execution has a stable internal role vocabulary.
- Phase cadence handling is correctly scoped as application, not selection.

Tradeoffs:

- The internal specialist split exists in config/models before full hierarchical runtime execution is enabled.
- Some internal roles are currently foundation-only.

## Alternatives Considered

### Keep coarse agent ownership until later

Rejected because it preserves real contradictions in contracts vs runtime/docs.

### Introduce full hierarchical season/phase execution in the same change

Deferred because it is larger than the authority cleanup itself and would raise rollout risk unnecessarily.
