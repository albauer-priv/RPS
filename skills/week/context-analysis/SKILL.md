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
- prefer the injected deterministic context over broad rediscovery

Retrieval policy:
- Athlete-managed inputs (`planning_events`, `availability`, `logistics`), authoritative week execution values, and latest authoritative planning artefacts/snapshots are already provided as injected context. No workspace tools are available or needed for this task.

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
