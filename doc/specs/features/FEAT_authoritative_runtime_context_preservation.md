Version: 1.0
Status: Draft
Last-Updated: 2026-05-19
Owner: Planning Runtime

# Context / Problem

Bounded Season specialists still fail because authoritative runtime facts are degraded between orchestrator injection and specialist execution:

- reasoning-enabled bounded specialists trigger framework observer/replan behavior with little planning value
- event-priority and peak-window tasks lacked direct workspace read tools
- compacted internal task input preserved `snapshot_ref` labels but not the actual authoritative snapshot/context content

This leads to specialists inventing file paths, reloading the wrong source type, or blocking despite code-owned runtime facts already existing.

# Goals & Non-Goals

## Goals

- Preserve authoritative runtime context blocks intact for internal planning specialists.
- Reduce framework-style agentic behavior on bounded specialists by disabling reasoning where it adds cost but not value.
- Give event-priority and peak-window specialists the minimal read tools they need.
- Align bounded Season, Phase, and Week planning tasks so their tool guidance matches the tools they actually receive.

## Non-Goals

- Re-architect the planning crews.
- Replace all prompt compaction.
- Change public artifact schemas or writer behavior.

# Proposed Behavior

- Internal planning task compaction must not truncate or flatten authoritative runtime blocks such as:
  - Athlete State Snapshot
  - Planning Context Snapshot
  - Resolved context blocks
  - Deterministic context blocks
- Bounded Season specialists should run without CrewAI reasoning observers.
- `season_event_priority_review` and `season_peak_window_review` should be able to read workspace inputs/versions directly when needed.
- Bounded Season, Phase, and Week planning tasks should carry short retrieval guidance that maps athlete-managed inputs to `workspace_get_input`, latest authoritative artefacts to `workspace_get_latest`, contract values to the dedicated contract tools, and week-sensitive history to `workspace_get_version`.
- Bounded planning tasks and season skills should carry a short retrieval policy that maps athlete-managed inputs to `workspace_get_input`, latest authoritative artefacts to `workspace_get_latest`, and week-sensitive historical artefacts to `workspace_get_version`.

# Implementation Analysis

- Add authoritative block extraction/preservation in `src/rps/agents/crewai_backend.py`
- Adjust `config/crewai/tasks.yaml` tool scopes for the season event/peak tasks
- Reduce reasoning in `config/crewai/runtime_profiles.yaml` for bounded Season specialists/reviewers
- Add targeted runtime tests

# Impact Analysis

- No schema changes
- No persistence changes
- Planning runtime behavior changes only

# Options & Recommendation

## Option A
Increase prompt size and stop compacting internal task input.

Cons:
- more tokens
- revives earlier prompt bloat

## Option B (Recommended)
Compact only the generic task wrapper and preserve authoritative runtime blocks verbatim.

Pros:
- retains necessary facts
- keeps token surface bounded

# Acceptance Criteria (DoD)

- Authoritative runtime blocks remain verbatim in internal specialist task descriptions.
- Event-priority and peak-window tasks expose direct workspace read tools.
- Bounded Season specialists no longer have reasoning enabled in runtime profiles.
- Runtime tests cover preserved authoritative blocks and updated tool scopes.

# Migration / Rollout

- No migration required

# Risks & Failure Modes

- If too many blocks are preserved, prompts may grow again.
- Mitigation: preserve only authoritative blocks and continue compacting generic wrapper text.

# Observability / Logging

- Existing task/model telemetry is sufficient to verify reduced observer activity and improved specialist progress.

# Documentation Updates

- `CHANGELOG.md`
- this feature doc

# Link Map

- [System Architecture](../../architecture/system_architecture.md)
- [Artefact Flow](../../overview/artefact_flow.md)
- [How To Plan](../../overview/how_to_plan.md)
