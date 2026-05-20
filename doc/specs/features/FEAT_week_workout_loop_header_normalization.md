---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning
---
# FEAT: Week Workout Loop Header Normalization

* **ID:** FEAT_week_workout_loop_header_normalization
* **Status:** Implemented
* **Owner/Area:** Planning
* **Last-Updated:** 2026-05-20
* **Related:** FEAT_week_workout_source_migration_completion

---

## 1) Context / Problem

**Current behavior**

* Week workout generation now reaches the strict workout subset more often.
* A remaining writer failure appears when the model emits inline loop shorthand like `- 3x 12m 80%-84% 88-94rpm`.

**Problem**

* The project subset requires standalone loop headers (`3x`) followed by step lines.
* The inline form is syntactically invalid, but its intent is deterministic and recoverable.

**Constraints**

* No schema change.
* No relaxation of workout validation.
* Only deterministic, non-semantic repair is allowed.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Repair inline loop shorthand deterministically before week-plan guardrail validation.
* [x] Keep the repair narrowly scoped to safe syntax transformation only.

**Non-Goals**

* [x] No prose-to-workout conversion.
* [x] No guessing of missing recovery steps or workout-family semantics.

---

## 3) Proposed Behavior

**User/System behavior**

* If a workout step is written as `- 3x 12m ...`, runtime normalization rewrites it to:

```text
3x
- 12m ...
```

* The transformation preserves the original step payload and only fixes the loop-header shape.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: week-plan output normalization before writer/store guardrails.
* Contracts touched: none; this only aligns output with the existing contract.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/output_normalization.py`: add deterministic inline-loop normalization helper.
* `src/rps/agents/crewai_backend.py`: apply it in the week workout normalization flow.
* `tests/test_output_normalization.py`: add unit coverage.

**Data flow**

* Inputs: `WEEK_PLAN.data.workouts[*].workout_text`
* Processing: detect safe inline loop shorthand and rewrite it to a standalone loop header plus step line.
* Outputs: normalized `workout_text` before writer guardrails run.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: repaired text should pass existing subset validation when otherwise valid.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none.
* Fallback behavior: non-repairable invalid text still fails validation.

**Conflicts with ADRs / Principles**

* No ADR conflict.
* Consistent with the normalization rule: repair obvious syntax drift, do not invent training semantics.

**Impacted areas**

* UI: none.
* Pipeline/data: week-plan pre-store normalization.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: fewer false-negative writer failures for recoverable loop shorthand.
* Deployment/config: none.

**Required refactoring**

* Extend the workout text normalization helper set with loop-header repair.

---

## 6) Options & Recommendation

### Option A — Deterministic loop-header normalization

**Summary**

* Repair only the inline loop-header shorthand.

**Pros**

* Safe and narrow.
* Removes a recurring writer failure.

**Cons**

* Does not fix broader malformed workout text.

### Option B — Keep strict failure only

**Summary**

* Rely on prompt/skill guidance alone and let the writer fail on inline shorthand.

**Pros**

* Zero code change.

**Cons**

* Repeats a recoverable runtime failure.

### Recommendation

* Choose: Option A
* Rationale: the error is syntactic, deterministic, and cheap to repair without changing training intent.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Inline loop shorthand `- Nx ...` is normalized to a standalone loop header plus step line.
* [x] Existing percent-range normalization still runs.
* [x] Targeted tests pass.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration.

**Rollout / gating**

* Immediate.
* Safe rollback is reverting the commit.

---

## 9) Risks & Failure Modes

* Failure mode: overly broad rewrite changes lines that are not intended as loop shorthand.
  * Detection: failing workout export tests.
  * Safe behavior: validation still blocks malformed output.
  * Recovery: narrow the regex further.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Writer guardrail failures for inline loop shorthand should disappear from `rps.log`.

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — record loop-header normalization.

---

## 12) Link Map (no duplication; links only)

* `doc/specs/features/FEAT_week_workout_source_migration_completion.md`
* `skills/week/workout-construction/SKILL.md`
* `src/rps/workouts/validator.py`
