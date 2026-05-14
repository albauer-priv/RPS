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
2. Preserve the approved season bundle exactly. Do not invent, optimize, or reinterpret planning content during writing.
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
- use the real approved phase ranges and dates; do not recompute them heuristically during writing
- if a required field is missing, unknown, or schema-invalid: stop rather than guess

Hard rules:
- no new season logic during writing
- no raw JSON in chat
- no tool call until schema validity is satisfied
- no empty placeholder strings for required fields or citations
