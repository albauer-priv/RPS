---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-28
Owner: Planning Runtime
---
# FEAT: Fix Contract Validation Assembly Bugs

* **ID:** FEAT_contract_validation_assembly_fix
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-28
* **Related:** FEAT_selected_scenario_contract_chain, FEAT_strict_season_selection_binding

---

## 1) Context / Problem

**Current behavior**

* Season planning derives a deterministic selected-scenario contract and uses guardrail validation before writing `SEASON_PLAN`.
* Week planning carries inherited planning posture in deterministic week context.

**Problem**

* `season_bundle_matches_contract(...)` assembled a synthetic Season candidate without `data.selected_scenario_contract`, then validated it against a deterministic authority that required the field.
* `validate_week_plan_against_week_context(...)` compared `week_calendar_context.inherited_planning_posture` against itself, so inherited-posture drift in a `WEEK_PLAN` payload could not be detected.

**Constraints**

* Fix must stay narrow and runtime-safe.
* No schema redesign or `meta.version_key` repair is included.
* Code-owned deterministic contracts remain the authority.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Fix the synthetic Season candidate assembly so deterministic selected-scenario contract validation works.
* [x] Fix the Week inherited-planning-posture comparison so payload-vs-authority drift is detectable.
* [x] Add regression tests that hit the real guardrail and contract-validation paths.

**Non-Goals**

* [x] No `meta.version_key` persistence repair.
* [x] No broader schema redesign; only the minimal `WEEK_PLAN.data.inherited_planning_posture` field addition needed to persist the canonical Week contract path.

---

## 3) Proposed Behavior

**User/System behavior**

* Valid Season planning runs no longer fail at final normalized contract validation because a code-built synthetic candidate forgot to carry `data.selected_scenario_contract`.
* Week validation now checks `data.inherited_planning_posture` in the `WEEK_PLAN` payload against deterministic week authority instead of comparing context to itself.

**UI impact**

* UI affected: Indirectly
* If Yes: Season Plan creation no longer fails late on this internal guardrail bug; downstream readiness can advance when the plan is otherwise valid.

**Non-UI behavior (if applicable)**

* Components involved: CrewAI guardrails, planning-contract validators, deterministic week-plan writer
* Contracts touched: `SEASON_PLAN.data.selected_scenario_contract`, `WEEK_PLAN.data.inherited_planning_posture`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/guardrails.py`: fix Season synthetic-candidate assembly and add a narrow defensive check.
* `src/rps/planning/contracts.py`: correct Week payload-vs-authority comparison.
* `src/rps/workouts/generator.py`: inject canonical `data.inherited_planning_posture` into deterministic `WEEK_PLAN` output.

**Data flow**

* Inputs: runtime guardrail context, deterministic season/phase/week contract blocks
* Processing: synthetic candidate assembly and contract comparison
* Outputs: valid Season/Week artifacts or deterministic contract failures only when payloads actually drift

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: `WEEK_PLAN` gains one persisted contract field without changing schema version
* Validator implications: Season and Week contract checks now validate the intended payload fields

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, with stricter correctness for Week payload validation
* Breaking changes: Week plans that omit `data.inherited_planning_posture` would fail once validated against real authority, so the deterministic week writer now injects the field
* Fallback behavior: none; deterministic authority remains required when present

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns with active planning-layer rule and code-owned authority

**Impacted areas**

* UI: indirect readiness unblocking after successful Season Plan
* Pipeline/data: deterministic contract injection in Season/Week validation paths
* Renderer: none
* Workspace/run-store: no storage model changes
* Validation/tooling: tighter real payload-vs-authority checks
* Deployment/config: none

**Required refactoring**

* Fix synthetic guardrail candidate construction
* Fix one tautological contract comparison

---

## 6) Options & Recommendation

### Option A — Fix synthetic assembly and payload comparison only

**Summary**

* Patch the Season guardrail candidate, patch the Week validator, and ensure the deterministic Week writer emits the checked field.

**Pros**

* Narrow and low risk
* Directly addresses the observed runtime failures

**Cons**

* Leaves unrelated metadata issues out of scope

**Risk**

* Low

### Option B — Broader contract/schema redesign

**Summary**

* Redesign contract persistence and schema requirements together.

**Pros**

* Could clean up adjacent issues in one pass

**Cons**

* Larger blast radius
* Unnecessary for the current failure

### Recommendation

* Choose: Option A
* Rationale: it fixes the real runtime bug class with minimal scope and clear regression coverage

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Valid normalized Season bundle no longer fails because `data.selected_scenario_contract` is missing from the synthetic candidate.
* [x] Week contract validation compares `data.inherited_planning_posture` against deterministic authority.
* [x] Deterministic `WEEK_PLAN` generation emits `data.inherited_planning_posture`.
* [x] Validation passes: `python3 -m py_compile`, `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`
* [x] No regressions in targeted Season/Week contract tests

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* No feature flag
* Safe rollback: revert the narrow runtime validation and generator changes

---

## 9) Risks & Failure Modes

* Failure mode: Week payloads generated outside the deterministic writer path still omit `data.inherited_planning_posture`

  * Detection: contract validation failures with `week_inherited_planning_posture_mismatch_missing`
  * Safe behavior: fail closed instead of silently accepting drift
  * Recovery: route generation through deterministic writer or inject the missing code-owned field

* Failure mode: future synthetic candidate assembly forgets another contract field

  * Detection: builder-specific guardrail message
  * Safe behavior: fail early with a code-owned assembly error instead of misclassifying as model drift
  * Recovery: patch the synthetic builder

---

## 10) Observability / Logging

**New/changed events**

* No new event families
* Season guardrail now returns a builder-specific failure message if synthetic selected-scenario contract injection is missing

**Diagnostics**

* Check `SEASON_BUNDLE_NORMALIZED_CONTRACT_FAILED`
* Check planning contract test failures for Week/Phase drift paths

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record the Season/Week contract-validation fix
* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — add implemented feature entry
