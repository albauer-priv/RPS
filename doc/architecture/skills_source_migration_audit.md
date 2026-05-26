Version: 1.0
Status: Updated
Last-Updated: 2026-05-23
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
| `specs/knowledge/_shared/sources/policies/workout_policy.md` | Superseded -> Skill | `skills/week/workout-construction/SKILL.md`, `skills/week/workout-construction/references/intervals_subset_examples.md`, `skills/week/workout-syntax-review/SKILL.md`, `skills/week/workout-syntax-review/references/validation_checklist.md` |
| `specs/knowledge/_shared/sources/policies/kpi_signal_effects_policy.md` | Superseded -> Skill | `skills/phase/intensity-distribution/SKILL.md`, `skills/report/analysis-methodology/SKILL.md` |
| `specs/knowledge/_shared/sources/policies/des_evaluation_policy.md` | Superseded -> Skill | `skills/report/analysis-methodology/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/load_estimation_spec.md` | Superseded -> Skill | `skills/shared/load-estimation-core/SKILL.md`, `skills/season/load-governance/SKILL.md`, `skills/phase/guardrails-authoring/SKILL.md`, `skills/week/load-estimation-week/SKILL.md`, `skills/week/load-governance-review/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/data_confidence_spec.md` | Superseded -> Skill | `skills/shared/traceability-and-naming/SKILL.md`, `skills/report/context-analysis/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/file_naming_spec.md` | Superseded -> Skill | `skills/shared/traceability-and-naming/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/traceability_spec.md` | Superseded -> Skill | `skills/shared/traceability-and-naming/SKILL.md`, `skills/season/artifact-writing/SKILL.md`, `skills/phase/artifact-writing/SKILL.md`, `skills/week/artifact-writing/SKILL.md`, `skills/report/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/agenda_enum_spec.md` | Superseded -> Skill | `skills/phase/execution-rules/SKILL.md`, `skills/phase/structure-authoring/SKILL.md`, `skills/week/workout-construction/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md` |
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
| `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md` | Superseded -> Skill | `skills/week/workout-construction/SKILL.md`, `skills/week/workout-construction/references/intervals_subset_examples.md`, `skills/week/workout-syntax-review/SKILL.md`, `skills/week/workout-syntax-review/references/validation_checklist.md` |
| `specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md` | Superseded -> Skill | `skills/week/workout-construction/SKILL.md`, `skills/week/workout-construction/references/intervals_subset_examples.md`, `skills/week/workout-syntax-review/SKILL.md`, `skills/week/workout-syntax-review/references/validation_checklist.md` |
| `specs/knowledge/_shared/sources/specs/workouts/workout_json_spec.md` | Superseded -> Skill | `skills/week/workout-construction/SKILL.md`, `skills/week/workout-syntax-review/SKILL.md`, `skills/week/artifact-writing/SKILL.md` |
| `specs/knowledge/_shared/sources/specs/events_interface_spec.md` | Deprecated Legacy | superseded by `specs/knowledge/_shared/sources/specs/planning_events_interface_spec.md` |
| `specs/knowledge/_shared/sources/specs/artefact_json_schema_spec.md` | Machine Layer | envelope/schema validation remains external to `SKILL.md` |
| `specs/knowledge/_shared/sources/specs/header_schema_spec.md` | Machine Layer | header/schema validation remains external to `SKILL.md` |
| `specs/knowledge/_shared/sources/specs/contract_precedence_spec.md` | Machine Layer | contract resolution remains external to `SKILL.md` |
| `specs/knowledge/_shared/sources/contracts/*` | Machine Layer | cross-artifact contracts remain canonical outside skills, but workout authoring/runtime method from `contracts/week__workout_export_contract.md` is mirrored into active week workout skills so planning no longer depends on loading the legacy prose file at runtime |
| `specs/knowledge/_shared/sources/schemas/bundled/*.json` | Machine Layer | canonical machine-readable validation |
| `specs/knowledge/_shared/sources/evidence/durability_bibliography.md` | Retrieval / Reference | supporting bibliography only |
| `specs/knowledge/_shared/sources/evidence/evidence_manifest.md` | Retrieval / Reference | evidence lookup only |

## Validation Notes
- Skill validation was performed by reading each planning-relevant prose source and checking that its operative rules now appear in the target `SKILL.md` files, not only in `references/`.
- Sources classified as `Machine Layer` were deliberately not moved into `SKILL.md` because they define schemas, envelope contracts, or cross-artifact precedence rather than agent method logic.
- `events_interface_spec.md` remains deprecated legacy and should not be used as the current canonical planning-event source.
- Week workout source migration is now complete for runtime purposes: `week__workout_export_contract.md`, `intervals_workout_ebnf.md`, `workout_syntax_and_validation.md`, and `workout_policy.md` are retained as audit/history sources, while the active planning method lives in the week workout `SKILL.md` bodies plus local `references/`.
- LoadEstimationSpec S5 and availability-capacity logic are now split deliberately: operative "when/why" rules live in the Season/Phase/Week `SKILL.md` files, while exact capacity and S5 band derivation is code-owned by `src/rps/planning/load_bands.py`. The calculated min/max bands are still injected into planning context: Season receives availability capacity min/typical/max, and Phase/Week receive deterministic S5 min/max bands once a Season corridor is available. CrewAI guardrails check that agents do not widen or overwrite those injected values.
- Season scenario horizon and phase math remain informational in the artefacts, but are resolved deterministically by `src/rps/planning/season_structure.py`. Scenario generation receives last-event horizon math and cadence options before writing `SEASON_SCENARIOS`; Season planning receives selected-scenario phase math and a fixed phase-slot skeleton before writing `SEASON_PLAN`.
- `src/rps/planning/deterministic_context.py` is now the shared injection registry for code-owned runtime facts. It renders Season Scenario Horizon, Cadence Options, Selected Scenario Structure, Season Phase Slot, Phase Execution, Week Calendar/Availability, Report Evidence, and Coach Operation contexts while keeping plan artefact schemas unchanged in this pass.
- ProgressiveOverloadPolicy was re-audited after migration. Concrete rules now live directly in active `SKILL.md` bodies and detailed references: deterministic baseline selection (`0.80/1.15` exclusions, `2 of 3` gates), ramp ranges (`+5-8%`, `+8-12%`, rare `+12-18%`, sustained `>15%` warning), deload targets (`BL * 0.60-0.80` or prior week `* 0.55-0.75`), re-entry ranges (`BL * 0.85-1.05` by readiness), cadence-specific `3:1`, `2:1`, `2:1:1` week formulas, and `2:1:1` next-baseline update.
- DurabilityFirstPrinciples was re-audited after migration. Binding guardrail content is now active in shared crew skills and method skills: principles cannot override governance artefacts, kJ/load-kJ remains primary while CTL/ATL/TSB and IF/intensity distribution are secondary/tertiary, durability claims require energetic preload, event labels and A/B/C conflict hierarchy are explicit, old Specificity/Taper intent is translated into schema-valid `Base | Build | Peak | Transition`, the Kinzlbauer-like ultra/brevet season archetype is available as season architecture only, and polarized/pyramidal intensity distribution is expressed as phase-level policy rather than week-level override authority.
- LoadEstimationSpec was re-audited after migration. Binding rules now live in active load skills and code: `planned_kj` is mechanical work, `planned_weekly_load_kj` is weekly governance load, `weekly_kj_bands`/`weekly_load_corridor_kj` mirror governance bands, IF is applied exactly once, IF-direct fallback is limited to missing/unparseable/intent-only segment cases, output rounding is final-only, and S5 availability/KPI/progression/fallback logic is code-owned by `src/rps/planning/load_bands.py`.
- The LoadEstimationSpec code audit also found and corrected two runtime softening risks: negative availability is no longer silently clamped to zero in deterministic context, and missing allowed intensity domains are no longer defaulted to `ENDURANCE` at context-build time. Both now surface as STOP/warning states. Selected KPI moving-time-rate guidance from `SEASON_SCENARIO_SELECTION` is now forwarded into deterministic Phase/Week S5 mapping when available.
- LoadEstimationSpec implementation was extended beyond bands: `src/rps/planning/workout_load.py` now owns deterministic per-workout segment-load estimation for the project workout-text subset, including simple loop blocks, percent/ramp targets, IF-direct fallback, final-only rounding, and week-plan load audit summaries. Week prompts receive `Deterministic Workout Load Estimation Context` so agents use code-owned per-domain hourly calibration instead of inventing load factors.
- S5 Level 2/3 wiring is now more complete: selected KPI guidance still comes from `SEASON_SCENARIO_SELECTION`, while alternative escalation bands are derived from the active KPI Profile when available. Complete `availability_table` data can now become the effective S5 availability-hour source; partial tables are still injected for day planning but do not replace `weekly_hours`.
- Daily availability is now enforced as a context-aware CrewAI guardrail for `week_plan`. `src/rps/planning/week_availability.py` performs the pure validation, and `week_daily_availability_check` receives `AVAILABILITY` plus target week through runtime guardrail context. It hard-blocks fixed-rest-day load, locked zero-availability day load, and planned durations above explicit day `hours_max`.
- The season cycle enum migration is intentionally conservative: `Base`, `Build`, `Peak`, and `Transition` remain the only valid season cycle values; `Specificity` and `Taper` are retained only as structural/narrative behavior inside existing schema-valid cycles where needed.

## 2026-05-23 Completeness Re-Audit

This re-audit applies a stricter standard than the earlier migration pass.

Current standard:
- active Season / Phase / Week planning layers must be upstream-first
- planner/finalizer must carry operative logic as early as possible
- review is a gate, not a second planner
- every variable-like term in active planning files must be locally defined, explicitly mapped to injected authority, or explicitly forbidden
- active planning skills should be locally usable and must not rely on thin "use reference X" wrappers for binding logic

### Status Legend
- `Complete for active scope`: the source is operationalized in the active runtime layer for the relevant scope
- `Mostly complete`: operationalized, but with small remaining structure/definition gaps
- `Partial`: meaningful migration exists, but one or more active files still remain too thin, split, or under-defined for the new standard
- `N/A by authority`: the source is not supposed to own this layer

### Source-to-Active Matrix

| Source | Season | Phase | Week | Current assessment |
|---|---|---|---|---|
| `progressive_overload_policy.md` | `Mostly complete` | `Mostly complete` | `Complete for active scope` | The operative cadence/ramp/deload/re-entry/fallback logic is now present in active planning layers, but residual variable-definition gaps still exist in some files. |
| `load_estimation_spec.md` | `Partial` | `Partial` | `Mostly complete` | Shared core math is strong and code-owned where appropriate, but Season/Phase wrappers are still thinner than the new self-contained standard. |
| `principles_durability_first_cycling.md` | `Mostly complete` | `Partial` | `Mostly complete` | Main durability rules are now visible in active planning layers, but the shared durability skill and some phase-facing translations are still less explicit than the new standard requires. |
| `workout_policy.md` | `N/A by authority` | `N/A by authority` | `Complete for active scope` | The active Week workout path is now the canonical runtime owner and is materially more complete than before. |

### Concrete findings

#### 1. `progressive_overload_policy.md`

What is now clearly migrated:
- Season:
  - `skills/season/load-governance/SKILL.md`
  - `skills/season/plan-synthesis/SKILL.md`
  - planner prompt/task layers
- Phase:
  - `skills/phase/guardrails-authoring/SKILL.md`
  - `skills/phase/cadence-recovery/SKILL.md`
  - `skills/phase/load-estimation-phase/SKILL.md`
  - `skills/phase/bundle-synthesis/SKILL.md`
- Week:
  - `skills/week/load-estimation-week/SKILL.md`
  - `skills/week/review-decision/SKILL.md`

What is still incomplete under the new standard:
- `skills/season/load-governance/SKILL.md` uses `LR_share` in an operative rule without defining it locally or mapping it to injected authority.
- `skills/phase/cadence-recovery/SKILL.md` uses `CH_kJ` in baseline-update logic without defining it locally or mapping it to injected authority.

Conclusion:
- The policy is no longer only "mentioned"; it is active in the planner path.
- It is not yet fully clean under the stricter explicit-variable rule.

#### 2. `load_estimation_spec.md`

What is strong:
- `skills/shared/load-estimation-core/SKILL.md` now carries the binding math, invariants, IF handling, governance-vs-mechanical semantics, and rounding rules clearly.
- `src/rps/planning/load_bands.py` owns deterministic S5 / capacity / progression-band derivation where the runtime should be code-owned.
- Week-level active handling is substantially operationalized in:
  - `skills/week/load-estimation-week/SKILL.md`

What remains incomplete:
- `skills/season/load-estimation-season/SKILL.md` is still thinner than the new self-contained target:
  - it lacks a proper `Definitions` section
  - it lacks a proper `Authority / injected sources` section
  - it still reads more like a guided companion than a fully self-contained active method
- `skills/phase/load-estimation-phase/SKILL.md` is improved, but still delegates meaningful operative behavior to companion skills instead of carrying the complete decision stack itself.

Conclusion:
- The source is functionally much better migrated than before.
- Under the new AGENTS standard, Season/Phase load-estimation wrappers still need one more pass.

#### 3. `principles_durability_first_cycling.md`

What is now operationalized:
- repeatability over cosmetic target centering
- recovery before catch-up
- kJ/work before intensity density
- one overload axis per step
- missed load is not debt
- compression handling by removing lower-priority stress first
- B-events support the A-event structure

Where this is visible:
- `skills/shared/durability-methodology/SKILL.md`
- `skills/season/load-governance/SKILL.md`
- `skills/season/plan-synthesis/SKILL.md`
- `skills/phase/guardrails-authoring/SKILL.md`
- `skills/phase/bundle-synthesis/SKILL.md`
- `skills/week/load-estimation-week/SKILL.md`
- `skills/week/workout-construction/SKILL.md`
- `skills/week/workout-syntax-review/SKILL.md`

What remains incomplete:
- `skills/shared/durability-methodology/SKILL.md` is still an active runtime skill without the newer self-contained structure (`Definitions`, `Authority / injected sources`, `Output expectation`).
- Phase-facing durability translation is present, but still more distributed and less explicit than the Season/Week active layers.

Conclusion:
- Durability-first is no longer just a reference source.
- It is still not as rigorously operationalized and structured as the load and workout layers.

#### 4. `workout_policy.md`

What is now clearly complete for active Week scope:
- active authoring:
  - `skills/week/workout-construction/SKILL.md`
- active syntax/semantics review:
  - `skills/week/workout-syntax-review/SKILL.md`
- active week legality gate:
  - `skills/week/review-decision/SKILL.md`

What is covered:
- family legality
- agenda/domain/modality mapping
- warmup/activation/cooldown rules
- export-safe subset restrictions
- family-specific progression order
- week-role semantic constraints
- durability-first anti-catch-up and no hidden accumulation constraints

Conclusion:
- This is the strongest migrated source among the four audited sources.
- No major active-scope gap was found in the Week workout path during this pass.

### Correction to earlier audit confidence

The earlier audit text overstated completeness in two places:
- it treated several active wrappers as "migrated" even when they were still too thin for the new self-contained standard
- it did not enforce the stricter explicit-variable rule now adopted in `AGENTS.md`

That means the correct current position is:
- migration quality is materially improved
- the runtime is much less dependent on legacy prose than before
- but the migration is still **not uniformly complete** under the stricter 2026-05-23 standard

### Next required cleanup pass

To close the remaining gaps, the next pass should:

1. Fix explicit-variable leftovers
   - define or map `LR_share`
   - define or map `CH_kJ`
   - repeat the audit for similar residual shorthand in active files

2. Upgrade thin active wrappers
   - `skills/season/load-estimation-season/SKILL.md`
   - `skills/phase/load-estimation-phase/SKILL.md`
   - `skills/shared/durability-methodology/SKILL.md`

3. Re-run the same source-to-active audit after that pass and only then treat the migration as complete under the new standard

## 2026-05-26 Prompt Source Migration Audit

This section extends the same audit to legacy prompt sources and all active prompt roles referenced by `config/crewai/agents.yaml`.

### Prompt-layer authority rule

Prompt ownership is now evaluated against this required order:

1. `code-owned`
2. `skill-owned`
3. `prompt-owned`
4. `task-owned`
5. `review-gate only`
6. `writer-only`

Prompt-owned content must cover:
- role authority
- injected-source precedence
- scope / non-scope
- upstream-first behavior
- no-review / no-writer semantic healing assumptions
- self-check / finalize-check / review-check behavior where relevant

### Prompt status legend

- `complete`: active prompt follows the new self-contained prompt standard
- `mostly_complete`: active prompt is strong but still missing one structural block or one explicit boundary
- `partial`: active prompt works, but is still too thin or too implicit for the new standard
- `missing`: active prompt does not yet meet the new standard in a meaningful way

### Legacy prompt-source mapping

| Source | Source type | Old responsibility / guidance | Target layer | Active target | Authority type | Variable completeness | Status | Residual gap |
|---|---|---|---|---|---|---|---|---|
| `prompts/agents/season_planner.md` | `legacy_prompt` + `active_prompt` | season planning surface, season-scope framing | prompt | `season_planner.md` | `prompt-owned` | `all defined` | `complete` | none after role-authority normalization |
| `prompts/agents/phase_architect.md` | `legacy_prompt` + `active_prompt` | phase planning surface, phase-scope framing | prompt | `phase_architect.md` | `prompt-owned` | `all defined` | `complete` | none after role-authority normalization |
| `prompts/agents/week_planner.md` | `legacy_prompt` + `active_prompt` | week planning surface and finalize framing | prompt | `week_planner.md` | `prompt-owned` | `all defined` | `complete` | none after template normalization |
| `prompts/agents/season_scenario.md` | `legacy_prompt` + `active_prompt` | season scenario generation/selection surface | prompt | `season_scenario.md` | `prompt-owned` | `all defined` | `complete` | none after advisory-authority normalization |
| `prompts/agents/performance_analysis.md` | `legacy_prompt` + `active_prompt` | completed-week advisory analysis surface | prompt | `performance_analysis.md` | `prompt-owned` | `all defined` | `complete` | none after evidence-boundary normalization |

### Active prompt inventory and status

#### Surface / root prompts

| Active role | Prompt | Authority type | Status | Current residual gap |
|---|---|---|---|---|
| `season_planner` | `season_planner.md` | `prompt-owned` | `complete` | none after role-authority normalization |
| `phase_architect` | `phase_architect.md` | `prompt-owned` | `complete` | none after role-authority normalization |
| `week_planner` | `week_planner.md` | `prompt-owned` | `complete` | none after template normalization |
| `season_scenario` | `season_scenario.md` | `prompt-owned` | `complete` | none after advisory-authority normalization |
| `performance_analysis` | `performance_analysis.md` | `prompt-owned` | `complete` | none after evidence-boundary normalization |

#### Manager / finalizer / review / writer prompts

| Active role | Prompt | Authority type | Status | Residual gap before hardening |
|---|---|---|---|---|
| `season_plan_manager` | `season_plan_manager.md` | `prompt-owned` | `complete` | none after template normalization |
| `season_review_manager` | `season_review_manager.md` | `review-gate only` | `complete` | none after explicit gate normalization |
| `phase_bundle_manager` | `phase_bundle_manager.md` | `prompt-owned` | `complete` | none after finalize-ownership normalization |
| `phase_review_manager` | `phase_review_manager.md` | `review-gate only` | `complete` | none after explicit gate normalization |
| `week_review_manager` | `week_review_manager.md` | `review-gate only` | `complete` | none after explicit gate normalization |
| `season_artifact_writer` | `season_artifact_writer.md` | `writer-only` | `complete` | none after writer-scope normalization |
| `phase_artifact_writer` | `phase_artifact_writer.md` | `writer-only` | `complete` | none after writer-scope normalization |
| `week_artifact_writer` | `week_artifact_writer.md` | `writer-only` | `complete` | none after writer-scope normalization |

#### Planning specialists

| Active role | Prompt | Authority type | Status | Residual gap before hardening |
|---|---|---|---|---|
| `load_governance_specialist` | `load_governance_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |
| `guardrails_specialist` | `guardrails_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |
| `scenario_interpreter` | `scenario_interpreter.md` | `prompt-owned` | `complete` | none after advisory-authority normalization |
| `macrocycle_architect` | `macrocycle_architect.md` | `prompt-owned` | `complete` | none after template normalization |
| `constraint_specialist` | `constraint_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |
| `historical_context_specialist` | `historical_context_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |
| `kpi_guidance_specialist` | `kpi_guidance_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |
| `structure_specialist` | `structure_specialist.md` | `prompt-owned` | `complete` | none after structural-authority normalization |
| `cadence_recovery_integrator` | `cadence_recovery_integrator.md` | `prompt-owned` | `complete` | none after cadence/recovery normalization |
| `intensity_distribution_specialist` | `intensity_distribution_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |
| `preview_synthesizer` | `preview_synthesizer.md` | `prompt-owned` | `complete` | none after preview-boundary normalization |
| `week_context_specialist` | `week_context_specialist.md` | `prompt-owned` | `complete` | none after context-authority normalization |
| `week_context_analyst` | `week_context_analyst.md` | `prompt-owned` | `complete` | none after injected-source normalization |
| `week_revision_specialist` | `week_revision_specialist.md` | `prompt-owned` | `complete` | none after bounded-revision normalization |
| `week_workout_authoring_specialist` | `week_workout_authoring_specialist.md` | `prompt-owned` | `complete` | none after writer-boundary and authority normalization |
| `week_recommendation_specialist` | `week_recommendation_specialist.md` | `prompt-owned` | `complete` | none after injected-source and non-scope normalization |

#### Secondary / non-planning or lower-priority roles

| Active role | Prompt | Authority type | Status | Residual gap before hardening |
|---|---|---|---|---|
| `performance_analysis_specialist` | `performance_analysis_specialist.md` | `prompt-owned` | `complete` | none after analysis-boundary normalization |
| `des_review_manager` | `des_review_manager.md` | `review-gate only` | `complete` | none after review-boundary normalization |
| `workout_editor` | `workout_editor.md` | `prompt-owned` | `complete` | none after bounded-edit normalization |
| `pending_resolution_specialist` | `pending_resolution_specialist.md` | `prompt-owned` | `complete` | none after injected-authority normalization |
| `coach` | `coach.md` | `prompt-owned` | `complete` | none after orchestration-boundary normalization |
| `conversation_manager` | `conversation_manager.md` | `prompt-owned` | `complete` | none after routing/finalization normalization |

### Prompt migration conclusions

- The repo now has a materially better **policy/principle** migration baseline than before.
- The **prompt layer** is now materially more normalized across active Season/Phase/Week planning roles.
- The remaining prompt debt after this pass is limited to future style tightening or new roles; the currently active Season/Phase/Week planning prompts audited here have been normalized to the new authority template.

### Required prompt migration order

1. root / surface prompts
2. manager / finalizer / review prompts
3. prioritized planning specialists
4. secondary prompts

This order is required because prompt authority must be fixed upstream before specialist and secondary prompt polishing can be considered complete.
