---
Type: Specification
Specification-For: DATA_CONFIDENCE_MODEL
Specification-ID: DataConfidenceSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Data-Pipeline
  - Season-Planner
  - Phase-Architect
  - Week-Planner

Notes: >
  Defines the canonical confidence and data-quality model for all factual
  and derived data artefacts. Confidence levels constrain downstream
  interpretation and decision-making.
---

# Data Confidence Specification

## Schema Reference (Normative)

The canonical confidence enum is defined in:
- `data_confidence.schema.json`

This spec defines semantics and usage constraints only. If there is any mismatch, the schema prevails.

## 1. Confidence Levels (Semantics)

| Level | Meaning | Allowed Use |
|------|---------|-------------|
| HIGH | Data complete, reliable, traceable | Full interpretation allowed |
| MEDIUM | Minor gaps or assumptions | Interpretation allowed, must be marked |
| LOW | Significant gaps or uncertainty | Informational only |
| UNKNOWN | Confidence not assessed | Treated as LOW |

## 2. Mandatory Confidence Annotation

All of the following artefacts must carry an explicit confidence level:
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`

Missing annotation renders the artefact invalid.

## 3. Producer Rules (Binding)

The Data-Pipeline MUST:
- assign confidence explicitly
- downgrade confidence when power/kJ data is missing or incomplete
- never upgrade confidence downstream without new source data

## 4. Consumer Constraints (Binding)

- Season-Planner: LOW or UNKNOWN confidence forbids strategic inference
- Phase-Architect: LOW confidence enforces conservative phase status
- Week-Planner: LOW confidence allows reporting only, no interpretation

## 5. Decision Interaction Rules

LOW confidence data MUST NOT:
- trigger progression
- justify deload avoidance
- override governance

MEDIUM confidence requires explicit annotation in outputs.

## 6. Lint Rules (Implied)

- Missing Data-Confidence field ⇒ FAIL
- Governance decision referencing LOW confidence without escalation ⇒ FAIL
- Confidence upgrade without new data ⇒ FAIL
