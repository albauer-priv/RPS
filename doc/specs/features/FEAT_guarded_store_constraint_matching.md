---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-13
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
* Recovery-protection notes normalize from string or list form before propagation checks.

## 4) Implementation Analysis

* `src/rps/workspace/guarded_store.py`
  * add season-constraint normalization helpers
  * add structured planned-event parsing
  * update guardrails/structure enforcement logic
* `tests/`
  * add validator regression tests for planned-event matching and recovery-note normalization

## 5) Impact Analysis

* Backward compatible: Yes
* Breaking changes: none intended
* Validation becomes less brittle while staying strict on actual semantic propagation

## 6) Recommendation

* Implement semantic validation in `guarded_store.py` and cover with unit tests.

## 7) Acceptance Criteria

* [ ] Guardrails with correctly represented event objects pass guarded-store validation.
* [ ] String-only shape differences between season-plan and guardrails no longer produce false missing-event errors.
* [ ] `recovery_protection.notes` as string no longer degrades into character-wise matching.

## 8) Documentation Updates

* [ ] `CHANGELOG.md` updated

## 12) Link Map

* Workspace: `doc/architecture/workspace.md`
* Validation / runbooks: `doc/runbooks/validation.md`
