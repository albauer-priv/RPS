---
Version: 1.1
Status: Updated
Last-Updated: 2026-05-20
Owner: Planning
---
# FEAT_protocol_driven_workout_engine

* **ID:** FEAT_protocol_driven_workout_engine
* **Status:** Implemented
* **Owner/Area:** Planning / Workouts
* **Last-Updated:** 2026-05-20
* **Related:** FEAT_deterministic_workout_generator_first, FEAT_deterministic_week_engine_configurable_families

---

## 1) Context / Problem

**Current behavior**

* The deterministic Week engine already replaces Week crews, but workout generation still depends on coarse family/profile renderers such as `duration_first_endurance`, `controlled_tempo_expansion`, and `tiz_first_sweet_spot`.
* Quality workouts are rendered from fixed code templates with limited progression semantics.
* Day-duration / kJ reconciliation can only stretch the overall workout duration; it does not reason about primary protocol versus Z2 add-on composition.

**Problem**

* The current renderer cannot express protocol-level progression such as `4x10 -> 4x12 -> 4x15 -> 5x12`.
* It cannot internally model set-based VO2 structures such as `3 x (10 x 40/20)` with per-set progression while still exporting flat Intervals text.
* Recovery, cadence, and target semantics are not consistently first-class for all work and recovery blocks.

**Constraints**

* Intervals export remains bound by the local EBNF and RPS subset: no nested loops, no freeride, canonical section order, every step with cadence.
* `workout_policy.md` and `principles_durability_first_cycling.md` remain the normative sources for progression and domain behavior.
* `WEEK_PLAN` persistence must remain schema-compatible.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Replace family-first rendering with protocol-driven deterministic workout generation.
* [x] Support protocol constraints and progression rules for Sweet Spot, Tempo, K3, VO2 microbursts, long VO2 intervals, ramps, long steady work, and fatigue-finish structures.
* [x] Allow optional Z2 add-ons to hit day duration / kJ targets without changing the primary workout intent.
* [x] Keep all week workout-producing paths on the same generator path.

**Non-Goals**

* [x] Add `freeride` support.
* [x] Replace Season or Phase planning logic.

---

## 3) Proposed Behavior

**User/System behavior**

* Week planning selects a protocol definition instead of only a workout family.
* The Week engine computes a workout blueprint with protocol metadata, progression parameters, target TiZ, and optional add-on policy.
* The workout renderer solves a concrete protocol instance from those rules and exports canonical Intervals subset text.
* When a prior-week `WEEK_PLAN` exists, the Week engine infers the last protocol structure from canonical workout text and reuses that progression reference while solving the next legal step.
* Preview/replan and coach-triggered week regeneration use the same solver and renderer as the main week path.

**UI impact**

* UI affected: No direct new UI surface.
* Existing Week / Coach / Workout Editor flows continue to consume `WEEK_PLAN`.

**Non-UI behavior**

* Components involved: Week engine, workout generator, workout validator, coach preview/apply orchestration.
* Contracts touched: `WeekWorkoutBlueprintModel`, internal workout protocol config, deterministic week engine runtime outputs.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/week_engine.py`: load protocol config, select protocols, attach protocol metadata to workout blueprints, set TiZ/add-on targets.
* `src/rps/workouts/generator.py`: replace family renderer with protocol solver and deterministic add-on composition.
* `src/rps/workouts/structured.py`: preserve canonical section rendering; internal richer protocol semantics stay code-owned and render into the flat subset.
* `src/rps/workouts/progression_history.py`: infer prior protocol signatures from persisted week-plan workout text.
* `config/planning/week_workout_protocols.yaml`: protocol registry, selection policy, constraints, and progression rules.

**Data flow**

* Inputs: week calendar context, load method context, protocol config, prior-week progression history, bounded adjustment intent.
* Processing: day-role allocation -> protocol selection -> prior signature matching -> load reconciliation -> protocol solving -> canonical export rendering.
* Outputs: `WeekPlanBundle`, persisted `WEEK_PLAN`, preview documents, bounded recompute results.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: `WEEK_PLAN` content generation only; schema envelope unchanged.
* Validator implications: generated workouts must remain valid under `intervals_workout_ebnf.md` and `workout_syntax_and_validation.md`.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for persisted `WEEK_PLAN`.
* Breaking changes: internal week blueprint semantics expand with protocol metadata.
* Fallback behavior: legacy text-edit path still canonicalizes user-provided text; new generation never authors free text.

**Conflicts with ADRs / Principles**

* Potential conflicts: none with the deterministic Week-engine cutover; this extends it.
* Resolution: see ADR-052.

**Impacted areas**

* UI: none directly.
* Pipeline/data: week generation, preview/replan, coach bounded recompute.
* Renderer: protocol solver replaces family/profile templates.
* Workspace/run-store: unchanged envelope persistence.
* Validation/tooling: expanded solver/protocol tests and exportability checks.
* Deployment/config: new protocol YAML config.

**Required refactoring**

* Replace family-selection loader with protocol-selection loader.
* Migrate generator render-spec fields from family/profile-first to protocol-first.
* Extend week blueprint models with protocol metadata.

---

## 6) Options & Recommendation

### Option A — Extend current family renderer with more conditionals

**Summary**

* Keep the family registry and add progressively more hardcoded render branches.

**Pros**

* Smaller short-term patch surface.

**Cons**

* Protocol progression, set redistribution, and add-on composition remain implicit and brittle.

### Option B — Protocol-driven workout engine

**Summary**

* Model training structure as protocols with constraints and progression semantics, then solve and render deterministically.

**Pros**

* Matches local policy sources.
* Separates progression logic from export format.
* Scales to Zwift-like public workout structures without allowing freeride.

**Cons**

* Larger refactor across engine + generator + tests.

### Recommendation

* Choose: Option B
* Rationale: protocol rules are already implicit in the repo’s planning policy; making them explicit removes the remaining fragile render heuristics.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Week workout generation is protocol-driven, not family-template-driven.
* [x] Quality workouts can solve TiZ progression and optional Z2 add-ons deterministically.
* [ ] Policy-defined progression order is explicitly operationalized from prior protocol state, not only approximated by generic TiZ fitting.
* [x] Export remains subset-valid and contains no nested loops or freeride.
* [x] Preview/replan and bounded week regeneration use the same generator path as main week creation.
* [x] Validation passes: `py_compile`, lint, typecheck, targeted week/workout tests.

---

## 8) Migration / Rollout

**Migration strategy**

* Introduce protocol config and expanded blueprint semantics while keeping `WEEK_PLAN` envelope stable.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert to the prior deterministic family renderer if protocol config or solver fails.

---

## 9) Risks & Failure Modes

* Failure mode: protocol config defines impossible TiZ / set constraints.
  * Detection: config loader or solver raises deterministic validation errors.
  * Safe behavior: fail week generation with a blocking deterministic result.
  * Recovery: correct config and rerun.

* Failure mode: protocol solver generates invalid subset text.
  * Detection: export validator/tests fail.
  * Safe behavior: reject persistence.
  * Recovery: adjust renderer or protocol constraints.

---

## 10) Observability / Logging

**New/changed events**

* Week engine logs protocol selection, TiZ target choice, add-on application, and solver blocking reasons.

**Diagnostics**

* Week flow logs, deterministic review result, export validator messages.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — note protocol-driven week workout generation.
* [x] This feature doc — implemented design and scope.

---

## 12) Link Map (no duplication; links only)

* [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
* [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
* [doc/architecture/system_architecture.md](/Users/alexander/RPS/doc/architecture/system_architecture.md)
* [specs/knowledge/_shared/sources/policies/workout_policy.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/policies/workout_policy.md)
* [specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md)
* [specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md)
* [specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md](/Users/alexander/RPS/specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md)
