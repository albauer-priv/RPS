---
Version: 1.1
Status: Superseded
Last-Updated: 2026-05-21
Owner: Planning Semantics
---
# FEAT: Normalized Phase Intent Semantic Backbone

* **ID:** FEAT_phase_intent_semantic_backbone
* **Status:** Superseded
* **Owner/Area:** Planning Semantics
* **Last-Updated:** 2026-05-21
* **Related:** [FEAT_season_plan_semantic_hardening](/doc/specs/features/FEAT_season_plan_semantic_hardening.md), [FEAT_week_plan_semantic_hardening](/doc/specs/features/FEAT_week_plan_semantic_hardening.md), [FEAT_workout_policy_skill_completion](/doc/specs/features/FEAT_workout_policy_skill_completion.md), [FEAT_canonical_phase_taxonomy_migration](/doc/specs/features/FEAT_canonical_phase_taxonomy_migration.md)

---

## 1) Context / Problem

**Superseded note**

* This feature established `phase_intent` as a first-class semantic field.
* It is now superseded by [FEAT_canonical_phase_taxonomy_migration](/doc/specs/features/FEAT_canonical_phase_taxonomy_migration.md), which replaces the repo-specific taxonomy with canonical `phase_type`, `phase_intent`, and `build_subtype`.
* Keep this document as implementation history only; do not use its enum set for new writes.

**Current behavior**

* Season, Phase, Week, and Workout planning already use skill-level semantic terms such as `ceiling_support`, `durability_build`, `b_event_rehearsal`, and `a_event_peak_taper`.
* These semantics are not persisted as normalized contract fields in core artifacts.
* Downstream planners often infer intent indirectly from prose, cycle labels, event windows, and domain lists.

**Problem**

* Season semantics drift because intent is not represented as a first-class contract field.
* Phase and Week planning can remain syntactically valid while semantically drifting away from the intended season model.
* Workout construction can produce valid syntax and legal domains while still selecting the wrong workout family for the intended phase.
* Optional archetypal season logic such as `ceiling_first_durability` cannot be expressed deterministically end to end.

**Constraints**

* Existing cycle enums remain unchanged: `Base`, `Build`, `Peak`, `Transition`.
* No new dependencies.
* Legacy artifacts must remain readable.
* New writes may require normalized semantic fields.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add normalized `season_archetype` at scenario level.
* [x] Add normalized `phase_intent` at season and downstream phase levels.
* [x] Make `phase_intent` drive phase semantics, week planning semantics, and workout-family choice.
* [x] Add deterministic intent derivation for the optional `ceiling_first_durability` archetype.
* [x] Add validation and review checks for intent coherence across artifacts.

**Non-Goals**

* [x] Replace existing cycle enums.
* [x] Add new graded intensity-domain enums such as `rare` or `selective`.
* [x] Guarantee that every season uses early VO2 support; it remains conditional.

---

## 3) Proposed Behavior

**User/System behavior**

* `SEASON_SCENARIOS` may declare `season_archetype = ceiling_first_durability`.
* After selection, deterministic context derives whether early ceiling/VO2 support is actually permitted.
* `SEASON_PLAN` persists `phase_intent` per phase.
* `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW` inherit and preserve `phase_intent`.
* `WEEK_PLAN` reasoning and workout construction use `phase_intent` as a first-class planning signal.
* Review and guardrail layers reject semantic mismatches even when raw syntax and schemas would otherwise pass.

**UI impact**

* UI affected: Yes.
* Season / Phase / Week displays should expose friendly intent labels where useful.

**Non-UI behavior**

* Components involved: season deterministic context, season/phase/week/workout skills, artifact writers, guardrails, contracts, renderers.
* Contracts touched: `SEASON_SCENARIOS`, `SEASON_PLAN`, `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, `PHASE_PREVIEW`.

---

## 4) Implementation Analysis

**Components / Modules**

* `specs/schemas/*`: add `season_archetype` and `phase_intent`.
* `src/rps/workspace/phase_intents.py`: canonical enums and normalization helpers.
* `src/rps/planning/season_structure.py`: selected-scenario archetype context.
* `src/rps/planning/load_bands.py`: deterministic `phase_intent` derivation and weighted season envelope.
* `src/rps/planning/contracts.py`: semantic validation.
* `src/rps/crewai_runtime/guardrails.py`: bundle-level and artifact-level semantic guards.
* `src/rps/planning/deterministic_context.py`: propagate inherited `phase_intent` into phase/week context blocks.
* `skills/season/*`, `skills/phase/*`, `skills/week/*`: planner, review, writer, and workout construction logic.

**Data flow**

* Inputs: selected scenario, deterministic phase slots, load context, event anchors, availability/recovery context.
* Processing: derive archetype context -> derive phase-intent sequence -> persist phase intent -> use it in downstream planning and workout construction.
* Outputs: artifacts with normalized semantic fields and stricter reviews.

**Schema / Artefacts**

* Changed artefacts:
  * `SEASON_SCENARIOS`
  * `SEASON_PLAN`
  * `PHASE_GUARDRAILS`
  * `PHASE_STRUCTURE`
  * `PHASE_PREVIEW`
* Validator implications: new required fields for new writes; legacy reads remain tolerated in runtime helpers.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for reads; stricter for new writes.
* Breaking changes: artifact producers must emit new normalized fields.
* Fallback behavior: readers/renderers use safe fallback labels when legacy data lacks the fields.

**Conflicts with ADRs / Principles**

* Potential conflicts: none known; this change makes existing season/phase semantics explicit rather than changing core planning ownership.
* Resolution: preserve deterministic cadence/slot math while adding deterministic intent sequencing.

**Impacted areas**

* UI: Season/Phase/Week views display intent labels.
* Pipeline/data: season/phase artifacts carry semantic fields.
* Renderer: updated templates and context builders.
* Workspace/run-store: no storage engine change, but stricter semantic validation.
* Validation/tooling: schema bundling, contract checks, guardrail tests.
* Deployment/config: none.

**Required refactoring**

* Introduce canonical phase-intent/archetype helpers.
* Propagate intent through deterministic context and artifact rendering.
* Update planning and workout skills to treat intent as first-class authority.

---

## 6) Options & Recommendation

### Option A — Persist normalized semantics and drive all layers from them

**Summary**

* Add `season_archetype` and `phase_intent` as real fields and propagate them through the stack.

**Pros**

* Deterministic and inspectable.
* Supports review and workout semantics cleanly.
* Stops prose-only semantic drift.

**Cons**

* Requires schema, validator, skill, and renderer changes.

**Risk**

* Cross-layer rollout touches many components and tests.

### Option B — Keep semantics only in skills and prose

**Summary**

* Improve prompts and reviews but do not add persisted fields.

**Pros**

* Smaller schema surface.

**Cons**

* Semantic drift remains likely.
* Downstream week/workout validation cannot rely on a stable contract field.

### Recommendation

* Choose: Option A.
* Rationale: this is a semantic-contract problem, not just a prompt-quality problem.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] `SEASON_SCENARIOS` supports `season_archetype`.
* [ ] `SEASON_PLAN` phases persist `phase_intent`.
* [ ] Downstream phase artifacts inherit and preserve `phase_intent`.
* [ ] Deterministic context derives `ceiling_first_durability` intent sequencing when permitted.
* [ ] Week planning uses `phase_intent` as an explicit planning signal.
* [ ] Workout construction and review use `phase_intent` for workout-family semantics.
* [ ] `season_load_envelope.expected_average_weekly_kj_range` is deterministic and validated.
* [ ] Validation passes: py_compile, lint, typecheck, targeted tests, schema bundling.

---

## 8) Migration / Rollout

**Migration strategy**

* New writes require normalized fields.
* Existing artifacts remain readable with safe fallback behavior.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert schema/skill/runtime changes; old artifacts remain intact.

---

## 9) Risks & Failure Modes

* Failure mode: season scenario declares an archetype but downstream plan omits valid phase-intent sequencing.
  * Detection: season review / contract validation.
  * Safe behavior: reject or replan rather than guess.
  * Recovery: regenerate season plan with corrected deterministic context or skill logic.

* Failure mode: week/workout planning ignores inherited `phase_intent`.
  * Detection: semantic audit and workout review failures.
  * Safe behavior: reject week plan/workout output.
  * Recovery: rerun after fixing skill/runtime intent propagation.

---

## 10) Observability / Logging

**New/changed events**

* No new event family required, but semantic guardrail failures should mention:
  * archetype id,
  * expected phase intent,
  * observed conflicting domains or workout family.

**Diagnostics**

* Run events in `runtime/athletes/<athlete_id>/runs/<run_id>/events.jsonl`
* Artifact JSON and rendered Markdown sidecars for intent propagation

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] This feature spec.
* [ ] `mandatory_output_season_scenarios.md`
* [ ] `mandatory_output_season_plan.md`
* [ ] `mandatory_output_phase_preview.md`
* [ ] relevant phase-guardrails / phase-structure specs
* [ ] `CHANGELOG.md`

---

## 12) Link Map

* [Season plan semantic hardening](/doc/specs/features/FEAT_season_plan_semantic_hardening.md)
* [Week plan semantic hardening](/doc/specs/features/FEAT_week_plan_semantic_hardening.md)
* [Workout policy skill completion](/doc/specs/features/FEAT_workout_policy_skill_completion.md)
* [Durability principles migration evidence](/specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md)
* [Season macrocycle architecture skill](/skills/season/macrocycle-architecture/SKILL.md)
* [Season plan synthesis skill](/skills/season/plan-synthesis/SKILL.md)
* [Phase intensity distribution skill](/skills/phase/intensity-distribution/SKILL.md)
* [Workout construction skill](/skills/week/workout-construction/SKILL.md)
