---
Version: 1.0
Status: Accepted
Last-Updated: 2026-07-07
Owner: Agent Runtime
---
# ADR-061: CrewAI Guardrails Module Split

## Context

`src/rps/crewai_runtime/guardrails.py` is 2346 lines and ~85 top-level names, mixing several distinct concerns: the `ContextVar`-based runtime-context threading mechanism used to bind per-task-run context, generic CrewAI output-shape validators, artifact-envelope/schema validators, season/phase/week domain validators enforcing ADR-035 authority boundaries, cross-domain payload-coercion and diagnostics utilities, and a `REGISTRY`/string-resolution layer wired directly into `config/crewai/task_policies.yaml`.

Unlike a purely internal refactor, this module owns cross-cutting mechanisms rather than merely consuming them: it defines the `ContextVar` itself (`_GUARDRAIL_CONTEXT`) and the `guardrail_runtime_context()`/`current_guardrail_runtime_context()` API that `crewai_task_execution.py`, `crewai_context_blocks.py`, and others bind against; and it defines the `REGISTRY` name→callable mapping that CrewAI task construction resolves guardrail names against at runtime, driven by string keys in `config/crewai/task_policies.yaml`. Per `.clinerules.d/10-docs-specs-adr.md`'s "Module and file size / responsibility" trigger, touching orchestration/authority flow and cross-cutting contracts requires an ADR before a split — the same category as `crewai_backend.py` (ADR-059), not the no-ADR-needed category that applied to `intervals_data.py`'s pure internal reorganization.

An audit of the file (structural map + full external-consumer trace) found:

- **8 production consumers** importing guardrail names directly: `src/rps/agents/crewai_bundle_normalization.py`, `src/rps/agents/crewai_context_blocks.py`, `src/rps/agents/crewai_output_extraction.py`, `src/rps/agents/crewai_task_execution.py`, `src/rps/agents/crewai_validation.py`, `src/rps/orchestrator/plan_week.py`, `src/rps/orchestrator/season_flow.py`, `src/rps/tools/workspace_read_tools.py`, `src/rps/tools/workspace_tools.py`.
- **13 test files** importing or monkeypatching guardrail names directly.
- `config/crewai/task_policies.yaml` references guardrails purely by string name, resolved at runtime through `REGISTRY`/`resolve_guardrail()` — no direct Python import path is baked into config, so moving a guardrail function between modules requires no config change as long as `REGISTRY` continues to import every domain module's callables.
- The file splits into 8 functional groups by dependency analysis, each with no circular dependency on any group scheduled for a later phase:
  - **Context core** (~35 lines): `_GUARDRAIL_CONTEXT`, `guardrail_runtime_context()`, `current_guardrail_runtime_context()`, and the shared type aliases `JsonMap`/`GuardrailResult`/`GuardrailFn`. Everything else in the file either calls into this or is called by code that does; extracting it first avoids touching it again in later phases.
  - **Generic output validators** (6 functions, ~90 lines): `typed_output_present`, `coaching_recommendation_text_present`, `adjustment_intent_has_preview_message`, `coach_preview_summary_complete`, `pending_resolution_summary_present`, `audit_lists_are_lists`. Self-contained aside from shared payload-coercion helpers (see Utilities group).
  - **Schema/envelope validators** (3 functions, ~65 lines): `artifact_envelope_basic`, `artifact_meta_data_present`, `artifact_schema_valid` (plus a small `_schema_registry()` cache helper). Depend only on `rps.workspace.schema_registry`.
  - **Phase validators** (7 functions + ISO-week helpers, ~230 lines): `phase_bundle_integrity`, `phase_bundle_matches_context`, `phase_bundle_review_readiness`, `phase_execution_context_match`, `phase_weeks_match_range`, `phase_week_role_load_coherence`, `phase_s5_band_match`, plus `_extract_expected_s5_band`, `_check_role_band_sequence`, `_iso_week_key`, `_next_iso_week`, `_weeks_in_range`, `_coerce_week_key`.
  - **Week validators** (14 functions, ~500 lines, the largest domain group after season): `week_bundle_integrity`, `week_bundle_matches_context`, `week_bundle_domain_legality_messages`, `week_bundle_domain_legality_check`, `week_bundle_review_readiness`, `week_corridor_and_capacity_check`, `week_active_corridor_match`, `week_recovery_day_load_check`, `week_agenda_shape_and_calendar_check`, `week_daily_availability_check`, `week_phase_role_alignment_check`, `week_contract_context_match`, `week_exportability_check`, `week_workout_structure_policy_check`, plus `review_decision_integrity`, `des_diagnostic_only`, and workout-domain-analysis helpers (`_normalized_domain_token`, `_workout_domain_hits`, `_workout_domain_sources`, `_derived_workout_domains`, `_percent_bounds`). One cross-domain call found: `week_phase_role_alignment_check` calls into the workout-domain-analysis helpers, which stay co-located in this same module — no cross-module dependency results.
  - **Season validators** (12 functions, ~700 lines, the largest and highest-risk group): `season_bundle_integrity`, `season_bundle_audit_slot_integrity`, `season_bundle_matches_contract`, `season_bundle_review_readiness`, `season_writer_bundle_match`, `season_phase_load_feasibility`, `season_scenario_selection_shape`, `season_scenarios_profile_quality` (440 lines alone, with 70+ marker-tuple constants), `season_scenarios_selection_contract_complete`, `season_phase_coverage_and_cadence`, `season_phase_load_context_match`, `season_cycle_ordering`, plus `_repair_season_plan_for_contract_validation` and `_target_week_from_context_or_meta`.
  - **Cross-domain utilities** (~330 lines): payload-coercion helpers (`_coerce_payload`, `_coerce_mapping`, `_as_float`, `_as_map`, `_as_list`, `_string_list`, `_scenario_rationale_text`, `_contains_any`, `_future_event_runtime_context`), `decode_json_object_from_text`, `canonicalize_season_bundle_shape_aliases`, `normalize_artifact_candidate_for_task_guardrails`, diagnostics helpers (`_phase_structure_guardrail_diagnostics`, `_first_contract_mismatch_path`, `_phase_structure_contract_diagnostics`, `_compose_guardrail_failure_reason`), the `_with_guardrail_telemetry` wrapper, `_loaded_input_version_key`, `_phase_guardrails_weekly_bands`, `_season_finalize_candidate_mapping`, and the runtime-context accessor helpers (`_active_weekly_band_from_context`, `_week_calendar_context`, `_phase_execution_context`, `_season_phase_slot_context`, `_season_phase_load_context`). This is the glue layer called by generic validators and all three domain groups; extracting it before the domain groups lets phase/week/season modules import from it cleanly instead of forward-referencing.
  - **Registry** (~100 lines): `REGISTRY`, `resolve_guardrail`, `resolve_task_policy`, `build_task_guardrail_kwargs`, `TaskExecutionPolicy`. Imports every domain module's callables by name to populate `REGISTRY`; must move last since it depends on everything else.

## Decision

Adopt a staged module split, one group per phase, tracked in `doc/specs/features/FEAT_guardrails_module_split.md` — same discipline as ADR-059/060's `crewai_backend.py` split:

1. **Phase 1**: extract the context core into `src/rps/crewai_runtime/guardrails_context.py`.
2. **Phase 2**: extract generic output validators into `src/rps/crewai_runtime/guardrails_generic.py` and schema/envelope validators into `src/rps/crewai_runtime/guardrails_schema.py`.
3. **Phase 3**: extract cross-domain utilities into `src/rps/crewai_runtime/guardrails_utilities.py`, ahead of the domain groups so they have a stable import target instead of forward-referencing code still in `guardrails.py`.
4. **Phase 4**: extract phase validators into `src/rps/crewai_runtime/guardrails_phase.py`.
5. **Phase 5**: extract week validators into `src/rps/crewai_runtime/guardrails_week.py`.
6. **Phase 6 (largest, highest risk)**: extract season validators into `src/rps/crewai_runtime/guardrails_season.py`.
7. **Phase 7 (final)**: extract the registry into `src/rps/crewai_runtime/guardrails_registry.py`, importing every domain module's callables to populate `REGISTRY`. Confirm every guardrail name string in `config/crewai/task_policies.yaml` still resolves via `resolve_guardrail(name)` unchanged — the config only ever referenced guardrails by string name, so no config change is needed, only the Python-side lookup module moves.

For each phase, function/constant bodies move verbatim (no logic changes). Neither the `ContextVar` mechanism nor the `REGISTRY` string-resolution pattern blocks a same-behavior split: a `ContextVar` works identically regardless of which module defines it, as long as every consumer imports the same instance (not a copy) — the same finding ADR-060 made for the closure-based execution flow in `crewai_backend.py`. The `REGISTRY` pattern already resolves guardrails purely by string name against a dict populated from imported callables; centralizing that dict in one final module and importing every domain module's functions into it preserves exact behavior. Where a moved function is still called from code that stays in (or was already extracted from) `guardrails.py`, the caller imports it back by name from the new module — no re-export shim in the other direction, per this repo's existing convention against compatibility-hack layers.

Each phase must:
- Preserve every existing external name and its behavior exactly, verified against the 13 test files that import or monkeypatch guardrail names directly.
- Not change orchestration boundaries, authority boundaries (ADR-035), or the config-driven guardrail resolution contract (`config/crewai/task_policies.yaml` guardrail name strings stay unchanged throughout).
- Land as its own commit with full validation (compile, lint, typecheck curated + full, full test suite), matching the discipline already used for the `crewai_backend.py` and `intervals_data.py` split series.
- Independently re-verify every moved name's exclusive-vs-shared status via direct `grep` before finalizing the phase's diff — this repo's established lesson that automated structural reports need direct verification before trusting them for import-trimming.

`guardrails.py` itself is expected to be fully retired once all 7 phases land (same outcome as `crewai_backend.py` after ADR-059/060), rather than kept as a near-empty shell — confirmed during Phase 7 based on what, if anything, remains.

## Consequences

- Positive: each extracted module has one clear domain responsibility (context threading, generic validation, schema validation, phase/week/season domain rules, cross-domain utilities, registry/resolution), and future changes to one domain's guardrails no longer risk touching unrelated domains in the same file/diff.
- Positive: no behavior change — this is purely an internal reorganization of an existing, already-decoupled validator/registry pattern. No SemVer bump is required for any phase.
- Trade-off: seven small commits are required instead of one large one, matching this repo's established staged-refactor discipline.
- Trade-off: the season-validators phase (Phase 6) carries real risk given its size (~700 lines including a 440-line function with 70+ marker-tuple constants) — it is scheduled last among the domain groups, after the utilities layer it depends on is already stable.
- Risk: `config/crewai/task_policies.yaml`'s guardrail name strings must continue resolving through `REGISTRY` unchanged after Phase 7; the phase's implementation must verify every configured name resolves before considering the phase complete, not just that the Python-level tests pass.

## Exceptions

None. Unlike ADR-059 (which excluded the `crewai_backend.py` orchestration core from its scope), this ADR's audit found no group in `guardrails.py` that requires a design decision before a same-behavior split — every group is either self-contained or has a clean one-way dependency on an already-scheduled earlier phase.
