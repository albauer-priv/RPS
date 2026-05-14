Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Planning Runtime

# Skills Source Migration Audit

Purpose:
- validate, file by file, how prose sources under `specs/knowledge/_shared/sources/` are handled after the single-method-skill migration
- distinguish canonical skill-owned planning logic from machine-layer contracts/schemas and retrieval-only evidence
- document which legacy prose docs are now superseded as canonical planning sources

## Disposition Legend
- `Superseded -> Skill`: planning logic has been validated into one or more `SKILL.md` files and the source doc is no longer canonical for runtime planning behavior
- `Machine Layer`: contract/interface/schema/validation source remains canonical outside the skill layer
- `Retrieval / Reference`: evidence or bibliography remains supporting material, not a `SKILL.md` canonical source
- `Deprecated Legacy`: kept only for backward reference and not used as current canonical planning input

## Validated Mapping

| Source | Disposition | Validated Target(s) |
|---|---|---|
| `specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md` | Superseded -> Skill | `skills/shared/durability-methodology/SKILL.md`, `skills/season/event-priority-anchoring/SKILL.md`, `skills/season/macrocycle-architecture/SKILL.md`, `skills/season/audit/SKILL.md`, `skills/week/recommendation-and-adjustment/SKILL.md`, `skills/week/revision-methodology/SKILL.md` |
| `specs/knowledge/_shared/sources/principles/evidence_layer_durability.md` | Retrieval / Reference | `skills/shared/durability-methodology/references/evidence_layer_durability.md` |
| `specs/knowledge/_shared/sources/policies/progressive_overload_policy.md` | Superseded -> Skill | `skills/season/load-governance/SKILL.md`, `skills/phase/guardrails-authoring/SKILL.md`, `skills/phase/cadence-recovery/SKILL.md`, `skills/week/load-estimation-week/SKILL.md` |
| `specs/knowledge/_shared/sources/policies/load_distribution_policy.md` | Superseded -> Skill | `skills/week/load-estimation-week/SKILL.md` |
| `specs/knowledge/_shared/sources/policies/workout_policy.md` | Superseded -> Skill | `skills/week/workout-text-authoring/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md` |
| `specs/knowledge/_shared/sources/policies/kpi_signal_effects_policy.md` | Superseded -> Skill | `skills/phase/intensity-distribution/SKILL.md`, `skills/report/analysis-methodology/SKILL.md` |
| `specs/knowledge/_shared/sources/policies/des_evaluation_policy.md` | Superseded -> Skill | `skills/report/analysis-methodology/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/load_estimation_spec.md` | Superseded -> Skill | `skills/shared/load-estimation-core/SKILL.md`, `skills/season/load-governance/SKILL.md`, `skills/phase/guardrails-authoring/SKILL.md`, `skills/week/load-estimation-week/SKILL.md`, `skills/week/load-governance-review/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/data_confidence_spec.md` | Superseded -> Skill | `skills/shared/traceability-and-naming/SKILL.md`, `skills/report/context-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/file_naming_spec.md` | Superseded -> Skill | `skills/shared/traceability-and-naming/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/traceability_spec.md` | Superseded -> Skill | `skills/shared/traceability-and-naming/SKILL.md`, `skills/season/artifact-writing/SKILL.md`, `skills/phase/artifact-writing/SKILL.md`, `skills/week/artifact-writing/SKILL.md`, `skills/report/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/agenda_enum_spec.md` | Superseded -> Skill | `skills/phase/execution-rules/SKILL.md`, `skills/phase/structure-authoring/SKILL.md`, `skills/week/workout-text-authoring/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/season_cycle_enum_spec.md` | Superseded -> Skill | `skills/phase/structure-authoring/SKILL.md`, `skills/season/macrocycle-architecture/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/athlete_profile_interface_spec.md` | Superseded -> Skill | `skills/season/context-analysis/SKILL.md`, `skills/season/constraint-synthesis/SKILL.md`, `skills/phase/context-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/availability_interface_spec.md` | Superseded -> Skill | `skills/season/context-analysis/SKILL.md`, `skills/season/constraint-synthesis/SKILL.md`, `skills/phase/context-analysis/SKILL.md`, `skills/week/constraint-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/logistics_interface_spec.md` | Superseded -> Skill | `skills/season/context-analysis/SKILL.md`, `skills/season/constraint-synthesis/SKILL.md`, `skills/phase/context-analysis/SKILL.md`, `skills/week/constraint-analysis/SKILL.md`, `skills/report/context-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/planning_events_interface_spec.md` | Superseded -> Skill | `skills/season/context-analysis/SKILL.md`, `skills/season/constraint-synthesis/SKILL.md`, `skills/phase/context-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/season_scenarios_interface_spec.md` | Superseded -> Skill | `skills/season/scenario-generation/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/season_scenario_selection_interface_spec.md` | Superseded -> Skill | `skills/season/scenario-interpretation/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/wellness_interface_spec.md` | Superseded -> Skill | `skills/report/context-analysis/SKILL.md`, `skills/report/analysis-methodology/SKILL.md`, `skills/week/constraint-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_season_scenarios.md` | Superseded -> Skill | `skills/season/scenario-generation/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_season_scenario_selection.md` | Superseded -> Skill | `skills/season/scenario-interpretation/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md` | Superseded -> Skill | `skills/season/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_season_phase_feed_forward.md` | Superseded -> Skill | `skills/season/feed-forward/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_phase_guardrails.md` | Superseded -> Skill | `skills/phase/artifact-writing/SKILL.md`, `skills/phase/guardrails-authoring/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_phase_structure.md` | Superseded -> Skill | `skills/phase/artifact-writing/SKILL.md`, `skills/phase/structure-authoring/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_phase_preview.md` | Superseded -> Skill | `skills/phase/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_phase_feed_forward.md` | Superseded -> Skill | `skills/phase/feed-forward/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_week_plan.md` | Superseded -> Skill | `skills/week/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/mandatory_output_des_analysis_report.md` | Superseded -> Skill | `skills/report/artifact-writing/SKILL.md`, `skills/report/analysis-methodology/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md` | Superseded -> Skill | `skills/week/workout-text-authoring/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md` | Superseded -> Skill | `skills/week/workout-text-authoring/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/workouts/workout_json_spec.md` | Superseded -> Skill | `skills/week/workout-text-authoring/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md`, `skills/week/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/events_interface_spec.md` | Deprecated Legacy | superseded by `specs/knowledge/_shared/sources/specs/planning_events_interface_spec.md` |
| `specs/knowledge/_shared/sources/specs/artefact_json_schema_spec.md` | Machine Layer | envelope/schema validation remains external to `SKILL.md` |
| `specs/knowledge/_shared/sources/specs/header_schema_spec.md` | Machine Layer | header/schema validation remains external to `SKILL.md` |
| `specs/knowledge/_shared/sources/specs/contract_precedence_spec.md` | Machine Layer | contract resolution remains external to `SKILL.md` |
| `specs/knowledge/_shared/sources/contracts/*` | Machine Layer | cross-artifact contracts remain canonical outside skills |
| `specs/knowledge/_shared/sources/schemas/bundled/*.json` | Machine Layer | canonical machine-readable validation |
| `specs/knowledge/_shared/sources/evidence/durability_bibliography.md` | Retrieval / Reference | supporting bibliography only |
| `specs/knowledge/_shared/sources/evidence/evidence_manifest.md` | Retrieval / Reference | evidence lookup only |

## Validation Notes
- Skill validation was performed by reading each planning-relevant prose source and checking that its operative rules now appear in the target `SKILL.md` files, not only in `references/`.
- Sources classified as `Machine Layer` were deliberately not moved into `SKILL.md` because they define schemas, envelope contracts, or cross-artifact precedence rather than agent method logic.
- `events_interface_spec.md` remains deprecated legacy and should not be used as the current canonical planning-event source.
