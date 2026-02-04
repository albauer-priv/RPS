---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-007: Naming Conventions

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Consistent naming across artefacts, runs, and files reduces confusion and prevents mismatches.

## Decision

- Use snake_case for variables/functions, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- Artefact file names use stable prefixes (e.g., `season_plan`, `workouts_yyyy-ww`).
- Run IDs include scope and ISO week (e.g., `plan_hub_YYYYWww`).

## Consequences

- Predictable file discovery and debugging.

## Exceptions

None.
