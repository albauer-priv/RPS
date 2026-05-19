Version: 1.0
Status: Draft
Last-Updated: 2026-05-19
Owner: Planning Runtime

# Context / Problem

Internal Season/Phase/Week planning specialists still produce low-quality blocked answers in runtime logs even after model routing and knowledge-surface fixes. The visible failure mode is:

- tools are available but not used first
- specialists ask for inputs that are already tool-loadable or already present in prior specialist context
- blocked answers repeat the same message multiple times
- task input carries the full shared system prompt plus an oversized task wrapper, which dilutes the actual step

This is now the main failure class in the planning runtime.

# Goals & Non-Goals

## Goals

- Make internal planning specialists clearly tool-first.
- Reduce prompt/context bulk for internal specialist tasks.
- Prevent repetitive “please provide X” blocked responses when X is tool-loadable.
- Give specialists a compact, deterministic blocked-answer policy.

## Non-Goals

- Re-architect CrewAI task context delivery.
- Change public artifact writer prompts.
- Add new dependencies or a new prompting subsystem.

# Proposed Behavior

Internal specialist tasks for Season/Phase/Week planning should receive:

- the agent-specific prompt only
- a compact shared binding block tailored to internal planning tasks
- a compacted task/user context
- an explicit tool contract for `payload_json`
- an explicit rule that tool-loadable inputs are not “missing” until relevant tools fail
- an explicit rule to prefer prior specialist context over re-asking for original workspace inputs

If a specialist is truly blocked, it should return one compact blocked response with:

- missing inputs
- attempted tools
- reason

and no repetition.

# Implementation Analysis

- Update `src/rps/agents/crewai_backend.py`:
  - add compact internal-task binding rules
  - switch internal specialist descriptions from `combined_system_prompt(...)` to `agent_prompt(...)`
  - compact long user/task input before injection
  - add explicit tool contract + missing-input rules
- Add targeted tests in `tests/test_crewai_runtime.py`
- Update changelog

# Impact Analysis

- No schema change
- No artifact contract change
- No UI contract change
- Affects only internal CrewAI task descriptions for planning specialists
- Low compatibility risk; public writer and coach paths stay unchanged

# Options & Recommendation

## Option A
Keep existing prompt wrapper and only change specialist prompt files.

Cons:
- still duplicates oversized shared system text
- still leaves tool contract ambiguous at runtime

## Option B (Recommended)
Harden internal task description assembly in code and keep prompt-file changes minimal.

Pros:
- one consistent fix across Season/Phase/Week specialists
- smallest behavioral surface change with highest leverage

# Acceptance Criteria (DoD)

- Internal specialist task descriptions no longer embed the full shared system prompt verbatim.
- Internal specialist descriptions include the `payload_json` tool contract.
- Internal specialist descriptions explicitly forbid treating tool-loadable inputs as missing before tool failure.
- Long internal user/task input is compacted before injection.
- Runtime tests cover the new description shape and compaction behavior.

# Migration / Rollout

- No migration needed
- Safe to roll out immediately

# Risks & Failure Modes

- If compaction is too aggressive, a specialist may lose useful context.
- Mitigation: preserve the most relevant task markers and apply a moderate cap.

# Observability / Logging

- Existing runtime telemetry remains sufficient.
- If blocked-answer quality is still poor after this change, add a dedicated retry/guard on “missing inputs without tool attempt”.

# Documentation Updates

- `CHANGELOG.md`
- this feature doc

# Link Map

- [System Architecture](../../architecture/system_architecture.md)
- [How To Plan](../../overview/how_to_plan.md)
- [Artefact Flow](../../overview/artefact_flow.md)
