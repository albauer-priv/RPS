---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Architecture
---
# Deployment

Version: 1.0  
Status: Draft  
Last-Updated: 2026-01-20

---

## Purpose

This document outlines environment setup and deployment conventions.

---

## Environment Variables

Core variables:

- `RPS_LLM_API_KEY`
- `RPS_LLM_MODEL` (optional)
- `ATHLETE_ID`
- `API_KEY` (Intervals.icu)
- `BASE_URL` (Intervals.icu)

Optional:

- `RPS_LLM_MODEL_SEASON_PLANNER`
- `RPS_LLM_MODEL_PHASE_ARCHITECT`
- `RPS_LLM_MODEL_WEEK_PLANNER`
- `RPS_LLM_MODEL_WORKOUT_BUILDER`
- `RPS_LLM_MODEL_PERFORMANCE_ANALYSIS`
- `ATHLETE_WORKSPACE_ROOT`
- `SCHEMA_DIR`
- `PROMPTS_DIR`
- `VECTORSTORE_STATE_PATH`

---

## Environments

Recommended environments:

- **dev**: local workspace under `var/athletes/`
- **staging**: separate `ATHLETE_WORKSPACE_ROOT` and vector stores
- **prod**: locked schemas, versioned prompts, audited syncs

---

## Secrets

- Never commit `.env`.
- Use a secret manager for production.
- Rotate API keys regularly.

---

## Vector Stores

Vector store IDs are environment-specific. Use `.cache/vectorstores_state.json`
for local development or provide overrides via env vars.

---

## End
