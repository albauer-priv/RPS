---
Version: 1.0
Status: Draft
Last-Updated: 2026-04-13
Owner: Tooling
---
# FEAT: Internal Type Cleanup

* **ID:** FEAT_internal_type_cleanup
* **Status:** Draft
* **Owner/Area:** Tooling / Core Python Code
* **Last-Updated:** 2026-04-13
* **Related:** `pyproject.toml`, `scripts/run_typecheck.sh`

---

## 1) Context / Problem

**Current behavior**

* The repo now has a mandatory pre-commit typecheck gate on a curated scope.
* A wider `mypy` run across `src/` still reports many errors in first-party code.

**Problem**

* The current internal typing debt is large enough to hide real regressions.
* Third-party stub noise should not dominate the signal; the remaining focus should be first-party code quality.

**Constraints**

* Cleanup must not destabilize the Streamlit UI or planning pipeline.
* Refactors should remove dead or weakly-typed code when that is simpler than preserving it.
* The migration should be incremental but leave the repo in a measurably cleaner state after each wave.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Ignore third-party stub noise in the committed typecheck configuration.
* [ ] Reduce first-party `mypy` errors substantially, starting with core/runtime modules.
* [ ] Expand the green typecheck scope after each cleanup wave.

**Non-Goals**

* [ ] Achieve perfect typing for every UI helper in a single change.
* [ ] Introduce a new type checker or replace `mypy`.

---

## 3) Proposed Behavior

**User/System behavior**

* `mypy` focuses on first-party errors rather than missing stubs.
* Core modules used in planning/runtime are cleaned first and can be promoted into the mandatory gate.

**UI impact**

* UI affected: No direct behavior change expected

**Non-UI behavior**

* Components involved: core logging, OpenAI runtime wrappers, orchestrator/runtime helpers, selected UI modules
* Contracts touched: internal Python typing contracts only

---

## 4) Implementation Analysis

**Components / Modules**

* `pyproject.toml`: ignore third-party stub noise at config level.
* core/runtime modules with high-value low-risk fixes first.
* commit-gate scope widened only after modules are green.

**Data flow**

* Inputs: current `mypy` findings
* Processing: fix first-party type mismatches, invalid unions, missing annotations, weak dict typing
* Outputs: lower internal error count and wider green scope

**Schema / Artefacts**

* none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none intended
* Fallback behavior: if a cleanup wave proves risky, keep the module out of the mandatory gate until fixed

**Conflicts with ADRs / Principles**

* none identified

**Impacted areas**

* UI: possible internal refactors only
* Pipeline/data: type cleanup in data pipeline helpers
* Renderer: type cleanup only
* Workspace/run-store: type cleanup only
* Validation/tooling: wider useful `mypy` coverage
* Deployment/config: `mypy` configuration update

**Required refactoring**

* remove or tighten weak `Any`/`object` paths
* clean invalid datetime/type annotations
* replace ad-hoc mixed dicts with typed dictionaries or narrower locals where needed

---

## 6) Options & Recommendation

### Option A — Full-repo cleanup in one wave

**Pros**

* Single convergence step

**Cons**

* Too risky and too broad for one change

### Option B — Incremental cleanup waves

**Pros**

* Safer, measurable, easier to review

**Cons**

* Temporary mixed state until later waves finish

### Recommendation

* Choose: Option B
* Rationale: typing debt is real, but the planning/runtime path should be cleaned first without destabilizing the repo.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] third-party stub noise is ignored in repo config
* [ ] first cleanup wave reduces internal `mypy` error count materially
* [ ] widened green scope is added to `scripts/run_typecheck.sh`
* [ ] syntax and targeted tests still pass

---

## 8) Migration / Rollout

**Migration strategy**

* Widen typecheck scope module group by module group.

**Rollout / gating**

* Commit gate only expands when the added modules are green.

---

## 9) Risks & Failure Modes

* Failure mode: typing refactor changes runtime behavior
  * Detection: tests/smoke checks fail
  * Safe behavior: keep changes local and revert the affected slice
  * Recovery: rework with narrower annotations

---

## 10) Observability / Logging

**Diagnostics**

* `PYTHONPATH=src python3 -m mypy src --disable-error-code import-untyped`
* `./scripts/run_typecheck.sh`

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_internal_type_cleanup.md`
* [ ] `CHANGELOG.md`

---

## 12) Link Map

* `AGENTS.md`
* `pyproject.toml`
* `scripts/run_typecheck.sh`
