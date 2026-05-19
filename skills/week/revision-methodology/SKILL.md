---
name: revision-methodology
description: Convert one bounded week intent into a coherent candidate revision while preserving upstream authority.
metadata:
  author: rps
  version: "2.0"
---
Revise the week conservatively and traceably.

Method:
1. Preserve phase intent, active corridor, and protected recovery structure.
2. Change only the minimum needed to satisfy the requested intent.
3. Keep week logic consistent before workout text details are refined.
4. Return one bounded candidate, not multiple variants.

Hard rules:
- keep scope expansion explicit and user-approved
- use downstream recovery-preserving adjustments after missed work
- revise only the days in the approved scope

Retrieval policy:
- Use `workspace_get_week_calendar_context` and `workspace_get_phase_execution_context` for authoritative week execution values.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots when direct retrieval is still needed.
- Use `workspace_get_input` only for athlete-managed inputs.
- Use `workspace_get_version` only for explicit week-sensitive historical artefacts.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
