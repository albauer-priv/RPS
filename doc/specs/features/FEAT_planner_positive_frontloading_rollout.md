---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-28
Owner: Planning
---
# FEAT: Planner Positive Frontloading Rollout

* **ID:** FEAT_planner_positive_frontloading_rollout
* **Status:** Implemented
* **Owner/Area:** Planning / CrewAI Season-Phase-Week chain
* **Last-Updated:** 2026-05-28
* **Related:** [FEAT_season_scenario_positive_frontloading](/Users/alexander/RPS/doc/specs/features/FEAT_season_scenario_positive_frontloading.md), [FEAT_active_prompt_policy_migration_completion](/Users/alexander/RPS/doc/specs/features/FEAT_active_prompt_policy_migration_completion.md)

---

## 1) Context / Problem

**Current behavior**

* The Season, Phase, and Week planning chains already state that review should mostly confirm and writer should serialize only.
* The active files already warn against leaving semantic repair to review or writer.

**Problem**

* The active planning files were still mostly constraint-led and not explicitly organized into planner-owned passes.
* Review was described as a formal gate, but not yet sharply enough as a classifier that routes defects back to the correct upstream pass.
* The chain therefore risked drifting into “review catches it” behavior instead of making planner/finalize own structural completion, semantic completion, and writer-readiness.

**Constraints**

* No schema change.
* No public interface change.
* Review must become narrower, not broader.
* Writer must remain strict and non-interpretive.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Apply one mandatory three-pass pattern to Season, Phase, and Week finalize/planner files.
* [x] Add planner-owned end-of-pass checklists.
* [x] Make Pass 3 and Review explicitly classify defects as Pass 1 return vs Pass 2 return.
* [x] Keep Review formal and narrow.
* [x] Keep Writer serialization-only and fail-closed.

**Non-Goals**

* [ ] No orchestration runtime redesign in this change.
* [ ] No schema migration.
* [ ] No widening of runtime guardrails as a substitute for planner-owned completion.

---

## 3) Proposed Behavior

**User/System behavior**

* Each Season/Phase/Week planner-finalize chain now follows:
  * Pass 1: structural draft
  * Pass 2: semantic finalization
  * Pass 3: planner self-audit
* Pass 3 must explicitly decide whether a defect belongs to:
  * Pass 2 return: structure valid, semantics incomplete
  * Pass 1 return: structure/authority malformed and not safely repairable in Pass 2
* Review now confirms and classifies only; it does not redraft semantics.
* Writer now explicitly runs only after Pass 3 readiness and Review approval.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * Season / Phase / Week finalize task descriptions
  * Season / Phase / Week manager prompts
  * Season / Phase / Week synthesis skills
  * Season / Phase / Week review prompts and skills
  * Season / Phase / Week writer prompts and skills
  * planner contract tests

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/tasks.yaml`
  * add three-pass and loopback language to finalize/review tasks
  * add writer precondition language to persisted-artifact tasks
* `prompts/agents/*`
  * add pass ordering, explicit loopback classification, and review-minimization wording
* `skills/season/plan-synthesis/SKILL.md`
* `skills/phase/bundle-synthesis/SKILL.md`
* `skills/week/plan-synthesis/SKILL.md`
  * add three-pass model and Pass 3 checklist framing
* `skills/season/review-decision/SKILL.md`
* `skills/phase/review-decision/SKILL.md`
* `skills/week/review-decision/SKILL.md`
  * add formal review confirmation checklist and explicit Pass 1 vs Pass 2 return classification
* writer skills/prompts
  * add precondition that writer only runs after Pass 3 and Review approval
* tests
  * assert presence of the pass model, checklist, loopback, formal review, and copy-only writer rules

**Data flow**

* Inputs: unchanged deterministic context and specialist drafts
* Processing: active planner guidance is more explicit about upstream passes and defect routing
* Outputs: unchanged artifact contracts, but stronger source-first completion discipline

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: prompt/skill/task contract tests expand

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: review still blocks bad bundles; writer still fails closed

**Conflicts with ADRs / Principles**

* Potential conflicts:
  * review could accidentally become a second planner
  * writer could accidentally inherit repair work
* Resolution:
  * explicit three-pass upstream model
  * explicit review classification-only rule
  * explicit writer preconditions

**Impacted areas**

* UI: none
* Pipeline/data: planner guidance only
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: new contract tests
* Deployment/config: task/prompt/skill text only

**Required refactoring**

* Make pass ordering explicit in active planner/finalize files.
* Convert generic finalize-check blocks into Pass 3 self-audit blocks with loopback rules.
* Convert review wording from “check and maybe fix” style to “confirm and classify” style.

---

## 6) Options & Recommendation

### Option A — keep review as an implicit quality backstop

**Summary**

* Leave the chain mostly as-is and rely on review wording plus runtime guards.

**Pros**

* Smaller edit surface

**Cons**

* Leaves semantic ownership blurry
* Encourages review-stage thinking and repair

### Option B — make the pass model explicit upstream

**Summary**

* Make planner/finalize own structure, semantics, and self-audit; make review formal and writer strict.

**Pros**

* Aligns active files with the repo’s upstream-first principle
* Shrinks review responsibility
* Keeps repair upstream where the model still has the right context

**Cons**

* Requires broader prompt/skill/task wording updates and contract tests

### Recommendation

* Choose: Option B
* Rationale: the desired behavior is a responsibility shift, not just a style change.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season, Phase, and Week finalize/planner active files contain explicit Pass 1 / Pass 2 / Pass 3 language.
* [x] Season, Phase, and Week finalize/planner active files contain explicit Pass 3 checklists.
* [x] Season, Phase, and Week finalize/planner active files contain explicit Pass 1 vs Pass 2 return rules.
* [x] Review prompts/skills describe a formal confirmation checklist and explicit classification-only behavior.
* [x] Writer prompts/skills state they run only after Pass 3 readiness and Review approval.
* [x] Writer prompts/skills remain copy-only / fail-closed.
* [x] Validation passes:
  * `python3 -m py_compile $(git ls-files '*.py')`
  * `./scripts/run_lint.sh`
  * `./scripts/run_typecheck.sh`
  * targeted `pytest` for the planner contract tests

---

## 8) Migration / Rollout

**Migration strategy**

* No migration required.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert task/prompt/skill text and planner contract tests.

---

## 9) Risks & Failure Modes

* Failure mode: pass language exists, but review wording still implies semantic repair.
  * Detection: prompt/skill tests fail
  * Safe behavior: runtime still blocks bad bundles
  * Recovery: tighten review prompt/skill wording further

* Failure mode: writer wording still sounds permissive enough to invite inference.
  * Detection: writer contract tests fail
  * Safe behavior: writer runtime still validates against approved structure
  * Recovery: further narrow writer precondition wording

---

## 10) Observability / Logging

**New/changed events**

* No telemetry changes in this pass.

**Diagnostics**

* `events.jsonl`
* `rps.log`
* planner contract tests

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — clarify umbrella rollout item
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record the 3-pass rollout

