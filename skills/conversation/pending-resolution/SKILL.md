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

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output in a conversational, bounded, and directly actionable form.
- Include the route, decision, preview/apply boundary, or pending-state result requested by the task.
- Keep the final user-facing answer clear, positive, compact, and focused on the next safe step.
