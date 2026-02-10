---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-10
Owner: UI
---
# FEAT: Remove Legacy CLI Entrypoint (UI-Only)

* **ID:** FEAT_remove_cli_entrypoint
* **Status:** Updated
* **Owner/Area:** UI / DX
* **Last-Updated:** 2026-02-10
* **Related:** N/A

---

## 1) Context / Problem

**Current behavior**

* `src/rps/main.py` provides a legacy CLI with commands like `plan-week`, `run-agent`,
  `run-task`, `parse-intervals`, and `preflight`.
* Documentation (README + runbooks) still references `python -m rps.main ...`.
* The product intent is UI-only Streamlit; CLI entrypoints are no longer desired.

**Problem**

* Legacy CLI code and docs add maintenance overhead and create conflicting workflows
  versus the UI-first experience.

**Constraints**

* No new dependencies.
* Keep internal maintenance scripts that are required for validation or schema bundling.
* Preserve UI functionality.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Remove the legacy CLI entrypoint (`src/rps/main.py`).
* [x] Identify and remove unused/deprecated CLI wrapper scripts (if safe).
* [x] Update documentation to remove `python -m rps.main ...` references.
* [x] Retain essential maintenance scripts (e.g., schema bundling, validation).

**Non-Goals**

* [ ] Removing core pipeline modules under `src/rps/**` that are used by the UI.
* [ ] Changing orchestration logic or agent behavior.

---

## 3) Proposed Behavior

**User/System behavior**

* The project is UI-only: Streamlit is the supported execution path.
* CLI usage documented in README/runbooks is removed or replaced with UI equivalents
  or direct module commands that remain supported.

**UI impact**

* UI affected: No (only docs and repo structure change).

**Non-UI behavior (if applicable)**

* Components involved:
  * `src/rps/main.py` (remove)
  * `scripts/` (evaluate and prune unused CLI wrappers)
  * Docs referencing `python -m rps.main ...` (update/remove)
* Contracts touched: none

---

## 4) Implementation Analysis

**Components / Modules**

* Remove `src/rps/main.py`.
* Review `scripts/`:
  * Keep: `bundle_schemas.py`, `check_schema_required.py`, `check_schema_refs.py`,
    `validate_outputs.py`, vectorstore helpers (`sync_vectorstores.py`, `smoke_vectorstores.py`,
    `list_vectorstores.py`, `prune_orphans.py`).
  * Evaluate removal of deprecated CLI wrappers: `scripts/data_pipeline/post_workout.py`,
    `scripts/data_pipeline/parse_season_brief_availability.py`, `scripts/data_pipeline/get_intervals_data.py`
    if no longer referenced by UI or required by tests.
* Update documentation to remove `python -m rps.main ...` references and point to UI
  or direct module invocations (e.g., `PYTHONPATH=src python3 src/rps/data_pipeline/intervals_data.py --help`).

**Data flow**

* No changes to data flow; only entrypoints and docs.

**Schema / Artefacts**

* None.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: No (removes legacy CLI).
* Breaking changes: CLI entrypoint and related docs removed.
* Fallback behavior: UI-only; scripts remain for maintenance tasks.

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified.

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: docs updated; scripts retained as needed
* Deployment/config: none

**Required refactoring**

* Documentation cleanup of CLI references.

---

## 6) Options & Recommendation

### Option A — Remove CLI entrypoint and prune scripts (recommended)

**Summary**

* Delete `src/rps/main.py`, remove deprecated CLI wrapper scripts, and clean docs.

**Pros**

* Aligns repo with UI-only product.
* Reduces maintenance overhead and confusion.

**Cons**

* Breaks any remaining CLI usage.

### Option B — Keep CLI but mark deprecated

**Summary**

* Leave `main.py` and scripts; only adjust docs.

**Pros**

* Minimal code changes.

**Cons**

* Inconsistent with UI-only goal; dead code persists.

### Recommendation

* Choose: Option A
* Rationale: Clean removal aligns with requested UI-only direction.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `src/rps/main.py` removed.
* [x] Deprecated CLI wrapper scripts removed if not required.
* [x] No documentation references to `python -m rps.main ...` (current docs updated).
* [ ] Validation passes: `python -m py_compile $(git ls-files '*.py')`.
* [ ] UI smoke run still works.

---

## 8) Migration / Rollout

**Migration strategy**

* Remove CLI entrypoint and update docs in the same change.

**Rollout / gating**

* None. Change is immediate.

---

## 9) Risks & Failure Modes

* Failure mode: Hidden dependency on CLI script in automation.
  * Detection: CI or developer workflows fail.
  * Safe behavior: Provide UI or direct module alternatives in docs.
  * Recovery: Restore specific scripts if needed.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* N/A.

---

## 11) Documentation Updates

* [x] `README.md` — remove `python -m rps.main ...` usage.
* [x] [doc/overview/how_to_plan.md](../../overview/how_to_plan.md) — replace CLI references with UI flow.
* [x] [doc/architecture/system_architecture.md](../../architecture/system_architecture.md) — remove CLI entrypoint references.
* [x] [doc/architecture/subsystems/data_pipeline.md](../../architecture/subsystems/data_pipeline.md) — update pipeline entrypoints.

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: [doc/ui/ui_spec.md](../../ui/ui_spec.md)
* UI contract (Streamlit): [doc/ui/streamlit_contract.md](../../ui/streamlit_contract.md)
* Architecture: [doc/architecture/system_architecture.md](../../architecture/system_architecture.md)
* Workspace: [doc/architecture/workspace.md](../../architecture/workspace.md)
* Schema versioning: [doc/architecture/schema_versioning.md](../../architecture/schema_versioning.md)
* Logging policy: [doc/specs/contracts/logging_policy.md](../contracts/logging_policy.md))
* Validation / runbooks: [doc/runbooks/validation.md](../../runbooks/validation.md)
* ADRs: [doc/adr/README.md](../../adr/README.md)
