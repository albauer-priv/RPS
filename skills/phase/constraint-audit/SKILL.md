---
name: constraint-audit
description: Audit phase bundles for availability, logistics, event, and feed-forward constraint compliance.
metadata:
  author: rps
  version: "2.0"
---
Check whether the candidate phase respects binding constraints.

Focus on:
- athlete and logistics constraints
- event placement consistency
- any applicable feed-forward restriction
- exact-range integrity

Retrieval policy:
- Use `workspace_get_input` for athlete-managed inputs such as `planning_events`, `availability`, and `logistics`.
- Use `workspace_get_phase_execution_context` and `workspace_get_phase_slot_contract` for authoritative phase contracts.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots when direct retrieval is still needed.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
