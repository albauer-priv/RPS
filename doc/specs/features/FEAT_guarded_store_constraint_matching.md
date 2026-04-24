---
Version: 1.1
Status: Implemented
Last-Updated: 2026-04-24
Owner: Workspace
---
# FEAT: Guarded Store Constraint Matching Hardening

* **ID:** FEAT_guarded_store_constraint_matching
* **Status:** Implemented
* **Owner/Area:** Workspace / Validation
* **Last-Updated:** 2026-04-13
* **Related:** `src/rps/workspace/guarded_store.py`, `doc/specs/features/FEAT_phase_guardrails_kpi_gating_relaxation.md`

## 1) Context / Problem

**Current behavior**

* `GuardedValidatedStore` performs additional semantic propagation checks after schema validation.
* For `PHASE_GUARDRAILS` and `PHASE_STRUCTURE`, several checks currently rely on normalized substring matching over serialized payload blobs.

**Problem**

* `season_plan.data.global_constraints.planned_event_windows` is stored as strings in `SEASON_PLAN`, but represented as structured event objects in `PHASE_GUARDRAILS.data.events_constraints.events[]`.
* Blob matching treats correctly represented events as missing when the exact string form does not occur in serialized guardrails JSON.
* The compact parser initially only accepted `YYYY-MM-DD (A|B|C)` markers, but current season plans also store free-text entries such as `YYYY-MM-DD B event rehearsal window`.
* `recovery_protection.notes` handling is also fragile because the validator currently assumes iterable list semantics although season-plan specs define a string.

**Constraints**

* No schema version bump is intended.
* Validation must remain strict, but it must validate semantic equivalence rather than string-shape coincidence.

## 2) Goals & Non-Goals

**Goals**

* [ ] Validate planned-event propagation using structured date/type matching where structured event objects exist.
* [ ] Accept `recovery_protection.notes` as `string | list[string]` in guarded-store normalization.
* [ ] Reduce false negatives in `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` validation.

**Non-Goals**

* [ ] No change to season-plan or phase-guardrails JSON schemas.
* [ ] No change to agent prompts beyond existing behavior.

## 3) Proposed Behavior

* `PHASE_GUARDRAILS` validation checks each expected planned-event window against `events_constraints.events[]` using `date` + `type`.
* `PHASE_STRUCTURE` validation uses relaxed semantic matching for planned-event window markers in `upstream_intent.constraints` instead of exact raw-string matching.
* Planned-event parsing accepts both compact `YYYY-MM-DD (A|B|C)` markers and free-text season-plan markers such as `YYYY-MM-DD B event rehearsal window`.
* Recovery-protection notes normalize from string or list form before propagation checks.

## 4) Implementation Analysis

* `src/rps/workspace/guarded_store.py`
  * add season-constraint normalization helpers
  * add structured planned-event parsing
  * update guardrails/structure enforcement logic
* `tests/`
  * add validator regression tests for planned-event matching and recovery-note normalization
* `PHASE_PREVIEW` validation remains traceability-only and does not cross-check `planned_event_windows`.

## 5) Impact Analysis

* Backward compatible: Yes
* Breaking changes: none intended
* Validation becomes less brittle while staying strict on actual semantic propagation

## 6) Recommendation

* Implement semantic validation in `guarded_store.py` and cover with unit tests.

## 7) Acceptance Criteria

* [x] Guardrails with correctly represented event objects pass guarded-store validation.
* [x] String-only shape differences between season-plan and guardrails no longer produce false missing-event errors.
* [x] Free-text planned-event markers such as `YYYY-MM-DD B event rehearsal window` are accepted for guardrails and phase-structure propagation checks.
* [x] `recovery_protection.notes` as string no longer degrades into character-wise matching.

## 8) Documentation Updates

* [ ] `CHANGELOG.md` updated

## 12) Link Map

* Workspace: `doc/architecture/workspace.md`
* Validation / runbooks: `doc/runbooks/validation.md`
