---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-22
Owner: ADR
---
# ADR-055: Season Semantic Recovery and Guardrail Serialization

**Status:** Accepted  
**Date:** 2026-05-22  

## Context

RPS already owns canonical phase taxonomy and deterministic season load context, but the final `SEASON_PLAN` still left several semantics under-specified or prompt-sensitive:

* `RECOVERY` was not treated consistently as a legal non-quality execution domain.
* `allowed_load_modalities` could collapse to `["K3"]`, which makes K3 appear mandatory.
* `events_constraints` could contain synthetic “no event” placeholders instead of real event anchors only.
* deterministic role-week load bands existed structurally upstream but were not consistently visible in the final season artifact.
* the primary season objective can materially mismatch the highest in-horizon A event, and this must be visible without blocking the user-owned plan flow.

These are cross-cutting semantic-contract concerns rather than one-off writer issues.

## Decision

RPS will treat these season semantics as code-owned and generic:

* `RECOVERY` is a systemwide legal non-quality execution domain across the canonical phase taxonomy unless an explicit hard override blocks it.
* Canonical load modalities are derived from phase semantics, not from writer prose:
  * `TRANSITION`, `PEAK`, `TAPER`, `RACE` => `["NONE"]`
  * `BASE`, `BUILD` => `["NONE", "K3"]`
  * `PREPARATION` => `["NONE"]` by default
* `SEASON_PLAN.events_constraints` contains only real A/B/C planning events; synthetic “no event” entries are not serialized there.
* Structured deterministic role-week bands remain the validation source of truth and are additionally rendered into existing season-plan narrative fields for auditability.
* Objective/A-event mismatch detection is warning-only:
  * it must be surfaced in the final plan,
  * it must not block finalization,
  * correction ownership remains upstream/user-owned.

## Consequences

- Positive outcomes
  - Final season artifacts become more audit-friendly without a schema migration.
  - Downstream Phase/Week planning receives cleaner canonical semantics.
  - Taper and event semantics become less vulnerable to writer drift.
  - Objective mismatches are transparent without stopping user workflows.

- Trade-offs / risks
  - Multiple planning layers must stay aligned: canonical semantics, normalization, contracts, prompts, and tests.
  - Role-week bands become visible text, which requires careful separation between human rendering and structured validation.
  - Exact event-date serialization must remain compatible with the existing `SeasonPlanInterface`.

## Exceptions

* If `events_constraints.window` exact dates are not schema-compatible in one path, the runtime may retain a schema-valid representation while still validating against the true event date internally.
* Objective/A-event mismatch remains non-blocking by design, even when clearly material.
