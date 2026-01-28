---
Type: Contract
Contract-Name: macro__meso
Version: 1.3
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Macro-Planner
To-Agent: Meso-Architect

Dependencies:
  - ID: SeasonPlanInterface
    Version: 1.0
  - ID: LoadEstimationSpec
    Version: 1.0
  - ID: PhaseGuardrailsInterface
    Version: 1.0
  - ID: PhaseStructureInterface
    Version: 1.0
  - ID: PhasePreviewInterface
    Version: 1.0
  - ID: BlockFeedForwardInterface
    Version: 1.0
  - ID: ZoneModelInterface
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Macro-Planner -> Meso-Architect (v1.3)

## 1) Purpose (Binding)
Translate macro-level seasonal intent into block-level governance and block
structural architecture without introducing week- or workout-level planning.

## 2) Producer Responsibilities (Macro-Planner)
- OWNS phase intent and seasonal priorities.
- OWNS macro weekly kJ corridors (kJ-first).
- OWNS high-level allowed/forbidden intensity domains and non-negotiables.
- MUST derive availability assumptions from the Season Brief weekday availability table
  (Mon-Sun hours, indoor possible, travel risk) and fixed rest days, and include them in
  `season_plan.data.global_constraints.availability_assumptions` and
  `season_plan.data.global_constraints.recovery_protection`.
- MUST validate macro outputs before release.
- MAY issue `macro_meso_feed_forward_yyyy-ww.json` when macro changes are required.

## 3) Consumer Responsibilities (Meso-Architect)
- OWNS block selection within macro corridors.
- OWNS block status (Green/Yellow/Red) and block-level guardrails.
- OWNS semantic permissions at block level.
- OWNS structural block architecture and preview (non-binding).
- MUST validate all input JSON before use and STOP on invalid artefacts.
- MUST validate all output JSON before release.
- MUST NOT reinterpret macro intent.
- MUST NOT exceed macro kJ corridor without explicit upstream change.
- MUST NOT derive block adjustments directly from `des_analysis_report_yyyy-ww.json`.
- MUST preserve macro availability assumptions and fixed rest days in phase guardrails
  non-negotiables and recovery protection rules.
- If the user explicitly specifies an `iso_week_range` for phase guardrails or execution,
  it MUST be honored and may override phase-aligned block context resolution; document
  the override in `meta.notes`.

## 4) Artefacts and Schemas (Binding)

### Inputs (Meso-Architect consumes)
- `season_plan_yyyy-ww--yyyy-ww.json` -> `season_plan.schema.json` (required)
- `macro_meso_feed_forward_yyyy-ww.json` -> `macro_meso_feed_forward.schema.json` (binding if present)

### Informational Inputs (no schema)
- `events.md`

### Informational JSON Inputs (schemas required)
- `activities_actual_yyyy-ww.json` -> `activities_actual.schema.json`
- `activities_trend_yyyy-ww.json` -> `activities_trend.schema.json`
- `zone_model_power_<FTP>W.json` -> `zone_model.schema.json` (informational; from Data-Pipeline)

### Outputs (Meso-Architect produces)
- `phase_guardrails_yyyy-ww--yyyy-ww.json` -> `phase_guardrails.schema.json` (required)
- `block_feed_forward_yyyy-ww.json` -> `block_feed_forward.schema.json` (optional)
- `phase_structure_yyyy-ww--yyyy-ww.json` -> `phase_structure.schema.json` (required)
- `phase_preview_yyyy-ww--yyyy-ww.json` -> `phase_preview.schema.json` (optional)

## 5) Constraints / Forbidden (Binding)
- All KPI-driven block changes require explicit `macro_meso_feed_forward_yyyy-ww.json`.
- `phase_structure_*` and `phase_preview_*` MUST NOT include:
  - workouts
  - intervals
  - zones/%FTP
  - daily kJ

## 6) Error Handling & STOP Rules
- Missing macro weekly kJ corridor -> STOP (E_MACRO_INPUT_INCOMPLETE).
- Conflicting macro directives -> STOP + escalate.
- Block output exceeds macro corridor -> STOP + escalate.

## 7) Traceability
- Every block artefact MUST reference upstream `season_plan_yyyy-ww--yyyy-ww.json`
  filename + version.
- Feed Forward MUST reference baseline `phase_guardrails_yyyy-ww--yyyy-ww.json`
  filename + version.

## 8) Precedence
- Not specified.
