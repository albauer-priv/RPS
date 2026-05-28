---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-28
Owner: Planning Contracts
---
# FEAT: Selected Scenario Contract Schema Alignment

* **ID:** FEAT_selected_scenario_contract_schema_alignment
* **Status:** Implemented
* **Owner/Area:** Planning / Schema Contracts
* **Last-Updated:** 2026-05-28
* **Related:** [FEAT_selected_scenario_contract_chain](/Users/alexander/RPS/doc/specs/features/FEAT_selected_scenario_contract_chain.md), [FEAT_season_scenarios_complete_selection_contract](/Users/alexander/RPS/doc/specs/features/FEAT_season_scenarios_complete_selection_contract.md)

---

## 1) Context / Problem

**Current behavior**

* `build_selected_scenario_contract_context(...)` emits a full code-owned selected-scenario contract.
* `SEASON_PLAN`, `PHASE_GUARDRAILS`, and `PHASE_STRUCTURE` persist that contract or inherit it from Season.

**Problem**

* The persisted schemas for Season and Phase drifted from the actual runtime contract shape.
* `SEASON_PLAN` store validation failed because list-valued fields and expanded structure fields were no longer accepted by `season_plan.schema.json`.
* Phase persistence was at risk of the same failure because Phase normalization already injects the full inherited contract into `PHASE_GUARDRAILS` and `PHASE_STRUCTURE`.

**Constraints**

* Week must remain on the reduced `inherited_planning_posture` shape.
* Phase Preview must remain derivation-only.
* The repo bundles canonical schemas into knowledge copies and validates strict required-property coverage.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Define one canonical shared schema for the full selected-scenario contract.
* [x] Reuse that schema across Season and Phase persisted artifacts.
* [x] Keep Week reduced and Preview derivation-only.
* [x] Add regression coverage at guarded-store and normalization boundaries.

**Non-Goals**

* [x] No `meta.version_key` repair.
* [x] No broad refactor of Week contract policy.
* [x] No expansion of `PHASE_PREVIEW` to carry the full contract.

---

## 3) Proposed Behavior

**User/System behavior**

* `SEASON_PLAN`, `PHASE_GUARDRAILS`, and `PHASE_STRUCTURE` accept the same full contract shape already carried by runtime.
* `WEEK_PLAN` continues to store only the reduced inherited planning posture.
* `PHASE_PREVIEW` continues to derive from Phase authority without persisting the full contract.

**UI impact**

* UI affected: No direct UI flow change.

**Non-UI behavior**

* Components involved: schema validation, guarded store, normalization, runtime bundle typing.
* Contracts touched: `SEASON_PLAN.data.selected_scenario_contract`, `PHASE_GUARDRAILS.data.inherited_scenario_contract`, `PHASE_STRUCTURE.data.inherited_scenario_contract`.

---

## 4) Implementation Analysis

**Components / Modules**

* `specs/schemas/selected_scenario_contract.schema.json`: canonical shared full-contract schema.
* `season_plan.schema.json`, `phase_guardrails.schema.json`, `phase_structure.schema.json`: refactor to shared `$ref`.
* `src/rps/crewai_runtime/models.py`: reusable `SelectedScenarioContractModel`.
* tests: guarded-store, normalization, planning-contract, runtime model coverage.

**Data flow**

* Inputs: `SEASON_SCENARIOS`, `SEASON_SCENARIO_SELECTION`, deterministic Season/Phase context.
* Processing: full contract derived once, persisted in Season, inherited into Phase, projected down to reduced Week posture.
* Outputs: schema-valid Season and Phase artifacts, unchanged reduced Week and Preview payloads.

**Schema / Artefacts**

* New schema: `selected_scenario_contract.schema.json`
* Changed schemas: `season_plan.schema.json`, `phase_guardrails.schema.json`, `phase_structure.schema.json`
* Validator implications: `check_schema_required.py`, `bundle_schemas.py`, guarded store acceptance must all pass.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: No, persisted artifact contract changes for Season and Phase.
* Breaking changes: older Season/Phase payloads that use the narrow contract shape may fail if revalidated under the new schemas.
* Fallback behavior: none; runtime authority is already on the full shape.

**Conflicts with ADRs / Principles**

* No ADR conflict identified.
* Aligns with single-source-of-truth and code-owned contract propagation rules.

**Impacted areas**

* UI: no direct UI change.
* Pipeline/data: Season and Phase persistence accept current runtime shape.
* Renderer: no template redesign required.
* Workspace/run-store: guarded-store validation changes.
* Validation/tooling: schema bundling and artifact model generation remain in sync.
* Deployment/config: version bump only.

**Required refactoring**

* Replace duplicated contract schema fragments with one shared schema.
* Add reusable internal Pydantic model for the full contract.

---

## 6) Options & Recommendation

### Option A — Shared full-contract schema

**Summary**

* One shared schema is referenced by Season and Phase contract fields.

**Pros**

* Removes the duplication that caused the drift.
* Keeps runtime and persisted contract policy aligned.

**Cons**

* Changes multiple schemas together.

**Risk**

* Requires careful bundle/regeneration and regression coverage.

### Option B — Local per-schema patches

**Summary**

* Patch each schema independently.

**Pros**

* Slightly smaller immediate code diff.

**Cons**

* Leaves duplicated contract definitions in place.
* High future drift risk.

### Recommendation

* Choose: Option A
* Rationale: the runtime already uses one full contract shape; persistence should do the same.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `SEASON_PLAN` accepts the full selected-scenario contract shape.
* [x] `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` accept the full inherited contract shape.
* [x] `WEEK_PLAN` remains reduced.
* [x] `PHASE_PREVIEW` remains derivation-only and unchanged as a persisted schema.
* [x] Validation passes: `check_schema_required.py`, `bundle_schemas.py`, syntax, lint, type check, targeted pytest.
* [x] No regressions in guarded store, normalization, and contract validation.

---

## 8) Migration / Rollout

**Migration strategy**

* Schema-only contract alignment; no explicit data migration.

**Rollout / gating**

* No feature flag.
* Safe rollback is git revert of schema + model + tests.

---

## 9) Risks & Failure Modes

* Failure mode: Phase starts failing after Season is fixed.

  * Detection: guarded-store/schema failures on `PHASE_GUARDRAILS` or `PHASE_STRUCTURE`
  * Safe behavior: fail closed at store validation
  * Recovery: ensure Phase schemas reference the shared full contract

* Failure mode: full contract leaks into Week or Preview

  * Detection: Week/Preview regression tests fail
  * Safe behavior: reject schema/contract mismatch
  * Recovery: preserve reduced projection in Week and derivation-only Preview

---

## 10) Observability / Logging

**New/changed events**

* No new event types required.

**Diagnostics**

* Store failures surface in `rps.workspace.guarded_store`
* Schema issues surface in `check_schema_required.py` / bundled outputs / guarded-store tests

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record schema alignment and runtime contract acceptance
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — mark implemented feature

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* Related features:
  * [FEAT_selected_scenario_contract_chain](/Users/alexander/RPS/doc/specs/features/FEAT_selected_scenario_contract_chain.md)
  * [FEAT_season_scenarios_complete_selection_contract](/Users/alexander/RPS/doc/specs/features/FEAT_season_scenarios_complete_selection_contract.md)
  * [FEAT_contract_validation_assembly_fix](/Users/alexander/RPS/doc/specs/features/FEAT_contract_validation_assembly_fix.md)
