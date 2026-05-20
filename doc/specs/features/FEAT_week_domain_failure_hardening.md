Version: 1.0
Status: Updated
Last-Updated: 2026-05-20
Owner: Planning Runtime

# Feature: Week Domain Failure Hardening

## Context / Problem

`WEEK_PLAN` creation for target week `2026-21` still fails after review approval because semantically illegal workout domains survive until the final writer guardrails. Crew-level planning is already disabled for week crews, so the visible `create_reasoning_plan(...)` calls are not the root cause.

Observed runtime failure:

- internal week planning/review completes
- writer stage fails with forbidden phase intensity domains such as `RECOVERY` and `THRESHOLD`
- the same semantic illegality was not blocked earlier in `week_plan_finalize` or `week_review`

Current gaps:

1. internal week bundles do not expose enough canonical workout legality fields
2. review can approve a candidate that is already semantically illegal
3. writer legality still relies too much on text heuristics
4. the workout authoring specialist uses a generic revision prompt path

## Goals & Non-Goals

### Goals

- make workout domain legality explicit in the internal week bundle
- block illegal workout domains before artifact writing
- align writer legality with approved internal blueprints
- give workout authoring a dedicated prompt path

### Non-Goals

- do not change crew-level planning flags
- do not disable `week_plan_manager.reasoning.enabled` in this pass
- do not redesign the full week planning loop

## Proposed Behavior

- each internal workout blueprint exposes canonical `intensity_domain` and `workout_family`
- `week_plan_finalize` fails when blueprint domains/families violate active phase guardrails
- `week_review` never spends LLM review work on an already illegal candidate; it returns deterministic `replan_required`
- writer checks legality against the approved planning bundle first, then checks final text consistency, then export syntax

## Implementation Analysis

- extend `WeekWorkoutBlueprintModel` with canonical workout-family and legality fields
- add an internal week-bundle legality guardrail to the planning task policy
- add deterministic review preflight against the same legality helper
- pass approved planning bundle into writer guardrail runtime context
- create a dedicated prompt for `week_workout_authoring_specialist`

## Impact Analysis

- no schema migration for persisted week artifacts
- no ADR required; this is a runtime guardrail/prompt hardening change
- affects internal planning bundle semantics, review orchestration, and writer legality messages

## Options & Recommendation

### Option A
Keep legality only in the final writer guardrail.

- Rejected: too late, wastes retries, and lets review approve illegal candidates.

### Option B
Add explicit internal blueprint legality plus early guardrails and keep writer as backstop.

- Recommended: smallest change that closes the whole failure chain.

## Acceptance Criteria

- illegal `RECOVERY` / `THRESHOLD` workout blueprints fail before `week_plan` writer execution
- review returns deterministic `replan_required` for illegal candidate bundles
- writer legality prefers approved blueprint authority over free-text-only inference
- workout authoring specialist uses a dedicated prompt
- tests cover bundle legality, review preflight, writer mismatch, and config wiring

## Migration / Rollout

- no data migration
- normal commit/push rollout

## Risks & Failure Modes

- overly strict family matching could block legal bundles; keep the first pass focused on forbidden-domain and declared-family legality
- if blueprint fields are omitted by the planner, early guardrails must fail clearly rather than silently infer

## Observability / Logging

- keep existing guardrail telemetry
- deterministic review preflight should produce precise `blocking_issues` with offending `workout_id`s

## Documentation Updates

- update active workout authoring and review skills where needed
- update changelog

## Link Map

- [System Architecture](../../architecture/system_architecture.md)
- [How To Plan](../../overview/how_to_plan.md)
- [Feature Template](./FEAT_TEMPLATE.md)
