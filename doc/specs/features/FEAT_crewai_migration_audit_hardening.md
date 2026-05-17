---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-16
Owner: Planning Runtime
---
# FEAT: CrewAI Migration Audit Hardening

* **ID:** FEAT_crewai_migration_audit_hardening
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-16
* **Related:** `doc/architecture/crewai_migration_audit.md`, `doc/adr/ADR-048-skills-first-multi-crew-planning-runtime.md`, `doc/adr/ADR-049-single-method-skill-attachment.md`

## 1) Context / Problem

**Current behavior**

* RPS uses CrewAI planning/review/writer stages for Season, Phase, Week, and Report.
* Legacy prompt logic was already migrated into skills, but several high-risk details remained too soft: scenario-selection routing, load-band math, phase S5 semantics, and season cadence review.

**Problem**

* `CREATE_SEASON_SCENARIO_SELECTION` reused the `season_scenarios` task blueprint.
* Phase weekly load bands could still be prompt-shaped instead of code-owned.
* Season cadence and deload rules from the old system needed stronger review contracts.

**Constraints**

* Do not add new Season cycle enum values. `Specificity` and `Taper` remain out of schema.
* Preserve the single-method-skill attachment model.
* Do not reintroduce long monolithic prompts.

## 2) Goals & Non-Goals

**Goals**

* [x] Preserve old Season/Phase/Week load and cadence logic in executable form.
* [x] Give Scenario Selection its own task blueprint.
* [x] Implement deterministic availability capacity and S5 phase-band derivation.
* [x] Implement deterministic per-workout segment-load estimation and prompt calibration.
* [x] Inject code-owned load context into Season, Phase, and Week planning prompts.
* [x] Inject deterministic non-load planning facts so agents do not recompute event horizons, cadence options, phase slots, phase week ranges, week calendars, report evidence versions, or Coach operation boundaries.
* [x] Add guardrails and regression tests for the new behavior.
* [x] Add context-aware daily availability guardrail for Week Plan output.

**Non-Goals**

* [x] No schema extension for `Specificity` or `Taper`.
* [x] No new dependencies.
* [x] No UI redesign.

## 3) Proposed Behavior

**User/System behavior**

* Planning still starts from the same Plan Hub/Season/Week flows.
* Agents receive deterministic `planned_weekly_load_kj` capacity and S5 context.
* Phase and Week outputs are checked against deterministic load semantics before persistence.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: `config/crewai`, `src/rps/agents/crewai_backend.py`, `src/rps/planning/load_bands.py`, `src/rps/planning/workout_load.py`, `src/rps/crewai_runtime/guardrails.py`, planner skills.
* Contracts touched: task blueprint mapping and runtime guardrail policy only; no schema version bump.

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/load_bands.py`: code-owned IF reference, capacity, KPI, progression, and S5 calculations.
* `src/rps/planning/workout_load.py`: code-owned per-workout segment parser and load estimator for the project workout-text subset.
* `src/rps/planning/season_structure.py`: code-owned scenario horizon, cadence option, selected-scenario structure, and phase-slot math.
* `src/rps/planning/deterministic_context.py`: registry-style builders for reusable deterministic prompt blocks and structured test/guardrail payloads.
* `season_flow.py` / `plan_week.py` / `coach.py`: inject deterministic context into Season Scenario, Season Plan, Phase, Week, Report, and Coach prompts.
* `guardrails.py`: semantic checks for scenario selection, season cycles, exact phase week coverage, phase S5 shape, week load corridor/recovery/exportability, and DES advisory-only boundaries.
* `src/rps/planning/week_availability.py`: code-owned validation of Week Plan daily durations against fixed rest days and `availability_table.hours_max`.
* `skills/**/SKILL.md`: align role methods with code-owned load logic and legacy cadence rules.

**Data flow**

* Inputs: Availability, Logistics, Athlete Profile, Zone Model, Wellness, KPI Profile/Selection, Season Plan, Phase Guardrails.
* Processing: compute `IF_ref_load`, availability capacity, optional KPI/progression bands, S5 final bands and trace; derive workout load calibration and post-output workout-load audit estimates; derive event horizon, cadence options, phase slots, phase execution frames, week day matrices, report evidence versions, and Coach operation status.
* Outputs: prompt context blocks and guardrail validation; no new persisted artifact.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: stricter CrewAI task guardrails.

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none intended.
* Fallback behavior: missing FTP or missing domains are surfaced as warnings/errors in deterministic context.

**Conflicts with ADRs / Principles**

* No conflict. This implements ADR-048 and ADR-049 by moving methodology into skills and exact logic into code.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: no new artifact type.
* Validation/tooling: new task guardrails and tests.
* Deployment/config: CrewAI task policy and task blueprint changes.

## 6) Options & Recommendation

### Option A — Code-owned S5 and prompt injection

**Summary**

* Compute deterministic load context in code and pass it to agents.

**Pros**

* Reproducible, testable, preserves old S5 logic.

**Cons**

* More orchestration complexity.

### Option B — Prompt-only S5 instructions

**Summary**

* Keep S5 in skill prose only.

**Pros**

* Less code.

**Cons**

* Not sufficiently reproducible for load-band authority.

### Recommendation

* Choose: Option A.
* Rationale: load bands are governance logic and must be deterministic.

## 7) Acceptance Criteria

* [x] Scenario Selection has its own CrewAI task blueprint.
* [x] Availability capacity is code-owned.
* [x] S5 band derivation is code-owned and tested.
* [x] Workout segment-load estimation is code-owned and tested for the project workout-text subset.
* [x] Season/Phase/Week receive deterministic load context.
* [x] Guardrails are registered and task policies reference them.
* [x] Week Plan daily availability violations are blocked by a CrewAI guardrail.
* [ ] Full validation passes before release.

## 8) Migration / Rollout

**Migration strategy**

* No stored artifact migration.

**Rollout / gating**

* Uses existing CrewAI runtime configuration.
* Safe rollback: remove task policy overrides and load-context injection.

## 9) Risks & Failure Modes

* Failure mode: missing FTP.
  * Detection: `missing_or_invalid_ftp` warning or S5 error.
  * Safe behavior: agent must not invent load capacity.
* Failure mode: phase output does not include S5 wording.
  * Detection: guardrail validates numeric bands; deterministic prompt instructs exact use.
  * Safe behavior: retry or fail before persistence.

## 10) Observability / Logging

**New/changed events**

* No new run-store event type.

**Diagnostics**

* Inspect planner prompt context in run traces and CrewAI events.
* Inspect task guardrail errors in run history.

## 11) Documentation Updates

* [x] `doc/architecture/crewai_migration_audit.md` — migration audit and mapping.
* [x] `doc/architecture/agents.md` — Scenario Selection task consistency.
* [x] `doc/architecture/crewai_flows.md` — deterministic load context note.
* [x] `doc/architecture/skills_source_migration_audit.md` — load/S5 disposition.
* [x] `CHANGELOG.md` — user-visible runtime architecture changes.

## 12) Link Map

* Architecture: `doc/architecture/agents.md`
* CrewAI flows: `doc/architecture/crewai_flows.md`
* Skill attachment: `doc/architecture/crewai_skills_attachment.md`
* Workspace: `doc/architecture/workspace.md`
* Schema versioning: `doc/architecture/schema_versioning.md`
* ADRs: `doc/adr/ADR-048-skills-first-multi-crew-planning-runtime.md`, `doc/adr/ADR-049-single-method-skill-attachment.md`
