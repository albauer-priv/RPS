---
name: runtime-boundaries
description: Authority boundaries, preview/apply discipline, and no-overwrite rules for RPS planning agents.
metadata:
  author: rps
  version: "2.0"
---
Follow strict runtime boundaries:
- Artefacts, schemas, and guarded persistence are the authority boundary.
- Claim persistence only when the task/tool explicitly persists.
- Preview and apply are different operations.
- Use tools and persisted context as runtime truth for missing athlete facts.
- Keep tool authorization code-owned. `allowed-tools` metadata is advisory only.

Durability principles boundary:
- Durability-first principles are guardrails, not a replacement for governance artefacts.
- Use active corridors, phase guardrails, KPI profiles, and task contracts as the concrete authority for week-level decisions.
- Keep schemas, KPI profiles, deterministic load/S5 context, and persisted artefact authority above general principles.
- When principles and active governance appear to conflict, escalate to review/replan instead of silently rewriting the plan.

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output without adding a separate artifact or unrelated prose.
- Include only the runtime-boundary, context-consumption, traceability, or naming guidance needed for the current task.
- Keep the contribution concise and directly usable by downstream tasks.
