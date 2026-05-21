---
name: context-analysis
description: Summarize the selected week plan, actuals, and active constraints without proposing changes.
metadata:
  author: rps
  version: "2.0"
---
Inspect the selected week factually.

Return:
- current plan shape
- actual execution signal
- active corridor and role constraints
- inherited `phase_type`, `phase_intent`, `build_subtype`, and what they imply for week shape
- likely change pressure

Summarize context only; route recommendations and revisions to the responsible downstream skill.

Hard rules:
- prefer the narrow configured workspace tools and injected deterministic context over broad rediscovery

Retrieval policy:
- Use `workspace_get_input` for athlete-managed inputs such as `planning_events`, `availability`, and `logistics`.
- Use `workspace_get_week_calendar_context` and `workspace_get_phase_execution_context` for authoritative week execution values.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots.
- Use `workspace_get_version` only when the task explicitly requires a week-sensitive historical artefact version.

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
