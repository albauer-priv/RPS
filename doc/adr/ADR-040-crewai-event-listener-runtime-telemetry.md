---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime / UI
---
# ADR-040: CrewAI Event Listener Runtime Telemetry

**Status:** Accepted  
**Date:** 2026-05-12

## Context

RPS already exposes run telemetry through its local run-store and UI. After the CrewAI cutover, Flow/Crew lifecycle events were still being emitted manually from multiple code paths even though CrewAI documents a central event bus with `BaseEventListener` for lifecycle instrumentation.

## Decision

Use CrewAI's native event listener system as the primary source for Flow/Crew/Task/Tool runtime telemetry.

Implementation rules:
- Register one singleton listener derived from `BaseEventListener`.
- Use a per-run context adapter to map CrewAI lifecycle events into the current `events.jsonl` target.
- Keep manual emission only for RPS-specific events without a CrewAI equivalent, such as `ARTEFACT_WRITTEN` and optional route markers.

## Consequences

- Positive outcomes
  - Telemetry is now CrewAI-first instead of RPS-emulated.
  - Fewer duplicated lifecycle hooks across runtime code.
  - Broader event coverage becomes available with less code.
- Trade-offs / risks
  - We depend on CrewAI event class names and listener API shape.
  - Context propagation must stay correct for nested Flow/Crew execution.

## Exceptions

- `ARTEFACT_WRITTEN` remains a manual RPS event because guarded-store persistence is outside CrewAI lifecycle ownership.
- If CrewAI listener registration fails at runtime, execution must continue without blocking planning.
