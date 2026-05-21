---
Version: 1.0
Status: Approved
Last-Updated: 2026-05-21
Owner: Planning Semantics
---
# FEAT: Canonical Phase Taxonomy Skill Migration

* **ID:** FEAT_canonical_phase_taxonomy_skill_migration
* **Status:** Approved
* **Owner/Area:** Planning Skills
* **Last-Updated:** 2026-05-21
* **Related:** [FEAT_canonical_phase_taxonomy_migration](/doc/specs/features/FEAT_canonical_phase_taxonomy_migration.md)

---

## 1) Context / Problem

**Current behavior**

* Runtime contracts, schemas, and validation now use canonical `phase_type`, `phase_intent`, and `build_subtype`.
* Several active planner skills and Crew task descriptions still refer to legacy terms such as `ceiling_support`, `build_progression`, `peak_preparation`, or `a_event_peak_taper`.

**Problem**

* Planner prompts and runtime contracts are now semantically inconsistent.
* Season, Phase, and Week planners can still reason with outdated intent semantics even though the write path now enforces the canonical taxonomy.
* This creates avoidable replan loops, drift, and writer/validator rejection for otherwise coherent planning drafts.

**Constraints**

* No new dependencies.
* This is a semantics and instruction migration, not a new runtime subsystem.
* Season, Phase, and Week all need the full semantic picture; `build_subtype` is not a Week-only concept.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Update Season, Phase, and Week planner skills to the canonical taxonomy.
* [x] Make `build_subtype` explicit in Season and Phase semantics, not only Week selection.
* [x] Update task descriptions so Crew roles reason with canonical semantics upstream.

**Non-Goals**

* [x] Introduce a canonical `week_role` taxonomy in the same change.
* [x] Rewrite every historical feature spec that mentions old labels.

---

## 3) Proposed Behavior

**User/System behavior**

* Season planning skills describe macro-periods with canonical `phase_type`.
* Season planning must emit canonical `phase_intent` and, for Build phases, explicit `build_subtype`.
* Phase planning skills treat `phase_type`, `phase_intent`, and `build_subtype` as inherited binding authority.
* Week skills read `phase_intent` plus `build_subtype` as the phase-method signal for week shape and workout-family bias.

**UI impact**

* UI affected: No direct layout change.

**Non-UI behavior**

* Components involved:
  * `skills/season/*`
  * `skills/phase/*`
  * `skills/week/*`
  * `config/crewai/tasks.yaml`

---

## 4) Implementation Analysis

**Components / Modules**

* Season synthesis + writing skills: replace legacy taxonomy tables and writer guidance.
* Phase authoring + writing skills: replace legacy phase-intent semantics with canonical planner semantics.
* Week synthesis + workout-construction + audit skills: replace remaining old Build/Peak terms with canonical Build subtype semantics.
* Crew task descriptions: mention canonical `phase_type`, `phase_intent`, and `build_subtype` where those fields are binding.

**Data flow**

* Inputs: injected deterministic context, approved bundles, canonical artifact contracts.
* Processing: planner prompt instructions interpret canonical semantics consistently across layers.
* Outputs: planner drafts align with new schema/runtime contract without legacy aliasing.

**Schema / Artefacts**

* No new schemas in this feature.
* This feature aligns active skill/task semantics with already-migrated artifact contracts.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: N/A for artifacts; this is prompt/skill alignment work.
* Breaking changes: active planner language no longer endorses legacy taxonomy values.
* Fallback behavior: none; skills should use canonical terms only.

**Impacted areas**

* Pipeline/data: lower prompt/runtime mismatch risk
* Validation/tooling: fewer schema rejections from legacy-value drift

**Required refactoring**

* Replace old taxonomy tables in Season/Phase skills.
* Update Week skill family-bias sections to canonical Build subtype terms.
* Update Writer skills to preserve `phase_type`, `phase_intent`, `build_subtype`, and `phase_taxonomy_version`.

---

## 6) Options & Recommendation

### Option A — Full skill/task migration

**Summary**

* Update Season, Phase, Week skills and Crew task descriptions to canonical semantics.

**Pros**

* Removes prompt/runtime semantic mismatch.
* Keeps upstream/downstream planning aligned.

**Cons**

* Touches several active skills and task descriptions in one pass.

### Option B — Leave skills on legacy terms and rely on runtime normalization

**Summary**

* Keep current skills and let writer/runtime reject or normalize.

**Pros**

* Smaller short-term change.

**Cons**

* Keeps planners reasoning in the wrong vocabulary.
* Creates avoidable replan/rejection churn.

### Recommendation

* Choose: Option A.
* Rationale: planner semantics must match the runtime contract at source, not only at validation time.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season planning skills use canonical `phase_type`, `phase_intent`, and `build_subtype`.
* [x] Phase planning skills use canonical semantics and no longer recommend legacy phase-intent labels.
* [x] Week skills read canonical Build subtype semantics.
* [x] Writer skills explicitly preserve `phase_type`, `phase_intent`, `build_subtype`, and taxonomy version where relevant.
* [x] Relevant Crew task descriptions mention canonical semantics where binding.

---

## 8) Migration / Rollout

**Migration strategy**

* Apply directly after canonical taxonomy runtime migration.

**Rollout / gating**

* No feature flag.
* Safe rollback: restore prior skill/task docs if needed.

---

## 9) Risks & Failure Modes

* Failure mode: some old terms remain in active skills and continue to bias model output.
  * Detection: grep for old taxonomy strings in active `skills/` and `config/crewai/tasks.yaml`.
  * Safe behavior: treat as follow-up bug and remove remaining legacy references.

---

## 10) Observability / Logging

**Diagnostics**

* Prompt-output drift should decrease in season/phase/week review artifacts and schema rejections.

---

## 11) Documentation Updates

* [x] [skills/season/plan-synthesis/SKILL.md](/Users/alexander/RPS/skills/season/plan-synthesis/SKILL.md)
* [x] [skills/phase/intensity-distribution/SKILL.md](/Users/alexander/RPS/skills/phase/intensity-distribution/SKILL.md)
* [x] [skills/week/plan-synthesis/SKILL.md](/Users/alexander/RPS/skills/week/plan-synthesis/SKILL.md)
* [x] [skills/week/workout-construction/SKILL.md](/Users/alexander/RPS/skills/week/workout-construction/SKILL.md)
* [x] [config/crewai/tasks.yaml](/Users/alexander/RPS/config/crewai/tasks.yaml)
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md)

---

## 12) Link Map (no duplication; links only)

* [FEAT_canonical_phase_taxonomy_migration](/doc/specs/features/FEAT_canonical_phase_taxonomy_migration.md)
* [ADR-053-canonical-phase-taxonomy-and-build-subtypes](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md)
