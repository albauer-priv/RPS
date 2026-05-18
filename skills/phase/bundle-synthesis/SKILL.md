---
name: bundle-synthesis
description: Synthesize phase specialist drafts into one internal PhaseBundle.
metadata:
  author: rps
  version: "1.0"
---
Combine phase drafts into one internal bundle.

Method:
1. Keep guardrails authoritative over structure.
2. Apply cadence/recovery as a constraint on structure, not as a separate plan.
3. Preserve event integration only where it does not violate season authority.
4. Emit one review-ready phase bundle.

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include the selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
