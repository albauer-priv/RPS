---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-11
Owner: Architecture
---
# Deployment

Version: 1.0  
Status: Draft  
Last-Updated: 2026-02-11

---

## Purpose

This document outlines environment setup and deployment conventions.

---

## Environment Variables

Core variables:

- `RPS_LLM_API_KEY`
- `RPS_LLM_MODEL` (optional)
- `RPS_LLM_EMBEDDING_MODEL`
- `ATHLETE_ID`
- `API_KEY` (Intervals.icu)
- `BASE_URL` (Intervals.icu)

Optional:

- `RPS_LLM_MODEL_SEASON_PLANNER`
- `RPS_LLM_MODEL_PHASE_ARCHITECT`
- `RPS_LLM_MODEL_WEEK_PLANNER`
- `RPS_LLM_MODEL_WORKOUT_BUILDER`
- `RPS_LLM_MODEL_PERFORMANCE_ANALYSIS`
- `RPS_LLM_VECTORSTORE_PATH`
- `RPS_LLM_EMBEDDING_BATCH_SIZE`
- `ATHLETE_WORKSPACE_ROOT`
- `SCHEMA_DIR`
- `PROMPTS_DIR`
- `VECTORSTORE_STATE_PATH`

---

## Environments

Recommended environments:

- **dev**: local workspace under `runtime/athletes/`
- **staging**: separate `ATHLETE_WORKSPACE_ROOT` and vector stores
- **prod**: locked schemas, versioned prompts, audited syncs

---

## Secrets

- Never commit `.env`.
- Use a secret manager for production.
- Rotate API keys regularly.

---

## GHCR Publishing (Optional)

The repo includes a GHCR workflow at `.github/workflows/ghcr-image.yml`.
It is **disabled by default** (manual dispatch only) so you can review the repo before publishing.

To enable automatic publishing on each `main` commit:

1. Edit `.github/workflows/ghcr-image.yml`.
2. Uncomment the `push` trigger for `main`.

Images are pushed to `ghcr.io/<owner>/<repo>` with tags:
- `latest`
- `sha-<short>`

---

## Vector Stores

Vector store IDs are environment-specific. Use `runtime/vectorstores_state.json`
for local development or provide overrides via env vars.

---

## End
