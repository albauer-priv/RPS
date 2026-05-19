---
name: structure-review
description: Review phase structural consistency across guardrails, cadence, and event integration.
metadata:
  author: rps
  version: "1.0"
---
Review whether the candidate phase structure is internally coherent.

Checklist:
- guardrails and structure agree
- cadence and deload logic are represented correctly
- event integration does not create illegal structure changes
- the range remains exact and traceable

Retrieval policy:
- Use `workspace_get_phase_execution_context` and `workspace_get_phase_slot_contract` for authoritative phase contracts.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots when direct retrieval is still needed.
- Use `workspace_get_input` only for athlete-managed inputs.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
