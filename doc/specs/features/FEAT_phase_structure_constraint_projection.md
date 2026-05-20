---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning Runtime
---
# FEAT: Phase Structure Constraint Projection

* **ID:** FEAT_phase_structure_constraint_projection
* **Status:** Implemented
* **Owner/Area:** Planning Runtime / Phase Structure
* **Last-Updated:** 2026-05-20
* **Related:** `src/rps/agents/output_normalization.py`, `src/rps/workspace/guarded_store.py`, `doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md`

---

## 1) Context / Problem

**Current behavior**

* `PHASE_STRUCTURE` is written after `PHASE_GUARDRAILS`.
* The guarded store requires:
  * all season constraints to be present in `data.upstream_intent.constraints`
  * `load_ranges.weekly_kj_bands` to match stored `PHASE_GUARDRAILS`
  * `load_ranges.source` to name the exact stored guardrails filename

**Problem**

* The phase writer produces semantically plausible structure payloads, but it does not reproduce those deterministic runtime-owned constraints exactly.
* After `PHASE_GUARDRAILS` succeeds, `PHASE_STRUCTURE` still fails persistence.

**Constraints**

* No schema bump.
* No relaxation of guarded-store validation.
* Exact guardrails filename must remain runtime-owned, not model-authored.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Deterministically project missing season constraints into `upstream_intent.constraints`.
* [x] Deterministically align `load_ranges.weekly_kj_bands` and `load_ranges.source` with stored `PHASE_GUARDRAILS`.
* [x] Keep the fix runtime-owned and exact-range aware.

**Non-Goals**

* [x] Changing `PHASE_STRUCTURE` schema.
* [x] Weakening contract enforcement.
* [x] Relying on another prompt retry to repair the payload.

---

## 3) Proposed Behavior

**User/System behavior**

* Before `PHASE_STRUCTURE` validation completes, the runtime supplements the structure payload with:
  * missing season availability/risk/recovery/event constraints in `upstream_intent.constraints`
  * exact `load_ranges.weekly_kj_bands` from stored `PHASE_GUARDRAILS`
  * exact `load_ranges.source` filename derived from the written guardrails version

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: guarded-store phase validation, shared normalization helpers
* Contracts touched: `SEASON_PLAN -> PHASE_STRUCTURE`, `PHASE_GUARDRAILS -> PHASE_STRUCTURE`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/output_normalization.py`
  * add a deterministic `PHASE_STRUCTURE` normalization helper
* `src/rps/workspace/guarded_store.py`
  * apply structure normalization once the exact-range guardrails payload/version is loaded
* `tests/test_output_normalization.py`
  * verify constraint projection and exact `load_ranges.source` rewrite
* `tests/test_guarded_store.py`
  * verify a paraphrased structure payload is repaired and accepted

**Data flow**

* Inputs: draft `PHASE_STRUCTURE`, loaded `SEASON_PLAN`, loaded exact-range `PHASE_GUARDRAILS`
* Processing: append constraints and overwrite guardrails-owned load metadata
* Outputs: store-ready `PHASE_STRUCTURE`

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: existing guarded-store checks remain strict

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: without a matching exact-range guardrails payload, persistence still fails safely

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: deterministic projection preserves runtime ownership of contract-critical fields

**Impacted areas**

* UI: none
* Pipeline/data: phase structure persistence becomes robust
* Renderer: none
* Workspace/run-store: exact-range phase bundle writes become less brittle
* Validation/tooling: no rule change; only pre-validation repair
* Deployment/config: none

**Required refactoring**

* Factor phase-structure repair into a shared normalizer helper

---

## 6) Options & Recommendation

### Option A — Normalize inside guarded-store with loaded guardrails

**Summary**

* Repair the structure payload at the point where exact-range guardrails version is already known.

**Pros**

* Uses authoritative runtime data
* Avoids guessing filenames upstream
* Keeps validation strict

**Cons**

* Slightly more guarded-store mutation logic

### Option B — Keep retrying the writer prompt

**Summary**

* Teach the model to emit exact season constraints plus exact guardrails filename.

**Pros**

* Smaller code change

**Cons**

* Still brittle
* Wrong ownership for exact runtime filename

### Recommendation

* Choose: Option A
* Rationale: the filename and exact guardrails payload are runtime facts, so the runtime should own them.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Missing season constraints are appended to `upstream_intent.constraints`.
* [x] `load_ranges.weekly_kj_bands` matches stored `PHASE_GUARDRAILS`.
* [x] `load_ranges.source` matches `phase_guardrails_<version>.json`.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `pytest -q tests/test_output_normalization.py tests/test_guarded_store.py`

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the structure projection helper and tests

---

## 9) Risks & Failure Modes

* Failure mode: wrong exact-range guardrails artifact loaded
  * Detection: guarded-store still rejects `load_ranges` mismatch
  * Safe behavior: persistence fails rather than storing incoherent structure
  * Recovery: inspect exact-range index selection and bundle sequencing

---

## 10) Observability / Logging

**New/changed events**

* No new event families

**Diagnostics**

* guarded-store persistence errors for `PHASE_STRUCTURE`
* regression tests covering exact `source` rewrite

---

## 11) Documentation Updates

* [x] [doc/specs/features/FEAT_phase_structure_constraint_projection.md](/Users/alexander/RPS/doc/specs/features/FEAT_phase_structure_constraint_projection.md)
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)

## 12) Link Map

* [doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md](/Users/alexander/RPS/doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md)
* [doc/specs/features/FEAT_guarded_store_constraint_matching.md](/Users/alexander/RPS/doc/specs/features/FEAT_guarded_store_constraint_matching.md)
