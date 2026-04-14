---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-14
Owner: Tooling
---
# FEAT: Mandatory Ruff Gate

* **ID:** FEAT_mandatory_ruff_gate
* **Status:** Implemented
* **Owner/Area:** Tooling / Validation
* **Last-Updated:** 2026-04-14
* **Related:** `pyproject.toml`, `.githooks/pre-commit`, `scripts/run_lint.sh`, `scripts/run_typecheck.sh`

---

## 1) Context / Problem

**Current behavior**

* The repository has a mandatory local commit gate for syntax and curated `mypy` checks.
* There is no mandatory linter in the repo-managed hook.

**Problem**

* Basic static hygiene issues can still be committed even when typing passes.
* Import sorting, unused code, and straightforward modernization opportunities are not enforced consistently.

**Constraints**

* The hook must remain fast enough for normal local commits.
* The initial rule set must avoid noisy stylistic churn.
* The repo already uses a repo-managed `.githooks/pre-commit` workflow and should extend it rather than add a second hook system.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add repo-local `ruff` configuration.
* [x] Add a reusable lint entrypoint script.
* [x] Make `ruff` mandatory in the existing repo-managed pre-commit hook.
* [x] Start with a conservative rule set focused on correctness, imports, a very small set of safe modernization rules, and low-risk bug-prevention checks.

**Non-Goals**

* [x] Introduce repo-wide auto-formatting as part of the hook.
* [x] Enable a broad style-only rule set that creates high churn.
* [x] Replace `mypy`, tests, or smoke checks.

---

## 3) Proposed Behavior

**User/System behavior**

* Local commits are blocked unless staged Python files pass:
  * `py_compile`
  * `ruff check`
  * the existing curated `mypy` gate
* Developers can run `./scripts/run_lint.sh` manually for the default repo lint scope.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: Git hooks, validation tooling, Python static analysis
* Contracts touched: local developer workflow before commit

---

## 4) Implementation Analysis

**Components / Modules**

* `pyproject.toml`: declare `ruff` dev dependency and lint configuration.
* `scripts/run_lint.sh`: reusable lint entrypoint for default scope or explicit file arguments.
* `.githooks/pre-commit`: extend mandatory local commit gate with `ruff`.
* `AGENTS.md`: update quick commands and done-check guidance.

**Data flow**

* Inputs: staged Python files or default lint targets
* Processing: syntax check -> `ruff check` -> curated `mypy`
* Outputs: local commit pass/fail exit code

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: adds a new mandatory lint validator step before commit

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: local commits now fail on lint violations in the enforced rule set
* Fallback behavior: developers can still bypass with `--no-verify`, but the intended workflow is blocked until issues are fixed

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with the repo rule to verify code quality before completion

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: adds `ruff` and a mandatory lint gate
* Deployment/config: local developer environment must install `ruff`

**Required refactoring**

* Introduce a shared lint entrypoint instead of ad-hoc local commands.
* Clean a small initial set of lint findings so the hook is usable immediately.

---

## 6) Options & Recommendation

### Option A — Full aggressive lint rules immediately

**Summary**

* Enable broad correctness + style + complexity rules in one pass.

**Pros**

* Highest theoretical coverage

**Cons**

* Large churn
* High risk of noisy hook failures on legacy code

### Option B — Conservative mandatory `ruff` gate

**Summary**

* Start with low-noise rules for correctness, imports, a few low-risk modernization checks, and only the safest bug-prevention checks.

**Pros**

* Practical immediately
* Good signal-to-noise ratio
* Easy to expand later

**Cons**

* Not all lint categories are enforced yet
* Some modernization categories remain intentionally deferred

### Recommendation

* Choose: Option B
* Rationale: it improves quality now without turning the hook into a broad style or modernization fight.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `ruff` config exists in repo
* [x] `ruff` is declared in repo dev dependencies
* [x] a repo-managed lint entrypoint exists
* [x] the repo-managed pre-commit hook runs `ruff`
* [x] initial selected `ruff` scope passes
* [x] Validation passes: `./scripts/run_lint.sh`
* [x] Validation passes: `./scripts/run_typecheck.sh`
* [x] No regressions in: existing local commit workflow

---

## 8) Migration / Rollout

**Migration strategy**

* Start with conservative rules and expand later when the repo is ready.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: remove the `ruff` hook call or revert `pyproject.toml` lint config

---

## 9) Risks & Failure Modes

* Failure mode: `ruff` not installed locally
  * Detection: hook fails with module-not-found / command-not-found
  * Safe behavior: commit is blocked with a clear instruction
  * Recovery: install dev dependencies including `ruff`

* Failure mode: selected rules create unexpected churn
  * Detection: repeated hook failures on unrelated style-only issues
  * Safe behavior: no invalid commit enters mainline
  * Recovery: narrow the rule set or add targeted ignores

---

## 10) Observability / Logging

**New/changed events**

* none; validation remains CLI/hook-driven

**Diagnostics**

* run `./scripts/run_lint.sh`
* inspect `.githooks/pre-commit`
* inspect `pyproject.toml` ruff config

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_mandatory_ruff_gate.md` — feature spec
* [x] `AGENTS.md` — quick commands + mandatory checks
* [x] `CHANGELOG.md` — note the mandatory lint gate

---

## 12) Link Map (no duplication; links only)

* `AGENTS.md`
* `doc/specs/features/FEAT_mandatory_typecheck_gate.md`
* `doc/specs/features/FEAT_internal_type_cleanup.md`
* `pyproject.toml`
* `.githooks/pre-commit`
* `scripts/run_lint.sh`
* `scripts/run_typecheck.sh`
