Version: 1.0
Status: Draft
Last-Updated: 2026-05-19
Owner: Core Runtime

# Context / Problem

`src/rps/core/config.py` currently reconstructs a large environment-driven override system for models, temperatures, reasoning settings, max tokens, and crew planning. This overlaps with:

- `config/crewai/runtime_profiles.yaml`
- `src/rps/crewai_runtime/provider.py`

The result is unnecessary duplication and contradictory override surfaces. The Streamlit app-level settings object should be small and predictable.

# Goals & Non-Goals

## Goals

- Reduce `config.py` to a minimal app-level configuration surface.
- Keep existing app/runtime call sites working without broad refactors.
- Make `runtime_profiles.yaml` and `provider.py` the place for fine-grained CrewAI provider policy.

## Non-Goals

- No full removal of environment overrides from `provider.py`.
- No schema or artifact changes.
- No broad UI/runtime rewiring in this step.

# Proposed Behavior

`load_app_settings()` resolves only:

- `RPS_LLM_MODEL`
- `RPS_LLM_TEMPERATURE`
- `RPS_LLM_REASONING_EFFORT`
- `RPS_LLM_REASONING_SUMMARY`
- `RPS_LLM_MAX_COMPLETION_TOKENS`
- `ATHLETE_WORKSPACE_ROOT`
- `SCHEMA_DIR`
- `PROMPTS_DIR`

Agent-/crew-scoped env overrides are no longer parsed by `config.py`.

Compatibility methods remain:

- `model_for_agent(...)`
- `temperature_for_agent(...)`
- `reasoning_effort_for_agent(...)`
- `reasoning_summary_for_agent(...)`
- `max_completion_tokens_for_agent(...)`
- `planning_enabled_for_crew(...)`
- `planning_model_for_crew(...)`

but they return only the global app defaults or the supplied fallback/default values.

# Implementation Analysis

- Simplify `AppSettings` fields to global defaults plus path settings.
- Remove env-map parsing loops from `load_app_settings()`.
- Keep `load_settings()` for API connection values.
- Update tests to assert that crew-planning env overrides remain in `provider.py` but not in app settings.

# Impact Analysis

- Reduces hidden coupling between Streamlit config and CrewAI provider config.
- Preserves existing callers via compatibility methods.
- Makes `config.py` easier to reason about and less contradictory.

# Options & Recommendation

## Option A

Keep app-level per-agent/per-crew override maps.

Tradeoff: no migration, but duplicated policy remains.

## Option B

Keep only global app defaults in `config.py`; leave scoped policy to `provider.py` and runtime profiles.

Tradeoff: some envs stop affecting `SETTINGS`, but behavior becomes clear and maintainable.

## Recommendation

Use Option B.

# Acceptance Criteria

- `config.py` no longer parses `RPS_LLM_MODEL_*`, `RPS_LLM_TEMPERATURE_*`, `RPS_LLM_REASONING_*_*`, `RPS_LLM_MAX_COMPLETION_TOKENS_*`, `RPS_CREW_PLANNING_*`, or `RPS_CREW_PLANNING_LLM_*`.
- `AppSettings` contains only global defaults and path settings.
- Existing callers compile unchanged.
- Tests verify that provider-level env overrides still work while `AppSettings` stays minimal.

# Migration / Rollout

- No migration required.
- Existing operator guidance should prefer runtime profiles and provider config for scoped overrides.

# Risks & Failure Modes

- A caller may have relied on app-level per-agent env overrides.
- If so, behavior changes from “scoped override in UI settings” to “global app default only”.

Mitigation:

- Keep provider-level scoped env overrides untouched.
- Keep compatibility methods so callers do not break at import/runtime level.

# Observability / Logging

- No new logging required.

# Documentation Updates

- Update `CHANGELOG.md`.

# Link Map

- [config.py](/Users/alexander/RPS/src/rps/core/config.py)
- [provider.py](/Users/alexander/RPS/src/rps/crewai_runtime/provider.py)
- [runtime_profiles.yaml](/Users/alexander/RPS/config/crewai/runtime_profiles.yaml)
