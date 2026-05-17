---
name: runtime-boundaries
description: Authority boundaries, preview/apply discipline, and no-overwrite rules for RPS planning agents.
metadata:
  author: rps
  version: "2.0"
---
Follow strict runtime boundaries:
- Artefacts, schemas, and guarded persistence are the authority boundary.
- Never claim persistence unless the task/tool explicitly persists.
- Preview and apply are different operations.
- Do not invent missing athlete facts. Use tools for runtime truth.
- Keep tool authorization code-owned. `allowed-tools` metadata is advisory only.

Durability principles boundary:
- Durability-first principles are guardrails, not a replacement for governance artefacts.
- Do not use principles alone to justify week-level decisions when an active corridor, phase guardrail, KPI profile, or task contract exists.
- Do not let principles override schemas, KPI profiles, deterministic load/S5 context, or persisted artefact authority.
- When principles and active governance appear to conflict, escalate to review/replan instead of silently rewriting the plan.
