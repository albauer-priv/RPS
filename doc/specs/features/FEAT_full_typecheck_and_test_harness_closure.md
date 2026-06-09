---
Version: 1.0
Status: Updated
Last-Updated: 2026-06-09
Owner: Repo Tooling
---
# FEAT: Full Typecheck and Test Harness Closure

* **ID:** FEAT_full_typecheck_and_test_harness_closure
* **Status:** Updated
* **Owner/Area:** Repo Tooling / Runtime / Tests
* **Last-Updated:** 2026-06-09
* **Related:** [FEAT_runtime_compat_boundary_reduction](/Users/alexander/RPS/doc/specs/features/FEAT_runtime_compat_boundary_reduction.md), [FEAT_runtime_flow_listener_adapter_hardening](/Users/alexander/RPS/doc/specs/features/FEAT_runtime_flow_listener_adapter_hardening.md), [ADR-046-crewai-state-memory-knowledge-guardrail-separation](/Users/alexander/RPS/doc/adr/ADR-046-crewai-state-memory-knowledge-guardrail-separation.md), [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)

---

## 1) Context / Problem

**Current behavior**

* The curated commit-gate typecheck is green.
* `./scripts/run_typecheck.sh --full` still fails across a mix of test-fixture typing debt and a smaller set of production helper/signature issues.

**Problem**

* The repo still carries a split typing standard:
  * active runtime slices are increasingly typed cleanly
  * several tests still rely on `dict[str, object]`, loose monkeypatch modules, and `object`-typed capture containers
  * some production helpers use over-broad `object` inputs or under-specified return types that now block full mypy closure

**Constraints**

* No repo-wide mypy rule relaxation.
* No broad addition of `type: ignore`.
* No schema or authority-model redesign unless a concrete type fix reveals a real contract defect.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make `./scripts/run_typecheck.sh --full` green.
* [x] Replace high-friction `dict[str, object]` / `object` test fixtures with small typed builders or typed aliases where needed.
* [x] Tighten production helper signatures only where required to remove real type ambiguity.

**Non-Goals**

* [ ] No new product feature work.
* [ ] No broad refactor of unrelated tests just for style consistency.
* [ ] No migration from mypy to another typing tool.

---

## 3) Proposed Behavior

**User/System behavior**

* Runtime and planning behavior stay unchanged.
* The full repo typecheck becomes a reliable engineering gate instead of a known failing background job.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * typed test fixtures/builders
  * planning/workout helper signatures
  * coach-chat structured-task wrappers
  * workspace/store helper signatures
* Contracts touched:
  * internal typing contracts only unless an existing persisted-shape inconsistency is exposed

---

## 4) Implementation Analysis

**Components / Modules**

* Test-first clusters:
  * `tests/test_season_selection_binding.py`
  * `tests/test_artifact_metadata.py`
  * `tests/test_workout_export.py`
  * `tests/test_generated_artifact_models.py`
  * `tests/test_crewai_runtime.py`
  * `tests/test_plan_hub_worker.py`
  * `tests/test_plan_pages.py`
* Production clusters:
  * `src/rps/planning/scenario_recommendation.py`
  * `src/rps/workouts/week_plan_consistency.py`
  * `src/rps/workouts/protocol_solver.py`
  * `src/rps/planning/contracts.py`
  * `src/rps/ui/performance_corridors.py`
  * `src/rps/workspace/local_store.py`
  * `src/rps/crewai_runtime/coach_chat.py`

**Data flow**

* Inputs: current full-repo mypy failures
* Processing: clustered fixes by fixture class and helper/signature class
* Outputs: full mypy closure without weakening rules

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none expected in the default path
* Validator implications: none expected unless a type fix reveals a real contract mismatch

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none introduced
* Fallback behavior: not needed after closure; curated and full typecheck are both green

**Conflicts with ADRs / Principles**

* Potential conflicts: none expected
* Resolution: aligns with explicit boundaries and fail-closed internal contracts

**Impacted areas**

* UI: helper typing only
* Pipeline/data: none expected
* Renderer: none expected
* Workspace/run-store: helper typing only
* Validation/tooling: full-repo typecheck closure
* Deployment/config: none

**Required refactoring**

* Introduce typed aliases/builders for nested artifact payload tests
* Replace dynamic mock-module `object` containers with typed module-like stubs where needed
* Tighten helper signatures from `list[object]` to covariant read shapes such as `Sequence[object]`
* Fix structured-task wrapper return types in `coach_chat.py`

---

## 6) Options & Recommendation

### Option A — Clustered Wave-3 closure by failure class

**Summary**

* Fix full-mypy debt in clusters: typed tests first, then small production signatures, then larger runtime wrappers.

**Pros**

* Keeps changes reviewable
* Reduces regression risk
* Matches the actual error distribution

**Cons**

* Requires several iterative validation passes

**Risk**

* Mid-wave fixes can surface secondary typing issues hidden by earlier noise

### Option B — Broad repo-wide suppression

**Summary**

* Silence the remaining errors with ignores or looser types.

**Pros**

* Faster short-term green check

**Cons**

* Contradicts the stated program goals
* Preserves type ambiguity at important test/runtime boundaries

### Recommendation

* Choose: Option A
* Rationale: the point of Wave 3 is to eliminate the debt, not hide it.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `./scripts/run_typecheck.sh --full` is green.
* [x] No new broad `type: ignore` debt is introduced.
* [x] Test builders no longer rely on `dict[str, object]` where nested indexed mutation is required.
* [x] Production helper/signature fixes are covered by targeted tests where behavior is non-trivial.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration
* Internal typing/test harness cleanup only

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the affected typing/test fixture clusters

---

## 9) Risks & Failure Modes

* Failure mode: typing cleanup accidentally changes behavior in helper code

  * Detection: targeted pytest clusters plus curated typecheck and syntax/lint gates
  * Safe behavior: tests fail before release
  * Recovery: revert the affected cluster and re-scope the fix

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* full mypy output is the primary diagnostic artifact
* targeted pytest clusters validate behavior preservation for touched code

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — mark Wave 3 progress/completion
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record full-typecheck closure work

---

## 13) Implementation Outcome

**Completed in this slice**

* Full-repo mypy closure is now green without rule relaxation.
* High-friction typing debt was removed from the active Wave-3 production/test clusters:
  * structured Season/Phase fixture modernization in runtime/page tests
  * typed helper cleanup in planning/workout/ui/store modules
  * coach-chat structured-task wrapper typing cleanup
* A real workspace/index defect was fixed while closing the tests:
  * `LocalArtifactStore._record_index_write(...)` now preserves string `iso_week` / `iso_week_range` metadata in `index.json`
  * exact-range queries for freshly written range-scoped artefacts now work correctly after `save_document(...)`

**Validation completed**

* `python3 -m py_compile $(git ls-files '*.py')`
* `./scripts/run_lint.sh`
* `./scripts/run_typecheck.sh`
* `./scripts/run_typecheck.sh --full`
* `PYTHONPATH=src pytest -q tests/test_season_selection_binding.py tests/test_artifact_metadata.py tests/test_workout_export.py tests/test_generated_artifact_models.py tests/test_crewai_runtime.py tests/test_plan_hub_worker.py tests/test_guarded_store.py tests/test_plan_pages.py`

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* ADRs:
  * [ADR-046-crewai-state-memory-knowledge-guardrail-separation](/Users/alexander/RPS/doc/adr/ADR-046-crewai-state-memory-knowledge-guardrail-separation.md)
  * [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)
