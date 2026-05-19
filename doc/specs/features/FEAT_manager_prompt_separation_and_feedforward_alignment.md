Version: 1.0
Status: Draft
Last-Updated: 2026-05-19
Owner: Planning Runtime

# Context / Problem

The planning-chain hardening work closed the main deterministic-contract rediscovery failures in season, phase, week, and review flows. Three architecture issues remain:

1. Feed-forward tasks still route through artifact writers even though dedicated feed-forward manager agents, prompts, and skills exist.
2. Review managers still reuse planning-manager prompts, which blurs the boundary between synthesis and review.
3. The conversation manager still allows free delegation, which risks losing bounded coach/apply/preview semantics in the same way earlier planning managers lost deterministic contract semantics.

# Goals & Non-Goals

## Goals

- Align active feed-forward tasks with the dedicated feed-forward manager agents.
- Separate review-manager prompts from planning-manager prompts.
- Harden conversation routing/finalization boundaries analog to planning-manager hardening.
- Preserve existing artifact schemas and persisted outputs.

## Non-Goals

- No schema changes.
- No rearchitecture of the coach specialist tree.
- No change to specialist output models unless required by prompt routing.

# Proposed Behavior

- `season_phase_feed_forward` and `phase_feed_forward` use their dedicated manager agents rather than artifact-writer agents.
- `season_review_manager`, `phase_review_manager`, `week_review_manager`, and `des_review_manager` each use a dedicated prompt file with review-specific instructions.
- `conversation_manager` becomes a bounded non-delegating router/finalizer and must not reopen scope, preview/apply, or authority boundaries.

# Implementation Analysis

- Update `config/crewai/tasks.yaml` to point active feed-forward tasks at feed-forward managers.
- Update `config/crewai/agents.yaml` to assign dedicated review prompt agents and disable delegation for `conversation_manager`.
- Create prompt files for the four review managers.
- Tighten `prompts/agents/conversation_manager.md` and `skills/conversation/routing-and-finalization/SKILL.md`.
- Add regression tests in `tests/test_crewai_runtime.py`.

# Impact Analysis

- No persistence or schema impact.
- Minor behavior change in CrewAI task orchestration and prompt selection.
- Reduced risk of rediscovery / boundary loss in feed-forward, review, and coach flows.

# Options & Recommendation

## Option A

Keep shared prompts and rely on tool scoping alone.

Tradeoff: lower maintenance, but manager role boundaries stay blurred and failure modes remain prompt-driven.

## Option B

Use dedicated prompts and dedicated feed-forward task routing.

Tradeoff: more prompt files, but clearer role semantics and lower cross-role leakage.

## Recommendation

Use Option B.

# Acceptance Criteria

- Feed-forward tasks no longer use artifact-writer agents as their active crew task agent.
- Review managers no longer reuse planning-manager prompt files.
- `conversation_manager` has `allow_delegation: false`.
- Conversation prompt/skill explicitly preserve specialist boundaries and forbid rediscovery.
- Runtime tests cover task-agent alignment, prompt-agent separation, and conversation-manager delegation settings.

# Migration / Rollout

- No migration required.
- Roll out directly with config/prompt/test changes.

# Risks & Failure Modes

- If feed-forward managers produce the wrong output shape, feed-forward task execution could regress.
- If review prompts diverge too far from current behavior, review quality could drop.
- If the conversation manager becomes too restrictive, some coach flows may under-route.

Mitigation:

- Keep output modes unchanged.
- Add regression tests for agent/task wiring.
- Leave specialist paths untouched.

# Observability / Logging

- Existing CrewAI task/agent telemetry should reflect the new active task agents and prompt routing.
- No new log event types required.

# Documentation Updates

- Update `CHANGELOG.md`.

# Link Map

- [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
- [tasks.yaml](/Users/alexander/RPS/config/crewai/tasks.yaml)
- [agents.yaml](/Users/alexander/RPS/config/crewai/agents.yaml)
- [conversation_manager.md](/Users/alexander/RPS/prompts/agents/conversation_manager.md)
