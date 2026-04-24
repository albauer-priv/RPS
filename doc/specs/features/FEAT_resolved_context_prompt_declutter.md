# FEAT_resolved_context_prompt_declutter
Version: 1.0
Status: Updated
Last-Updated: 2026-04-24
Owner: Planner Prompts

## Context / Problem
Planner prompts still contained redundant fetch-before-stop and load-order language that encouraged duplicate artefact reads even after the orchestrator had already injected authoritative `Resolved ... Context` blocks.

## Goals & Non-Goals
Goals
- Reduce duplicate deterministic artefact reads in planner prompts.
- Preserve strict reads for exact-range predecessors and week-sensitive versioned artefacts.
- Keep STOP behavior strict only for unresolved required facts.

Non-Goals
- Changing orchestrator tool availability.
- Relaxing exact-range predecessor requirements.
- Changing schema contracts.

## Proposed Behavior
Planner prompts explicitly distinguish between:
- resolved deterministic facts already injected by the orchestrator
- artefact reads still required for unresolved details, exact traceability, or exact-range dependencies

## Implementation Analysis
- Update `season_planner`, `phase_architect`, `week_planner`, and `season_scenario` prompts.
- Add a shared `resolved_context_fetch_policy` rule.
- Narrow fetch-before-stop wording so it applies only to unresolved facts.

## Impact Analysis
- Reduces prompt pressure toward unnecessary tool calls.
- Keeps strict exact-range and week-sensitive reads intact.
- No schema or artefact-format impact.

## Options & Recommendation
Option A: Leave prompts as-is and rely only on orchestration.
- Rejected because prompts still push duplicate reads.

Option B: Align prompt language with resolved-context architecture.
- Recommended.

## Acceptance Criteria (DoD)
- All four planner prompts contain explicit fetch-policy language for resolved context.
- Load-order sections describe loading unresolved items rather than unconditional duplicate reads.
- Existing prompt tests still pass.

## Migration / Rollout
- No migration.
- Effective immediately after deploy.

## Risks & Failure Modes
- Risk: prompt becomes too permissive and skips a required traceability read.
- Mitigation: exact-range predecessor and week-sensitive explicit-version reads remain mandatory in prompt text.

## Observability / Logging
- No logging changes.
- Expected downstream signal: fewer redundant tool calls in agent logs.

## Documentation Updates
- `CHANGELOG.md`: note prompt declutter for resolved context.
- This feature doc.

## Link Map
- `doc/specs/features/FEAT_resolved_context_prompt_alignment.md`
- `doc/specs/features/FEAT_resolved_athlete_context.md`
- `src/rps/orchestrator/resolved_context.py`
- `prompts/agents/season_planner.md`
- `prompts/agents/phase_architect.md`
- `prompts/agents/week_planner.md`
- `prompts/agents/season_scenario.md`
