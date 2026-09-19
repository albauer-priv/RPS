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

Capability tiers — what each agent layer can and cannot authorize:
- **Specialist agents** (context, evidence, load, cadence, structure, intensity, event-integration): propose content and flag risks; they cannot authorize plan submission or override upstream decisions
- **Manager/synthesis agents** (plan-manager, bundle-manager, review-manager): aggregate specialist contributions and dispatch work; they cannot substitute for specialist decisions or skip review steps
- **Audit/review agents** (governance-auditor, constraint-auditor, plan-auditor, load-governance-audit): emit blocking_issues and warnings; they cannot rewrite plan content directly
- **Writer agents** (artifact-writer): transform approved plans into artifacts; they cannot alter plan logic, load math, or corridor values
- **The plan advances only when the review layer approves it.** No single agent can bypass the review layer or authorize its own work as final.
- When in doubt about your tier: do your designated job; escalate via blocking_issue or warning; do not reach into a higher tier's authority


Output format:
- Return the active task expected_output without adding a separate artifact or unrelated prose.
- Include only the runtime-boundary, context-consumption, traceability, or naming guidance needed for the current task.
- Keep the contribution concise and directly usable by downstream tasks.
