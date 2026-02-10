---
Type: Contract
Contract-Name: data_pipeline__scenario
Version: 1.0
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Data-Pipeline
To-Agent: Season-Scenario-Agent

Dependencies:
  - ID: AvailabilityInterface
    Version: 1.0
  - ID: ArtefactJsonSchemaSpec
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Data-Pipeline -> Season-Scenario-Agent (v1.0)

## 1) Purpose (Binding)
Provide normalized availability data from user-managed Availability inputs.

## 2) Producer Responsibilities (Data-Pipeline)
- MUST emit `availability_yyyy-ww.json` validated against `availability.schema.json`
  when Availability inputs exist.
- MUST include required meta fields and trace_upstream references per `traceability_spec.md`.
- MUST STOP on schema validation failure.

## 3) Consumer Responsibilities (Season-Scenario-Agent)
- MUST validate input JSON before use and STOP on invalid artefacts.
- MUST use availability for scenario constraint summaries and phase shaping.

## 4) Artefacts and Schemas (Binding)

### Inputs (Season-Scenario-Agent consumes)
- `availability_yyyy-ww.json` -> `availability.schema.json`

### Outputs
- None.

## 5) Constraints / Forbidden (Binding)
- Availability artefact MUST be treated as binding constraints, not optional hints.

## 6) Error Handling & STOP Rules
- Missing or invalid availability artefact -> STOP and escalate.

## 7) Traceability
- Data-Pipeline outputs MUST include trace_upstream entries.

## 8) Precedence
- Not specified.
