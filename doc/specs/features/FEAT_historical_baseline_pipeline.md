# FEAT: Historical Baseline via Pipeline

* **ID:** FEAT_historical_baseline_pipeline
* **Status:** Approved
* **Owner/Area:** Data Pipeline
* **Last-Updated:** 2026-02-05
* **Related:** [doc/ui/pages/athlete_profile.md](../../ui/pages/athlete_profile.md)

---

## 1) Context / Problem

**Current behavior**

* Historic Data page computes yearly summaries by scanning `activities_actual` files.

**Problem**

* `activities_actual` only covers recent weeks, so yearly historical summaries are incomplete.
* Users want full-year aggregates fetched from Intervals for each year.

**Constraints**

* Must reuse existing Intervals API fetch logic.
* No new dependencies.
* Must keep artifacts append-only and stored in the workspace.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Build yearly historical summaries by fetching full-year Intervals activity data.
* [x] Store summaries in a workspace artifact for UI consumption.
* [x] Keep Historic Data UI read-only and sourced from the artifact.

**Non-Goals**

* [ ] Replace the main activities pipeline output formats.
* [ ] Add new UI controls beyond a refresh trigger.

---

## 3) Proposed Behavior

**User/System behavior**

* The pipeline fetches full-year activities for the most recent N years and stores a yearly summary.
* Historic Data UI reads the summary from `HISTORICAL_BASELINE`.
* Refreshing Intervals data recomputes the historical baseline.

**UI impact**

* UI affected: Yes
* Where: Athlete Profile → Historic Data
* Key states: shows summary table if present; refresh triggers pipeline.

### UI Flow (Mermaid)

```mermaid
flowchart TD
  A["Open Historic Data"] --> B["Read HISTORICAL_BASELINE"]
  B --> C{ "Baseline present?" }
  C -->|"Yes"| D["Render baseline + yearly summary"]
  C -->|"No"| E["Show missing baseline message"]
  E --> F["Trigger Intervals refresh"]
```

**Non-UI behavior**

* Components involved: `rps.data_pipeline.intervals_data`, `rps.ui.intervals_refresh`, `rps.ui.pages.athlete_profile.historic_data`
* Contracts touched: `historical_baseline.schema.json`

---

## 4) Implementation Analysis

**Components / Modules**

* `intervals_data.py`: add yearly fetch + aggregation to store `HISTORICAL_BASELINE`.
* `intervals_refresh.py`: pass historical years parameter to pipeline.
* `historic_data.py`: read yearly summaries from artifact, stop scanning activities_actual.

**Data flow**

* Inputs: Intervals activities by year
* Processing: aggregate per year (count, moving_time, distance, work_kj)
* Outputs: `HISTORICAL_BASELINE` (baseline metrics + yearly_summary)

**Schema / Artefacts**

* Changed artefacts: `HISTORICAL_BASELINE` (adds optional `yearly_summary`)
* Validator implications: schema updated, bundled schemas regenerated.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes (new optional field)
* Breaking changes: None
* Fallback behavior: UI shows message when baseline missing.

**Conflicts with ADRs / Principles**

* None known.

**Impacted areas**

* UI: Historic Data reads artifact instead of scanning local files.
* Pipeline/data: new yearly aggregation step.
* Workspace/run-store: new data written under existing artifact.
* Validation/tooling: schema update + bundle.

**Required refactoring**

* Remove direct activities_actual scan from Historic Data UI.

---

## 6) Options & Recommendation

### Option A (recommended) — Pipeline yearly aggregation

**Summary**

* Fetch full-year Intervals data and store yearly summaries in `HISTORICAL_BASELINE`.

**Pros**

* Accurate history without relying on partial weekly files.
* Centralized in pipeline.

**Cons**

* More API calls per refresh.

**Risk**

* Longer pipeline runtime.

### Option B — Keep UI scanning local data

**Summary**

* Continue scanning activities_actual files.

**Pros**

* No extra API calls.

**Cons**

* Incomplete history; contradicts requirements.

### Recommendation

* Choose: Option A
* Rationale: Meets full-year historical requirement.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] `HISTORICAL_BASELINE` includes `yearly_summary` for last N years.
* [ ] Historic Data UI renders yearly summary from the artifact.
* [ ] Pipeline refresh recomputes baseline and yearly summary.
* [ ] Schema validation passes and bundled schemas updated.

---

## 8) Migration / Rollout

**Migration strategy**

* Optional field added; old artifacts remain valid.

**Rollout / gating**

* None.

---

## 9) Risks & Failure Modes

* Failure mode: Intervals API rate limits
  * Detection: pipeline error logs
  * Safe behavior: keep previous baseline
  * Recovery: re-run pipeline later

---

## 10) Observability / Logging

**New/changed events**

* Log when yearly summary is compiled and stored.

**Diagnostics**

* Run-store + pipeline logs

---

## 11) Documentation Updates

* [ ] [doc/architecture/subsystems/data_pipeline.md](../../architecture/subsystems/data_pipeline.md) — add historical baseline step.
* [ ] [doc/ui/pages/athlete_profile.md](../../ui/pages/athlete_profile.md) — historic data source and refresh behavior.

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: `doc/ui/ui_spec.md#athlete-profile`
* UI contract (Streamlit): `doc/ui/streamlit_contract.md#athlete-profile-pages`
* Architecture: `doc/architecture/system_architecture.md#data-pipeline`
* Workspace: `doc/architecture/workspace.md#analysis-artifacts`
* Schema versioning: `doc/architecture/schema_versioning.md#artifact-schemas`
* Logging policy: [doc/specs/contracts/logging_policy.md](../contracts/logging_policy.md))
* Validation / runbooks: [doc/runbooks/validation.md](../../runbooks/validation.md)
* ADRs: [doc/adr/README.md](../../adr/README.md)

---
