---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Runbooks
---
# CrewAI Memory in RPS

## Purpose

Document where CrewAI memory is allowed and what it must not replace.

## Policy boundary

Memory is assistive only.

Memory must not replace:
- authoritative plan artifacts
- selected artifact versions
- pending operation state
- schema or contract truth

## Config

See `config/crewai/memory_policy.yaml`.

Crew-level examples:
- `coach_conversation`
- `workout_editor_conversation`
- `season_planning`
- `phase_planning`
- `week_planning`
- `report_advisory`
- `feed_forward_advisory`

Agent-level examples:
- private scope: `/athlete/<id>/coach/session/<surface>`
- read-only slice: coach preferences + accepted patterns

## Debugging

Inspect:
- `src/rps/crewai_runtime/memory.py`
- CrewAI storage path configured from policy
- whether an agent received shared crew memory or a scoped view
