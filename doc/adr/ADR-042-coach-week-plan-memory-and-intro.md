---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-13
Owner: Coach / Workspace / UI
---
# ADR-042: Coach Week-Plan Memory and Intro Summary

**Status:** Accepted  
**Date:** 2026-05-13

## Context

Coach already consumes snapshot-based memory first, but the memory layer only carried a minimal week summary and did not expose the concrete selected-week workout list. Users also had no immediate visible confirmation of the exact phase/week context loaded into Coach.

## Decision

Extend the existing memory system rather than creating a new Coach-only context path.

Implementation rules:
- Enrich `ADVISORY_MEMORY` with a derived current-week plan summary block from the latest `WEEK_PLAN`.
- Insert one deterministic assistant intro message on a fresh Coach context using loaded memory and pending-operation state.
- Refresh `ADVISORY_MEMORY` after successful Coach-applied week-plan changes.
- Do not add a dedicated model call for startup summary generation.

## Consequences

- Positive outcomes
  - Coach gets the concrete week plan directly through memory.
  - Users can immediately verify the loaded phase/week context.
  - The fix stays inside the accepted snapshot-memory architecture.
- Trade-offs / risks
  - Startup intro is deterministic text, not model-authored.
  - Advisory-memory refresh points must remain complete when more Coach write paths are added.

## Exceptions

- The intro message is informational only and does not replace the later conversational Coach turn.
- If memory artefacts are absent, Coach still falls back to the existing raw preload/tool path.
