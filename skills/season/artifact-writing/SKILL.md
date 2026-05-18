---
name: artifact-writing
description: Serialize the final approved season artifact envelope without adding planning content.
metadata:
  author: rps
  version: "3.0"
---
Write the approved `SEASON_PLAN` envelope only.

Method:
1. Emit one top-level object with exactly `meta` and `data`.
2. Preserve the approved season bundle exactly and write only the approved planning content.
3. Fill envelope constants exactly:
   - `artifact_type = SEASON_PLAN`
   - `schema_id = SeasonPlanInterface`
   - `authority = Binding`
   - `owner_agent = Season-Planner`
4. Preserve exact `iso_week`, `iso_week_range`, `temporal_scope`, `trace_upstream`, `trace_data`, and `trace_events`.
5. Keep season-wide constraints, event windows, phase definitions, and citations complete and schema-valid.
6. Validate locally against `season_plan.schema.json` before any store call.

Writer rules:
- season output is binding; scenario artifacts remain informational
- required strings must be non-empty
- use the real approved phase ranges and dates exactly as provided during writing
- if a required field is missing, unknown, or schema-invalid: stop rather than guess

Hard rules:
- write only approved season logic during writing
- render user-facing chat as readable prose/tables instead of raw JSON
- call persistence tools only after schema validity is satisfied
- fill required fields and citations with real approved content

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return only the schema-compliant artifact envelope required by the active task expected_output.
- Include top-level `meta` and `data` content exactly as required by the artifact schema.
- Preserve approved bundle content, review decisions, deterministic context, and trace references.
- Emit only the artifact object.
