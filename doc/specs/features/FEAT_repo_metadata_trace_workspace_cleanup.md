---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: Workspace / Rendering
---
# FEAT: Repo Metadata, Trace, and Workspace Cleanup

* **ID:** FEAT_repo_metadata_trace_workspace_cleanup
* **Status:** Implemented
* **Owner/Area:** Workspace / Rendering / Metadata
* **Last-Updated:** 2026-06-09
* **Related:** [FEAT_week_constraint_metadata_housekeeping_closure](/Users/alexander/RPS/doc/specs/features/FEAT_week_constraint_metadata_housekeeping_closure.md), [FEAT_season_preview_trace_consistency](/Users/alexander/RPS/doc/specs/features/FEAT_season_preview_trace_consistency.md), [ADR-051-code-owned-artifact-metadata](/Users/alexander/RPS/doc/adr/ADR-051-code-owned-artifact-metadata.md), [ADR-058-phase-authority-chain-and-shared-week-skeleton](/Users/alexander/RPS/doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md)

---

## 1) Context / Problem

**Current behavior**

* Newer guarded/validated writes already normalize artifact metadata toward canonical dict-based trace references.
* Several repo-internal types and helper APIs still declared `meta.trace_upstream` as `list[str]`.
* Local-store reads still perform legacy envelope normalization for older artifact shapes.
* Renderer code already formats trace entries for display, but renderer docs still described string-list behavior.

**Problem**

* The repo carried a type-contract mismatch: internal metadata models and workspace APIs still suggested string-based trace surfaces while normalization/tests expected canonical dict references.
* `save_version(...)` and `save_document(...)` did not consistently normalize trace fields write-time, so older or mixed trace shapes could survive longer than necessary.
* Legacy-read normalization existed, but its role as explicit compatibility logic versus new-write behavior was not clearly separated.

**Constraints**

* No schema redesign in this feature.
* Existing legacy persisted artifacts remain readable when their trace entries are deterministically normalizable.
* New writes must not invent missing trace truth.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make repo-internal metadata types and APIs use canonical dict-based trace references.
* [x] Normalize trace fields write-time in local-store write paths as well as read-time for legacy envelopes.
* [x] Preserve explicit legacy-read normalization in `local_store` for older artifacts.
* [x] Keep renderer/templates on display-ready trace data only.

**Non-Goals**

* [x] No runtime/compat boundary redesign.
* [x] No planner authority-model change.
* [x] No artifact schema version bump in this feature alone.

---

## 3) Proposed Behavior

**User/System behavior**

* Governed artifact metadata now consistently treats `trace_upstream`, `trace_data`, and `trace_events` as canonical dict references in internal types and write paths.
* Local-store legacy reads still normalize older trace strings/partial dicts in memory when the source can be deterministically resolved.
* Renderer consumers continue to receive display-ready strings; templates no longer rely on any raw trace-shape distinction.

**UI impact**

* UI affected: Indirectly only
* Rendered markdown sidecars and page rendering keep the same visible trace output, but are now sourced from one canonical internal trace shape.

**Non-UI behavior**

* Components involved: workspace types/API/local store, CrewAI artifact-envelope model, artifact metadata normalization, renderer docs.
* Contracts touched: repo-internal metadata typing and local-store normalization semantics.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/types.py`
  * adds canonical `TraceReference` typing.
* `src/rps/workspace/api.py`
  * aligns write-path signatures to dict-based trace references.
* `src/rps/crewai_runtime/models.py`
  * replaces string-based artifact-envelope trace lists with structured trace-reference models.
* `src/rps/workspace/artifact_metadata.py`
  * accepts legacy string trace entries, normalizes them into canonical dict references, and deduplicates canonically.
* `src/rps/workspace/local_store.py`
  * keeps `_normalize_loaded_meta(...)` as explicit legacy-read normalization and applies canonical trace normalization on write paths.
* `doc/architecture/renderer.md`
  * documents display-ready trace rendering instead of raw string-list assumptions.

**Data flow**

* Inputs: envelope metadata from validated writes, direct store writes, older artifacts read from disk.
* Processing:
  * normalize trace references on write
  * normalize legacy trace references on read when possible
  * format canonical trace references into display strings in the renderer
* Outputs: canonical dict-based trace metadata persisted for new writes; normalized in-memory trace metadata for legacy reads.

**Schema / Artefacts**

* No schema shape change required.
* Persisted metadata behavior is tightened: new writes now consistently normalize trace fields before disk write.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, for deterministically normalizable legacy traces
* Breaking changes: repo-internal type contracts now reject string-based trace surfaces as the primary write shape
* Fallback behavior:
  * legacy string traces remain read-compatible where the artifact token can be resolved
  * unresolvable legacy strings are dropped instead of invented

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns directly with ADR-051 write-time metadata ownership and ADR-058 trace quality expectations.

**Impacted areas**

* UI: renderer documentation only
* Pipeline/data: local-store trace normalization on write
* Renderer: still receives formatted strings, but from one canonical internal shape
* Workspace/run-store: typed trace metadata contracts align with actual normalization behavior
* Validation/tooling: generated/typed models now match canonical trace-entry expectations
* Deployment/config: none

**Required refactoring**

* replace stale `list[str]` trace annotations
* centralize local-store write-time trace normalization
* explicitly document legacy-read normalization as compatibility logic

---

## 6) Options & Recommendation

### Option A — Canonical dict traces everywhere, legacy strings read-only

**Summary**

* Keep dict-based trace references as the only canonical write shape and preserve legacy string support only during reads/normalization.

**Pros**

* Matches current normalization/tests
* Reduces metadata ambiguity
* Keeps backward compatibility where it is actually needed

**Cons**

* Requires small typed-model and local-store updates

**Risk**

* Low; isolated to metadata surfaces and compatible renderer behavior

### Option B — Continue supporting string traces as co-equal internal shape

**Summary**

* Leave internal APIs permissive and keep dict-vs-string ambiguity alive.

**Pros**

* Less immediate refactoring

**Cons**

* Preserves contract drift
* Keeps renderer/store/tests on mixed assumptions

### Recommendation

* Choose: Option A
* Rationale: it matches the existing canonical metadata direction and removes avoidable internal ambiguity without changing public artifact schemas.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Workspace metadata typing uses canonical dict-based trace references.
* [x] CrewAI artifact-envelope models use structured trace-reference entries instead of strings.
* [x] Local-store write paths normalize `trace_upstream`, `trace_data`, and `trace_events`.
* [x] Local-store read paths still normalize deterministic legacy trace strings/partial dicts.
* [x] Renderer docs no longer describe `trace_upstream` as a raw string-list special case.
* [x] Validation passes for the targeted metadata/workspace/renderer test areas.

---

## 8) Migration / Rollout

**Migration strategy**

* No one-time migration required.
* Existing legacy artifacts remain readable through read-time normalization.
* New writes always persist canonical trace-reference dicts.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert typed-model and local-store write normalization changes

---

## 9) Risks & Failure Modes

* Failure mode: old string trace entries cannot be resolved to a canonical artifact token

  * Detection: normalized trace entry disappears after read-time normalization
  * Safe behavior: drop the unresolvable entry instead of inventing metadata
  * Recovery: rewrite or regenerate the affected legacy artifact if lineage matters operationally

---

## 10) Observability / Logging

**New/changed events**

* No new runtime event types

**Diagnostics**

* Inspect persisted artifact `meta.trace_*` fields
* Use existing metadata/renderer/workspace tests for regression coverage

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/architecture/renderer.md](/Users/alexander/RPS/doc/architecture/renderer.md) — document display-ready trace rendering and remove string-list wording
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — record this cleanup feature as implemented
