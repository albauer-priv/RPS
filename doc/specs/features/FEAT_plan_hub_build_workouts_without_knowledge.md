---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-21
Owner: Plan Hub
---
# FEAT: Plan Hub Build Workouts Without Knowledge Store

* **ID:** FEAT_plan_hub_build_workouts_without_knowledge
* **Status:** Implemented
* **Owner/Area:** Plan Hub / Workout Export
* **Last-Updated:** 2026-04-21

## 1) Context / Problem

**Current behavior**

* Plan Hub disables all planning actions when the shared knowledge store is not ready.
* `Build Workouts` is treated like an agent-driven step.

**Problem**

* `Build Workouts` now uses a local deterministic exporter and no longer depends on the vector store.
* The global knowledge gate unnecessarily disables direct `Run Workouts` actions and scoped `Build Workouts` runs.

**Constraints**

* `Week Plan`, `Phase`, and orchestrated planning still depend on agent knowledge and must remain gated.
* No change to run-store, queue, or artifact contracts.

## 2) Goals & Non-Goals

**Goals**

* [x] Allow direct `Build Workouts` execution when the knowledge store is unavailable.
* [x] Allow scoped `Build Workouts` manual runs without the knowledge store.
* [x] Keep knowledge gating for agent-based scopes.

**Non-Goals**

* [ ] Removing the knowledge store gate for `Week Plan`, `Phase`, `Season`, or orchestrated runs.

## 3) Proposed Behavior

* Plan Hub keeps showing knowledge-store readiness.
* If the knowledge store is missing:
  * agent-backed planning actions remain disabled
  * `Build Workouts` direct actions remain enabled
  * scoped `Build Workouts` runs remain allowed

## 4) Implementation Analysis

* `src/rps/ui/pages/plan/hub.py`
  * add explicit helpers for scope/step knowledge requirements
  * use step-specific lock state instead of one global `planning_locked` value for every button

## 5) Impact Analysis

* Backward compatible: Yes
* Breaking changes: none
* UI impact: direct `Run Workouts` button and scoped `Build Workouts` manual run become available when only the knowledge store is missing

## 6) Recommendation

* Use scope-aware knowledge gating rather than a global planning lock for all actions.

## 7) Acceptance Criteria

* [x] `Build Workouts` direct action is not disabled solely because the knowledge store is unavailable.
* [x] Scoped `Build Workouts` manual run is not disabled solely because the knowledge store is unavailable.
* [x] `Week Plan` and orchestrated runs still require a ready knowledge store.

## 8) Migration / Rollout

* No migration needed.

## 9) Risks & Failure Modes

* Failure mode: another step becomes unintentionally ungated
  * Detection: targeted unit tests around helper logic
  * Safe behavior: keep default as knowledge-required except the explicit workout-export scope

## 10) Observability / Logging

* No new runtime logging required.

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_plan_hub_build_workouts_without_knowledge.md`
* [x] `CHANGELOG.md`

## 12) Link Map

* `doc/ui/pages/plan_hub.md`
* `doc/architecture/system_architecture.md`
* `doc/overview/artefact_flow.md`
* `doc/runbooks/validation.md`
