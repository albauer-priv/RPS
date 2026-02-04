---
Version: 1.0
Status: Approved
Last-Updated: 2026-02-04
Owner: UI Analytics
---
# FEAT: Prefer Parquet Cache for Data & Metrics

* **ID:** FEAT_parquet_readers
* **Status:** Approved
* **Owner/Area:** UI Analytics
* **Last-Updated:** 2026-02-04
* **Related:** FEAT_parquet_cache

---

## 1) Context / Problem

**Current behavior**

* Data & Metrics reads activities_trend from JSON only.

**Problem**

* JSON parsing is slower and ignores the new Parquet cache.

**Constraints**

* Parquet cache is non-canonical; JSON remains source of truth.
* UI must continue to function without Parquet.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Prefer Parquet cache for activities_trend when available.
* [ ] Fall back to JSON on missing/failed Parquet reads.

**Non-Goals**

* [ ] Remove JSON/CSV usage elsewhere.
* [ ] Require Parquet for UI operation.

---

## 3) Proposed Behavior

**User/System behavior**

* Data & Metrics loads weekly trend rows from Parquet when present.
* If Parquet is missing or invalid, JSON is used.

**UI impact**

* UI affected: Yes
* Page: Analyse → Data & Metrics

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/ui/pages/performance/data_metrics.py` — load activities_trend from Parquet first.

**Data flow**

* Inputs: `latest/activities_trend.parquet` or `latest/activities_trend.json`.
* Outputs: unchanged charts and tables.

**Schema / Artefacts**

* No new artefacts; cache only.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None.

**Impacted areas**

* UI: Data & Metrics only.
* Pipeline/data: none.

---

## 6) Options & Recommendation

### Option A (recommended) — Prefer Parquet, fallback to JSON

**Pros**

* Faster reads when cache is present.
* Zero risk when cache is missing.

**Cons**

* Slightly more complex loader logic.

### Recommendation

* Choose: Option A.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Data & Metrics uses Parquet when available.
* [ ] JSON fallback remains functional.
* [ ] No regressions in charts or tables.

---

## 8) Migration / Rollout

* No migration; cache is optional.

---

## 9) Risks & Failure Modes

* Failure: Parquet read error.
  * Detection: warning log.
  * Safe behavior: JSON fallback.

---

## 10) Observability / Logging

* Warning log on Parquet read failure.

---

## 11) Documentation Updates

* [ ] `doc/ui/pages/performance_data_metrics.md` — note Parquet preference.

---

## 12) Link Map (no duplication; links only)

* UI: `doc/ui/pages/performance_data_metrics.md`
* Architecture: `doc/architecture/subsystems/data_pipeline.md`
* Feature cache: `doc/specs/features/FEAT_parquet_cache.md`

