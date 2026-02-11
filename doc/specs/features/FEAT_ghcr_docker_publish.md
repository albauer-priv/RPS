---
Version: 1.0
Status: Implemented
Last-Updated: 2026-02-11
Owner: DevOps
---
# FEAT: GHCR Docker Build on Main

* **ID:** FEAT_ghcr_docker_publish
* **Status:** Implemented
* **Owner/Area:** Deployment
* **Last-Updated:** 2026-02-11
* **Related:** N/A

---

## 1) Context / Problem

**Current behavior**

* The repo has no Dockerfile and no GitHub Actions workflow to publish a container image.

**Problem**

* There is no automated container build on `main`, so deployment requires manual steps and is easy to drift.

**Constraints**

* Use GitHub Container Registry (GHCR).
* Build should be triggered on `main` pushes.
* Streamlit must run on `0.0.0.0:8501` with a non-root `WORKDIR`.
* No new dependencies without approval.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Provide a Dockerfile that runs the Streamlit UI reliably.
* [ ] Add a GitHub Actions workflow that builds and pushes to GHCR on `main`.
* [ ] Ensure the image is tagged with `latest` and a short SHA tag.
* [ ] Keep the workflow disabled by default until the repo is made public.

**Non-Goals**

* [ ] No multi-arch builds in this first iteration.
* [ ] No runtime secrets management changes.

---

## 3) Proposed Behavior

**User/System behavior**

* On each push to `main`, GitHub Actions builds the Docker image and publishes it to GHCR.
* The workflow is present but disabled (manual dispatch only) until re-enabled.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: GitHub Actions, Dockerfile.
* Contracts touched: None.

---

## 4) Implementation Analysis

**Components / Modules**

* `Dockerfile`: Streamlit entrypoint with `--server.address=0.0.0.0` and `--server.port=8501`.
* `.dockerignore`: Exclude `runtime/`, `var/`, `logs/`, `.env`, and local artifacts.
* `.github/workflows/ghcr.yml`: Build+push workflow for GHCR.

**Data flow**

* Inputs: Repo source code on `main`.
* Processing: Build image with `docker/build-push-action`.
* Outputs: GHCR image tagged with `latest` and short SHA.

**Schema / Artefacts**

* New artefacts: None.
* Changed artefacts: None.
* Validator implications: None.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None.
* Fallback behavior: Workflow can stay disabled.

**Conflicts with ADRs / Principles**

* Potential conflicts: None known.
* Resolution: N/A.

**Impacted areas**

* UI: None.
* Pipeline/data: None.
* Renderer: None.
* Workspace/run-store: None.
* Validation/tooling: None.
* Deployment/config: Adds GHCR workflow and Dockerfile.

**Required refactoring**

* None.

---

## 6) Options & Recommendation

### Option A — GHCR on main push (disabled until re-enabled)

**Summary**

* Add Dockerfile + GHCR workflow with `workflow_dispatch` only until public release.

**Pros**

* Minimal change, easy to turn on.
* Uses official GitHub and Streamlit guidance.

**Cons**

* Not active until toggled.

**Risk**

* Low.

### Option B — Enable immediately on `main`

**Summary**

* Ship active workflow right away.

**Pros**

* Automatic builds immediately.

**Cons**

* Undesired before repo is public.

### Recommendation

* Choose: Option A.
* Rationale: Lets you audit the repo before enabling public publishing.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Dockerfile builds locally and runs Streamlit on port 8501.
* [ ] `.dockerignore` excludes `runtime/`, `var/`, `logs/`, and `.env`.
* [ ] GHCR workflow exists with `workflow_dispatch` only (disabled by default).
* [ ] Workflow uses GHCR login with `GITHUB_TOKEN` and pushes `latest` + short SHA tags.
* [ ] Documentation updated in README or deployment docs.

---

## 8) Migration / Rollout

**Migration strategy**

* None.

**Rollout / gating**

* Workflow uses `workflow_dispatch` only until manually enabled.
* Safe rollback: Remove the workflow file or disable it in GitHub UI.

---

## 9) Risks & Failure Modes

* Failure mode: Docker build fails on CI.
  * Detection: GitHub Actions status.
  * Safe behavior: No image published.
  * Recovery: Fix Dockerfile and re-run.

---

## 10) Observability / Logging

**New/changed events**

* GitHub Actions workflow logs.

**Diagnostics**

* GitHub Actions run logs.

---

## 11) Documentation Updates

* [ ] `README.md` — add GHCR deployment note.
* [ ] `doc/architecture/deployment.md` — add GHCR workflow summary.

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: `doc/ui/ui_spec.md`
* UI contract (Streamlit): `doc/ui/streamlit_contract.md`
* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Schema versioning: `doc/architecture/schema_versioning.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* ADRs: N/A
