---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: Workspace / Data Pipeline
---
# FEAT: Pipeline Meta Version-Key Backfill

* **ID:** FEAT_pipeline_meta_version_key_backfill
* **Status:** Implemented
* **Owner/Area:** Workspace / Data Pipeline
* **Last-Updated:** 2026-06-09
* **Related:** Intervals refresh `ZONE_MODEL` schema-validation regression

---

## 1) Context / Problem

**Current behavior**

* Data-pipeline artefact builders can emit valid envelope metadata except for `meta.version_key`.
* `canonicalize_artifact_envelope_meta(...)` normalizes many metadata fields, but currently does not derive a missing `version_key`.

**Problem**

* Schemas now require `meta.version_key`.
* `ZONE_MODEL` refresh can fail during schema validation even though `iso_week`, `iso_week_range`, and `created_at` are present and are sufficient to derive a canonical version key.

**Constraints**

* No schema change.
* Existing deterministic version-key derivation rules in `rps.workspace.versioning` remain the source of truth.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Missing `meta.version_key` is deterministically backfilled during envelope canonicalization.
* [x] Data-pipeline schema failures surface concrete validation details in logs.

**Non-Goals**

* [x] No change to artefact schemas.
* [x] No redesign of pipeline payload builders beyond this metadata repair.

---

## 3) Proposed Behavior

**User/System behavior**

* Pipeline payloads that already carry enough metadata to derive a canonical version key no longer fail schema validation because `meta.version_key` was omitted.
* When validation still fails, logs show the concrete schema errors instead of only the wrapper exception.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: `artifact_metadata`, `versioning`, `intervals_data`
* Contracts touched: persisted envelope metadata completeness

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/artifact_metadata.py`: derive missing `meta.version_key` from existing envelope metadata
* `src/rps/data_pipeline/intervals_data.py`: log concrete `ZONE_MODEL` schema validation errors before re-raising
* `tests/test_artifact_metadata.py`: regression coverage

**Schema / Artefacts**

* No schema changes
* No artefact version bump required at schema level

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes
* Breaking changes: None
* Fallback behavior: if deterministic derivation cannot resolve a meaningful key, current downstream validation remains fail-closed

**Conflicts with ADRs / Principles**

* None. This reinforces existing write-time metadata canonicalization.

**Impacted areas**

* Pipeline/data: fixed metadata completeness for schema validation
* Workspace/run-store: canonicalization now owns missing-key backfill
* Validation/tooling: unchanged schema contract, better diagnostics

---

## 6) Options & Recommendation

### Option A — derive missing `version_key` centrally during canonicalization

**Pros**

* One fix covers all envelope producers using the canonicalization path.
* Reuses existing version-key derivation rules.

**Cons**

* Slightly broadens canonicalization responsibility.

### Option B — patch every payload builder individually

**Pros**

* Localized changes only.

**Cons**

* Easy to miss producers.
* Duplicates version-key derivation logic.

### Recommendation

* Choose: Option A
* Rationale: the defect is generic metadata incompleteness, not a `ZONE_MODEL`-only modeling error.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `canonicalize_artifact_envelope_meta(...)` backfills `meta.version_key` when derivable from envelope metadata
* [x] `ZONE_MODEL` payload validates when only `version_key` was missing
* [x] `write_zone_model(...)` logs concrete schema errors before re-raising
* [x] Validation passes: syntax + targeted tests + lint + typecheck

---

## 8) Migration / Rollout

**Migration strategy**

* None required; behavior applies on new canonicalization runs.

**Rollout / gating**

* No feature flag
* Safe rollback: revert the canonicalization fallback and logging change

---

## 9) Risks & Failure Modes

* Failure mode: a producer lacks enough metadata to derive a useful key
  * Detection: schema validation still fails or downstream versioning remains `unversioned`
  * Safe behavior: fail closed
  * Recovery: add the missing source metadata or pass `version_key` explicitly

---

## 10) Observability / Logging

**Diagnostics**

* `ZONE_MODEL` validation now prints concrete schema error lines before raising.

---

## 11) Documentation Updates

* [x] This feature doc records the regression and fix

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* ADRs: `doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md`
