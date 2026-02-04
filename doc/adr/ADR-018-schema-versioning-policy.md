---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-018: Schema Versioning Policy

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Schemas are used by agents and validators. Breaking changes must be explicit.

## Decision

- No schema changes without changelog/version bump.
- Bundled schemas must be re-generated after changes.
- All tool schemas must list every property in `required`.

## Consequences

- Predictable compatibility for agents and validators.

## Exceptions

None.
