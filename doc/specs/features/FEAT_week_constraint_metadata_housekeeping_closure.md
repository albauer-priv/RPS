---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: Planning Pipeline
---
# FEAT: Week Constraint, Metadata, and Housekeeping Closure

* **ID:** FEAT_week_constraint_metadata_housekeeping_closure
* **Status:** Implemented
* **Owner/Area:** Planning Pipeline / Workspace / UI Runtime
* **Last-Updated:** 2026-06-09
* **Related:** [FEAT_week_plan_semantic_hardening](/Users/alexander/RPS/doc/specs/features/FEAT_week_plan_semantic_hardening.md), [FEAT_season_preview_trace_consistency](/Users/alexander/RPS/doc/specs/features/FEAT_season_preview_trace_consistency.md), [FEAT_code_owned_artifact_metadata](/Users/alexander/RPS/doc/specs/features/FEAT_code_owned_artifact_metadata.md), [ADR-058-phase-authority-chain-and-shared-week-skeleton](/Users/alexander/RPS/doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md)

---

## 1) Context / Problem

**Current behavior**

* `SEASON_PLAN.data.phases[].role_week_load_bands` is already the authoritative season-owned week-band source.
* `PHASE_PREVIEW` is already derived from the shared deterministic skeleton and stores as informational.
* Artifact metadata is already code-owned at write time, but persisted canonical `meta.version_key` and direct trace lineage were still incomplete in some paths.
* Background housekeeping iterated athlete workspace roots too loosely.

**Problem**

* `SEASON_PLAN.season_load_envelope.expected_average_weekly_kj_range` needed to be treated strictly as a deterministic aggregate of authoritative role-week bands, not as a broad corridor proxy.
* `WEEK_PLAN` exposed scenario posture, but not the effective week-local legality/band as a separate persisted contract surface.
* `week_summary.week_objective` could describe a nominal midpoint target instead of the actual planned week load inside the active band.
* Persisted artifacts could miss canonical `meta.version_key`, preserve malformed/duplicate `trace_upstream`, or keep lower-quality synthetic run ids despite better in-process metadata.
* Global housekeeping could create pseudo-athlete activity under `athlete=runs`.

**Constraints**

* Keep the existing Season -> Phase -> Preview -> Week authority model unchanged.
* `PHASE_PREVIEW` remains informational.
* No athlete-specific logic.
* `WEEK_PLAN` schema extension is allowed in this patch.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make the deterministic role-week-band recomputation the sole producer/validator source for the season load envelope average range.
* [x] Persist effective week-local legality and the active week load band separately from scenario posture.
* [x] Make `week_objective` describe the actual approved week load against the active binding band.
* [x] Persist canonical `meta.version_key`, real `run_id`, and deduplicated direct `trace_upstream` on governed artifacts.
* [x] Restrict housekeeping enumeration to real athlete workspaces only.

**Non-Goals**

* [x] No redesign of scenario ceiling vs phase legality separation.
* [x] No change to shared skeleton ownership.
* [x] No change to structural-vs-operational `NONE`.
* [x] No change to `PHASE_PREVIEW.meta.authority = Informational`.

---

## 3) Proposed Behavior

**User/System behavior**

* Season load envelope average min/max is produced and validated only from authoritative phase role-week load bands.
* `WEEK_PLAN` now persists two clearly separate surfaces:
  * `inherited_planning_posture` = scenario-level posture
  * `effective_week_constraints` = actual week-local legality, modalities, phase intent, week role, and binding weekly kJ band
* `week_summary.week_objective` now states the actual planned week load inside the governing band instead of implying a different midpoint target.
* Governed artifacts persist canonical `meta.version_key` and normalized direct upstream lineage.
* Housekeeping only emits per-athlete work for actual athlete workspace directories.

**UI impact**

* UI affected: Yes
* Week-plan rendering now surfaces effective week constraints directly.
* No page layout redesign is introduced.

**Non-UI behavior**

* Components involved: week engine, workout generator, planning contracts, workspace metadata normalization, guarded store, local store, Streamlit startup housekeeping.
* Contracts touched: `week_plan.schema.json`, governed artifact metadata contract.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/deterministic_context.py`
  * adds deterministic `effective_week_constraints` assembly and shared modality resolution.
* `src/rps/planning/week_engine.py`
  * projects direct upstream trace and effective allowed modalities into week context.
* `src/rps/workouts/generator.py`
  * persists `effective_week_constraints`, truthful week objective text, and direct upstream lineage on `WEEK_PLAN`.
* `src/rps/planning/contracts.py`
  * validates effective week constraints against deterministic context and tightens season-envelope wording.
* `src/rps/workspace/artifact_metadata.py`, `validated_api.py`, `guarded_store.py`, `local_store.py`
  * canonicalize/persist `meta.version_key` and deduplicated trace references.
* `src/rps/ui/streamlit_app.py`
  * scopes housekeeping to real athlete workspaces.

**Data flow**

* Inputs: persisted Season/Phase artifacts, deterministic week calendar context, in-process run id/version key, workspace root.
* Processing:
  * recompute season envelope average from role-week bands
  * derive effective week constraints from the same deterministic week authority used for planning
  * canonicalize artifact metadata and direct upstream trace on write
  * enumerate only athlete-shaped workspace directories for housekeeping
* Outputs: updated `WEEK_PLAN`, canonical persisted metadata, cleaner housekeeping runs.

**Schema / Artefacts**

* New persisted `WEEK_PLAN.data.effective_week_constraints`.
* `artefact_meta.schema.json` now requires persisted canonical `version_key`.
* Existing artifact schemas remain otherwise stable.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Partially
* Breaking changes:
  * new `WEEK_PLAN.data.effective_week_constraints` is required for new writes
  * persisted metadata now includes write-time canonical `meta.version_key`
* Fallback behavior:
  * direct write paths canonicalize metadata before validation
  * legacy reads still normalize older metadata in memory where supported

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns with ADR-058 because week-local legality is projected from existing deterministic authority, not from scenario posture.

**Impacted areas**

* UI: Week render context gains effective constraints.
* Pipeline/data: week bundle persistence and metadata normalization.
* Renderer: week template shows effective constraints.
* Workspace/run-store: canonical `version_key` is now persisted, housekeeping root scan is tighter.
* Validation/tooling: `WEEK_PLAN` contract validation and metadata-related tests changed.
* Deployment/config: no new config.

**Required refactoring**

* Move week-local legality into one deterministic persisted block instead of leaving it implicit.
* Treat canonical metadata persistence as a write-time concern, not a load-only annotation.
* Replace broad root iteration in housekeeping with a workspace-shape filter.

---

## 6) Options & Recommendation

### Option A — Extend `WEEK_PLAN` and tighten central metadata handling

**Summary**

* Add a minimal explicit week-local constraints block and push metadata/housekeeping fixes into existing central write/runtime paths.

**Pros**

* Keeps authority explicit where operators and downstream code need it.
* Preserves existing Season/Phase/Preview model.
* Fixes auditability and housekeeping scope in one coherent patch.

**Cons**

* Requires a schema change and associated test updates.

### Option B — Keep week-local legality implicit

**Summary**

* Leave week-local legality in runtime-only context and fix only wording/metadata.

**Pros**

* Smaller patch surface.

**Cons**

* Persisted `WEEK_PLAN` remains under-specified for audit and review.

### Recommendation

* Choose: Option A
* Rationale: it closes the audit gaps without reopening solved authority layers.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `SEASON_PLAN.season_load_envelope.expected_average_weekly_kj_range` validates against deterministic recomputation from role-week bands only.
* [x] `WEEK_PLAN.data.effective_week_constraints` is persisted and validated against deterministic week context.
* [x] `WEEK_PLAN.data.inherited_planning_posture` remains scenario-level posture only.
* [x] `week_summary.week_objective` describes the actual planned week load inside the active band.
* [x] Governed artifacts persist canonical `meta.version_key`.
* [x] Direct upstream trace on Phase/Week artifacts is canonical and deduplicated.
* [x] Housekeeping ignores global runtime directories such as `runs/`.
* [x] Validation passes: `py_compile`, targeted pytest, lint, typecheck.

---

## 8) Migration / Rollout

**Migration strategy**

* New writes require the updated `WEEK_PLAN` schema.
* Metadata persistence now writes canonical `meta.version_key` directly instead of treating it as a load-only annotation.
* Existing artifacts remain readable through existing runtime normalization where applicable.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert the schema and central write-path changes together.

---

## 9) Risks & Failure Modes

* Failure mode: week-local constraints drift from deterministic context.
  * Detection: week contract validation failure.
  * Safe behavior: fail closed before persistence/export.
  * Recovery: regenerate week plan from current phase/week context.
* Failure mode: persisted metadata path omits `version_key`.
  * Detection: schema validation failure on write or regression test failure.
  * Safe behavior: reject invalid envelope.
  * Recovery: route writes through canonical metadata builder/store path.
* Failure mode: housekeeping skips a valid athlete directory.
  * Detection: missing housekeeping events for a known athlete workspace.
  * Safe behavior: no cross-athlete corruption; only missed housekeeping.
  * Recovery: adjust workspace-shape predicate and rerun.

---

## 10) Observability / Logging

**Diagnostics**

* Existing guarded-store validation logs surface metadata and week-context mismatches.
* No new telemetry contract is required.
* Housekeeping behavior is diagnosable through existing background-run logs per athlete.

---

## 11) Documentation Updates

* [x] [doc/specs/features/FEAT_week_plan_semantic_hardening.md](/Users/alexander/RPS/doc/specs/features/FEAT_week_plan_semantic_hardening.md) — related baseline for week semantics
* [x] [doc/specs/features/FEAT_season_preview_trace_consistency.md](/Users/alexander/RPS/doc/specs/features/FEAT_season_preview_trace_consistency.md) — related season/preview consistency baseline
* [x] [doc/specs/features/FEAT_code_owned_artifact_metadata.md](/Users/alexander/RPS/doc/specs/features/FEAT_code_owned_artifact_metadata.md) — related metadata ownership baseline
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — implementation tracking
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — release note entry

---

## 12) Link Map (no duplication; links only)

* Architecture: [doc/architecture/system_architecture.md](/Users/alexander/RPS/doc/architecture/system_architecture.md)
* Workspace: [doc/architecture/workspace.md](/Users/alexander/RPS/doc/architecture/workspace.md)
* Artefact flow: [doc/overview/artefact_flow.md](/Users/alexander/RPS/doc/overview/artefact_flow.md)
* Planner flow: [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
* ADR: [doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md](/Users/alexander/RPS/doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md)
