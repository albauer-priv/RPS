---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-016: Staleness Policy for Wellness / Zone Model

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Planning depends on wellness and zone model data, but these can become stale.

## Decision

Treat wellness and zone_model as stale if older than 4 weeks relative to target ISO week.

## Consequences

- Encourages refreshed inputs before planning.
- Consistent readiness gating.

## Exceptions

None.
