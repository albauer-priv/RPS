---
Type: Contract
Contract-Name: data_pipeline__season
Version: 1.3
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Data-Pipeline
To-Agent: Season-Planner

Dependencies:
  - ID: ActivitiesActualInterface
    Version: 1.0
  - ID: ActivitiesTrendInterface
    Version: 1.0
  - ID: AvailabilityInterface
    Version: 1.0
  - ID: WellnessInterface
    Version: 1.0
  - ID: ZoneModelInterface
    Version: 1.0
  - ID: ArtefactJsonSchemaSpec
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Data-Pipeline -> Season-Planner (v1.3)

## 1) Purpose (Binding)
Provide validated factual artefacts (activities, wellness, zone model) to the Season-Planner.

## 2) Producer Responsibilities (Data-Pipeline)
- MUST emit `activities_actual_yyyy-ww.json` validated against `activities_actual.schema.json`.
- MUST emit `activities_trend_yyyy-ww.json` validated against `activities_trend.schema.json`.
- MUST emit `availability_yyyy-ww.json` validated against `availability.schema.json` when Season Brief availability exists.
- MUST emit `wellness_yyyy-ww.json` validated against `wellness.schema.json` when data exists.
- MUST emit `zone_model_power_<FTP>W.json` validated against `zone_model.schema.json` when sport settings allow.
- MUST include required meta fields and trace_upstream references per `traceability_spec.md`.
- MUST STOP on schema validation failure.

## 3) Consumer Responsibilities (Season-Planner)
- MUST validate input JSON before use and STOP on invalid artefacts.
- MUST treat activities artefacts as informational unless explicitly overridden by season governance.
- MUST use `wellness.body_mass_kg` as the sole body-mass source for any kJ/kg/h or W/kg scaling.

## 4) Artefacts and Schemas (Binding)

### Inputs (Season-Planner consumes)
- `activities_actual_yyyy-ww.json` -> `activities_actual.schema.json`
- `activities_trend_yyyy-ww.json` -> `activities_trend.schema.json`
- `availability_yyyy-ww.json` -> `availability.schema.json`
- `wellness_yyyy-ww.json` -> `wellness.schema.json`
- `zone_model_power_<FTP>W.json` -> `zone_model.schema.json`

### Outputs
- None.

## 5) Constraints / Forbidden (Binding)
- Season-Planner MUST NOT treat activities artefacts as governance.

## 6) Error Handling & STOP Rules
- Missing or invalid activities artefacts -> STOP and escalate.

## 7) Traceability
- Data-Pipeline outputs MUST include trace_upstream entries.

## 8) Precedence
- Not specified.
