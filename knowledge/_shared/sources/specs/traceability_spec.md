---
Type: Specification
Specification-For: TRACEABILITY
Specification-ID: TraceabilitySpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Data-Pipeline
  - Season-Planner
  - Phase-Architect
  - Week-Planner
  - Workout-Builder

Notes: >
  Defines mandatory traceability, Run-ID semantics, upstream reference rules,
  and precedence logic across all artefacts. This specification governs
  artefact headers and lineage consistency and is required for CI validation.
---

# Traceability Specification

## 1. Purpose
Define mandatory traceability rules across all artefacts:
- upstream references
- run identity
- precedence rules for updates (e.g., Feed Forward)

## 2. Global Requirements
The `meta` object structure is defined in `artefact_meta.schema.json`. This spec
adds semantic requirements for traceability and run identity.

If an artefact has no upstream (e.g., Data-Pipeline raw outputs), it MUST include:
- `trace_upstream: []`

## 3. Run-ID
- `run_id` MUST be a non-empty string.
- Recommended format (not mandatory): `YYYYMMDD-HHMMSS-<agent>-<shortid>`
- A Run-ID identifies ONE generation run and MUST NOT be reused for a different artefact.

## 4. Upstream Trace Rules
### Season outputs
- MUST reference Season Brief (if present) or equivalent upstream input identifier in `trace_upstream`.

### Phase outputs (Phase-Architect)
- MUST reference exactly one `season_plan_yyyy-ww--yyyy-ww.json` in `trace_upstream`.

### Week outputs (Week-Planner)
- MUST reference exactly one `phase_guardrails_yyyy-ww--yyyy-ww.json` in `trace_upstream`.
- If a `phase_feed_forward_yyyy-ww.json` is applied, it MUST also be referenced.

### Workout-Builder outputs
- MUST reference the input `week_plan_yyyy-ww.json` (or `workout_request_*` if introduced later).

## 5. Precedence & “Latest Valid” Rules
### phase_feed_forward_yyyy-ww.json precedence
If multiple `phase_feed_forward_yyyy-ww.json` artefacts exist:
- Apply the one with:
  1) scope covering the target week, AND
  2) `Valid-Until` not expired, AND
  3) latest `Created-At`

If conflicts remain → STOP and escalate.

### Data precedence
If multiple Data-Pipeline artefacts exist for the same `yyyy-ww`:
- Choose latest `Created-At` with same `Data-Window` (if specified),
- otherwise choose latest `Created-At`.

## 6. Immutability
Published artefacts are immutable.
Changes require creating a new artefact with:
- new `run_id`
- updated `created_at`
- proper upstream references
