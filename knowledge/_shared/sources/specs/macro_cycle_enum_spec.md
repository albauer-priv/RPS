---
Type: Specification
Specification-For: MACRO_CYCLE_ENUM
Specification-ID: MacroCycleEnumSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Performance-Analyst

Notes: >
  Defines the canonical cycle labels used in macro-level planning.
  These are labels only and must match exactly.
---

# MACRO CYCLE ENUM SPECIFICATION

## Schema Reference (Normative)

The canonical enum values are defined in:
- `macro_cycle_enum.schema.json`

This spec defines semantics only. If there is any mismatch, the schema prevails.

## 1) Macro Cycle Semantics

| Cycle       | Meaning                                     |
| ----------- | ------------------------------------------- |
| Base        | Foundation building and durability ramp-up  |
| Build       | Capacity/quality development and progression|
| Peak        | Specificity, readiness, and taper emphasis  |
| Transition  | Recovery, reset, or post-event downshift    |

### Rules
- Use exactly one value per phase.
- Values are case-sensitive per schema.

---
End of MACRO CYCLE ENUM SPECIFICATION v1.0
