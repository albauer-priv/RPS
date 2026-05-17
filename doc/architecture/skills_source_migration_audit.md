Version: 1.0
Status: Updated
Last-Updated: 2026-05-16
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
- LoadEstimationSpec S5 and availability-capacity logic are now split deliberately: operative "when/why" rules live in the Season/Phase/Week `SKILL.md` files, while exact capacity and S5 band derivation is code-owned by `src/rps/planning/load_bands.py`. The calculated min/max bands are still injected into planning context: Season receives availability capacity min/typical/max, and Phase/Week receive deterministic S5 min/max bands once a Season corridor is available. CrewAI guardrails check that agents do not widen or overwrite those injected values.
- Season scenario horizon and phase math remain informational in the artefacts, but are resolved deterministically by `src/rps/planning/season_structure.py`. Scenario generation receives last-event horizon math and cadence options before writing `SEASON_SCENARIOS`; Season planning receives selected-scenario phase math and a fixed phase-slot skeleton before writing `SEASON_PLAN`.
- `src/rps/planning/deterministic_context.py` is now the shared injection registry for code-owned runtime facts. It renders Season Scenario Horizon, Cadence Options, Selected Scenario Structure, Season Phase Slot, Phase Execution, Week Calendar/Availability, Report Evidence, and Coach Operation contexts while keeping plan artefact schemas unchanged in this pass.
- ProgressiveOverloadPolicy was re-audited after migration. Concrete rules now live directly in active `SKILL.md` bodies and detailed references: deterministic baseline selection (`0.80/1.15` exclusions, `2 of 3` gates), ramp ranges (`+5-8%`, `+8-12%`, rare `+12-18%`, sustained `>15%` warning), deload targets (`BL * 0.60-0.80` or prior week `* 0.55-0.75`), re-entry ranges (`BL * 0.85-1.05` by readiness), cadence-specific `3:1`, `2:1`, `2:1:1` week formulas, and `2:1:1` next-baseline update.
- DurabilityFirstPrinciples was re-audited after migration. Binding guardrail content is now active in shared crew skills and method skills: principles cannot override governance artefacts, kJ/load-kJ remains primary while CTL/ATL/TSB and IF/intensity distribution are secondary/tertiary, durability claims require energetic preload, event labels and A/B/C conflict hierarchy are explicit, old Specificity/Taper intent is translated into schema-valid `Base | Build | Peak | Transition`, the Kinzlbauer-like ultra/brevet season archetype is available as season architecture only, and polarized/pyramidal intensity distribution is expressed as phase-level policy rather than week-level override authority.
- LoadEstimationSpec was re-audited after migration. Binding rules now live in active load skills and code: `planned_kj` is mechanical work, `planned_weekly_load_kj` is weekly governance load, `weekly_kj_bands`/`weekly_load_corridor_kj` mirror governance bands, IF is applied exactly once, IF-direct fallback is limited to missing/unparseable/intent-only segment cases, output rounding is final-only, and S5 availability/KPI/progression/fallback logic is code-owned by `src/rps/planning/load_bands.py`.
- The LoadEstimationSpec code audit also found and corrected two runtime softening risks: negative availability is no longer silently clamped to zero in deterministic context, and missing allowed intensity domains are no longer defaulted to `ENDURANCE_LOW` at context-build time. Both now surface as STOP/warning states. Selected KPI moving-time-rate guidance from `SEASON_SCENARIO_SELECTION` is now forwarded into deterministic Phase/Week S5 mapping when available.
- LoadEstimationSpec implementation was extended beyond bands: `src/rps/planning/workout_load.py` now owns deterministic per-workout segment-load estimation for the project workout-text subset, including simple loop blocks, percent/ramp targets, IF-direct fallback, final-only rounding, and week-plan load audit summaries. Week prompts receive `Deterministic Workout Load Estimation Context` so agents use code-owned per-domain hourly calibration instead of inventing load factors.
- S5 Level 2/3 wiring is now more complete: selected KPI guidance still comes from `SEASON_SCENARIO_SELECTION`, while alternative escalation bands are derived from the active KPI Profile when available. Complete `availability_table` data can now become the effective S5 availability-hour source; partial tables are still injected for day planning but do not replace `weekly_hours`.
- Daily availability is now enforced as a context-aware CrewAI guardrail for `week_plan`. `src/rps/planning/week_availability.py` performs the pure validation, and `week_daily_availability_check` receives `AVAILABILITY` plus target week through runtime guardrail context. It hard-blocks fixed-rest-day load, locked zero-availability day load, and planned durations above explicit day `hours_max`.
- The season cycle enum migration is intentionally conservative: `Base`, `Build`, `Peak`, and `Transition` remain the only valid season cycle values; `Specificity` and `Taper` are retained only as structural/narrative behavior inside existing schema-valid cycles where needed.
