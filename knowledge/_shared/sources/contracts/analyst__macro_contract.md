---
Type: Contract
Contract-Name: analyst__macro
Version: 1.0
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Performance-Analyst
To-Agent: Macro-Planner

Dependencies:
  - ID: ActivitiesActualInterface
    Version: 1.0
  - ID: ActivitiesTrendInterface
    Version: 1.0
  - ID: EventInterface
    Version: 1.0
  - ID: KPIProfileInterface
    Version: 1.0
  - ID: DESAnalysisInterface
    Version: 1.1
  - ID: SeasonPlanInterface
    Version: 1.0
  - ID: PhaseGuardrailsInterface
    Version: 1.0
  - ID: PhaseStructureInterface
    Version: 1.0
  - ID: LoadEstimationSpec
    Version: 1.0
  - ID: DESEvaluationPolicy
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Performance-Analyst -> Macro-Planner (v1.0)

## 1) Purpose (Binding)
Provide evidence-based DES analysis for the Macro-Planner without granting
operational control or progression authority.

## 2) Producer Responsibilities (Performance-Analyst)
- MUST validate all input JSON against schema before use and STOP on invalid artefacts.
- MUST produce `des_analysis_report_yyyy-ww.json` validated against `des_analysis_report.schema.json`.
- MAY analyze KPI profiles, actuals, trends, and events as context (informational only).
- MAY formulate advisory recommendations.
- MUST NOT modify phase guardrails.
- MUST NOT address Micro- or Meso-Architect directly.
- MUST NOT approve or stop progression.
- MUST NOT define operational actions.

## 3) Consumer Responsibilities (Macro-Planner)
- MUST validate `des_analysis_report_yyyy-ww.json` before use and STOP on invalid artefacts.
- MAY read DES reports.
- MAY interpret recommendations with delay as needed.
- MAY issue feed-forward to Meso-Architect if needed.

## 4) Artefacts and Schemas (Binding)

### Inputs (Performance-Analyst consumes)
- `activities_actual_yyyy-ww.json` -> `activities_actual.schema.json`
- `activities_trend_yyyy-ww.json` -> `activities_trend.schema.json`
- `kpi_profile_des_*.json` -> `kpi_profile.schema.json`
- `season_plan_yyyy-ww--yyyy-ww.json` -> `season_plan.schema.json`
- `phase_guardrails_yyyy-ww--yyyy-ww.json` -> `phase_guardrails.schema.json`
- `phase_structure_yyyy-ww--yyyy-ww.json` -> `phase_structure.schema.json`

### Outputs (Performance-Analyst produces)
- `des_analysis_report_yyyy-ww.json` -> `des_analysis_report.schema.json`

### Informational Inputs (no schema)
- `events.md`

## 5) Constraints / Forbidden (Binding)
- Outputs are advisory only and MUST NOT be treated as operational control.

## 6) Error Handling & STOP Rules
- Missing required inputs or invalid JSON -> STOP and escalate.
- Output failing schema validation -> STOP and re-emit.

## 7) Traceability
- Outputs MUST include trace_upstream references per `traceability_spec.md`.

## 8) Precedence
- Not specified.
