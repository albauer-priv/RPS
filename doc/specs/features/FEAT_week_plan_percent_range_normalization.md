---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-27
Owner: Workouts / Planner
---
# FEAT: Week Plan Percent Range Normalization

* **ID:** FEAT_week_plan_percent_range_normalization
* **Status:** Implemented
* **Owner/Area:** Workouts / Week Planner
* **Last-Updated:** 2026-04-27

## 1) Context / Problem

**Current behavior**

* The workout subset validator accepts power percent ranges only in the form `NN%-NN%`.
* The Week Planner still emits or repairs some steady/range lines as `NN-NN%`.

**Problem**

* Valid planning content is blocked by a narrow formatting defect in `workout_text`.
* Examples:
  * invalid: `68-72%`
  * valid: `68%-72%`

**Constraints**

* Do not broaden the grammar beyond the documented subset.
* Keep the validator strict.
* Fix should be deterministic and low-risk.

## 2) Goals & Non-Goals

**Goals**

* [x] Make the Week Planner prompt explicit about the required percent-range form.
* [x] Normalize the known malformed pattern `NN-NN%` to `NN%-NN%` before guarded validation.

**Non-Goals**

* [x] No change to the formal EBNF or subset validator contract.
* [x] No automatic normalization of arbitrary malformed workout syntax.

## 3) Proposed Behavior

* Percent ranges in `workout_text` must be written as `NN%-NN%`.
* Before guarded `WEEK_PLAN` validation, a deterministic normalization rewrites the specific malformed pattern `NN-NN%` inside step lines to `NN%-NN%`.

## 4) Implementation Analysis

* `prompts/agents/week_planner.md`
  * add explicit valid/invalid percent-range examples
* `src/rps/agents/multi_output_runner.py`
  * normalize known malformed percent-range tokens inside `WEEK_PLAN.workouts[].workout_text`

## 5) Impact Analysis

* Backward compatible: Yes
* Schema changes: none
* Validator contract: unchanged

## 6) Recommendation

* Use prompt hardening plus narrow normalization.
* Rationale: keeps validation strict while preventing a recurring, deterministic formatting miss.

## 7) Acceptance Criteria

* [x] `68-72%` is normalized to `68%-72%` in `WEEK_PLAN.workout_text`.
* [x] Existing validator still rejects unrelated malformed step syntax.
* [x] Tests cover normalization and prompt/source behavior.

## 8) Migration / Rollout

* No migration required.

## 9) Risks & Failure Modes

* Risk: over-normalizing non-target strings
  * Mitigation: normalize only bounded numeric-percent-range patterns

## 10) Observability / Logging

* No new logging required.

## 11) Documentation Updates

* [x] `CHANGELOG.md`
* [x] `doc/specs/features/FEAT_week_plan_percent_range_normalization.md`

## 12) Link Map

* `specs/knowledge/_shared/sources/specs/workouts/intervals_workout_ebnf.md`
* `specs/knowledge/_shared/sources/specs/workouts/workout_syntax_and_validation.md`
* `doc/runbooks/validation.md`
