---
name: artifact-writing
description: Serialize the approved DES analysis report without adding diagnostic reasoning.
metadata:
  author: rps
  version: "3.1"
---
Write the approved `DES_ANALYSIS_REPORT` data only.

Method:
1. Prefer emitting the approved `data` payload. If the active task still requires an envelope, emit exactly one top-level `{meta,data}` object.
2. Preserve the approved diagnostic content exactly.
3. Do not invent persisted `meta`. Runtime owns `artifact_type`, `schema_id`, `schema_version`, `authority`, `owner_agent`, `run_id`, and `created_at`.
4. Validate against `des_analysis_report.schema.json` before storing.

Required sections:
- `summary_meta`
- `kpi_summary`
- `weekly_analysis`
- `trend_analysis`
- `recommendation`
- `narrative_report`

Writer rules:
- each KPI domain must include `status`, `confidence`, `evidence_window`, and `delta_vs_baseline`
- recommendation must remain `advisory`, scoped to `Season-Planner`
- `explicitly_not` must contain exactly `direct_phase_change` and `weekly_intervention`
- all required narrative strings must be non-empty

Hard rules:
- write the approved interpretation only
- keep the report diagnostic and route planning instructions to planning tasks
- stop on schema errors or missing required fields

Output format:
- Return only the schema-compliant object required by the active task expected_output.
- Focus on `data`; if an envelope is requested, `meta` is a runtime-overwritten placeholder/hint.
- Preserve approved bundle content, review decisions, deterministic context, and trace references.
- Emit only the artifact object.
