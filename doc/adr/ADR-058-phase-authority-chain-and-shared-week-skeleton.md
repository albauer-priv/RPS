---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-29
Owner: Planning Runtime
---
# ADR-058: Phase Authority Chain and Shared Week Skeleton

## Context

Phase planning inherited the selected-scenario contract from Season and also consumed exact-range S5/load context. In practice this created an ambiguous authority split:

* scenario-level posture could be treated as if it directly authorized exact phase legality
* exact role-week load bands could be re-derived or narrowed from S5
* Preview and Week could evolve separate day-role/domain semantics

This was visible in downstream Phase artifacts that widened Base-phase domains and rewrote exact weekly kJ bands without a formal upstream change.

## Decision

Adopt a strict one-way authority chain:

1. `selected_scenario_contract` is a season-wide posture ceiling only.
2. Persisted `SEASON_PLAN.data.phases[]` is the binding source for:
   * exact phase legality
   * phase-local objective
   * exact structured `role_week_load_bands`
3. `phase_execution_context` projects that persisted Season phase authority directly.
4. S5 remains feasibility/reference context only and must not silently overwrite exact persisted phase week bands.
5. `PHASE_PREVIEW` and `WEEK_PLAN` align through one shared deterministic week skeleton.

Supporting decisions:

* legacy string `role_week_load_bands` remain readable
* new Season writes use structured `role_week_load_bands`
* objective mismatch remains warning-only
* writer remains serialization-only and may not repair authority drift

## Alternatives Considered

### Prompt-only authority hardening

Rejected. It leaves runtime authority ambiguous and does not prevent normalization or writer-stage drift.

### Keep S5 as the exact downstream weekly-band source

Rejected. S5 is broader feasibility context and is not the same as persisted Season-owned exact phase authority.

## Consequences

### Positive

* exact phase legality is deterministic and auditable
* exact role-week load bands are stable across Season -> Phase -> Preview -> Week
* Preview and Week share one semantic day-shape source
* legacy Season plans remain readable without batch migration

### Negative

* schema and internal model surfaces must support structured `role_week_load_bands`
* normalization, validation, snapshots, prompts, and renderers must stay aligned

## Follow-up

* keep active Phase/Week prompts and tasks aligned with the authority split
* maintain shared-skeleton validation as Week planning evolves
* avoid reintroducing scenario-level legality widening in future planner files
