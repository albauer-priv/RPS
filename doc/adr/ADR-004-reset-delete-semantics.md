---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-004: Latest Artefact Reset/Delete Semantics

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Athletes need a safe reset vs a full delete. Ambiguous behavior can cause accidental loss of scenario work.

## Decision

- **Reset** removes latest Season Plan, Phase artefacts, Week Plan, and Workouts exports.
- **Delete** removes the same plus Season Scenarios and Scenario Selection.

## Consequences

- Reset keeps scenario work intact.
- Delete clears planning context for a clean restart.

## Exceptions

None.
