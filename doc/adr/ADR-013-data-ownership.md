---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-013: Data Ownership (Source of Truth vs Derived)

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Multiple artefacts represent planning and analysis data. Without clear ownership, updates can conflict or create stale chains.

## Decision

- **Source of truth**: inputs (Athlete Profile, Planning Events, Logistics, KPI Profile, Availability) and raw pipeline outputs (activities_actual, activities_trend, zone_model, wellness).
- **Derived**: season/phase/week plans, previews, exports, and reports.
- Derived artefacts must reference their source context via meta headers.

## Consequences

- Clear dependency chain for validity and staleness checks.
- Fewer ambiguous updates.

## Exceptions

None.
