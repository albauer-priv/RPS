---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning
---
# FEAT: Workout Policy Skill Completion

* **ID:** FEAT_workout_policy_skill_completion
* **Status:** Implemented
* **Owner/Area:** Planning
* **Last-Updated:** 2026-05-20
* **Related:** FEAT_week_plan_semantic_hardening

---

## 1) Context / Problem

**Current behavior**

* Week workout authoring and workout syntax review are attached to `skills/week/workout-construction` and `skills/week/workout-syntax-review`.
* `specs/knowledge/_shared/sources/policies/workout_policy.md` is marked as superseded and claims its operative rules were migrated into the active skills.

**Problem**

* The active week workout skills contain only a subset of the binding workout-policy semantics.
* Missing runtime guidance includes QUALITY intent target-band lookup, canonical workout-family selection, workout-type parameter ranges, and workout-type progression constraints.
* That gap leaves too much room for LLM invention during week workout authoring and too little review coverage for policy-semantic drift.

**Constraints**

* No schema change.
* No new dependency.
* Keep the week planner contract model intact: scheduling and weekly load distribution remain outside workout policy authority.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move the binding operative parts of `workout_policy.md` into active workout skills.
* [x] Make the authoring skill explicit about canonical workout families, intensity-domain mapping, QUALITY intent target-band lookup, and progression constraints.
* [x] Make the review skill check policy-semantic compliance, not only syntax subset compliance.
* [x] Align task descriptions with the strengthened skill scope.
* [x] Remove redundant workout-text reference files once their operative content lives directly in the active skills.
* [x] Adjust review/audit skills so policy-semantic blockers propagate beyond authoring.

**Non-Goals**

* [x] No change to week-plan schema or workout export schema.
* [x] No new deterministic workout generator in code.
* [x] No change to season/phase authority boundaries.

---

## 3) Proposed Behavior

**User/System behavior**

* The week workout author no longer improvises missing workout semantics from partial hints.
* QUALITY intent uses an explicit target-band lookup inside the allowed intensity domain and remains subordinate to Phase Guardrails and Phase Structure.
* Workout families are chosen from a defined canonical set, with binding parameter ranges and progression rules.
* Workout review checks both export syntax and policy-semantic compliance.

**UI impact**

* UI affected: No.

**Non-UI behavior (if applicable)**

* Components involved: week workout authoring skill, week workout syntax review skill, CrewAI task descriptions.
* Contracts touched: workout authoring/review runtime method only; export contract remains unchanged.

---

## 4) Implementation Analysis

**Components / Modules**

* `skills/week/workout-construction/SKILL.md`: add missing operative workout-policy semantics and authoring examples.
* `skills/week/workout-syntax-review/SKILL.md`: add policy-semantic review checks and subset/EBNF restrictions that must remain visible at runtime.
* `skills/week/consistency-audit/SKILL.md`: treat workout-policy semantic drift as a blocking coherence issue.
* `skills/week/review-decision/SKILL.md`: make policy-semantic blockers approval-stopping conditions.
* `config/crewai/tasks.yaml`: align week workout task descriptions with the strengthened semantics.
* `skills/week/workout-construction/references/*.md`: delete redundant files whose operative content is now in `SKILL.md`.

**Data flow**

* Inputs: deterministic week context, phase execution context, candidate day role, intensity domain, duration/load intent, athlete context.
* Processing: authoring skill chooses a canonical workout family and parameter placement inside policy and zone-model constraints; review skill checks syntax and policy-semantic fit.
* Outputs: stronger workout-authoring draft and stronger week workout review draft.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: runtime behavior is stricter; persisted schema unchanged.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for artefact shape.
* Breaking changes: week workout drafts that previously passed with vague or semantically drifting workout choices may now be revised or rejected in review.
* Fallback behavior: existing deterministic context and export validation still apply if the richer policy semantics are not triggered by a given week.

**Conflicts with ADRs / Principles**

* No ADR conflict.
* Reinforces the existing migration rule that operative prose must live in `SKILL.md`, not only in references.

**Impacted areas**

* UI: none.
* Pipeline/data: stronger week workout reasoning and review.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: skill/runtime behavior aligns with the supersession claim in the architecture audit.
* Deployment/config: no new config.

**Required refactoring**

* Replace the residual under-specified workout-authoring semantics with explicit canonical-family and QUALITY-intent guidance.
* Expand workout review from syntax-only wording to syntax-plus-policy wording.
* Remove low-value duplicate reference fragments that no longer carry unique runtime content.

---

## 6) Options & Recommendation

### Option A — Complete the skill migration

**Summary**

* Put the missing workout-policy rules directly into the active workout skills and align task descriptions.

**Pros**

* Restores the single-runtime-source claim.
* Reduces LLM invention.
* Improves consistency between authoring and review.

**Cons**

* Skills become longer and more prescriptive.

**Risk**

* Overly verbose skill text could reduce prompt efficiency if not kept disciplined.

### Option B — Keep lean skills and rely on references

**Summary**

* Leave the main skills short and push the missing semantics into references only.

**Pros**

* Smaller skill files.

**Cons**

* Conflicts with the migration-audit rule that operative rules must appear in `SKILL.md`.
* Leaves runtime behavior dependent on implicit retrieval and model recall.

### Recommendation

* Choose: Option A.
* Rationale: the missing semantics are operative week-planning rules, not optional background material.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `skills/week/workout-construction/SKILL.md` contains explicit QUALITY intent lookup semantics and precedence.
* [x] `skills/week/workout-construction/SKILL.md` contains canonical workout-family rules, ranges, and progression guidance for the active workout families.
* [x] `skills/week/workout-construction/SKILL.md` contains compact canonical examples for the critical workout families.
* [x] `skills/week/workout-syntax-review/SKILL.md` checks policy-semantic compliance in addition to syntax subset compliance.
* [x] Redundant workout-text reference fragments are removed after migration.
* [x] Week review/decision skills mention workout-policy semantic blockers explicitly.
* [x] `config/crewai/tasks.yaml` descriptions reflect the richer authoring/review responsibilities.
* [x] Validation passes: syntax check, lint, type check.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema or data migration.
* Immediate runtime behavior improvement through skill/task updates.

**Rollout / gating**

* No feature flag.
* Safe rollback is reverting the commit.

---

## 9) Risks & Failure Modes

* Failure mode: skill text becomes inconsistent with the policy source again.
  * Detection: future audit comparing `workout_policy.md` and skill bodies.
  * Safe behavior: review catches explicit drift; runtime remains bounded by export/contract checks.
  * Recovery: update the skills and audit doc together.

* Failure mode: review becomes stricter than current authoring outputs.
  * Detection: more week review rejections on workout policy reasons.
  * Safe behavior: reject/revise instead of emitting semantically drifting workouts.
  * Recovery: tune prompts or deterministic inputs, not by weakening policy boundaries blindly.

* Failure mode: unique guidance is deleted together with redundant references.
  * Detection: source-vs-skill audit finds a missing operative rule after cleanup.
  * Safe behavior: keep active skills authoritative and restore any genuinely unique missing rule into `SKILL.md`.
  * Recovery: re-add a focused reference only when it contains unique non-duplicated content.

---

## 10) Observability / Logging

**New/changed events**

* No new event type.
* Existing week review/task outputs should surface more explicit workout-policy failure reasons.

**Diagnostics**

* Week-planning task outputs and review artifacts show whether rejection came from syntax-only or policy-semantic mismatch.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `skills/week/workout-construction/SKILL.md` — add missing operative workout-policy semantics.
* [x] `skills/week/workout-syntax-review/SKILL.md` — add policy-semantic review guidance.
* [x] `skills/week/consistency-audit/SKILL.md` — mention workout-policy semantic blockers.
* [x] `skills/week/review-decision/SKILL.md` — treat policy-semantic blockers as approval blockers.
* [x] `config/crewai/tasks.yaml` — align workout task descriptions with actual runtime responsibility.
* [x] `CHANGELOG.md` — record workout-policy skill completion.

---

## 12) Link Map (no duplication; links only)

* `specs/knowledge/_shared/sources/policies/workout_policy.md`
* `specs/knowledge/_shared/sources/contracts/week__workout_export_contract.md`
* `doc/architecture/skills_source_migration_audit.md`
* `doc/architecture/agents.md`
* `doc/specs/features/FEAT_week_plan_semantic_hardening.md`
