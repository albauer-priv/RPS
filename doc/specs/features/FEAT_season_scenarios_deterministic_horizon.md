---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-21
Owner: Planning Pipeline
---
# FEAT: Deterministic Season Scenario Horizon & Math

* **ID:** FEAT_season_scenarios_deterministic_horizon
* **Status:** Implemented
* **Owner/Area:** Planning Pipeline
* **Last-Updated:** 2026-04-21
* **Related:** season_scenario, season_planner, PLANNING_EVENTS, SEASON_SCENARIOS

---

## 1) Context / Problem

**Current behavior**

* `season_scenario` generates `SEASON_SCENARIOS` with model-authored `meta.iso_week_range`, `meta.temporal_scope`, `data.planning_horizon_weeks`, and `scenario_guidance.phase_plan_summary`.
* `season_planner` later cross-checks the scenario math against the stored range and stops on mismatches.

**Problem**

* `SEASON_SCENARIOS` can be schema-valid but internally inconsistent.
* Planning horizon can stop before the last A/B/C event in `PLANNING_EVENTS`.
* `phase_plan_summary` can disagree with both `planning_horizon_weeks` and `meta.iso_week_range`.
* This burdens agents with deterministic calendar arithmetic and creates avoidable STOPs.

**Constraints**

* No new dependencies.
* Existing `SEASON_SCENARIOS` and `SEASON_PLAN` schemas remain unchanged.
* Season planning must stay advisory at scenario stage and binding at season-plan stage.
* Prompt/runtime changes must preserve current tool wiring and store semantics.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Derive the season scenario horizon deterministically from `PLANNING_EVENTS`.
* [ ] Normalize `SEASON_SCENARIOS` planning math so `phase_plan_summary` always matches the stored horizon.
* [ ] Reduce agent prompt burden by removing deterministic math instructions that code now owns.
* [ ] Preserve backward compatibility for artefact schema/versioning.

**Non-Goals**

* [ ] Redesign scenario content, labels, or scenario count.
* [ ] Change `SEASON_PLAN` schema or downstream phase/week planning semantics.
* [ ] Introduce a new artefact type for scenario math.

---

## 3) Proposed Behavior

**User/System behavior**

* When `SEASON_SCENARIOS` is generated, the runtime derives the planning horizon from the latest `PLANNING_EVENTS` A/B/C dates.
* The runtime overwrites scenario horizon metadata to match the last relevant event week.
* The runtime recomputes `planning_horizon_weeks`, `phase_count_expected`, `shortening_budget_weeks`, and `phase_plan_summary` from the stored horizon and each scenario's `phase_length_weeks`.
* If the model emits conflicting math, the code normalizes it instead of passing the inconsistency downstream.
* `season_planner` can continue to cross-check, but should no longer hit routine STOPs caused by scenario arithmetic drift.

**UI impact**

* UI affected: No direct UI behavior change.

**Non-UI behavior (if applicable)**

* Components involved: `multi_output_runner`, `season_flow`, `season_scenario` prompt/injection, tests.
* Contracts touched: `SEASON_SCENARIOS`, `PLANNING_EVENTS`, scenario-season contract, mandatory output docs.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/multi_output_runner.py`: normalize scenario horizon and planning math before store.
* `prompts/agents/season_scenario.md`: remove deterministic calendar/math burden from the agent.
* `config/agent_knowledge_injection.yaml`: keep only knowledge required for qualitative scenario generation and output contract.
* `tests/`: add regression coverage for horizon normalization and prompt simplification.

**Data flow**

* Inputs: `PLANNING_EVENTS`, `ATHLETE_PROFILE`, `LOGISTICS`, `KPI_PROFILE`, `AVAILABILITY`.
* Processing:
  * capture loaded `planning_events` document in runner
  * derive inclusive end week from last A/B/C event date
  * normalize `meta.iso_week_range`, `meta.temporal_scope`, `data.planning_horizon_weeks`
  * recompute scenario guidance planning math per scenario
* Outputs: normalized `SEASON_SCENARIOS` envelope persisted to workspace.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: `SEASON_SCENARIOS` content becomes deterministically normalized pre-store.
* Validator implications: schema stays same; content coherence becomes stricter.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None at schema level; scenario content may differ from raw model output.
* Fallback behavior: if no valid A/B/C events exist, keep current STOP behavior.

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified; aligns with existing principle to keep deterministic validation in code.
* Resolution: n/a.

**Impacted areas**

* UI: indirect only; fewer scenario-generation failures.
* Pipeline/data: `SEASON_SCENARIOS` becomes normalized before store.
* Renderer: none.
* Workspace/run-store: no format change; stored values become more reliable.
* Validation/tooling: tests and docs update.
* Deployment/config: no new config.

**Required refactoring**

* Capture loaded `PLANNING_EVENTS` document in runner context.
* Extract season scenario normalization into deterministic helpers.
* Simplify `season_scenario` prompt guidance around planning math and horizon derivation.

---

## 6) Options & Recommendation

### Option A — Normalize in code before store

**Summary**

* Keep the model responsible for qualitative scenario content only; runtime computes horizon and planning math.

**Pros**

* Deterministic.
* Removes repeated agent error surface.
* Preserves existing artifact contract.

**Cons**

* Adds normalization logic in runner.
* Model output and stored output can differ.

**Risk**

* If event parsing is wrong, normalized horizon will still be wrong.

### Option B — Tighten prompt only

**Summary**

* Leave all math with the model and improve instructions.

**Pros**

* Smaller code change.

**Cons**

* Still nondeterministic.
* Does not eliminate current failure class.

### Recommendation

* Choose: Option A.
* Rationale: horizon and planning math are deterministic calendar calculations and should not be delegated to the model.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] `SEASON_SCENARIOS.meta.iso_week_range` is normalized to the week containing the last A/B/C planning event.
* [ ] `SEASON_SCENARIOS.meta.temporal_scope` matches the normalized week range.
* [ ] `SEASON_SCENARIOS.data.planning_horizon_weeks` equals inclusive weeks in `meta.iso_week_range`.
* [ ] For every scenario, `phase_plan_summary` exactly matches `planning_horizon_weeks`.
* [ ] `shortened_phases[].len` is always `< phase_length_weeks`.
* [ ] Prompt/injection content no longer requires the model to compute or preserve authoritative planning math.
* [ ] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`, `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`, targeted pytest.
* [ ] No regressions in season scenario generation / season plan gating tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration.
* Existing old artefacts remain readable; new artefacts are normalized on write.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: revert normalization helper and prompt simplification commits.

---

## 9) Risks & Failure Modes

* Failure mode: `PLANNING_EVENTS` contains invalid or missing A/B/C dates.
  * Detection: normalization helper cannot derive target end week.
  * Safe behavior: preserve current STOP semantics.
  * Recovery: fix `PLANNING_EVENTS` input and rerun.
* Failure mode: prompt still over-constrains or duplicates logic.
  * Detection: tests or logs still show model-driven math mismatch STOPs.
  * Safe behavior: stored artifact remains normalized.
  * Recovery: further simplify prompt/injection text.

---

## 10) Observability / Logging

**New/changed events**

* `Season scenarios horizon normalized`: emitted when code adjusts range/temporal scope/horizon from planning events.
* `Season scenarios phase math normalized`: emitted when code rewrites phase summary fields.

**Diagnostics**

* Check `rps.log` around season scenario generation.
* Inspect stored `SEASON_SCENARIOS` envelope fields.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [ ] `prompts/agents/season_scenario.md` — remove deterministic planning math burden.
* [ ] `specs/knowledge/_shared/sources/specs/mandatory_output_season_scenarios.md` — clarify runtime normalization ownership.
* [ ] `specs/knowledge/_shared/sources/contracts/scenario__season_contract.md` — clarify that scenario math is normalized from horizon.
* [ ] `CHANGELOG.md` — record deterministic season scenario normalization.

## 12) Link Map

* `doc/overview/how_to_plan.md`
* `doc/overview/artefact_flow.md`
* `doc/architecture/system_architecture.md`
* `specs/knowledge/_shared/sources/specs/planning_events_interface_spec.md`
* `specs/knowledge/_shared/sources/specs/season_scenarios_interface_spec.md`
* `specs/knowledge/_shared/sources/contracts/scenario__season_contract.md`
