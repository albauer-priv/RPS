Version: 1.0
Status: Draft
Last-Updated: 2026-05-19
Owner: Core Runtime

# Context / Problem

The repository still exposes a large LLM-related environment surface:

- per-agent provider env overrides
- coach-specific provider env overrides
- crew-planning env overrides
- docs that still advertise historical env keys that are no longer needed

This duplicates runtime-profile authority and makes `.env` difficult to maintain.

# Goals & Non-Goals

## Goals

- Reduce the repo-supported LLM env surface to a minimal, global set.
- Make `runtime_profiles.yaml` the authority for role-specific model policy.
- Remove coach-specific provider env keys from active runtime behavior.
- Remove crew-planning env overrides from active runtime behavior.

## Non-Goals

- No removal of required provider connection envs.
- No removal of non-LLM operational envs such as log retention or historical baseline windows.
- No schema or artifact changes.

# Proposed Behavior

Supported LLM/provider envs after this change:

- `RPS_LLM_API_KEY`
- `RPS_LLM_BASE_URL`
- `RPS_LLM_ORG_ID`
- `RPS_LLM_PROJECT_ID`
- `RPS_LLM_MODEL`
- `RPS_LLM_TEMPERATURE`
- `RPS_LLM_REASONING_EFFORT`
- `RPS_LLM_REASONING_SUMMARY`
- `RPS_LLM_MAX_COMPLETION_TOKENS`

Role-specific model/planning behavior is controlled by:

- `config/crewai/runtime_profiles.yaml`
- deterministic runtime code inputs

No longer supported as active runtime config:

- `RPS_LLM_*_<AGENT>`
- `RPS_LLM_*_COACH`
- `RPS_CREW_PLANNING_*`
- `RPS_CREW_PLANNING_LLM_*`

# Implementation Analysis

- Simplify `src/rps/crewai_runtime/provider.py` to read only global provider envs.
- Keep the same public helper signatures for compatibility.
- Update Coach UI status hints to use `SETTINGS` instead of direct coach env keys.
- Update tests and deployment docs.

# Impact Analysis

- `.env` becomes much smaller and less contradictory.
- Runtime-profile YAML becomes the only role-policy surface.
- Existing operator setups that relied on scoped provider env overrides will need to move those choices into runtime profiles or code-owned runtime inputs.

# Options & Recommendation

## Option A

Keep scoped env overrides and document them better.

Tradeoff: no migration, but policy remains split across too many layers.

## Option B

Support only global provider envs and move all scoped behavior into runtime profiles.

Tradeoff: fewer override escape hatches, but the system becomes coherent.

## Recommendation

Use Option B.

# Acceptance Criteria

- Provider resolution no longer reads `RPS_LLM_*_<AGENT>`.
- Coach page no longer reads coach-specific provider env keys.
- Crew-planning provider helpers no longer read `RPS_CREW_PLANNING*` env vars.
- Deployment docs list the new minimal env set.
- Tests verify that ignored scoped env vars no longer affect runtime behavior.

# Migration / Rollout

- Remove deprecated scoped LLM env keys from `.env`.
- Move role-specific model choices to `runtime_profiles.yaml`.

# Risks & Failure Modes

- Operators may still expect old scoped envs to work.

Mitigation:

- Keep global env keys unchanged.
- Update docs and tests to make the new supported surface explicit.

# Observability / Logging

- No new logs required.

# Documentation Updates

- Update `doc/architecture/deployment.md`
- Update `CHANGELOG.md`

# Link Map

- [provider.py](/Users/alexander/RPS/src/rps/crewai_runtime/provider.py)
- [config.py](/Users/alexander/RPS/src/rps/core/config.py)
- [runtime_profiles.yaml](/Users/alexander/RPS/config/crewai/runtime_profiles.yaml)
