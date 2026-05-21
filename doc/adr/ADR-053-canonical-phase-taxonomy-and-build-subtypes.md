---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-21
Owner: ADR
---
# ADR-053: Canonical Phase Taxonomy and Build Subtypes

**Status:** Accepted  
**Date:** 2026-05-21  

## Context

RPS already persists phase semantics, but the current contract uses repo-specific `phase_intent` values and a separate `cycle` label that do not map cleanly to standard periodization language. Build semantics are also under-specified because there is no explicit selector key for Build-specific focus.

This creates four problems:

1. planner/runtime semantics are harder to audit end to end,
2. Build-specific workout selection remains more implicit than intended,
3. legacy terms mix macro-period, block purpose, and week-shape semantics,
4. migration safety is weaker when unknown legacy values are normalized too loosely.

## Decision

RPS will adopt a canonical semantic phase model:

* `phase_type` = macro-period container
* `phase_intent` = primary methodological purpose
* `build_subtype` = explicit Build selector key

Canonical `phase_type` values:

* `TRANSITION`
* `PREPARATION`
* `BASE`
* `BUILD`
* `PEAK`
* `TAPER`
* `RACE`

Canonical `phase_intent` values are constrained by `phase_type`.

For `phase_type = BUILD`:

* `build_subtype` is required,
* `build_subtype` must equal `phase_intent`.

This redundancy is intentional. `build_subtype` is not a second semantic degree of freedom. It is an explicit selector and audit key that makes Build-specific downstream behavior deterministic.

Additional migration rules:

* new writes may emit only canonical taxonomy values,
* legacy reads may normalize through an explicit mapping layer,
* unknown legacy values must fail closed,
* taxonomy version is persisted in `data.body_metadata.phase_taxonomy_version` where body metadata exists.

Season-planning propagation rule:

* canonical phase semantics are code-owned, not writer-inferred,
* raw Season/Phase finalizer outputs are draft state only and must not be treated as canonical semantics,
* Python normalization is the required boundary between draft planning output and review/writer-safe bundle state,
* Season bundle/review/writer handoff must carry deterministic `phase_type`, `phase_intent`, `build_subtype`, `phase_taxonomy_version`, and code-owned semantic-contract fields,
* methodology-critical fields such as allowed/forbidden domains, threshold role, taper/event-kJ framing, and season load-envelope must be validated before writer execution,
* writer tasks serialize approved Season semantics rather than rediscovering them from prose.

## Consequences

- Positive outcomes
  - Stronger, clearer planner semantics across Season -> Phase -> Week -> Workout selection.
  - Build focus becomes explicit and audit-friendly.
  - Legacy taxonomy drift is contained to a well-defined normalization boundary.
  - New writes are schema-enforced against canonical semantics.
  - Season bundle/review/writer propagation becomes deterministic and auditable, instead of relying on prompt-only compliance.
  - Season and Phase now share the same draft-to-normalized ownership boundary, reducing cross-level contract drift.

- Trade-offs / risks
  - This is a breaking semantic migration for new writes.
  - Several cross-layer contracts and validators must be updated together.
  - A few legacy mappings require rollout validation before long-term trust:
    - `general_build`
    - `build_progression`
    - `transition_coupling`

## Exceptions

* Legacy artifacts remain readable through explicit normalization during migration.
* `week_role` remains a separate follow-up taxonomy; it is not folded into `phase_intent` in this ADR.
