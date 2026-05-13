---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-13
Owner: Coach / Workspace / Intervals
---
# ADR-044: Coach Current Week Status Snapshot

**Status:** Accepted  
**Date:** 2026-05-13

## Context

Coach needs a current-week "what is planned vs what already happened" view. The stable historical activity context inside `PLANNING_CONTEXT_SNAPSHOT` must remain based on the last complete historical week and must not be replaced by partial-week data.

Directly reading current-week `ACTIVITIES_ACTUAL` inside Coach is not the correct solution:

* current-week partial actuals are not owned by the stable historical snapshot contract
* Coach should consume code-owned memory rather than ad-hoc raw reads
* current-week actuals require a separate live Intervals.icu fetch path

## Decision

Introduce a dedicated persisted `CURRENT_WEEK_STATUS_SNAPSHOT` for Coach.

Rules:

* Historical `Resolved Activity Context` in `PLANNING_CONTEXT_SNAPSHOT` remains unchanged.
* `CURRENT_WEEK_STATUS_SNAPSHOT` is the only Coach memory layer for partial current-week actuals.
* Snapshot refresh for the selected current week uses the existing Intervals.icu API + normalization helpers and persists the result before Coach consumes it.
* Snapshot freshness for the current week is governed by:
  * a short TTL
  * latest selected-week `WEEK_PLAN` version match
* Coach startup summary uses this snapshot for:
  * current-week actuals
  * deterministic plan-vs-actual comparison

## Consequences

* Positive outcomes
  * Coach remains snapshot-first.
  * Current-week state is inspectable and reproducible in the workspace.
  * Plan-vs-actual remains deterministic code logic, not model speculation.
* Trade-offs / risks
  * Adds another derived context artefact.
  * Requires periodic live Intervals fetch for the current week.

## Exceptions

* If live current-week refresh fails, Coach may reuse an existing snapshot if present.
* If no snapshot exists and refresh fails, Coach falls back to the remaining memory layers without inventing current-week actuals.
