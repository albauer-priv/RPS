---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning
---

# FEAT_deterministic_week_engine_configurable_families

## Context / Problem

Week planning currently depends on CrewAI planning, review, and writer stages even though the authoritative week inputs are already code-owned:

- `PHASE_GUARDRAILS`
- `PHASE_STRUCTURE`
- `AVAILABILITY`
- deterministic week/phase/load contracts
- deterministic workout rendering and syntax validation

This creates unnecessary runtime complexity and failure modes:

- late writer failures after review
- bounded replan loops for issues that are already deterministic
- drift between week bundle semantics and final workout text
- hardcoded workout family selection in code without configurable policy

## Goals & Non-Goals

### Goals

- Replace the runtime Week Crew path with a deterministic week engine.
- Keep workout syntax/rendering code-owned and validator-backed.
- Make workout families and family selection policies configurable.
- Use the same engine for main week planning, preview/replan, and bounded coach week recompute paths.

### Non-Goals

- Replacing Season or Phase planning.
- Making hard constraints configurable.
- Supporting arbitrary free-text workout family definitions.

## Proposed Behavior

The week engine becomes the single authority for Week planning:

- context loading from workspace
- week contract construction
- day-role allocation
- weekly load targeting and reconciliation
- workout-family selection from config
- deterministic workout rendering
- deterministic review/replan result generation
- persistence of `WEEK_PLAN`

Workout family behavior is split into:

- config-owned family registry and selection policy
- code-owned generator profiles and rendering rules

## Implementation Analysis

- Add a central planning module for deterministic week execution.
- Add a YAML-backed family registry and selection-policy loader.
- Extend workout blueprint models to preserve family selection metadata.
- Route `run_week_flow()` through the deterministic engine instead of the Week CrewAI chain.
- Keep existing workout editor text replacement path, but ensure bounded week replan/recompute uses the same deterministic engine.

## Impact Analysis

- `CREATE_WEEK_PLAN` runtime behavior changes from CrewAI Week crews to deterministic code execution.
- Preview and apply flows for scoped week replan now share the same generation logic as main week planning.
- Existing `WEEK_PLAN` schema remains unchanged.
- Existing Week CrewAI configs/prompts become non-authoritative runtime residue and may remain only for historical/reference purposes.

## Options & Recommendation

### Option A — Keep Week Crew and harden prompts

Reject. The deterministic inputs are already strong enough that the Crew adds failure surface without providing essential reasoning value.

### Option B — Deterministic engine with configurable workout families

Recommended. It keeps hard rules in code while allowing training-style/product tuning through configuration.

## Acceptance Criteria

- `CREATE_WEEK_PLAN` no longer requires Week planning/review/writer crews at runtime.
- Week preview/replan uses the same deterministic engine.
- Workout family selection is driven by YAML config and validated at load time.
- Generated workout text remains binding-subset valid.
- No persisted week workout contains inline loop shorthand like `- 3x ...`.

## Migration / Rollout

- Roll out for Week only.
- Preserve artifact schema compatibility.
- Keep legacy Week CrewAI config files in place initially, but remove them from the active runtime path.

## Risks & Failure Modes

- Overly narrow family config could make legal week construction impossible.
- Deterministic selection heuristics may initially be less expressive than legacy free-text planning.
- Mitigation: fail with structured deterministic blocking/replan output instead of silent fallback.

## Observability / Logging

- Log deterministic week-engine step transitions and blocking reasons.
- Preserve the top-level week flow/orchestrator logging contract.

## Documentation Updates

- Update `CHANGELOG.md`.
- Add this feature doc.

## Link Map

- [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
- [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
- [doc/architecture/agents.md](/Users/alexander/RPS/doc/architecture/agents.md)
- [doc/specs/features/FEAT_deterministic_workout_generator_first.md](/Users/alexander/RPS/doc/specs/features/FEAT_deterministic_workout_generator_first.md)
