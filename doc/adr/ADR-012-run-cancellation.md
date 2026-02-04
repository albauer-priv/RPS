---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-012: Run Cancellation (cancel_requested)

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Long-running runs should be cancellable without corrupting artefacts or leaving ambiguous state.

## Decision

- Introduce a `cancel_requested` flag in Run Store.
- Workers should check `cancel_requested` between steps and stop safely.
- On cancel: set status to `CANCELLED` with reason and timestamp.

## Consequences

- Safer stop behavior for long runs.
- UI can offer a clear cancel action.

## Exceptions

None.
