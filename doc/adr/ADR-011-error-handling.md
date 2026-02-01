# ADR-011: Error Handling (Retry vs Fail-Fast)

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Failures in planning flows can be transient (network, API) or structural (missing artefacts). We need consistent behavior across UI and orchestrators.

## Decision

- **Fail-fast** on structural errors (missing required artefacts, invalid schemas).
- **Retry** only for transient errors (timeouts, temporary API issues), and cap retries.
- UI must surface failure reason and next action.
- Run status must reflect failure in Run Store (FAILED + reason).

## Consequences

- Clear and predictable error behavior.
- Avoids hidden loops and duplicated work.

## Exceptions

None.
