---
Type: Specification
Specification-For: ARTEFACT_JSON_SCHEMA
Specification-ID: ArtefactJsonSchemaSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Data-Pipeline
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder
  - Performance-Analyst
  - Policy-Owner

Notes: >
  Defines the canonical JSON envelope and validation rules for all
  agent-generated and agent-consumed artefacts. Markdown artefacts are
  no longer valid inputs for agents.
---

# Artefact JSON Schema Specification

## 1. Purpose
Define a canonical JSON envelope (`meta` + `data`) and require validation
against a JSON Schema for every agent-generated/consumed artefact.

## 2. Canonical Envelope
Every artefact MUST be a JSON object with:
- `meta` (identity, ownership, traceability)
- `data` (artefact-specific payload)

The envelope schema is defined in:
- `artefact_envelope.schema.json`

## 3. Meta Fields (Required)
The meta structure (required and optional fields, formats, enums) is defined in:
- `artefact_meta.schema.json`

This spec does not redefine meta fields; if there is any mismatch, the schema prevails.

## 4. Payload Schemas
Artefact payloads MUST validate against the artefact-specific schema in
the schema store.

Narrative artefacts use `structured_doc.schema.json` unless an artefact-specific
schema defines a stricter payload (e.g., `season_plan.schema.json`).
Tabular artefacts use `tabular_data.schema.json`.

## 5. Sidecar (Human-Readable)
Optional human-readable sidecars are allowed:
- `<basename>.rendered.md`

Sidecars are informational only and MUST NOT be used as agent inputs.

## 6. Required JSON Schemas (V1)
- `season_plan.schema.json`
- `macro_meso_feed_forward.schema.json`
- `phase_guardrails.schema.json`
- `phase_structure.schema.json`
- `phase_preview.schema.json`
- `block_feed_forward.schema.json`
- `zone_model.schema.json`
- `week_plan.schema.json`
- `workouts.schema.json` (Workout-Builder output)
- `activities_actual.schema.json`
- `activities_trend.schema.json`
- `wellness.schema.json`
- `des_analysis_report.schema.json`
- `kpi_profile.schema.json`

## 7. Validation Rule
Agents MUST stop if the produced artefact does not validate against its schema.

## End of Spec
