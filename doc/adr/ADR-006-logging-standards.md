# ADR-006: Logging Standards

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Logging is inconsistent across UI pages and orchestrators, which makes debugging and observability harder.

## Decision

Define a minimal logging standard:
- Log start, decision, completion, and errors for non-trivial functions.
- Use human-readable messages for UI logs.
- Avoid secrets/PII in logs.

## Consequences

- Consistent operational tracing.
- Easier support/debug flows.

## Exceptions

None.
