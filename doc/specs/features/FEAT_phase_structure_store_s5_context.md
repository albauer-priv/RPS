---
Version: 1.1
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning Contracts
---
# FEAT: Phase Structure Store S5 Context

* **ID:** FEAT_phase_structure_store_s5_context
* **Status:** Implemented
* **Owner/Area:** Planning Contracts
* **Last-Updated:** 2026-05-20
* **Related:** `PHASE_STRUCTURE` guarded-store validation, deterministic phase execution context

---

## 1) Context / Problem

**Current behavior**

* `PHASE_STRUCTURE` writes are validated against `validate_phase_against_execution_context(...)`.
* The guarded store rebuilds `phase_execution_context` at write time.

**Problem**

* The store helper passed an invalid `planning_events_payload` keyword into `build_load_capacity_block(...)`, then swallowed the resulting exception and returned `{}`.
* The store also needs phase-scoped inputs such as `target_week`, `phase_range`, `season_plan_payload`, `week_role_by_week`, `phase_role_by_week`, and `scenario_cadence`.
* As a result, `build_phase_execution_context(...)` received an empty load-capacity payload and emitted an empty `phase_s5_bands` list.
* Guarded-store validation then failed with `phase_s5_context_missing` although the orchestrator had already derived valid S5 bands for the same phase.

**Constraints**

* No schema change.
* Fix must stay deterministic and code-owned.
* Store-time validation must remain aligned with orchestrator/runtime authority.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Rebuild phase-scoped S5 context in the guarded store using the same deterministic inputs as the orchestrator.
* [x] Prevent false `phase_s5_context_missing` failures for valid `PHASE_STRUCTURE` payloads.

**Non-Goals**

* [x] No change to `PHASE_STRUCTURE` schema.
* [x] No prompt-only workaround or validator relaxation.

---

## 3) Proposed Behavior

**User/System behavior**

* When `PHASE_STRUCTURE` is stored, the guarded store derives phase-scoped load-capacity context from the active phase range and selected scenario authority before validating S5 bands.
* `phase_execution_context.phase_s5_bands` is available whenever the underlying deterministic inputs are available.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `guarded_store`, deterministic planning context, phase contract validation
* Contracts touched: `PHASE_STRUCTURE` store-time contract validation

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/guarded_store.py`: build phase-scoped load-capacity context for `PHASE_STRUCTURE` validation and log deterministic failures.
* `src/rps/planning/deterministic_context.py`: tighten `build_load_capacity_block(...)` to the real supported keyword set.
* `tests/test_guarded_store.py`: regression coverage for forwarded phase-scope parameters and logged builder failures.

**Data flow**

* Inputs: season plan, selected scenario, availability, logistics, zone model, wellness, KPI profile
* Processing: derive phase execution seed -> forward phase-scoped values into `build_load_capacity_block(...)` -> log empty/failed S5 state before contract validation
* Outputs: non-empty deterministic `phase_s5_bands` in store-time validation context

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: `validate_phase_against_execution_context(...)` now receives complete phase-scoped S5 context

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: unchanged if upstream deterministic context is genuinely unavailable

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns store validation with existing deterministic-contract architecture

**Impacted areas**

* UI: none
* Pipeline/data: `PHASE_STRUCTURE` persistence path
* Renderer: none
* Workspace/run-store: guarded-store validation path only
* Validation/tooling: phase contract validation gets the correct deterministic context
* Deployment/config: none

**Required refactoring**

* Introduce a phase-specific store helper for load-capacity context assembly
* Remove silent exception swallowing for load-capacity helper failures

---

## 6) Options & Recommendation

### Option A — Rebuild full phase-scoped load-capacity context in store

**Summary**

* Reuse existing deterministic builders with the same phase-scope inputs the orchestrator already provides.

**Pros**

* Keeps one source of truth
* Deterministic and testable
* Preserves strict validation

**Cons**

* Slightly more assembly logic in guarded store

**Risk**

* Low; mirrors existing orchestration path

### Option B — Relax `phase_s5_bands` validator

**Summary**

* Allow empty S5 context during store validation.

**Pros**

* Small code change

**Cons**

* Weakens a useful contract
* Hides real context regressions

### Recommendation

* Choose: Option A
* Rationale: the bug is missing deterministic input wiring, not over-strict validation

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `PHASE_STRUCTURE` store-time validation rebuilds phase-scoped load-capacity context with `target_week` and `phase_range`.
* [x] Week-role and scenario-cadence inputs are forwarded into phase-scoped S5 derivation.
* [x] Regression test covers the new store helper wiring.
* [x] Invalid builder kwargs are rejected by the wrapper instead of being silently forwarded.
* [x] Builder failures are logged explicitly in the guarded store.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `./scripts/run_lint.sh`
* [x] Validation passes: `./scripts/run_typecheck.sh`
* [x] Validation passes: targeted `pytest`

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert guarded-store helper change

---

## 9) Risks & Failure Modes

* Failure mode: store still cannot derive phase-scoped context because upstream artifacts are genuinely missing
  * Detection: `phase_s5_context_missing` or related deterministic-context blockers in `rps.log`
  * Safe behavior: store rejects invalid payload
  * Recovery: restore missing upstream artifacts or selected-scenario inputs

---

## 10) Observability / Logging

**New/changed events**

* No new log event required
* Guarded store now logs phase validation context weeks and load-capacity builder failures explicitly

**Diagnostics**

* Check `rps.workspace.guarded_store` store-failure logs and `PHASE_STRUCTURE` payload dump

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — add fix note

---

## 12) Link Map

* [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
* [doc/overview/artefact_flow.md](/Users/alexander/RPS/doc/overview/artefact_flow.md)
* [src/rps/planning/deterministic_context.py](/Users/alexander/RPS/src/rps/planning/deterministic_context.py)
* [src/rps/planning/load_bands.py](/Users/alexander/RPS/src/rps/planning/load_bands.py)
* [src/rps/workspace/guarded_store.py](/Users/alexander/RPS/src/rps/workspace/guarded_store.py)
