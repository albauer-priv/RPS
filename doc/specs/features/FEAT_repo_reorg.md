---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-10
Owner: Architecture
---
# FEAT: Repository Layout Consolidation

* **ID:** FEAT_repo_reorg
* **Status:** Approved
* **Owner/Area:** Architecture / DX
* **Last-Updated:** 2026-02-10
* **Related:** N/A

---

## 1) Context / Problem

**Current behavior**

* The repo has many top-level directories (`runtime/`, `specs/knowledge/`, `specs/kpi_profiles/`, `specs/schemas/`, `legacy/`, `evals/`, etc.).
* Runtime outputs (artifacts/logs/runs) live in multiple top-level paths.
* Spec/knowledge material is spread across multiple roots.
* `evals/` is empty (only `.gitkeep`) and unused.

**Problem**

* Top-level sprawl makes navigation, ownership, and tooling assumptions unclear.
* Runtime data is not clearly separated from source/knowledge.
* Path coupling across the codebase and docs makes reorg risky without a plan.

**Constraints**

* Must preserve UI-only Streamlit runtime (no CLI assumptions).
* Must avoid breaking imports, path references, and run-store/workspace IO.
* No new dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Reduce top-level clutter by consolidating runtime and specs/knowledge roots.
* [ ] Remove unused `evals/` directory.
* [ ] Provide a clear, documented repo layout with migration steps.
* [ ] Keep path changes safe via staged migration and compatibility shims.

**Non-Goals**

* [ ] Redesign artifact schemas or storage format.
* [ ] Change UI behavior or Streamlit page structure.

---

## 3) Proposed Behavior

**User/System behavior**

* Repo layout is organized into:
  * `runtime/` (runtime data: workspace, logs, runs)
  * `specs/` (knowledge + schemas + KPI profiles)
  * `src/`, `tests/`, `doc/`, `scripts/`, `static/` remain
* `evals/` is removed.

**UI impact**

* UI affected: No (paths resolved via config/SETTINGS)

**Non-UI behavior (if applicable)**

* Components involved: workspace index manager, run store, settings, data pipeline, docs.
* Contracts touched: workspace root resolution, run-store paths, knowledge search paths.

---

## 4) Implementation Analysis

**Components / Modules**

* `rps.ui.shared`, `rps.core.config`: update default root paths.
* `rps.workspace.*`: adjust workspace root location and migrations.
* `rps.ui.run_store`: update run store root.
* `rps.openai.vectorstore_state`: update specs/knowledge/specs roots.
* `scripts/*`: update path assumptions.
* Docs: update repo structure references.

**Data flow**

* Inputs: existing `runtime/` directory, specs/knowledge/specs roots.
* Processing: migrate to new roots and update path resolution.
* Outputs: new directory layout + compatibility shims.

**Schema / Artefacts**

* New artefacts: None
* Changed artefacts: None
* Validator implications: none, but validation tools must read from new roots.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Partially (with temporary shims)
* Breaking changes: direct path references to `runtime/`, `specs/knowledge/`, `specs/schemas/`, `specs/kpi_profiles/`.
* Fallback behavior: provide a migration step + optional read-from-old-root if present.

**Conflicts with ADRs / Principles**

* Potential conflicts: none known; requires ADR because it changes repo boundaries and runtime roots.
* Resolution: create ADR describing new layout and migration.

**Impacted areas**

* UI: path resolution for workspace/run store/knowledge roots.
* Pipeline/data: intervals pipeline output paths, validation script paths.
* Renderer: sidecar lookup paths (if any direct path use).
* Workspace/run-store: root path changes and migrations.
* Validation/tooling: scripts that assume top-level paths.
* Deployment/config: environment defaults and .env examples.

**Required refactoring**

* Centralize root resolution in config and remove hardcoded top-level paths.
* Update docs and runbooks to match new layout.

---

## 6) Options & Recommendation

### Option A — Big-bang move (all at once)

**Summary**

* Move directories to new roots in a single change and update all references.

**Pros**

* Clean cut; no temporary compatibility layer.

**Cons**

* High risk of broken paths; harder to roll back.

**Risk**

* High; many path assumptions could be missed.

### Option B — Staged migration with shims (recommended)

**Summary**

* Introduce new roots + compatibility read-paths, then remove old paths after a grace period.

**Pros**

* Lower risk; supports partial migration and rollback.

**Cons**

* Temporary complexity (dual paths).

### Option C — Documentation-only

**Summary**

* Keep layout, only document it.

**Pros**

* No risk.

**Cons**

* Does not reduce clutter or clarify runtime/specs separation.

### Recommendation

* Choose: **Option A**
* Rationale: hard cut-over keeps the layout clean and avoids dual-path complexity.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] `evals/` is removed.
* [ ] Runtime root is consolidated under `runtime/` (or approved name).
* [ ] Specs/knowledge root is consolidated under `specs/`.
* [ ] All code paths resolve via config/SETTINGS (no hardcoded top-level paths).
* [ ] Docs updated to reflect new layout.
* [ ] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`.
* [ ] No regressions in UI startup and basic page navigation.

---

## 8) Migration / Rollout

**Migration strategy**

* Create new roots (`runtime/`, `specs/`).
* Move contents and update path references.
* Remove old roots (no compatibility shim).

**Rollout / gating**

* Feature flag / config: `RPS_RUNTIME_ROOT`, `RPS_SPECS_ROOT` (defaults to new roots).
* Safe rollback: set env vars to old roots or revert commit.

---

## 9) Risks & Failure Modes

* Failure mode: missing path updates cause file-not-found.
  * Detection: UI errors, failing scripts, missing artifacts.
  * Safe behavior: fail fast with clear error.
  * Recovery: update config or restore old directory.

---

## 10) Observability / Logging

**New/changed events**

* `workspace_root_resolved`: log chosen runtime/spec roots and fallback usage.

**Diagnostics**

* `rps.log` for root resolution messages.
* UI error banners if paths missing.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [ ] `README.md` — repo layout overview.
* [ ] `doc/overview/artefact_flow.md` — update runtime/spec root references.
* [ ] `doc/architecture/workspace.md` — workspace root + run store paths.
* [ ] `doc/runbooks/validation.md` — updated paths for scripts/tools.

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: `doc/ui/ui_spec.md`
* UI contract (Streamlit): `doc/ui/streamlit_contract.md`
* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Schema versioning: `doc/architecture/schema_versioning.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* ADRs: `doc/adr/` (new ADR required)

---

## Open Questions (max 5) — optional

* Final names: `runtime/` and `specs/` or alternatives (e.g., `.runtime/`, `data/`).
* Grace period for fallback reads from old roots.

---

## Out of Scope / Deferred — optional

* Refactor of artifact schemas or names.
* Any new CLI entrypoints.
