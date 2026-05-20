---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Agents/Runtime
---
# FEAT: Week Replan Handoff Hardening

* **ID:** FEAT_week_replan_handoff_hardening
* **Status:** Implemented
* **Owner/Area:** CrewAI runtime / week planning
* **Last-Updated:** 2026-05-20
* **Related:** FEAT_phase_week_review_subject_and_runtime_hardening, FEAT_review_contract_context_hardening

## 1) Context / Problem

**Current behavior**

* Week planning runs a bounded planning -> review -> replan loop.
* When review returns `replan_required`, the runtime feeds the full prior review decision JSON into the next planning round.

**Problem**

* The full prior decision contains stale `blocking_issues` and `warnings` in addition to the actual replan delta.
* Later planning rounds can echo contradictory text such as "load brought into band" and "still above band before final review adjustment" inside the same candidate bundle.
* Review may keep requesting another replan even when the actionable issue was already fixed, exhausting the allowed rounds and failing the whole week run.

**Constraints**

* No schema change for `WeekPlanBundleModel` or `WeekReviewDecisionModel`.
* Keep the bounded multi-round week replan loop.
* Preserve deterministic week/phase contract authority.

## 2) Goals & Non-Goals

**Goals**

* [x] Pass only the active replan delta into the next week planning round.
* [x] Prevent stale review warnings/blockers from being copied into subsequent week bundles by runtime context alone.
* [x] Add regression coverage for week replan handoff semantics.

**Non-Goals**

* [ ] Redesign week review prompts or schemas.
* [ ] Add new persisted intermediate week-review artifacts.

## 3) Proposed Behavior

**User/System behavior**

* When week review returns `replan_required`, the next planning round receives:
  * the original user request
  * a compact structured `Active replan instructions` block
  * an explicit handoff rule that prior warnings/blockers are superseded unless they still apply after revision
* The next planning round does not receive the previous review decision wholesale.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `src/rps/agents/crewai_backend.py`
  * `tests/test_crewai_runtime.py`
* Contracts touched:
  * week planning/review runtime handoff only

## 4) Implementation Analysis

**Components / Modules**

* `crewai_backend.py`
  * add sanitized replan-context extraction for bounded replans
  * use sanitized context in `_run_multicrew_cycle`
* `tests/test_crewai_runtime.py`
  * verify stale review warnings do not get forwarded to later planning rounds

**Data flow**

* Inputs: original user request, review decision
* Processing: extract active replan instructions + bounded metadata only
* Outputs: next planning-round input without stale blocker/warning payloads

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none at artifact/schema level
* Fallback behavior: existing review decision still governs; only the replan handoff payload is narrowed

**Impacted areas**

* Pipeline/data: week bounded replan loop
* Validation/tooling: runtime tests

**Required refactoring**

* Replace full-decision replan replay with sanitized replan-context replay.

## 6) Options & Recommendation

### Option A — Sanitize replan handoff payload (recommended)

**Pros**

* Removes stale review noise at the runtime boundary.
* Leaves prompts and schemas stable.
* Targets the exact failure mode in the observed log.

**Cons**

* Requires careful choice of what metadata remains useful across rounds.

### Option B — Keep full prior decision replay

**Cons**

* Continues to leak stale blocker/warning prose into later rounds.

### Recommendation

* Choose: Option A

## 7) Acceptance Criteria (Definition of Done)

* [x] Week replans receive a sanitized `Active replan instructions` context block.
* [x] Prior `warnings` and `blocking_issues` are not replayed wholesale into the next planning round.
* [x] Regression tests cover the sanitized handoff.
* [x] Validation passes: syntax, targeted pytest, lint, typecheck.

## 8) Migration / Rollout

* No migration needed.
* Runtime-only hardening applies on next deploy.

## 9) Risks & Failure Modes

* Failure mode: planner loses needed context from the prior review.
  * Detection: later week replans omit specific required adjustments.
  * Safe behavior: review still returns `replan_required`.
  * Recovery: widen the sanitized replan payload, but keep stale warnings excluded.

## 10) Observability / Logging

* Existing `CREW_EXECUTION_FAILED` and review telemetry remain sufficient.
* The planning input for later rounds becomes narrower and less contradictory.

## 11) Documentation Updates

* [x] `CHANGELOG.md`
* [x] this feature spec

## 12) Link Map

* [src/rps/agents/crewai_backend.py](/Users/alexander/RPS/src/rps/agents/crewai_backend.py)
* [tests/test_crewai_runtime.py](/Users/alexander/RPS/tests/test_crewai_runtime.py)
* [doc/architecture/crewai_flows.md](/Users/alexander/RPS/doc/architecture/crewai_flows.md)
