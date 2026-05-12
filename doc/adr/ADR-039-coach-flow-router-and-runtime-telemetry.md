---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime / UI
---
# ADR-039: Coach Flow Router and Runtime Telemetry

## Context

The repository now uses CrewAI as the only runtime, outer flows for planning/advisory chains, and hierarchical crews for season/phase internals. The Coach page and direct UI-triggered runs still lacked two things:

* a real Flow-owned routing boundary for confirmation/apply/discard behavior
* visible runtime telemetry for Flow and Crew execution outside background Plan Hub runs

## Decision

1. Coach turns are routed through an explicit CrewAI Flow wrapper.
2. The Coach Flow handles explicit confirmation/discard/pending-status routes before falling back to the general Coach tool-based turn.
3. Flow and Crew execution append additive run-store events to `events.jsonl` for both direct foreground runs and orchestrated runs.
4. Plan Hub, System Status, and System History render these Flow/Crew events as readable telemetry.

## Alternatives considered

### Keep Coach page-local orchestration

Rejected because confirmation/apply logic would stay fragmented in the page and runtime visibility would remain poor.

### Build a full deterministic Coach intent classifier first

Rejected for now because it delays the requested observability and provides limited immediate operational value.

## Consequences

### Positive

* Coach behavior aligns better with the Flow-first outer orchestration direction.
* Direct UI runs now produce inspectable runtime traces similar to queued background runs.
* Runtime debugging becomes materially easier for season/phase/week/report/feed-forward and Coach-triggered operations.

### Negative

* More event types increase event-log volume.
* Coach routing still uses a narrow heuristic layer for explicit confirm/discard paths.

## Guardrails

* Event writes must remain best-effort and must not block the main flow result.
* Guarded store remains the persistence boundary; telemetry does not change artefact ownership or validation.
* Existing run readers must remain compatible with additive event types.
