---
Version: 1.0
Status: Approved
Last-Updated: 2026-02-04
Owner: Data Pipeline
---

# FEAT: Parquet Cache for Intervals Pipeline Outputs

* **ID:** FEAT_parquet_cache
* **Status:** Approved
* **Owner/Area:** Data Pipeline
* **Last-Updated:** 2026-02-04
* **Related:** ADR-024-parquet-cache.md

---

## 1) Context / Problem

**Current behavior**

* The Intervals pipeline writes CSV/JSON outputs into `data/<year>/<week>/` and `latest/`.
* UI analytics repeatedly parse CSV/JSON, which is slower than columnar formats.

**Problem**

* Analytics pages benefit from a columnar cache for faster reads and easier aggregation.

**Constraints**

* Canonical artifacts remain JSON (schemas, validation, auditability).
* No change to existing artifact contracts or naming.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Write Parquet caches automatically during the Intervals pipeline run.
* [ ] Keep caches in the same week/latest folders as CSV/JSON.
* [ ] Treat Parquet as non-canonical (best-effort cache only).

**Non-Goals**

* [ ] Replace JSON/CSV artifacts as the source of truth.
* [ ] Change UI readers to require Parquet.

---

## 3) Proposed Behavior

**User/System behavior**

* Every pipeline run writes Parquet mirrors for activities_actual and activities_trend.
* If Parquet writing fails, the pipeline still completes; log a warning.

**UI impact**

* UI affected: No (future readers may optionally use the cache).

**Non-UI behavior (if applicable)**

* Components involved: `rps.data_pipeline.intervals_data`.
* Contracts touched: none (cache only).

---

## 4) Implementation Analysis

**Components / Modules**

* `intervals_data.py`: write `.parquet` alongside existing `.csv`/`.json` outputs.

**Data flow**

* Inputs: CSV export from Intervals.
* Processing: same dataframe used for CSV/JSON export.
* Outputs: `.parquet` cache files in `data/<year>/<week>/` and `latest/`.

**Schema / Artefacts**

* New artefacts: none (cache files only).
* Changed artefacts: none.
* Validator implications: none.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None.
* Fallback behavior: If Parquet fails, keep CSV/JSON as usual.

**Conflicts with ADRs / Principles**

* Potential conflicts: None (cache is non-canonical).

**Impacted areas**

* UI: optional future performance improvement (no dependency).
* Pipeline/data: adds cache writes.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: none.
* Deployment/config: add Parquet dependency (pyarrow).

**Required refactoring**

* None.

---

## 6) Options & Recommendation

### Option A (recommended) — Parquet cache alongside CSV/JSON

**Summary**

* Write `.parquet` next to existing outputs, keep JSON/CSV canonical.

**Pros**

* Faster reads for analytics.
* Zero impact on existing contracts.

**Cons**

* Adds a dependency (pyarrow).

**Risk**

* Parquet write failures; mitigated by warning-only behavior.

### Option B — Parquet-only canonical

**Summary**

* Replace JSON/CSV outputs.

**Pros**

* Smaller and faster.

**Cons**

* Breaks current workflow, reduces transparency, requires migration.

### Recommendation

* Choose: Option A.
* Rationale: performance benefit with minimal risk.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Parquet cache files are written for activities_actual and activities_trend.
* [ ] Cache writes are best-effort; pipeline does not fail if Parquet fails.
* [ ] Dependency updated to support Parquet.
* [ ] Docs updated to note cache behavior and non-canonical status.

---

## 8) Migration / Rollout

**Migration strategy**

* None (cache only).

**Rollout / gating**

* No feature flag required.

---

## 9) Risks & Failure Modes

* Failure mode: Parquet write error.
  * Detection: warning log with path and exception.
  * Safe behavior: pipeline continues; CSV/JSON available.

---

## 10) Observability / Logging

**New/changed events**

* Warning log on Parquet write failure (path + error).

**Diagnostics**

* Check pipeline logs for cache write warnings.

---

## 11) Documentation Updates

* [ ] `doc/architecture/subsystems/data_pipeline.md` — mention Parquet cache.
* [ ] `doc/adr/ADR-024-parquet-cache.md` — decision record.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Schema versioning: `doc/architecture/schema_versioning.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* ADRs: `doc/adr/ADR-024-parquet-cache.md`

