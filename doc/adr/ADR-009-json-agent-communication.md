---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-009: JSON as Primary Agent Communication Format

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Agent interactions require consistency to avoid parsing errors and to support schema validation.

## Decision

Prefer JSON for communication between agents and tooling.
- All outputs should conform to JSON schemas.
- Free-text content should be nested inside JSON fields (e.g., `summary`, `notes`).

## Consequences

- Stronger schema validation and easier tooling integration.

## Exceptions

None.
