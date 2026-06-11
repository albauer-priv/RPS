---
Version: 1.1
Status: Updated
Last-Updated: 2026-06-10
Owner: Planning Runtime
---
# FEAT: Phase Structure Constraint Projection

* **ID:** FEAT_phase_structure_constraint_projection
* **Status:** Updated
* **Owner/Area:** Planning Runtime / Phase Structure
* **Last-Updated:** 2026-06-10
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
* [x] Shift-left canonicalization of `upstream_intent.constraints` to phase bundle normalization before writer handoff.
* [x] Restrict the field to inherited planning facts plus narrow residual external constraints.

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
* Final `PHASE_STRUCTURE` normalization also canonicalizes `upstream_intent.constraints` against deterministic upstream fact groups:
  * one canonical injected sentence per known season/global fact
  * no surviving writer paraphrase for the same fact
  * exact residual external planning constraints preserved once when they do not map to a deterministic upstream fact
  * runtime/process/governance reminders removed
* Phase bundle normalization now applies the same canonicalization before writer handoff:
  * primary source is the loaded `season_plan`
  * if the loaded `season_plan` is unavailable, normalization strips process-rule entries and exact duplicates only
  * no canonical inherited wording is invented from free prose when season authority is absent at that boundary
* Stored constraint order is stabilized as:
  * availability/logistics
  * risk/recovery resilience
  * event windows/anchors
  * remaining residual exact strings

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: guarded-store phase validation, shared normalization helpers
* Contracts touched: `SEASON_PLAN -> PHASE_STRUCTURE`, `PHASE_GUARDRAILS -> PHASE_STRUCTURE`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/output_normalization.py`
  * add a shared deterministic phase-structure constraint canonicalizer
* `src/rps/agents/crewai_backend.py`
  * apply phase-structure constraint canonicalization at bundle normalization time
* `src/rps/workspace/guarded_store.py`
  * apply structure normalization once the exact-range guardrails payload/version is loaded
* `tests/test_output_normalization.py`
  * verify constraint projection, residual filtering, and exact `load_ranges.source` rewrite
* `tests/test_crewai_runtime.py`
  * verify active-file frontloading and bundle-stage canonicalization
* `tests/test_guarded_store.py`
  * verify a paraphrased structure payload is repaired and accepted

**Data flow**

* Inputs: draft phase bundle structure payload, loaded `SEASON_PLAN`, loaded exact-range `PHASE_GUARDRAILS`
* Processing:
  * bundle normalization canonicalizes and freezes `upstream_intent.constraints`
  * final structure normalization re-applies the same deterministic canonicalization and overwrites guardrails-owned load metadata
* Outputs: writer-ready structure bundle and store-ready `PHASE_STRUCTURE`

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

* Factor phase-structure constraint repair into a shared normalizer helper used by bundle and final normalization

---

## 6) Options & Recommendation

### Option A — Normalize only inside guarded-store / final artifact path

**Summary**

* Repair the structure payload at the point where exact-range guardrails version is already known.

**Pros**

* Uses authoritative runtime data
* Keeps validation strict

**Cons**

* Fixes too late
* Writer still sees noisy structure constraints
* Does not shift left

### Option B — Shift canonicalization to bundle normalization and keep final normalization as safety net

**Summary**

* Teach the model to emit exact season constraints plus exact guardrails filename.

**Pros**

* Moves correction to the earliest common Phase boundary
* Writer receives pre-cleaned constraints
* Final normalization still guarantees stored correctness

**Cons**

* Slightly more shared normalization logic

### Recommendation

* Choose: Option B
* Rationale: this closes the defect as far left as possible without inventing truth when season authority is absent.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Missing season constraints are appended to `upstream_intent.constraints`.
* [x] Process/runtime/governance sentences are removed from `upstream_intent.constraints`.
* [x] Same-fact paraphrases collapse to canonical inherited wording.
* [x] Bundle normalization canonicalizes the field before writer handoff.
* [x] `load_ranges.weekly_kj_bands` matches stored `PHASE_GUARDRAILS`.
* [x] `load_ranges.source` matches `phase_guardrails_<version>.json`.
* [ ] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [ ] Validation passes: `./scripts/run_lint.sh`
* [ ] Validation passes: `./scripts/run_typecheck.sh`
* [ ] Validation passes: targeted `pytest` for runtime and output normalization

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
* regression tests covering bundle-stage and final-stage canonicalization

---

## 11) Documentation Updates

* [x] [doc/specs/features/FEAT_phase_structure_constraint_projection.md](/Users/alexander/RPS/doc/specs/features/FEAT_phase_structure_constraint_projection.md)
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)

## 12) Link Map

* [doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md](/Users/alexander/RPS/doc/specs/features/FEAT_phase_guardrails_season_constraint_projection.md)
* [doc/specs/features/FEAT_guarded_store_constraint_matching.md](/Users/alexander/RPS/doc/specs/features/FEAT_guarded_store_constraint_matching.md)
