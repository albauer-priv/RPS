---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-27
Owner: Planning Runtime
---
# FEAT: Evidence Refresh GitHub Action

* **ID:** FEAT_evidence_refresh_github_action
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-27
* **Related:** `scripts/refresh_evidence_library.py`, `.github/workflows/evidence-refresh.yml`, `doc/specs/features/FEAT_repo_wide_evidence_library_and_refresh.md`

---

## 1) Context / Problem

**Current behavior**

* The evidence refresh pipeline is implemented and runnable in a Linux / Python 3.13 context.
* Local refresh attempts on macOS Intel can fail because the CrewAI dependency chain is not installable there.
* The Docker image only contains whatever evidence-library state is already committed in the repo at build time.

**Problem**

* There is no repo-native automation that refreshes the evidence library in a compatible runtime and commits the updated state back into `main`.
* This leaves the refresh step dependent on ad hoc manual execution in a separate Linux/Docker environment.

**Constraints**

* Run in GitHub-hosted Linux, not in local platform-dependent environments.
* Use Python 3.13 to match the Docker/runtime compatibility envelope.
* Do not require new runtime dependencies beyond `requirements.txt`.
* Only push when the refresh actually changes the canonical library outputs.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a GitHub Actions workflow that runs the evidence refresh in a compatible Linux/Python 3.13 environment.
* [x] Support both scheduled refresh and manual dispatch.
* [x] Commit and push refreshed evidence-library outputs back to `main` only when changes exist.
* [x] Document the required secrets/env surface for the workflow.

**Non-Goals**

* [x] No replacement of the existing GHCR image workflow.
* [x] No direct Docker build step inside the evidence refresh workflow.
* [x] No PR-based review flow in this first pass; the workflow writes directly back to `main`.

---

## 3) Proposed Behavior

**User/System behavior**

* A dedicated GitHub Actions workflow runs weekly and can also be triggered manually.
* The workflow installs Python 3.13, project requirements, and executes:
  * `PYTHONPATH=src python3 scripts/refresh_evidence_library.py --discover`
* If the refresh modifies the canonical evidence registry or generated outputs, the workflow commits and pushes those changes to `main`.
* The existing GHCR image workflow then rebuilds from the updated repo state on push.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: GitHub Actions, evidence refresh script, canonical evidence library outputs
* Contracts touched: none beyond operational automation

---

## 4) Implementation Analysis

**Components / Modules**

* `.github/workflows/evidence-refresh.yml`: scheduled/manual refresh runner
* `scripts/refresh_evidence_library.py`: refresh entrypoint used by the workflow
* `doc/runbooks/evidence_refresh.md`: operator-facing workflow/secrets/run instructions

**Data flow**

* Inputs: repo checkout, GitHub Actions secrets, primary-source discovery, LLM runtime env
* Processing: install deps -> run evidence refresh -> detect git diff -> commit/push if changed
* Outputs: updated YAML registry, study briefs, tables, manifest, git commit to `main`

**Schema / Artefacts**

* New artefacts: GitHub Actions workflow file, evidence refresh runbook
* Changed artefacts: canonical evidence library outputs when refresh produces changes
* Validator implications: workflow YAML must parse; refresh command must remain the single entrypoint

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if refresh fails, no commit/push occurs and the existing library state remains unchanged

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: refresh remains repo-scoped evidence maintenance, not planner authority

**Impacted areas**

* UI: none
* Pipeline/data: evidence refresh can now be run by CI in the supported environment
* Renderer: refreshed outputs may regenerate markdown surfaces
* Workspace/run-store: none in GitHub Actions context
* Validation/tooling: workflow YAML and operator runbook
* Deployment/config: GitHub Actions secrets/env for LLM runtime

**Required refactoring**

* none beyond adding workflow/runbook/docs

---

## 6) Options & Recommendation

### Option A — Dedicated scheduled/manual refresh workflow

**Summary**

* Run the refresh in a Linux/Python 3.13 GitHub Actions job and push updates back to `main`.

**Pros**

* Compatible environment
* Deterministic path
* Keeps Docker images aligned with committed evidence state

**Cons**

* Requires write-capable workflow permissions
* Pushes directly to `main`

**Risk**

* A bad refresh could commit undesired library changes without PR review

### Option B — Manual refresh only outside GitHub Actions

**Summary**

* Keep refresh execution entirely external.

**Pros**

* Less CI automation

**Cons**

* Operationally fragile
* Reintroduces environment drift and manual dependency on Linux/Docker access

### Recommendation

* Choose: Option A
* Rationale: the refresh already requires a compatible environment; GitHub-hosted Linux is the cleanest repo-native execution surface.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] A GitHub Actions workflow exists for manual and scheduled evidence refresh.
* [x] The workflow uses Python 3.13.
* [x] The workflow runs the canonical refresh script with discovery enabled.
* [x] The workflow commits and pushes only when the refresh changes files.
* [x] A runbook documents required secrets and the execution model.
* [x] Validation passes: workflow YAML parses, repo Python syntax check passes.

---

## 8) Migration / Rollout

**Migration strategy**

* Add the workflow and runbook without changing the refresh script contract.

**Rollout / gating**

* Workflow trigger: scheduled + `workflow_dispatch`
* Safe rollback: disable or delete the workflow file

---

## 9) Risks & Failure Modes

* Failure mode: PubMed throttling or provider errors during refresh
  * Detection: workflow failure logs
  * Safe behavior: no commit/push
  * Recovery: rerun manually or wait for next schedule

* Failure mode: no-op refresh creates empty commit attempt
  * Detection: git diff check
  * Safe behavior: skip commit/push
  * Recovery: none needed

* Failure mode: missing secrets break curation stage
  * Detection: workflow failure at runtime bootstrap
  * Safe behavior: no state change
  * Recovery: add/repair GitHub Actions secrets

---

## 10) Observability / Logging

**New/changed events**

* GitHub Actions run logs for evidence refresh

**Diagnostics**

* GitHub Actions workflow logs
* resulting git commit on `main`

---

## 11) Documentation Updates

* [x] `doc/README.md` — add the feature doc to specs index
* [x] `doc/runbooks/evidence_refresh.md` — document CI/manual refresh execution
* [x] `CHANGELOG.md` — note CI refresh automation

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* CrewAI flows: `doc/architecture/crewai_flows.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* Existing evidence refresh feature: `doc/specs/features/FEAT_repo_wide_evidence_library_and_refresh.md`
* Existing curation feature: `doc/specs/features/FEAT_evidence_curation_pipeline.md`
