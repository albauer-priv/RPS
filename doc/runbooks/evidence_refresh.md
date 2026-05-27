---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-27
Owner: Runbook
---
# Evidence Refresh

## Purpose

This runbook explains how the canonical evidence library is refreshed in a
compatible Linux / Python 3.13 environment and how that refreshed state is
committed back into the repository.

---

## GitHub Actions Workflow

Canonical workflow:

- `.github/workflows/evidence-refresh.yml`

Trigger modes:

- scheduled weekly refresh
- manual `workflow_dispatch`

The workflow:

1. checks out the repo
2. sets up Python 3.13
3. installs `requirements.txt`
4. runs:

```bash
python3 scripts/refresh_evidence_library.py --discover
```

5. commits and pushes updated evidence-library files to `main` only if files changed

The existing GHCR image workflow then rebuilds from the refreshed repo state on
push to `main`.

---

## Required GitHub Secrets

The refresh uses the same LLM runtime surface as the application.

Required:

- `RPS_LLM_API_KEY`

Optional, depending on provider/setup:

- `RPS_LLM_BASE_URL`
- `RPS_LLM_ORG_ID`
- `RPS_LLM_PROJECT_ID`
- `RPS_LLM_MODEL`
- `RPS_LLM_TEMPERATURE`
- `RPS_LLM_REASONING_EFFORT`
- `RPS_LLM_REASONING_SUMMARY`
- `RPS_LLM_MAX_COMPLETION_TOKENS`

---

## What Gets Updated

The workflow may change:

- `skills/shared/durability-methodology/references/library/core_studies.yaml`
- `skills/shared/durability-methodology/references/library/applied_sources.yaml`
- generated study briefs under `.../library/studies/`
- generated evidence tables / manifest
- `discovery_state.json`

Only committed repo-scoped evidence-library outputs are refreshed. No
athlete-scoped workspace state is persisted by the workflow.

---

## Failure Modes

Common failures:

- PubMed throttling / HTTP 429
- provider / API auth failure
- model/runtime failure during evidence curation

Current mitigation:

- the workflow retries the refresh command up to 3 times
- no git commit is created if the refresh fails

---

## Manual Equivalent

In a compatible Linux / Python 3.13 environment, the equivalent manual command
is:

```bash
PYTHONPATH=src python3 scripts/refresh_evidence_library.py --discover
```
