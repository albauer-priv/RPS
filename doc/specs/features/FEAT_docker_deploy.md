---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: Infra / Deploy
---
# FEAT: Docker Build & Deployment Workflow

* **ID:** FEAT_docker_deploy
* **Status:** Draft
* **Owner/Area:** Infra / Deploy
* **Last-Updated:** 2026-09-15
* **Related:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/ghcr-image.yml`, `FEAT_user_management`

---

## 1) Context / Problem

**Current behavior**

* `Dockerfile`, `docker-compose.yml`, and a GHCR build/push workflow (`ghcr-image.yml`) already exist.
* The image builds on every push to `main` and is pushed to `ghcr.io/albauer-priv/rps`.

**Problems**

1. `pyproject.toml` lists `altair>=5.0.1` (no direct import in source; arrives as a Streamlit transitive dep) but is missing `plotly>=5.22.0`, which IS directly imported in `data_metrics.py`. The `requirements.txt` used by the Dockerfile has `plotly` but not `altair` — the two files are out of sync.
2. `.dockerignore` does not exclude `.venv/`, `tests/`, `doc/`, `memory/` — these directories inflate the build context unnecessarily.
3. `docker-compose.yml` uses the deprecated `version: "3.9"` key.
4. `docker-compose.yml` has no provision for `RPS_USERS_FILE` (added by FEAT_user_management).
5. The CI build workflow has no BuildKit layer caching → pip install runs from scratch on every push even when `requirements.txt` is unchanged.
6. No local build/run helper script.

**Constraints**

* `requirements.txt` is the file used by the Dockerfile; `pyproject.toml` is used for editable installs. Both must stay in sync for runtime dependencies.
* No new heavy CI steps or dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Sync `pyproject.toml` with `requirements.txt`: add `plotly`, remove `altair` (transitive via Streamlit).
* [x] Update `.dockerignore` to exclude `.venv/`, `tests/`, `doc/`, `memory/`, `.pytest_cache/`, `.mypy_cache/`, `*.md` at repo root.
* [x] Update `docker-compose.yml`: remove deprecated `version:` key; add commented config-volume block for `RPS_USERS_FILE`.
* [x] Update CI workflow: add GitHub Actions BuildKit layer cache (`type=gha`).
* [x] Add `scripts/docker_build.sh`: local build + optional push helper.

**Non-Goals**

* [ ] Multi-stage Dockerfile build (separate build/runtime layers).
* [ ] Dependency lock file generation (pip-compile / poetry).
* [ ] Kubernetes / Helm deployment manifests.
* [ ] Automated production deploys (rolling restarts, health-check gates).

---

## 3) Proposed Changes

### `pyproject.toml`
- Remove `altair>=5.0.1` from runtime dependencies.
- Add `plotly>=5.22.0` to runtime dependencies (matches `requirements.txt`).

### `.dockerignore`
Add:
```
.venv/
tests/
doc/
memory/
*.md
node_modules/
```

### `docker-compose.yml`
- Remove `version: "3.9"`.
- Add commented config-volume block so operators can enable auth by creating `config/users.yaml` and uncommenting two lines.

### `.github/workflows/ghcr-image.yml`
Add to the `Build & Push` step:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

### `scripts/docker_build.sh`
```bash
#!/usr/bin/env bash
# Local Docker build helper. Usage:
#   ./scripts/docker_build.sh             # build only
#   ./scripts/docker_build.sh --push      # build and push to GHCR
set -euo pipefail
IMAGE="ghcr.io/albauer-priv/rps"
TAG="${TAG:-local}"
docker build -t "$IMAGE:$TAG" .
if [[ "${1:-}" == "--push" ]]; then
    docker push "$IMAGE:$TAG"
fi
```

---

## 4) Impact Analysis

**Compatibility**

* Fully backward-compatible. Running containers and compose deployments unchanged unless the operator uncomments the new config-volume block.

---

## 5) Acceptance Criteria (Definition of Done)

* [x] `plotly` present in `pyproject.toml` runtime deps; `altair` absent.
* [x] `.dockerignore` excludes `.venv/`, `tests/`, `doc/`, `memory/`.
* [x] `docker-compose.yml` has no `version:` key and includes commented config-volume block.
* [x] CI workflow `Build & Push` step has `cache-from`/`cache-to` with `type=gha`.
* [x] `scripts/docker_build.sh` is executable and runnable locally.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `./scripts/run_lint.sh`

---

## 6) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.

---

## 7) Link Map

* `pyproject.toml`
* `requirements.txt`
* `.dockerignore`
* `docker-compose.yml`
* `.github/workflows/ghcr-image.yml`
* `scripts/docker_build.sh`
