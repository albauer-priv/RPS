---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-017: Intervals Posting Policy

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Posting to Intervals is irreversible and should be safe and idempotent.

## Decision

- Posting is manual/explicit.
- Receipts are used for idempotency.
- Deletes only happen when explicitly enabled.

## Consequences

- Safer external side effects.
- Clear user control over deletes.

## Exceptions

None.
