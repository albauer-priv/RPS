---
Version: 1.1
Status: Superseded
Last-Updated: 2026-05-13
Owner: Coach / Workspace / UI
---
# ADR-043: Coach Current Week Actuals Context

**Status:** Superseded  
**Date:** 2026-05-13

Superseded by `ADR-044-coach-current-week-status-snapshot.md`.

## Context

Coach already uses persisted snapshot/advisory memory for athlete context, planning context, and the current week plan. That still leaves one blind spot: selected-week completed sessions up to now.

The historical activity block inside `PLANNING_CONTEXT_SNAPSHOT` intentionally points to the last complete reference week. That behavior is correct for planning stability and must not be replaced with a partial current-week view.

Users still need Coach to answer operational questions about what has already happened this week.

## Decision

Keep the historical planning snapshot unchanged and add a second, explicit current-week actuals layer for Coach only.

Implementation rules:

* `PLANNING_CONTEXT_SNAPSHOT` keeps the historical reference-week activity block.
* Coach resolves selected-week `ACTIVITIES_ACTUAL` directly and derives a `Current Week Actuals Snapshot` block.
* The block must be marked as partial and describe completed sessions in the current target week up to now.
* Coach startup summary includes a `Current Week Actuals` section when the block exists.
* No new persisted artefact type is introduced for this data.

## Consequences

* Positive outcomes
  * Coach can discuss "yesterday" and "this week so far" without extra agent/tool rediscovery.
  * Historical planning context stays stable and comparable across runs.
  * The new context remains clearly separated from binding planning memory.
* Trade-offs / risks
  * Current-week actuals are read dynamically rather than from a persisted memory artefact.
  * The block is only as fresh as the selected-week `ACTIVITIES_ACTUAL` workspace data.

## Exceptions

* If selected-week `ACTIVITIES_ACTUAL` is absent, Coach does not synthesize the block and falls back to existing memory only.
* The current-week actuals block is conversational context only and does not replace authoritative planning guardrails.
