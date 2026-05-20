---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning Runtime
---
# FEAT: Deterministic Workout Generator First

* **ID:** FEAT_deterministic_workout_generator_first
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-20
* **Related:** FEAT_week_domain_failure_hardening, FEAT_week_workout_loop_header_normalization

---

## 1) Context / Problem

**Current behavior**

* The Week pipeline still lets LLM-authored `workout_text` reach review and writer stages.
* Deterministic normalization exists, but it runs too late for syntax and semantics to be trustworthy during writer validation.
* Coach and preview edit paths still accept arbitrary `workout_text` blocks directly.

**Problem**

* Invalid loop syntax such as `- 3x 12m ...` still appears in runtime-visible output.
* Free-text section labels and semantically drifting workout families still cause late writer guardrail failures.
* The same workout subset is described deterministically, but not generated deterministically.

**Constraints**

* `src/rps/workouts/validator.py` remains the binding syntax authority.
* `WEEK_PLAN` schema stays at `1.2`.
* No new dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make deterministic code generation the primary author of `workout_text` for new/generated week plans.
* [x] Reuse the same canonical syntax path across week generation, preview/replan generation, and coach text edits.
* [x] Keep parser/validator as a strict gate for compatibility and manual text entry.

**Non-Goals**

* [ ] Full removal of every legacy free-text entry point in one change.
* [ ] Exhaustive implementation of every conceivable workout family beyond the currently planned week families.

---

## 3) Proposed Behavior

**User/System behavior**

* Week-plan creation no longer trusts LLM-authored final `workout_text`.
* Approved week workout blueprints are rendered into canonical subset text by code.
* Preview and coach text-edit flows canonicalize accepted text through parse/render before persistence.

**UI impact**

* UI affected: No direct layout changes.
* Persisted and previewed workouts become more canonical and stable.

**Non-UI behavior**

* Components involved: CrewAI backend, week-plan edits, workout validator, guarded store.
* Contracts touched: internal `WeekWorkoutBlueprintModel`, `WEEK_PLAN` generation path, workout canonicalization path.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workouts/structured.py`: workout AST, parser, canonical renderer.
* `src/rps/workouts/generator.py`: deterministic family-based workout generation and week document builder.
* `src/rps/agents/crewai_backend.py`: deterministic week-plan writer path and contract capture.
* `src/rps/orchestrator/week_plan_edits.py`: canonicalize manual workout-text edits.
* `src/rps/workspace/guarded_store.py`: enforce canonical week-plan workout text before persistence.

**Data flow**

* Inputs: approved planning bundle, deterministic week contract, optional manual workout text.
* Processing: blueprint -> workout AST -> rendered text -> validator -> persisted `WEEK_PLAN`.
* Outputs: canonical `WEEK_PLAN` workout text and normalized edit previews.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: internal week workout blueprint fields expanded for deterministic rendering.
* Validator implications: generated and canonicalized workouts must pass the strict workout export subset.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, with stricter canonicalization of accepted workout text.
* Breaking changes: non-canonical manual workout text may now be rewritten into canonical form or rejected earlier.
* Fallback behavior: unsupported or invalid free-text edits continue to fail validation.

**Conflicts with ADRs / Principles**

* No ADR conflict found.
* This change reduces LLM authority and increases code-owned determinism in line with existing planning principles.

**Impacted areas**

* UI: workout preview/apply reflects canonical text.
* Pipeline/data: week-plan generation becomes code-owned for workout text.
* Renderer: no direct template change required.
* Workspace/run-store: guarded store canonicalizes week-plan workout text before final validation.
* Validation/tooling: semantic checks can rely on canonical render output instead of heuristic drift.
* Deployment/config: no new config flags.

**Required refactoring**

* Centralize workout text parsing/rendering into one shared module.
* Replace week writer dependence on free-text workout authoring for `WEEK_PLAN`.

---

## 6) Options & Recommendation

### Option A — Parser-first repair

**Summary**

* Keep the LLM as text author and repair later.

**Pros**

* Smaller change.

**Cons**

* Syntax and semantic drift remain upstream.

### Option B — Generator first

**Summary**

* Make structured blueprints authoritative and render canonical workout text in code.

**Pros**

* Removes the main defect source.
* Keeps syntax enforcement deterministic.

**Cons**

* Requires a code-owned workout family renderer.

### Recommendation

* Choose: Option B
* Rationale: the workout subset, family set, and progression constraints are already narrow enough to render deterministically.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Generated `WEEK_PLAN` workouts use deterministic canonical workout text.
* [x] Inline loop shorthand never persists in generated output.
* [x] Manual workout-text preview/apply canonicalizes accepted text before persistence.
* [x] Validation passes: `py_compile`, targeted pytest, lint, typecheck.
* [x] No regressions in week plan export validation and workout editor preview flows.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration required.
* Existing manually-authored text remains accepted only if it canonicalizes and validates cleanly.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: revert deterministic week builder and canonical edit hook.

---

## 9) Risks & Failure Modes

* Failure mode: a blueprint cannot map to a supported deterministic family.

  * Detection: week writer/build failure with explicit unsupported blueprint error.
  * Safe behavior: fail before persistence.
  * Recovery: add or adjust the family mapping in code.

* Failure mode: canonicalization rejects a manual edit that previously slipped through.

  * Detection: preview/apply validation failure.
  * Safe behavior: do not persist.
  * Recovery: fix the edit to match the subset or expand canonicalization intentionally.

---

## 10) Observability / Logging

**New/changed events**

* Existing week planning logs remain; failure shifts from late writer syntax drift toward explicit deterministic builder errors.

**Diagnostics**

* Runtime logs, preview errors, week export validation failures.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_deterministic_workout_generator_first.md` — canonical feature spec
* [x] `CHANGELOG.md` — implementation note

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* Related specs: `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md`

