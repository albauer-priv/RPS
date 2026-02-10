---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-002: Run Store is the Source of Truth for Planning Status

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Multiple pages need consistent, real-time planning status. Spreading status logic across pages risks divergence.

## Decision

Run status is persisted in the run store (`runtime/athletes/<athlete_id>/runs/<run_id>/*`) and is the single source of truth. UI pages read status via helpers (e.g., `get_planning_run_status`).

## Consequences

- System → Status and Plan Hub always reflect the same run state.
- Worker logic updates status in one place; UI only reads.

## Exceptions

None.
