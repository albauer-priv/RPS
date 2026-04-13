---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-13
Owner: Tooling
---
# FEAT: Mandatory Typecheck Gate

* **ID:** FEAT_mandatory_typecheck_gate
* **Status:** Implemented
* **Owner/Area:** Tooling / Validation
* **Last-Updated:** 2026-04-13
* **Related:** `pyproject.toml`, `.githooks/pre-commit`, `scripts/run_typecheck.sh`

---

## 1) Context / Problem

**Current behavior**

* The repository enforces syntax checks and targeted tests by convention only.
* There is no committed typecheck configuration and no commit-time guard.

**Problem**

* Type regressions can be committed unnoticed.
* A full `mypy src` run is currently not a viable mandatory gate because the repo still contains many legacy errors and third-party stub gaps.

**Constraints**

* The gate must be fast enough for local commits.
* The initial implementation must avoid blocking all work on unrelated legacy modules.
* New dependencies are acceptable here because the requested feature is an explicit typecheck workflow.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a repo-local `mypy` configuration.
* [x] Add a mandatory pre-commit hook that runs syntax + type checks before commit.
* [x] Start with a narrow, stable scope that is green today and can be expanded later.

**Non-Goals**

* [x] Make the entire repository pass `mypy` immediately.
* [x] Replace targeted tests or smoke checks with type checks.

---

## 3) Proposed Behavior

**User/System behavior**

* Commits are blocked unless:
  * staged Python files pass `py_compile`
  * the configured `mypy` scope passes
* The hook is stored in-repo and activated via `core.hooksPath=.githooks`.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: Git hooks, validation tooling, Python static analysis
* Contracts touched: local developer workflow before commit

---

## 4) Implementation Analysis

**Components / Modules**

* `pyproject.toml`: declare `mypy` dev dependency and config.
* `scripts/run_typecheck.sh`: single repo command for commit gate and manual use.
* `.githooks/pre-commit`: enforce syntax + typecheck before local commit.

**Data flow**

* Inputs: staged Python files, configured typecheck targets
* Processing: collect staged Python files -> syntax check -> `mypy` on curated scope
* Outputs: exit code for local commit gate

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: adds a new mandatory validator step

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: local commits now fail when syntax/typecheck fail
* Fallback behavior: developers can still run `git commit --no-verify` manually, but the intended workflow is blocked until issues are fixed

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with the repository rule to verify changes before completion

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: adds `mypy` and a pre-commit gate
* Deployment/config: local developer environment must have `mypy`

**Required refactoring**

* Introduce a shared typecheck entrypoint instead of ad-hoc local commands.

---

## 6) Options & Recommendation

### Option A — Full repo `mypy` gate now

**Summary**

* Run `mypy src` before every commit.

**Pros**

* Strongest long-term guarantee

**Cons**

* Not viable with the current legacy error count
* Would block normal development immediately

### Option B — Curated green scope gate

**Summary**

* Gate commits on a stable, explicitly configured subset and expand scope over time.

**Pros**

* Practical immediately
* Still prevents regressions in critical modules

**Cons**

* Does not cover the entire repo yet

### Recommendation

* Choose: Option B
* Rationale: it creates an enforceable quality bar now without pretending the repo is already fully typed.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `mypy` configuration exists in repo
* [x] a repo-managed pre-commit hook runs syntax + typecheck
* [x] the mandatory gate passes on the selected initial scope
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: manual run of the new typecheck entrypoint
* [x] No regressions in: current commit workflow

---

## 8) Migration / Rollout

**Migration strategy**

* Start with a curated scope and expand later as legacy files are fixed.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: remove `.githooks/pre-commit` or reset `core.hooksPath`

---

## 9) Risks & Failure Modes

* Failure mode: `mypy` not installed locally
  * Detection: hook fails with command-not-found or module-not-found
  * Safe behavior: commit is blocked with a clear message
  * Recovery: install dependencies from `pyproject.toml`

* Failure mode: scope is too broad and blocks normal work on unrelated legacy files
  * Detection: repeated hook failures in unchanged legacy modules
  * Safe behavior: no invalid commit enters mainline
  * Recovery: narrow scope or fix legacy types before widening again

---

## 10) Observability / Logging

**New/changed events**

* none; validation is CLI/hook-driven

**Diagnostics**

* run `scripts/run_typecheck.sh`
* inspect `.githooks/pre-commit`
* inspect `pyproject.toml` mypy config

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_mandatory_typecheck_gate.md` — feature spec
* [ ] `CHANGELOG.md` — note the new mandatory typecheck gate

---

## 12) Link Map

* `AGENTS.md`
* `doc/overview/feature_backlog.md`
* `pyproject.toml`
* `scripts/run_typecheck.sh`
