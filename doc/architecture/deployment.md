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
- `RPS_LLM_BASE_URL` (optional)
- `RPS_LLM_ORG_ID` (optional)
- `RPS_LLM_PROJECT_ID` (optional)
- `RPS_LLM_TEMPERATURE` (optional)
- `RPS_LLM_REASONING_EFFORT` (optional)
- `RPS_LLM_REASONING_SUMMARY` (optional)
- `RPS_LLM_MAX_COMPLETION_TOKENS` (optional)
- `ATHLETE_ID`
- `API_KEY` (Intervals.icu)
- `BASE_URL` (Intervals.icu)

Optional:

- `RPS_LOG_LEVEL`
- `RPS_LOG_CONSOLE`
- `RPS_LOG_FILE`
- `RPS_LOG_UI`
- `RPS_LOG_ROTATE_MB`
- `RPS_LOG_RETENTION_DAYS`
- `RPS_RUN_RETENTION_DAYS`
- `RPS_INTERVALS_MAX_AGE_HOURS`
- `RPS_HISTORICAL_YEARS`
- `RPS_DISABLE_INTERVALS_REFRESH`
- `RPS_COACH_PRELOAD_ARTIFACTS`
- `RPS_COACH_PRELOAD_MAX_CHARS`
- `ATHLETE_WORKSPACE_ROOT`
- `SCHEMA_DIR`
- `PROMPTS_DIR`

Role-specific LLM policy is not configured via environment variables anymore. Use:

- `config/crewai/runtime_profiles.yaml`

---

## Environments

Recommended environments:

- **dev**: local workspace under `runtime/athletes/`
- **staging**: separate `ATHLETE_WORKSPACE_ROOT`
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

## End
