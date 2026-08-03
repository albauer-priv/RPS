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
- Athlete-managed inputs (`planning_events`, `availability`, `logistics`), authoritative phase contracts, and latest planning artefacts/snapshots are already provided as injected context. No workspace tools are available or needed for this task.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
