---
Version: 1.1
Status: Draft
Last-Updated: 2026-07-05
Owner: Planner Orchestration
---
# FEAT: Plan Week Testability and Resolution Refactor

* **ID:** FEAT_plan_week_testability_and_resolution_refactor
* **Status:** Draft
* **Owner/Area:** Planner Orchestration / Test Infrastructure
* **Last-Updated:** 2026-07-05
* **Related:** `src/rps/orchestrator/plan_week.py`, `src/rps/planning/deterministic_context.py`, `tests/test_plan_pages.py`, `tests/test_plan_hub_worker.py`

---

## 1) Context / Problem

**Current behavior**

* `plan_week(...)` coordinates previous-week evidence gating, phase dependency resolution, deterministic context injection, week planning, optional report creation, and export follow-up in one large orchestration path.
* UI/orchestrator integration tests in `tests/test_plan_pages.py` rely on large inline setup blocks and many ad hoc monkeypatches to reach the targeted planning branch.
* Deterministic phase execution fallback logic existed partly in placeholder form, so integration tests were discovering missing fallback behavior indirectly instead of focused unit tests catching it first.

**Problem**

* Legitimate runtime contract tightening around previous-week evidence and DES report gating caused multiple scoped/isolated tests to fail before they reached the behavior they were intended to validate.
* Test setup is duplicated and fragile: missing `KPI_PROFILE`, `LOGISTICS`, or previous-week evidence caused repeated false-negative failures across unrelated test intentions.
* Internal `plan_week(...)` state is passed around through loose dicts/tuples and implicit branching, which makes isolated testing harder and increases regression risk when prerequisites evolve.
* Deterministic context fallback rules for cadence and phase week roles are not surfaced as first-class, typed resolution results.

**Constraints**

* UI pages must remain thin and continue delegating all execution to orchestrator/service helpers.
* Authority boundaries, persistence ownership, and upstream-first staged planning rules must remain unchanged.
* Deterministic truth must stay code-owned; prompt/test helpers must not become a second source of runtime truth.
* The refactor should be incremental and low-risk, with no required schema migration.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Extract canonical test fixtures/builders for `plan_week` and related UI/orchestrator tests.
* [ ] Introduce typed dataclasses for `plan_week` request and resolution stages instead of ad hoc intermediate tuples/dicts.
* [ ] Decompose `plan_week(...)` into smaller resolver/execution phases that are unit-testable in isolation.
* [ ] Add focused deterministic-context tests so cadence/role fallback behavior is verified directly.
* [ ] Preserve current user-visible behavior while reducing test fragility and clarifying internal contracts.

**Non-Goals**

* [ ] Redesigning Season/Phase/Week authority boundaries.
* [ ] Changing persisted artifact schemas or versioning strategy.
* [ ] Moving runtime truth into prompt text, YAML, or test helpers.
* [ ] Rewriting Plan Hub / Week planning UI semantics.

---

## 3) Proposed Behavior

**User/System behavior**

* No intentional end-user workflow change is introduced by this refactor.
* `plan_week(...)` keeps the same planning/report/export semantics, but its preflight and resolution steps become explicit internal stages.
* Tests stop encoding large amounts of implicit prerequisite knowledge inline and instead use shared canonical setup helpers.
* Deterministic phase-execution resolution becomes explicitly typed and directly tested rather than being validated only via integration side effects.

**UI impact**

* UI affected: No direct UX change
* If Yes: n/a — stability and maintainability only

**Non-UI behavior (if applicable)**

* Components involved: `src/rps/orchestrator/plan_week.py`, new internal resolver/model helpers, `src/rps/planning/deterministic_context.py`, test helper modules under `tests/`
* Contracts touched: internal Python orchestration contracts only; no artifact schema change

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/orchestrator/plan_week.py`: split monolithic orchestration into explicit request, evidence, phase-dependency, and execution steps.
* `src/rps/orchestrator/plan_week_models.py` (new): dataclasses for orchestration request/resolution objects.
* `src/rps/planning/deterministic_context.py`: route phase cadence/role fallback through explicit resolution logic.
* `src/rps/planning/deterministic_context_models.py` (optional new file): dataclass for typed phase execution resolution.
* `tests/helpers/planning_context.py` (new): canonical seed/mock helpers for week-planning tests.
* `tests/helpers/artifact_factories.py` (new, optional): shared minimal artifact factories to reduce inline JSON duplication.
* `tests/test_plan_pages.py`, `tests/test_plan_hub_worker.py`: switch to canonical helpers and shrink branch-specific setup noise.
* `tests/test_deterministic_context.py` (new) or targeted additions to existing deterministic/planning tests: cover fallback behavior directly.

**Data flow**

* Inputs: `athlete_id`, target week, existing artifacts, previous-week evidence versions, exact-range phase artifacts, optional forced steps.
* Processing:
  1. build a typed week-run request
  2. resolve previous-week evidence/report state
  3. resolve phase dependencies and effective requested steps
  4. resolve deterministic phase execution context
  5. execute phase / week / export scopes through explicit helpers
* Outputs: unchanged planning artifacts and run-store entries, but with clearer internal control flow and test surfaces.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: no artifact schema/version changes; tests and typing should expand

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none expected at artifact or UI contract level
* Fallback behavior: if the refactor is incomplete, existing orchestration semantics must remain fail-closed and explicit

**Conflicts with ADRs / Principles**

* Potential conflicts: none if the refactor stays internal to orchestrator/test structure
* Resolution: aligns with `ADR-001` (UI delegates to orchestrators) and `ADR-056` (upstream-first planning pipeline)
* ADR decision: no new ADR is required **if** this work does not change authority boundaries, persistence strategy, cross-cutting contracts, or orchestration ownership. If the implementation expands into those areas, an ADR update becomes mandatory before merge.

**Impacted areas**

* UI: no direct UX change; integration tests around Plan Hub / Week pages become less fragile
* Pipeline/data: no change to artifact production semantics
* Renderer: none expected
* Workspace/run-store: no contract change; internal resolution typing only
* Validation/tooling: new unit/integration test helpers and stronger focused coverage
* Deployment/config: none

**Required refactoring**

* Extract canonical plan-week test fixtures/builders and report-gate mocks from `tests/test_plan_pages.py`
* Introduce orchestration dataclasses for request/resolution boundaries
* Split `plan_week(...)` into explicit internal phases with isolated tests
* Introduce typed deterministic phase execution resolution and direct tests for cadence/role fallback logic

---

## 6) Options & Recommendation

### Option A (recommended) — Incremental internal refactor with dataclasses and shared test infrastructure

**Summary**

* Keep current runtime behavior, but introduce typed internal models, resolver helpers, and canonical test fixtures.

**Pros**

* Low migration risk
* Preserves authority/runtime boundaries
* Reduces monkeypatch-heavy integration tests
* Makes evidence/phase/deterministic fallback logic directly unit-testable

**Cons**

* Still leaves `plan_week` within the same domain module unless a second cleanup step further separates helpers
* Requires disciplined sequencing across tests and production code to avoid behavior drift

**Risk**

* Moderate implementation risk if refactor and semantic changes get mixed in the same PR

### Option B — Keep current monolith and only harden tests

**Summary**

* Limit the response to better fixtures and mocks while leaving `plan_week(...)` structurally unchanged.

**Pros**

* Smaller immediate change surface
* Lowest short-term code risk

**Cons**

* Leaves the orchestration complexity in place
* Future contract changes will still be harder to isolate and debug
* Does not address loose intermediate state passing

### Recommendation

* Choose: Option A
* Rationale: the recent failures showed both test fragility **and** a small but real orchestration/fallback design gap; a fixture-only cleanup would address symptoms but not the maintainability root cause.

---

## 6a) Implementation Readiness Review

Before implementation starts, the feature owner/agent must explicitly review:

* [x] Scope completeness: all affected modules, contracts, tests, docs, and helper paths are named
* [x] Decision completeness: no critical product or architecture decisions are left implicit
* [x] Architecture conformity: the proposal matches current ADRs, authority boundaries, persistence rules, and validation ownership
* [x] Execution readiness: the plan is concrete enough to implement without inventing missing behavior during coding

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Shared test helpers exist for previous-week evidence, minimal phase/week context, and report-gate mocking.
* [ ] `tests/test_plan_pages.py` no longer carries repeated large inline setup blocks for standard `plan_week` prerequisites.
* [ ] `plan_week(...)` uses typed request/resolution dataclasses for its main internal orchestration boundaries.
* [ ] Deterministic phase cadence/role fallback logic has focused unit tests independent of UI integration tests.
* [ ] Existing `tests/test_plan_pages.py` and `tests/test_plan_hub_worker.py` remain green.
* [ ] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [ ] Validation passes: `./scripts/run_lint.sh`
* [ ] Validation passes: `./scripts/run_typecheck.sh`
* [ ] Validation passes: targeted pytest for `tests/test_plan_pages.py`, `tests/test_plan_hub_worker.py`, and new focused resolver/context tests

---

## 8) Migration / Rollout

**Migration strategy**

* No artifact or schema migration required.
* Execute in small PR slices:
  1. test helper extraction
  2. orchestration dataclasses
  3. `plan_week(...)` internal decomposition
  4. deterministic-context typed resolution + focused tests

## 8a) Deterministic Context Dataclass Migration Follow-Up Plan

This feature now also tracks the agreed follow-up direction for deterministic runtime truth:

> Convert as much deterministic context resolution as practical to internal dataclasses, while keeping dict/JSON payload projection stable at prompt/render/guardrail/snapshot boundaries until each downstream consumer is intentionally migrated.

### Migration principles

* Start with internal resolution models, not big-bang public return-type changes.
* Prefer `dataclass -> to_payload()` staging over direct replacement of dict-returning builders.
* Keep deterministic truth code-owned and derived from authoritative runtime/workspace data only.
* Do not let typed models become a second persisted artifact contract layer.

### Recommended staged sequence

1. **Phase execution resolution**
   * Introduce an internal dataclass such as `PhaseExecutionResolution` in `src/rps/planning/deterministic_context.py`.
   * Cover at least:
     * `scenario_cadence`
     * `cadence_week_roles`
     * `week_role_by_iso_week`
     * `blocking_issues`
     * `used_fallbacks`
   * Keep `build_phase_execution_context(...)` outwardly compatible by still returning a dict payload.

2. **Phase execution context object**
   * Wrap typed resolution plus objective/rest-day/event details in a typed context model.
   * Add explicit `to_payload()` projection.

3. **Week calendar context**
   * Type day-matrix resolution, active weekly load band, and availability/logistics/event joins.

4. **Load capacity context**
   * Type code-owned load-band/KPI/intensity-domain resolution with explicit fallback tracking.

5. **Selected scenario structure / phase slot context**
   * Type phase-slot math, shortened-phase handling, cadence-derived role generation, and related blockers.

6. **Report evidence context (later/optional)**
   * Type report/evidence resolution after the planning-critical contexts stabilize.

7. **Call-site migration later**
   * Only after typed internals stabilize, evaluate moving `plan_week.py`, renderers, and guardrail consumers away from dict `.get(...)` access.

### Phase-1 direct test expectations

* active slot already provides complete cadence roles
* fallback to `phase_raw.cadence_week_roles`
* fallback to cadence-pattern-derived roles
* unsupported cadence produces a blocking issue
* cadence-role count mismatch vs. phase length produces a blocking issue

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the latest refactor slice; no persisted data migration is involved

---

## 9) Risks & Failure Modes

* Failure mode: resolver extraction changes planning semantics accidentally

  * Detection: existing integration tests or targeted smoke runs fail
  * Safe behavior: fail the run/test rather than silently broadening or skipping prerequisites
  * Recovery: revert to the last known-good slice and compare typed resolver outputs against prior behavior

* Failure mode: dataclasses duplicate or drift from existing runtime truth

  * Detection: tests require contradictory field population or wrapper-only conversion logic grows unexpectedly
  * Safe behavior: keep dataclasses internal and derived from authoritative workspace/code-owned truth only
  * Recovery: reduce dataclass scope to request/resolution transport only

* Failure mode: test helpers become a second semantic source of runtime rules

  * Detection: helper defaults start inventing behavior not justified by production contracts
  * Safe behavior: helpers seed only canonical minimal artifacts and explicit mocks
  * Recovery: move behavior-specific logic back into production resolvers and keep helpers purely mechanical

---

## 10) Observability / Logging

**New/changed events**

* No new event types required
* Existing `plan_week` logs should remain sufficient, but internal helper naming should make failure points easier to interpret in stack traces and logs

**Diagnostics**

* `runtime/athletes/<athlete_id>/logs/rps.log`
* targeted pytest failure output around `plan_week` resolver/context helpers
* run-store entries from Plan Hub / week planning flows

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [ ] `doc/overview/feature_backlog.md` — add the refactor item and keep status current
* [ ] `doc/specs/features/FEAT_plan_week_testability_and_resolution_refactor.md` — keep scope, ADR decision, and implementation audit current
* [ ] `CHANGELOG.md` — record the refactor when implementation lands

---

## 11a) Post-Implementation Audit

Complete this section before closing the feature:

* [ ] Spec implemented fully
* [ ] Acceptance criteria verified
* [ ] Verification commands/tests recorded
* [ ] Residual gaps/deferred items recorded
* [ ] Recommended next step recorded

**Implementation report**

* Implemented scope: pending
* Verification performed: pending
* Remaining gaps/risks: pending
* Recommended next step: implement PR1 test-helper extraction before further `plan_week` structural work

---

## 12) Link Map (no duplication; links only)

* `doc/overview/feature_backlog.md`
* `doc/specs/features/FEAT_plan_hub_phase_step_isolation.md`
* `doc/specs/features/FEAT_resolved_activity_context.md`
* `doc/specs/features/FEAT_resolved_kpi_context_injection.md`
* `doc/specs/features/FEAT_shift_left_planning_evidence_alignment.md`
* `doc/adr/ADR-001-ui-delegates-orchestrators.md`
* `doc/adr/ADR-056-upstream-first-planning-pipeline.md`
* `src/rps/orchestrator/plan_week.py`
* `src/rps/planning/deterministic_context.py`
* `tests/test_plan_pages.py`
* `tests/test_plan_hub_worker.py`