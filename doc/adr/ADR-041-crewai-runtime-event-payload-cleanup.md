---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-12
Owner: Runtime / UI
---
# ADR-041: CrewAI Runtime Event Payload Cleanup

**Status:** Accepted  
**Date:** 2026-05-12

## Context

ADR-040 moved lifecycle telemetry to CrewAI's native event listener. A real Coach run then showed that some event payload fields were still poor: `CREW_TASK_*` stored the full injected task prompt through task-object stringification, and `CREW_*` sometimes collapsed to a generic `crew` label.

## Decision

Normalize CrewAI runtime payload labels before persisting them into the run-store.

Implementation rules:
- Probe a narrow set of safe object attributes such as `name`, `role`, `tool_name`, and `id`.
- Never stringify arbitrary task objects into telemetry fields.
- Fall back to the current run component, a short object-id form, or the object type name when no better label exists.
- Keep the existing event types and `events.jsonl` file layout unchanged.

## Consequences

- Positive outcomes
  - Run telemetry remains readable in both raw JSONL and UI tables.
  - Prompt-sized task payloads no longer leak into persisted runtime events.
  - The cleanup stays local to the listener adapter instead of spreading into UI renderers.
- Trade-offs / risks
  - Some rows may still use generic type-based fallback labels when CrewAI exposes little metadata.
  - Attribute probe lists may need minor maintenance if CrewAI changes runtime object shape.

## Exceptions

- Event ordering is unchanged by this ADR; this decision only cleans payload labels.
- Existing historical runs are not rewritten.
