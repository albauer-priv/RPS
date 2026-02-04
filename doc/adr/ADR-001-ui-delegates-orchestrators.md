---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-001: UI Pages Delegate to Orchestrators

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

UI pages were mixing presentation and controller logic (agent calls, worker loops). This made reuse from other pages (e.g., System → Status) harder and duplicated flow logic.

## Decision

UI pages must remain UI-only. All run execution, worker loops, and agent calls live in orchestrator/service helpers. UI pages call a single helper per action and read status from shared helpers.

## Consequences

- Plan Hub is UI-only; background worker lives in `rps.orchestrator.plan_hub_worker`.
- System/Status can show planning worker status via shared helper.
- Future actions should be added to orchestrator modules, not UI pages.

## Exceptions

None.
