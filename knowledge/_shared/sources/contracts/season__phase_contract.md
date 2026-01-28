---
Type: Contract
Contract-Name: season__phase
Version: 1.3
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Season-Planner
To-Agent: Phase-Architect

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
  - ID: PhaseFeedForwardInterface
    Version: 1.0
  - ID: ZoneModelInterface
    Version: 1.0
  - ID: TraceabilitySpec
    Version: 1.0
  - ID: FileNamingSpec
    Version: 1.0
---

# Contract: Season-Planner -> Phase-Architect (v1.3)

## 1) Purpose (Binding)
Translate season-level intent into phase-level governance and phase
structural architecture without introducing week- or workout-level planning.

## 2) Producer Responsibilities (Season-Planner)
- OWNS phase intent and seasonal priorities.
- OWNS season weekly kJ corridors (kJ-first).
- OWNS high-level allowed/forbidden intensity domains and non-negotiables.
- MUST derive availability assumptions from the Season Brief weekday availability table
  (Mon-Sun hours, indoor possible, travel risk) and fixed rest days, and include them in
  `season_plan.data.global_constraints.availability_assumptions` and
  `season_plan.data.global_constraints.recovery_protection`.
- MUST validate season outputs before release.
- MAY issue `season_phase_feed_forward_yyyy-ww.json` when season changes are required.

## 3) Consumer Responsibilities (Phase-Architect)
- OWNS phase selection within season corridors.
- OWNS phase status (Green/Yellow/Red) and phase-level guardrails.
- OWNS semantic permissions at phase level.
- OWNS structural phase architecture and preview (non-binding).
- MUST validate all input JSON before use and STOP on invalid artefacts.
- MUST validate all output JSON before release.
- MUST NOT reinterpret season intent.
- MUST NOT exceed season kJ corridor without explicit upstream change.
- MUST NOT derive phase adjustments directly from `des_analysis_report_yyyy-ww.json`.
- MUST preserve season availability assumptions and fixed rest days in phase guardrails
  non-negotiables and recovery protection rules.
- If the user explicitly specifies an `iso_week_range` for phase guardrails or execution,
  it MUST be honored and may override phase-aligned phase context resolution; document
  the override in `meta.notes`.

## 4) Artefacts and Schemas (Binding)

### Inputs (Phase-Architect consumes)
- `season_plan_yyyy-ww--yyyy-ww.json` -> `season_plan.schema.json` (required)
- `season_phase_feed_forward_yyyy-ww.json` -> `season_phase_feed_forward.schema.json` (binding if present)

### Informational Inputs (no schema)
- `events.md`

### Informational JSON Inputs (schemas required)
- `activities_actual_yyyy-ww.json` -> `activities_actual.schema.json`
- `activities_trend_yyyy-ww.json` -> `activities_trend.schema.json`
- `zone_model_power_<FTP>W.json` -> `zone_model.schema.json` (informational; from Data-Pipeline)

### Outputs (Phase-Architect produces)
- `phase_guardrails_yyyy-ww--yyyy-ww.json` -> `phase_guardrails.schema.json` (required)
- `phase_feed_forward_yyyy-ww.json` -> `phase_feed_forward.schema.json` (optional)
- `phase_structure_yyyy-ww--yyyy-ww.json` -> `phase_structure.schema.json` (required)
- `phase_preview_yyyy-ww--yyyy-ww.json` -> `phase_preview.schema.json` (optional)

## 5) Constraints / Forbidden (Binding)
- All KPI-driven phase changes require explicit `season_phase_feed_forward_yyyy-ww.json`.
- `phase_structure_*` and `phase_preview_*` MUST NOT include:
  - workouts
  - intervals
  - zones/%FTP
  - daily kJ

## 6) Error Handling & STOP Rules
- Missing season weekly kJ corridor -> STOP (E_SEASON_INPUT_INCOMPLETE).
- Conflicting season directives -> STOP + escalate.
- Phase output exceeds season corridor -> STOP + escalate.

## 7) Traceability
- Every phase artefact MUST reference upstream `season_plan_yyyy-ww--yyyy-ww.json`
  filename + version.
- Feed Forward MUST reference baseline `phase_guardrails_yyyy-ww--yyyy-ww.json`
  filename + version.

## 8) Precedence
- Not specified.
