---
name: pending-resolution
description: Handle inspect/apply/discard for one existing pending preview operation.
metadata:
  author: rps
  version: "2.0"
---
Resolve one pending preview lifecycle action.

Rules:
- inspect, apply, or discard only the current pending operation
- stay with the pending resolution path for the current turn
- report exact effect and remaining state clearly


Output format:
- Return the active task expected_output in a conversational, bounded, and directly actionable form.
- Include the route, decision, preview/apply boundary, or pending-state result requested by the task.
- Keep the final user-facing answer clear, positive, compact, and focused on the next safe step.
