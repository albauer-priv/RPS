---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-020: Run Housekeeping Retention

**Status:** Accepted  
**Date:** 2026-02-02  

## Context

Run history and queue files in `runtime/athletes/*/runs` grow quickly and clutter the workspace. We need automated cleanup that preserves recent runs while keeping queues clean.

## Decision

- Add a background housekeeping job that:
  - deletes run directories older than `RPS_RUN_RETENTION_DAYS` (default 7), and
  - clears queue items in `runtime/athletes/runs/queue/done` and `runtime/athletes/runs/queue/failed`.
- The job runs once per Streamlit session startup, using the same background tracker pattern as index cleanup.

## Consequences

- Keeps workspace size bounded without manual cleanup.
- Recent run history remains available for debugging.
- Done/failed queue items are ephemeral and may not be available after cleanup.

## Exceptions

- If retention needs to be longer for auditing, set `RPS_RUN_RETENTION_DAYS` to a larger value.
