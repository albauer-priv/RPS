---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning
---
# FEAT: Week Workout Source Migration Completion

* **ID:** FEAT_week_workout_source_migration_completion
* **Status:** Implemented
* **Owner/Area:** Planning
* **Last-Updated:** 2026-05-20
* **Related:** FEAT_workout_policy_skill_completion, FEAT_week_plan_semantic_hardening

---

## 1) Context / Problem

**Current behavior**

* The active week workout runtime is supposed to be skill-owned.
* Four legacy workout sources under `specs/knowledge/_shared/sources/` still act as practical source material for runtime behavior:
  * `contracts/week__workout_export_contract.md`
  * `specs/workouts/intervals_workout_ebnf.md`
  * `specs/workouts/workout_syntax_and_validation.md`
  * `policies/workout_policy.md`
* The active skill bodies already contain some migrated semantics, but the runtime method is still under-specified in places.

**Problem**

* Workout authoring still drifts into prose and non-export-safe syntax.
* Review can approve a candidate week bundle that the writer/export guardrails later reject.
* The skill layer still leaves too much implicit knowledge in legacy sources that are no longer meant to be live runtime planning inputs.

**Constraints**

* No schema change.
* No new dependency.
* Preserve machine-layer validation in code and contracts.
* Keep the active runtime method self-contained in `SKILL.md` plus local `references/`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move the operative workout-authoring and syntax-review method fully into active week skills.
* [x] Keep compact canonical examples and syntax tables in local skill `references/`.
* [x] Remove practical runtime dependence on the four legacy workout prose sources.
* [x] Align week authoring, review, and writing with the same exported Intervals subset.
* [x] Make phase-guardrails authority explicit when `RECOVERY` is forbidden for the active week.

**Non-Goals**

* [x] No change to the `WEEK_PLAN` schema.
* [x] No relaxation of `src/rps/workouts/validator.py`.
* [x] No prose-to-Intervals auto-conversion layer.

---

## 3) Proposed Behavior

**User/System behavior**

* Week workout authoring now operates from the active skill layer alone.
* The authoring skill carries the exact subset rules needed to emit export-safe workout text.
* The syntax-review skill carries the exact blocking review logic needed to reject prose, illegal targets, and phase-authority drift before writer execution.
* The writer skill and writer prompt now state plainly that workout text must already be in the strict project subset.
* Recovery-like low-load work is authored as low-end `ENDURANCE` when the active phase guardrails forbid the `RECOVERY` domain.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: week workout-construction skill, week workout-syntax-review skill, week artifact-writing skill, week writer prompt, week task descriptions, guardrail diagnostics.
* Contracts touched: workout-authoring runtime method only; machine-layer validation stays code-owned.

---

## 4) Implementation Analysis

**Components / Modules**

* `skills/week/workout-construction/SKILL.md`: embed the operative authoring rules directly.
* `skills/week/workout-construction/references/*`: hold compact canonical examples and accepted target/section forms.
* `skills/week/workout-syntax-review/SKILL.md`: embed blocking syntax and semantic review logic directly.
* `skills/week/workout-syntax-review/references/*`: hold compact syntax checklist and forbidden-token summary.
* `skills/week/artifact-writing/SKILL.md`: clarify strict writer obligations.
* `prompts/agents/week_artifact_writer.md`: mirror the strict writer subset.
* `config/crewai/tasks.yaml`: sharpen week workout/review/writer descriptions.
* `src/rps/crewai_runtime/guardrails.py`: improve workout-domain failure diagnostics.

**Data flow**

* Inputs: week calendar context, phase execution context, candidate week bundle, local workout skill references.
* Processing: authoring emits only subset-compliant workout text; review blocks illegal syntax or phase-authority drift; writer serializes approved content only.
* Outputs: tighter week-plan runtime behavior and clearer guardrail failures.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: no validator rule changes; runtime behavior is brought into alignment with existing validators.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for artifact shape.
* Breaking changes: bundles that previously relied on prose or `RECOVERY` drift will now fail earlier.
* Fallback behavior: existing guardrails and export validation still stop invalid output even if review misses something.

**Conflicts with ADRs / Principles**

* No ADR conflict.
* Reinforces the repo rule that operative method logic belongs in `SKILL.md` and not in superseded legacy prose.

**Impacted areas**

* UI: none.
* Pipeline/data: stricter week planning and review behavior.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: improved week guardrail diagnostics.
* Deployment/config: no new config.

**Required refactoring**

* Finish migration of the workout method into skill bodies and skill references.
* Remove residual vagueness from writer prompt and week task descriptions.
* Add regression tests for prose syntax and forbidden `RECOVERY` handling.

---

## 6) Options & Recommendation

### Option A — Complete the migration in active skills

**Summary**

* Put the operative rules in active week skills and use local references for compact supporting material.

**Pros**

* Matches the architecture intent.
* Reduces model invention.
* Keeps runtime self-contained.

**Cons**

* Requires longer skill bodies and curated references.

**Risk**

* Skill/reference drift if future workout changes are only made in legacy prose.

### Option B — Keep relying on superseded prose docs

**Summary**

* Leave active skills partially specified and continue treating the old files as practical runtime source material.

**Pros**

* Smaller skill edits right now.

**Cons**

* Keeps the current runtime ambiguity.
* Conflicts with the migration audit and source-of-truth policy.

### Recommendation

* Choose: Option A
* Rationale: the runtime method needs one active source surface, and the workout failure shows the current split source model is not working.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Active week workout skills contain the operative method needed for authoring and syntax review.
* [x] Local skill references contain compact canonical examples and syntax/checklist material.
* [x] Week writer prompt and skill text state the exact strict subset expectation.
* [x] Week task descriptions mention export-safe syntax and phase-authority precedence.
* [x] Guardrail diagnostics identify offending workout ids on domain failures.
* [x] Regression tests cover prose rejection and forbidden `RECOVERY` handling.
* [x] Validation passes: syntax check, lint, type check, targeted tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema or data migration.
* Immediate runtime behavior change through skill/prompt/task updates.

**Rollout / gating**

* No feature flag.
* Safe rollback is reverting the commit.

---

## 9) Risks & Failure Modes

* Failure mode: active skills and references drift apart again.

  * Detection: future source audit or unexpected planner behavior.
  * Safe behavior: code guardrails and export validation still block invalid output.
  * Recovery: update the active skills and local references together.

* Failure mode: review remains too soft and invalid bundles still reach the writer.

  * Detection: recurring writer guardrail failures in runtime logs.
  * Safe behavior: writer still blocks persistence.
  * Recovery: tighten review skill/task wording further or add stricter decision-time checks.

---

## 10) Observability / Logging

**New/changed events**

* No new event type.
* Week guardrail failures now report offending workout ids for phase-domain mismatches.

**Diagnostics**

* Inspect `rps.log`, `events.jsonl`, and week writer guardrail failures in Plan Hub / System History.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `skills/week/workout-construction/SKILL.md` — complete operative source migration.
* [x] `skills/week/workout-syntax-review/SKILL.md` — complete operative review migration.
* [x] `skills/week/artifact-writing/SKILL.md` — clarify strict writer subset.
* [x] `doc/architecture/skills_source_migration_audit.md` — record completed migration status for the four workout sources.
* [x] `CHANGELOG.md` — record the migration completion and runtime hardening.

---

## 12) Link Map (no duplication; links only)

* `doc/architecture/skills_source_migration_audit.md`
* `doc/specs/features/FEAT_workout_policy_skill_completion.md`
* `specs/knowledge/_shared/sources/contracts/week__workout_export_contract.md`
* `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md`
* `specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md`
* `specs/knowledge/_shared/sources/policies/workout_policy.md`
