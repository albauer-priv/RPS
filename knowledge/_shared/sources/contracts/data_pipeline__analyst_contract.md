---
Type: Contract
Contract-Name: data_pipeline__analyst
Version: 1.0
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Data-Pipeline
To-Agent: Performance-Analyst

Dependencies:
  - ID: ActivitiesActualInterface
    Version: 1.0
  - ID: ActivitiesTrendInterface
    Version: 1.0
  - ID: ArtefactJsonSchemaSpec
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Data-Pipeline -> Performance-Analyst (v1.0)

## 1) Purpose (Binding)
Provide validated weekly activities actuals and trend artefacts for analysis.

## 2) Producer Responsibilities (Data-Pipeline)
- MUST emit `activities_actual_yyyy-ww.json` validated against `activities_actual.schema.json`.
- MUST emit `activities_trend_yyyy-ww.json` validated against `activities_trend.schema.json`.
- MUST include required meta fields and trace_upstream references per `traceability_spec.md`.
- MUST STOP on schema validation failure.

## 3) Consumer Responsibilities (Performance-Analyst)
- MUST validate input JSON before use and STOP on invalid artefacts.
- MUST treat activities artefacts as factual inputs only.

## 4) Artefacts and Schemas (Binding)

### Inputs (Performance-Analyst consumes)
- `activities_actual_yyyy-ww.json` -> `activities_actual.schema.json`
- `activities_trend_yyyy-ww.json` -> `activities_trend.schema.json`

### Outputs
- None.

## 5) Constraints / Forbidden (Binding)
- Activities artefacts MUST NOT be treated as governance.

## 6) Error Handling & STOP Rules
- Missing or invalid activities artefacts -> STOP and escalate.

## 7) Traceability
- Data-Pipeline outputs MUST include trace_upstream entries.

## 8) Precedence
- Not specified.
