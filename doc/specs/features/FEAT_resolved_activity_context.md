# FEAT_resolved_activity_context
Version: 1.0
Status: Updated
Last-Updated: 2026-04-24
Owner: Planner Orchestration

## Context / Problem
`phase_architect` and `week_planner` still rely on explicit `ACTIVITIES_ACTUAL` and `ACTIVITIES_TREND` reads for historical context, even though the planner-relevant content is a relatively small subset of the trend and actual artefacts. This creates avoidable search/reconstruction work and pushes raw data interpretation into the agents.

## Goals & Non-Goals
Goals
- Inject a compact `Resolved Activity Context` block for planner agents.
- Preserve exact version traceability to the historical activity artefacts used.
- Include high-signal durability, load, long-ride, and structure facts without dumping raw artefacts.

Non-Goals
- Replacing exact-range phase predecessor reads.
- Injecting full `ACTIVITIES_ACTUAL` or `ACTIVITIES_TREND` JSON artefacts.
- Changing planner schemas or governance contracts.

## Proposed Behavior
The orchestrator resolves the latest historical `ACTIVITIES_ACTUAL` and `ACTIVITIES_TREND` versions before the target week and injects a compact summary block including:
- reference versions
- weekly aggregate and durability signals from `ACTIVITIES_TREND`
- selected key sessions from `ACTIVITIES_ACTUAL`

## Implementation Analysis
- Add a builder to `src/rps/orchestrator/resolved_context.py`.
- Inject the new block into `phase_architect` and `week_planner` user input.
- Keep raw activity reads available as fallback/traceability, but make the resolved block authoritative for the injected fields.

## Impact Analysis
- Reduces redundant activity artefact interpretation inside planner agents.
- Keeps version traceability explicit.
- No schema migration required.

## Options & Recommendation
Option A: Keep raw activity reads only.
- Rejected because it keeps unnecessary search/reasoning pressure in the agent.

Option B: Inject a compact resolved activity summary.
- Recommended.

## Acceptance Criteria (DoD)
- `phase_architect` and `week_planner` user input contain `Resolved Activity Context` when historical activity artefacts exist.
- The block includes both version keys and at least one trend summary signal.
- Tests cover the injection path.

## Migration / Rollout
- No migration.
- Effective immediately after deploy.

## Risks & Failure Modes
- Risk: summary omits a needed field.
- Mitigation: keep raw artefact reads available for unresolved detail or traceability.

## Observability / Logging
- No new logging.
- Agent logs should show less pressure to search activity artefacts for already-resolved signals.

## Documentation Updates
- `CHANGELOG.md`
- this feature doc

## Link Map
- `src/rps/orchestrator/resolved_context.py`
- `src/rps/orchestrator/plan_week.py`
- `prompts/agents/phase_architect.md`
- `prompts/agents/week_planner.md`
- `specs/knowledge/_shared/sources/specs/load_estimation_spec.md`
- `specs/knowledge/_shared/sources/contracts/season__phase_contract.md`
- `specs/knowledge/_shared/sources/contracts/phase__week_contract.md`
