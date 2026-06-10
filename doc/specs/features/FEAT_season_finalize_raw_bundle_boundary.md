---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-10
Owner: Planning Runtime
---
# FEAT: Season Finalize Raw Bundle Boundary

* **ID:** FEAT_season_finalize_raw_bundle_boundary
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-06-10
* **Related:** `season_plan_finalize`, `SeasonPlanDraftBundleModel`

---

## 1) Context / Problem

**Current behavior**

* `season_plan_finalize` emitted structured output directly into `SeasonPlanDraftBundleModel`.
* Governance-shaped audit objects could land in `constraints[]` and fail strict parse before repo-owned normalization ran.

**Problem**

* The first strict boundary was too early.
* `normalize_season_plan_draft_bundle(...)` could not repair structurally recoverable audit-slot drift.

**Constraints**

* No Season authority-model redesign.
* No persisted `SEASON_PLAN` schema change.
* Guardrails remain active and strict.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move `season_plan_finalize` to a raw JSON boundary.
* [x] Add one narrow repo-owned coercion step for `constraints[]` vs `load_governance[]`.
* [x] Preserve strict `SeasonPlanDraftBundleModel` validation after coercion.

**Non-Goals**

* [x] No change to persisted Season artifact schema.
* [x] No change to Phase or Week finalizer output boundaries.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_plan_finalize` now returns JSON first.
* Repo code reclassifies misplaced audit items between `constraints[]` and `load_governance[]`.
* Strict bundle validation still runs before Season normalization and writer/store flow.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: CrewAI task policy, season finalizer execution path, active Season finalizer guidance.
* Contracts touched: internal `SeasonPlanDraftBundleModel` boundary only.

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/task_policies.yaml`: `season_plan_finalize` moved to `output_mode: json`
* `src/rps/agents/crewai_backend.py`: raw-bundle extraction, audit-slot coercion, strict post-coercion validation
* `config/crewai/tasks.yaml`, `prompts/agents/season_plan_manager.md`, `skills/season/plan-synthesis/SKILL.md`: explicit slot-discipline frontloading

**Data flow**

* Inputs: raw finalizer JSON
* Processing: task-specific slot coercion -> strict `SeasonPlanDraftBundleModel` validation -> existing Season normalization -> existing normalized-contract validation
* Outputs: unchanged internal normalized season bundle and persisted Season artifact

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: strict validation remains fail-closed after coercion

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none on persisted artifacts
* Fallback behavior: fail closed if audit items are mixed or unclassifiable

**Conflicts with ADRs / Principles**

* Potential conflicts: none; this reinforces early repo-owned correction before later enforcement
* Resolution: compatible with current active planning-layer rule

**Impacted areas**

* UI: none
* Pipeline/data: Season finalizer execution path only
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: new pre-model coercion for one task
* Deployment/config: task policy output-mode change

**Required refactoring**

* Add one task-specific raw-bundle coercion helper
* Teach internal multi-agent execution to return JSON-mode non-artifact outputs

---

## 6) Recommendation

* Choose a raw JSON boundary for `season_plan_finalize`, then validate strictly after repo-owned audit-slot coercion.
* Do not weaken guardrails or broaden coercion beyond the two audit slots.

---

## 7) Acceptance Criteria

* [x] `season_plan_finalize` uses `output_mode: json`
* [x] Governance-shaped audit items inside `constraints[]` are moved to `load_governance[]` before strict model validation
* [x] Mixed or unclassifiable audit items fail deterministically
* [x] Existing Season normalization and normalized-contract validation still run after strict bundle validation

---

## 8) Migration / Rollout

**Migration strategy**

* None; internal execution-path change only.

**Rollout / gating**

* No feature flag.
* Safe rollback is direct revert of task policy plus helper path.

---

## 9) Risks & Failure Modes

* Failure mode: raw bundle contains mixed audit-family fields in one object
  * Detection: deterministic runtime error before normalization
  * Safe behavior: abort Season finalize
  * Recovery: adjust active finalizer guidance or offending raw output

---

## 10) Observability / Logging

**Diagnostics**

* Existing Season finalizer failure path remains the main runtime signal.
* Raw-bundle coercion failures surface before Season normalization.

---

## 11) Documentation Updates

* [x] [doc/specs/features/FEAT_season_finalize_raw_bundle_boundary.md](/Users/alexander/RPS/doc/specs/features/FEAT_season_finalize_raw_bundle_boundary.md) — new feature record
* [x] `CHANGELOG.md` — behavior change summary
