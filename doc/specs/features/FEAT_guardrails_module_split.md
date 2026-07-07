---
Version: 1.1
Status: In Progress
Last-Updated: 2026-07-07
Owner: Agent Runtime
---
# FEAT: CrewAI Guardrails Module Split

* **ID:** FEAT_guardrails_module_split
* **Status:** In Progress (Phase 1 done)
* **Owner/Area:** Agent Runtime
* **Last-Updated:** 2026-07-07
* **Related:** `doc/adr/ADR-061-crewai-guardrails-module-split.md`, `src/rps/crewai_runtime/guardrails.py`, `config/crewai/task_policies.yaml`, `src/rps/agents/crewai_bundle_normalization.py`, `src/rps/agents/crewai_context_blocks.py`, `src/rps/agents/crewai_output_extraction.py`, `src/rps/agents/crewai_task_execution.py`, `src/rps/agents/crewai_validation.py`, `src/rps/orchestrator/plan_week.py`, `src/rps/orchestrator/season_flow.py`, `src/rps/tools/workspace_read_tools.py`, `src/rps/tools/workspace_tools.py`

---

## 1) Context / Problem

**Current behavior**

* `src/rps/crewai_runtime/guardrails.py` is 2346 lines, mixing the `ContextVar`-based runtime-context mechanism, generic/schema output validators, season/phase/week domain validators (enforcing ADR-035 authority boundaries), cross-domain payload-coercion/diagnostics utilities, and the `REGISTRY` string-resolution layer wired into `config/crewai/task_policies.yaml`.

**Problem**

* Low cohesion: changes to one domain's validation rules (e.g. week corridor/capacity checks) routinely sit in the same file/diff as unrelated season or generic validator changes.
* 8 production consumers and 13 test files import from this single file, all sharing one blast radius for any change.

**Constraints**

* No behavior change: same functions, same runtime behavior, only import paths for internal-only names move.
* Authority boundaries (ADR-035) and the config-driven guardrail-name resolution contract must not change — `config/crewai/task_policies.yaml`'s guardrail name strings must resolve identically before and after every phase.
* No re-export shim left behind — external callers update their imports directly, per this repo's established convention (same as ADR-059/060 and the `intervals_data.py` split).
* Staged, incremental delivery — one group per phase, same discipline as the `crewai_backend.py` and `intervals_data.py` split series.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Phase 1: extract the context core (`_GUARDRAIL_CONTEXT`, `guardrail_runtime_context`, `current_guardrail_runtime_context`, shared type aliases) into `src/rps/crewai_runtime/guardrails_context.py`.
* [x] Phase 2: extract generic output validators (6 functions) into `src/rps/crewai_runtime/guardrails_generic.py`, and schema/envelope validators (3 functions) into `src/rps/crewai_runtime/guardrails_schema.py`. (Also pulled the payload-coercion helpers forward into `guardrails_utilities.py` early — see Phase 3.)
* [x] Phase 3: extract the rest of the cross-domain utilities (diagnostics, telemetry wrapper, context accessors) into `src/rps/crewai_runtime/guardrails_utilities.py` (payload coercion already moved there in Phase 2, to avoid a circular import).
* [x] Phase 4: extract phase validators (7 functions + ISO-week helpers) into `src/rps/crewai_runtime/guardrails_phase.py`.
* [x] Phase 5: extract week validators (14 functions + workout-domain-analysis helpers) into `src/rps/crewai_runtime/guardrails_week.py`.
* [x] Phase 6 (largest, highest risk): extract season validators (12 functions, including the 440-line `season_scenarios_profile_quality`) into `src/rps/crewai_runtime/guardrails_season.py`.
* [ ] Phase 7 (final): extract the registry (`REGISTRY`, `resolve_guardrail`, `resolve_task_policy`, `build_task_guardrail_kwargs`, `TaskExecutionPolicy`) into `src/rps/crewai_runtime/guardrails_registry.py`, importing every domain module's callables. Confirm every guardrail name in `config/crewai/task_policies.yaml` still resolves.

**Non-Goals**

* [ ] Redesigning the `ContextVar` mechanism or the `REGISTRY` string-resolution pattern — ADR-061 found neither blocks a same-behavior split.
* [ ] Any change to Season/Phase/Week authority boundaries (ADR-035), persisted artifact schemas, or `config/crewai/task_policies.yaml`'s guardrail name strings.
* [ ] Splitting the 13 test files that import guardrail names directly — they only need their import statements updated per phase, not restructuring.

---

## 3) Proposed Behavior

**User/System behavior**

* No end-user or runtime behavior change. Pure internal code-organization refactor.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: `src/rps/crewai_runtime/guardrails.py` and the 7 new modules listed under Goals.
* Contracts touched: internal Python import paths only; no artifact schema, orchestration, authority, or config contract changes.

---

## 4) Implementation Analysis

**Components / Modules**

* `guardrails.py`: loses each group's functions per phase; imports back whatever the not-yet-moved remainder still calls, until Phase 7 when it is expected to be fully retired (matching `crewai_backend.py`'s outcome after ADR-059/060).
* New modules per phase, per the group breakdown in ADR-061's Context section.
* 8 production consumers and 13 test files: each phase updates only the import statements for names that moved in that phase.

**Data flow**

* No data-flow change. Validator call graphs are identical; only which module owns which function body changes. The `REGISTRY` dict (moved in Phase 7) continues to map the same string names to the same callables.

**Schema / Artefacts**

* None. No artifact, schema, or contract changes in any phase.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for production code within each phase (per-phase import updates land in the same commit as the move).
* Breaking changes: none — every consumer's import path is updated in lockstep with the phase that moves its target name.
* Fallback behavior: n/a.

**Conflicts with ADRs / Principles**

* None. Governed directly by ADR-061.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: the 13 test files' import statements, updated per phase.
* Deployment/config: none — `config/crewai/task_policies.yaml`'s guardrail name strings are unaffected throughout; only Phase 7 needs to re-verify they still resolve.

**Required refactoring**

* All 7 phases, executed staged as listed under Goals.

---

## 6) Options & Recommendation

### Option A (recommended) — Staged extraction, context/utilities first, season last

**Summary:** Extract the context core and cross-domain utilities before any domain group (so phase/week/season modules have a stable import target), extract domain groups smallest-to-largest, extract the registry last since it depends on everything.

**Pros:** Matches this repo's proven staged-refactor discipline (ADR-059/060, `intervals_data.py`); each phase is independently reviewable; front-loading the utilities layer avoids forward-references during the domain-group phases; the highest-risk group (season) lands once the pattern is well-proven across 6 prior phases in this same effort.

**Cons:** Seven separate commits instead of one; the file stays large until Phase 6 lands.

**Risk:** Low per phase, given ADR-061's audit found no circular dependencies between any pair of groups.

### Option B — Big-bang full split in one pass

**Summary:** Extract all 8 groups in one commit.

**Pros:** File reaches its final state immediately.

**Cons:** A single large diff touching authority-adjacent validator code (ADR-035) is exactly the kind of change this repo's rules require extra scrutiny for; a mistake in one group's extraction is harder to isolate and revert.

**Risk:** High — a season-validator regression (the largest, most complex group) could ship alongside six other groups' changes, making root-causing a test failure much slower.

### Recommendation

* Choose: Option A.
* Rationale: proven pattern in this repo (ADR-059/060, `intervals_data.py`'s 6-phase split all landed cleanly using this discipline), keeps each change independently verifiable, and orders phases to minimize forward-references and risk exposure.

---

## 6a) Implementation Readiness Review

* [x] Scope completeness: all 8 groups named with function counts and line estimates (see ADR-061's audit).
* [x] Decision completeness: ADR-061 made the phase-ordering and no-exceptions decision explicitly.
* [x] Architecture conformity: confirmed against ADR-035 (authority boundaries) — no change; config-driven guardrail resolution contract preserved throughout.
* [x] Execution readiness: exact function names and group boundaries traced via `grep` before this spec was written (see ADR-061's Context section).

---

## 7) Acceptance Criteria (Definition of Done, all phases)

* [ ] Each of the 7 new modules exists with its assigned group's functions/constants moved verbatim, no logic changes.
* [ ] `guardrails.py` imports back only what its current residual still calls; by Phase 7 it is either fully retired or reduced to a near-empty shell (decided during Phase 7 based on what remains).
* [ ] All 8 production consumers' and 13 test files' import statements updated to the new module paths, per the phase that moved their target names.
* [ ] `config/crewai/task_policies.yaml`'s guardrail name strings all resolve unchanged after Phase 7 (verified via a script iterating the YAML's guardrail lists against `REGISTRY.keys()`).
* [ ] Validation passes every phase: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/`.
* [ ] No regressions in: Season/Phase/Week guardrail enforcement, CrewAI task guardrail wiring, artifact schema validation.

## 7a) Acceptance Criteria (Definition of Done, Phase 1)

* [x] `src/rps/crewai_runtime/guardrails_context.py` exists with `_GUARDRAIL_CONTEXT`, `guardrail_runtime_context`, `current_guardrail_runtime_context`, and the `JsonMap`/`GuardrailResult`/`GuardrailFn` type aliases, moved verbatim.
* [x] `guardrails.py` imports back `_GUARDRAIL_CONTEXT`, `GuardrailFn`, `GuardrailResult`, `JsonMap`, and `current_guardrail_runtime_context` for its own internal use — a follow-up `ruff` pass caught 8 direct `_GUARDRAIL_CONTEXT.get(...)` call sites (in addition to the two accessor functions) that an initial import list missed.
* [x] 7 production files (`src/rps/tools/workspace_read_tools.py`, `src/rps/tools/workspace_tools.py`, `src/rps/agents/crewai_context_blocks.py`, `src/rps/agents/crewai_bundle_normalization.py`, `src/rps/orchestrator/plan_week.py`, `src/rps/orchestrator/season_flow.py`, `src/rps/agents/crewai_task_execution.py`) updated to import `guardrail_runtime_context`/`current_guardrail_runtime_context` from `guardrails_context` directly — no re-export shim left in `guardrails.py`.
* [x] 11 test files updated the same way (`test_crewai_review_readiness_and_load_context.py`, `test_crewai_scenario_profile_quality.py`, `test_crewai_season_semantics_normalization.py`, `test_crewai_output_extraction_and_audit.py`, `test_workout_generator.py`, `test_crewai_phase_week_review_guardrails.py`, `test_crewai_week_planning_guardrails.py`, `test_crewai_config_and_builders.py`, `test_crewai_phase_writer_guardrails.py`, `test_crewai_season_phase_bundle_normalization.py`, `test_workspace.py`).
* [x] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/` (623/623).

## 7b) Acceptance Criteria (Definition of Done, Phase 2)

* [x] `src/rps/crewai_runtime/guardrails_generic.py` exists with the 6 generic output-shape validators, moved verbatim.
* [x] `src/rps/crewai_runtime/guardrails_schema.py` exists with `artifact_envelope_basic`, `artifact_meta_data_present`, `artifact_schema_valid`, and the `_schema_registry()` cache helper (with its own `ROOT`/`SCHEMA_DIR` constants), moved verbatim.
* [x] `src/rps/crewai_runtime/guardrails_utilities.py` created early (not originally scheduled until Phase 3) with `_coerce_payload`/`_coerce_mapping`, once the audit found both new Phase 2 modules needed them and importing from `guardrails.py` would create a cycle with `REGISTRY` importing the moved validators back — same resolution pattern as `intervals_schema_utils.py` in the `intervals_data.py` split.
* [x] `guardrails.py` imports the 9 moved validator functions back (for `REGISTRY`, not yet extracted) and `_coerce_payload`/`_coerce_mapping` back (used by ~50 call sites in validators not yet moved). Dead `ROOT`/`SCHEMA_DIR` constants (only consumer was `_schema_registry()`, which moved) deleted from the residual rather than kept as an unused duplicate.
* [x] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/` (623/623).

## 7c) Acceptance Criteria (Definition of Done, Phase 3)

* [x] The remaining 22 cross-domain utility functions/constants moved into `src/rps/crewai_runtime/guardrails_utilities.py` (alongside the payload-coercion helpers from Phase 2): `_as_map`/`_as_list`/`_as_float`/`_string_list`, `_CADENCE_RATIONALE_FIELDS`/`_scenario_rationale_text`/`_contains_any`, `_future_event_runtime_context`, the 5 runtime-context accessors (`_active_weekly_band_from_context`, `_week_calendar_context`, `_phase_execution_context`, `_season_phase_slot_context`, `_season_phase_load_context`), `_loaded_input_version_key`, `_phase_guardrails_weekly_bands`, `canonicalize_season_bundle_shape_aliases`, `decode_json_object_from_text`, `_season_finalize_candidate_mapping`, `normalize_artifact_candidate_for_task_guardrails`, the 4 diagnostics helpers, and `_with_guardrail_telemetry`.
* [x] Used an AST-based extraction script (`ast.parse` to find each name's exact `lineno`/`end_lineno`) instead of manual line-range `sed`, since these 22 names are physically interleaved throughout the file (unlike Phases 1-2's contiguous blocks) — avoids the boundary mistakes self-caught during the `intervals_data.py` split's interleaved-content phases.
* [x] `guardrails.py` imports all 22 names back for its own internal use (phase/week/season validators not yet moved call them extensively).
* [x] Found and fixed 1 external production consumer the ADR's audit missed: `src/rps/agents/crewai_output_extraction.py` imported `canonicalize_season_bundle_shape_aliases`/`decode_json_object_from_text` directly from `guardrails.py`, repointed to `guardrails_utilities`.
* [x] Found and fixed a subtler break in 2 test files: `tests/test_crewai_config_and_builders.py` and `tests/test_crewai_phase_writer_guardrails.py` monkeypatched `crewai_guardrails.emit_runtime_event`/`crewai_guardrails.normalize_artifact_candidate_for_task_guardrails` (attributes on the `guardrails` module). Since `_with_guardrail_telemetry` now lives in `guardrails_utilities.py` and its internal calls resolve those names in *that* module's own namespace, patching the old module's attribute silently stopped intercepting anything — a class of bug none of the prior phases' `grep`-based consumer audits catch, since the import statement itself doesn't change, only where the bare-name call resolves at runtime. Caught by running the full test suite, not by static analysis. Repointed both monkeypatches and 6 direct-call sites across the 2 files to `guardrails_utilities`.
* [x] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/` (623/623).

## 7d) Acceptance Criteria (Definition of Done, Phase 4)

* [x] `src/rps/crewai_runtime/guardrails_phase.py` exists with the 7 phase-artifact validators (`phase_bundle_integrity`, `phase_bundle_matches_context`, `phase_bundle_review_readiness`, `phase_execution_context_match`, `phase_weeks_match_range`, `phase_week_role_load_coherence`, `phase_s5_band_match`) plus their exclusive helpers (`_extract_expected_s5_band`, `_check_role_band_sequence`, `_iso_week_key`, `_weeks_in_range`, `_coerce_week_key`), moved verbatim via the same AST-based extraction as Phase 3.
* [x] Found a cross-cluster dependency: `_next_iso_week`, physically adjacent to the other ISO-week helpers, is called exclusively by `season_phase_coverage_and_cadence` (a season-group function not scheduled to move until Phase 6) — not by any phase-group function. Left in `guardrails.py`'s residual rather than moved, avoiding both a false grouping and a premature season-group touch.
* [x] `guardrails.py` imports the 7 phase validators back (for `REGISTRY`, not yet extracted).
* [x] Updated the 1 of 8 original production consumers affected (`src/rps/agents/crewai_validation.py`, which imports a mix of phase-group and season/week-group names — split into two import statements) and 3 test files whose import blocks mixed moving and staying names (`tests/test_crewai_season_phase_bundle_normalization.py`, `tests/test_crewai_review_readiness_and_load_context.py`, `tests/test_crewai_week_planning_guardrails.py`).
* [x] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/` (623/623).

## 7e) Acceptance Criteria (Definition of Done, Phase 5)

* [x] `src/rps/crewai_runtime/guardrails_week.py` exists with the 14 week-artifact validators, `week_bundle_domain_legality_messages`, `_normalized_domain_token`, the workout-domain-analysis helpers (`_workout_domain_hits`, `_workout_domain_sources`, `_derived_workout_domains`, `_percent_bounds`), `_target_week_from_context_or_meta`, and `des_diagnostic_only`, moved verbatim via the same AST-based extraction as Phases 3-4.
* [x] Found another cross-cluster dependency, same pattern as Phase 4's `_next_iso_week`: `_repair_season_plan_for_contract_validation`, physically located within this cluster's line range, is called exclusively by `season_phase_load_context_match` (a season-group function not scheduled to move until Phase 6) — left in `guardrails.py`'s residual.
* [x] `guardrails.py` imports the 15 REGISTRY-referenced week validators back (`week_bundle_domain_legality_messages` and the private helpers are not REGISTRY entries and are not called by the residual).
* [x] Updated the 2 of 8 original production consumers affected (`src/rps/agents/crewai_task_execution.py` for `week_bundle_domain_legality_messages`, `src/rps/agents/crewai_validation.py` for `week_bundle_review_readiness`) and 5 test files whose imports referenced moved names (`tests/test_crewai_week_planning_guardrails.py`, `tests/test_crewai_review_readiness_and_load_context.py`, `tests/test_crewai_multi_output_execution.py`, `tests/test_workout_generator.py`, `tests/test_crewai_runtime_config_and_status.py`).
* [x] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/` (623/623).

## 7f) Acceptance Criteria (Definition of Done, Phase 6)

* [x] `src/rps/crewai_runtime/guardrails_season.py` exists with the 12 season-artifact validators, the 11 marker-tuple constants (`_SUPPORTED_SCENARIO_CADENCES`, `_CADENCE_TOKENS`, `_SHARED_CADENCE_MARKERS`, `_DIFFERENTIATION_MARKERS`, `_SCENARIO_SELECTION_POSITIVE_MARKERS`, `_SCENARIO_SELECTION_NEGATIVE_MARKERS`, `_DOMAIN_ELIGIBILITY_MARKERS`, `_DOMAIN_AUTHORIZATION_MARKERS`, `_OBJECTIVE_RESOLUTION_MARKERS`, `_VO2_RATIONALE_MARKER_GROUPS`, `_ARCHETYPE_REQUIRED_MARKER_GROUPS`), and the 2 helpers left behind from Phases 4-5 (`_next_iso_week`, `_repair_season_plan_for_contract_validation`), moved verbatim via the same AST-based extraction as Phases 3-5.
* [x] `guardrails.py`'s residual reduced to purely `TaskExecutionPolicy`, `REGISTRY`, and the 3 resolution functions (`resolve_guardrail`, `resolve_task_policy`, `build_task_guardrail_kwargs`) — 176 lines, from 2346 originally. No cross-cluster dependency found pointing further downstream (Phase 6 was the last domain group).
* [x] Updated the 1 of 8 original production consumers affected (`src/rps/agents/crewai_validation.py`) and 6 test files whose imports referenced moved names (`tests/test_crewai_season_phase_bundle_normalization.py`, `tests/test_crewai_output_extraction_and_audit.py`, `tests/test_crewai_review_readiness_and_load_context.py`, `tests/test_crewai_phase_writer_guardrails.py`, `tests/test_crewai_scenario_profile_quality.py`).
* [x] Validation passes: `py_compile`, `run_lint.sh`, `run_typecheck.sh` (curated + `--full`), full `pytest tests/` (623/623) — confirms `season_scenarios_profile_quality`'s 440-line behavior is unchanged.

---

## 8) Migration / Rollout

**Migration strategy:** None — internal Python import path change only, no data migration.

**Rollout / gating:** None — no feature flag; ships as normal internal refactor commits, one per phase.

---

## 9) Risks & Failure Modes

* Failure mode: a test file's import or monkeypatch still targets `"rps.crewai_runtime.guardrails.<moved_name>"` after a phase's move.

  * Detection: that test fails immediately (`ImportError` or `AttributeError`) since the name no longer exists at the old path.
  * Safe behavior: full test suite run before considering any phase complete.
  * Recovery: update the import/monkeypatch string to the new module path.

* Failure mode: `config/crewai/task_policies.yaml` references a guardrail name that Phase 7's `REGISTRY` no longer resolves (e.g. a domain module's callable wasn't imported into the final registry module).

  * Detection: a script iterating the YAML's guardrail lists against `REGISTRY.keys()`, run as part of Phase 7's validation.
  * Safe behavior: this check runs before Phase 7 is considered complete, not deferred to runtime discovery.
  * Recovery: add the missing import to `guardrails_registry.py`.

---

## 10) Observability / Logging

* No new/changed events. `emit_runtime_event` and the `_with_guardrail_telemetry` wrapper (moved in Phase 3) preserve their existing telemetry event shapes (ADR-040) — only the module that defines them changes.

---

## 11) Documentation Updates

* [x] `doc/adr/ADR-061-crewai-guardrails-module-split.md` — created.
* [x] `doc/adr/README.md` — index entry added.
* [ ] `doc/overview/feature_backlog.md` — updated to reference this spec and record each phase's status as phases land.
* [ ] `doc/architecture/agents.md` — update any guardrail-module references once phases land, if that doc names `guardrails.py` specifically.

---

## 11a) Post-Implementation Audit

* [ ] Spec implemented fully (all 7 phases).
* [ ] Acceptance criteria verified.
* [ ] Verification commands/tests recorded.
* [ ] Residual gaps/deferred items recorded.
* [ ] Recommended next step recorded.

**Implementation report**

* Not yet implemented — this section is filled in as each phase lands, following the same running-log pattern used in `FEAT_crewai_backend_module_split.md`.

---

## 12) Link Map

* ADR: [doc/adr/ADR-061-crewai-guardrails-module-split.md](/doc/adr/ADR-061-crewai-guardrails-module-split.md)
* Backlog: [doc/overview/feature_backlog.md](/doc/overview/feature_backlog.md)

---

## Out of Scope / Deferred

* Redesigning the `ContextVar` mechanism or the `REGISTRY` string-resolution pattern — ADR-061 found this unnecessary for the file split.
* Splitting the 13 consumer test files themselves — only their import statements change, per phase.
