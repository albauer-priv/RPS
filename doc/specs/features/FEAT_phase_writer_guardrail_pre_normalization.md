---
Version: 1.3
Status: Implemented
Last-Updated: 2026-06-08
Owner: Planning Pipeline
---
# FEAT: Phase Writer Guardrail Pre-Normalization

* **ID:** FEAT_phase_writer_guardrail_pre_normalization
* **Status:** Implemented
* **Owner/Area:** Planning Pipeline
* **Last-Updated:** 2026-06-08
* **Related:** [FEAT_phase_authority_realignment_and_shared_week_skeleton](/Users/alexander/RPS/doc/specs/features/FEAT_phase_authority_realignment_and_shared_week_skeleton.md), [ADR-058-phase-authority-chain-and-shared-week-skeleton](/Users/alexander/RPS/doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md)

---

## 1) Context / Problem

**Current behavior**

* `SEASON_PLAN` persists exact phase legality and exact role-week bands.
* `PHASE_GUARDRAILS` stores successfully.
* `PHASE_STRUCTURE` and downstream `PHASE_PREVIEW` writer tasks are validated by CrewAI guardrails before deterministic artifact normalization runs.

**Problem**

* Raw writer candidates can still carry broader scenario-level legality.
* `phase_execution_context_match(...)` correctly rejects that drift, but too early, before the same deterministic projection used by guarded-store normalization is applied.

**Constraints**

* No authority-model redesign.
* No schema change.
* Guardrails must remain validators, not semantic repair owners.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Normalize `PHASE_GUARDRAILS` writer candidates before task guardrails run.
* [x] Normalize `PHASE_STRUCTURE` writer candidates before task guardrails run.
* [x] Normalize `PHASE_PREVIEW` writer candidates on the same early path.
* [x] Reuse existing code-owned normalization instead of duplicating authority logic in guardrails.
* [x] Repair final `trace_upstream` metadata and canonical `quality_intent` drift in downstream Phase artifacts.

**Non-Goals**

* [x] No repo-wide generic artifact preprocessor system.
* [x] No change to Phase authority ownership, Season persistence, or shared skeleton design.

---

## 3) Proposed Behavior

**User/System behavior**

* Writer-task guardrails for Phase artifacts see the same exact-authority-projected candidate that guarded-store persistence would later enforce.
* `PHASE_GUARDRAILS` is projected to exact role-week bands, exact legality, and exact phase-local objective before task guardrails evaluate it.
* `PHASE_STRUCTURE` is narrowed to exact legality from bound `phase_execution_context` and persisted `PHASE_GUARDRAILS` load bands before task guardrails evaluate it.
* `PHASE_PREVIEW` is normalized to stored/shared skeleton semantics before task guardrails evaluate it.
* Exact phase legality remains structural only; operational `REST -> NONE/NONE` semantics are handled downstream by day-role validation and are not reintroduced into persisted `PHASE_STRUCTURE.allowed_intensity_domains`.
* Writer task input for Phase artifacts now carries a compact exact-authority block so the active writer sees field-level exact copy expectations before emitting output.
* `phase_bundle_finalize` now receives a dedicated compact authority-freeze block and, when deterministic phase authority is already injected, no longer gets live access to the same contract-read tools for rediscovery.
* Final artifact normalization now repairs missing immediate `trace_upstream` references and canonicalizes `quality_intent` for supported phase semantics.

**UI impact**

* UI affected: No direct UI change.

**Non-UI behavior**

* Components involved:
  * `src/rps/crewai_runtime/guardrails.py`
  * `src/rps/agents/crewai_backend.py`
  * existing deterministic normalization in `src/rps/agents/output_normalization.py`
* Contracts touched:
  * writer-task guardrail execution order
  * Phase artifact candidate normalization path

---

## 4) Implementation Analysis

**Components / Modules**

* `guardrails.py`: use bound `phase_execution_context` as the primary exact-authority source in the narrow pre-guardrail `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` projection helpers and emit compact legality-source diagnostics on mismatch.
* `crewai_backend.py`: frontload compact exact-authority blocks into Phase writer and phase-finalizer task input; add task-scoped tool overrides so `phase_bundle_finalize` can run tool-free when deterministic contracts are already injected.
* `output_normalization.py`: project exact `PHASE_GUARDRAILS` authority, canonicalize supported `quality_intent` values, and repair `trace_upstream` for `PHASE_STRUCTURE` and `PHASE_PREVIEW`.
* `guarded_store.py`: accept operational `NONE` only for `REST` / fixed non-training days instead of requiring `NONE` inside exact structural phase legality.

**Data flow**

* Inputs:
  * bound `phase_execution_context`
  * stored/just-persisted `phase_guardrails`
  * stored/just-persisted `phase_structure`
  * optional `season_plan` for verbatim constraint enrichment only
* Processing:
  * writer emits candidate
  * pre-guardrail helper projects exact authority
  * task guardrails validate projected candidate
  * phase finalizer consumes an injected authority-freeze block and loses contract-read tools when both deterministic phase contracts are already bound
  * guarded-store normalization remains second-line protection
* Outputs:
  * same persisted artifact types
  * fewer false writer-task guardrail failures

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: writer-task validation now runs against pre-normalized candidates for `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none at schema/interface level
* Fallback behavior: if exact authority inputs are unavailable, writer guardrails still fail clearly against the uncorrected candidate

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns with upstream-first ownership and existing authority ADRs by keeping semantic repair ahead of validation

**Impacted areas**

* UI: none
* Pipeline/data: Phase writer-task execution order changes
* Renderer: none
* Workspace/run-store: no contract change; persisted outputs remain store-normalized
* Validation/tooling: writer-task guardrails now evaluate projected candidates
* Deployment/config: none

---

## 6) Options & Recommendation

**Option A**

* Add a narrow pre-guardrail normalization hook for Phase writer tasks only.

**Option B**

* Move repair logic into `phase_execution_context_match(...)`.

**Recommendation**

* Choose Option A. It preserves validation ownership boundaries and reuses the existing deterministic projection path without broad redesign.

---

## 7) Acceptance Criteria (DoD)

* [x] `PHASE_GUARDRAILS` writer candidates are normalized before task guardrails evaluate them.
* [x] `PHASE_STRUCTURE` writer candidates are normalized before task guardrails evaluate them.
* [x] `PHASE_PREVIEW` candidates can consume the same early normalization path.
* [x] `phase_execution_context_match(...)` passes for candidates that only drift in code-owned exact-authority fields and are repairable from deterministic inputs.
* [x] Missing exact authority still fails deterministically.
* [x] Final normalized Phase artifacts carry canonical immediate upstream lineage and supported canonical `quality_intent` values.
* [x] Targeted regression tests cover the original `phase_structural_allowed_domains_mismatch` class and the remaining first-pass `phase_s5_band_mismatch` drift.

---

## 8) Migration / Rollout

* No migration required.
* Rollout is immediate with code deployment.

---

## 9) Risks & Failure Modes

* If `loaded_inputs` are not threaded into the writer path, the pre-guardrail helper cannot project exact authority.
* If just-persisted upstream Phase artifacts are not retained in the same run, downstream writer tasks may normalize against stale or missing inputs.
* Detection: writer-task guardrail failures in `rps.log` / telemetry with the same mismatch codes.

---

## 10) Observability / Logging

* Existing `CREW_TASK_GUARDRAIL_FAILED` events remain the primary signal.
* No new event type required; the meaningful change is that false failures on code-owned Phase authority fields are removed.

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — record the writer-task pre-normalization fix.
* [x] `doc/overview/feature_backlog.md` — add implemented feature entry.

---

## 12) Link Map

* [FEAT_phase_authority_realignment_and_shared_week_skeleton](/Users/alexander/RPS/doc/specs/features/FEAT_phase_authority_realignment_and_shared_week_skeleton.md)
* [ADR-058-phase-authority-chain-and-shared-week-skeleton](/Users/alexander/RPS/doc/adr/ADR-058-phase-authority-chain-and-shared-week-skeleton.md)
* [FEAT_upstream_first_planning_pipeline](/Users/alexander/RPS/doc/specs/features/FEAT_upstream_first_planning_pipeline.md)
* [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)
