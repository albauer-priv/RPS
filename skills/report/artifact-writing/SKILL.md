---
name: artifact-writing
description: Serialize the approved DES analysis report without adding diagnostic reasoning.
metadata:
  author: rps
  version: "3.0"
---
Write the approved `DES_ANALYSIS_REPORT` envelope only.

Method:
1. Emit exactly one top-level `{meta,data}` object.
2. Preserve the approved diagnostic content exactly.
3. Fill report constants exactly:
   - `artifact_type = DES_ANALYSIS_REPORT`
   - `schema_id = DESAnalysisInterface`
   - `authority = Binding`
   - `owner_agent = Performance-Analyst`
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
- do not add new interpretation during writing
- do not convert the report into a planning instruction
- stop on schema errors or missing required fields
