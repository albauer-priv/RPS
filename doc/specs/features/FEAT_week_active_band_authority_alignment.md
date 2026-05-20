Version: 1.0
Status: Updated
Last-Updated: 2026-05-20
Owner: Planning Runtime

# Feature: Week Active Band Authority Alignment

## Context / Problem

The week runtime currently injects both:

- `active_weekly_kj_band`: the binding week-level corridor for the target week
- `active_s5_band`: a broader deterministic S5/capacity band

The runtime validators already prefer `active_weekly_kj_band`, but several week skills, task descriptions, and rendered contract texts still say "active Phase/S5 band" or "active S5 band". In practice this lets review/planning agents lock onto the broader `active_s5_band` and request replans against the wrong corridor.

Observed failure:

- target week `2026-21`
- binding week corridor from phase guardrails: `7329-8372 kJ`
- broader deterministic S5 band: `10175-11275 kJ`
- week review requested replan against `10175-11275 kJ` after an otherwise valid week candidate

## Goals & Non-Goals

### Goals

- Make the binding authority explicit across week planning/review/writer skills.
- Ensure rendered deterministic week context states that `active_weekly_kj_band` outranks `active_s5_band` when present.
- Align week task descriptions and prompts with the same precedence.

### Non-Goals

- No change to deterministic load-band calculation.
- No change to guarded-store or schema contracts.
- No change to whether agent-level reasoning is enabled.

## Proposed Behavior

- For week tasks, `active_weekly_kj_band` is the binding corridor.
- `phase_weekly_kj_band` is an equivalent week-scoped band when present.
- `active_s5_band` is fallback/background capacity context only when no week-specific band is available.
- Week review/replan instructions must be framed against the binding active weekly band, not the broader S5 band.

## Implementation Analysis

- Update rendered deterministic week calendar context in `src/rps/planning/deterministic_context.py`.
- Update week skills and references that currently say "Phase/S5 band".
- Update week task descriptions that still mention "active S5-band" for week review.
- Add a regression test that locks the rendered context wording and precedence cues.

## Impact Analysis

- No schema or persistence change.
- No ADR required: this is contract-authority clarification inside an existing subsystem.
- This reduces false replans in the week planning loop.

## Options & Recommendation

### Option A
Keep current wording and rely on validators alone.

- Rejected: the agent-facing contract remains ambiguous and keeps causing replans against the wrong band.

### Option B
Clarify week-band precedence in rendered contracts, skills, and task descriptions.

- Recommended: smallest fix with direct impact on agent behavior.

## Acceptance Criteria

- Week planning/review skills describe `active_weekly_kj_band` as binding.
- Rendered deterministic week context explicitly states that `active_weekly_kj_band` outranks `active_s5_band`.
- Week task descriptions no longer instruct review against an "active S5-band" when week-specific band exists.
- Regression tests pass.

## Migration / Rollout

- No migration required.
- Normal runtime rollout via commit/push is sufficient.

## Risks & Failure Modes

- If phrasing is changed incompletely, some specialists may still anchor on S5 wording.
- If future week contexts intentionally omit `active_weekly_kj_band`, fallback to `active_s5_band` must remain documented.

## Observability / Logging

- No new log events required.
- Existing review/replan logs should become consistent with the binding week corridor.

## Documentation Updates

- Update active week skills/references.
- Update task descriptions.
- Update changelog.

## Link Map

- [System Architecture](../../architecture/system_architecture.md)
- [How To Plan](../../overview/how_to_plan.md)
- [Feature Template](./FEAT_TEMPLATE.md)
