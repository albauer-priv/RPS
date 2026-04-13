---
Version: 1.0
Status: Approved
Last-Updated: 2026-04-13
Owner: Orchestration / Planning
---
# FEAT: Phase Guardrails KPI Gating Relaxation

* **ID:** FEAT_phase_guardrails_kpi_gating_relaxation
* **Status:** Approved
* **Owner/Area:** Plan Week Orchestration / Phase Architect
* **Last-Updated:** 2026-04-13
* **Related:** `src/rps/orchestrator/plan_week.py`, `prompts/agents/phase_architect.md`, `tests/test_plan_pages.py`

---

## 1) Context / Problem

**Current behavior**

* The selected KPI moving-time-rate guidance is chosen in `SEASON_SCENARIO_SELECTION` and should flow into `SEASON_PLAN`.
* `phase_architect` loads `SEASON_PLAN` plus optional `SEASON_PHASE_FEED_FORWARD`.
* `plan_week(...)` previously also injected the selected KPI guidance directly into `phase_architect` runs, which made the optional feed-forward artefact effectively act like a binding prerequisite.

**Problem**

* Direct `PHASE_GUARDRAILS` creation can hard-stop with KPI gating errors, even when no applicable `SEASON_PHASE_FEED_FORWARD` exists for the requested phase range.
* This blocks storing Guardrails entirely, which then cascades into `PHASE_STRUCTURE` and `PHASE_PREVIEW` failures.
* The KPI source of truth should remain the selected scenario as carried into `SEASON_PLAN`, while feed-forward stays optional.

**Constraints**

* `phase_architect` is explicitly KPI-agnostic unless instructed via higher-level season intent.
* The fix must not remove KPI guidance from unrelated flows unless necessary.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Keep KPI guidance available to `PHASE_GUARDRAILS` via `SEASON_PLAN`.
* [x] Prevent optional `SEASON_PHASE_FEED_FORWARD` from becoming a binding blocker for `PHASE_GUARDRAILS`.
* [x] Keep Week-Planner behavior unchanged for now.
* [x] Add regression coverage that Phase-Architect user input no longer contains direct KPI-selection steering text.

**Non-Goals**

* [x] Redesign KPI gating across the full planning system.
* [x] Change `SEASON_PHASE_FEED_FORWARD` generation rules.

---

## 3) Proposed Behavior

**User/System behavior**

* `phase_architect` runs no longer receive `Selected KPI guidance: kpi_rate_band_selector ...` directly from `plan_week(...)`.
* `PHASE_GUARDRAILS` should derive KPI guidance from `SEASON_PLAN` body metadata / season context.
* `SEASON_PHASE_FEED_FORWARD` remains optional context and is ignored for `PHASE_GUARDRAILS` when it does not apply to the requested phase range.
* `week_planner` still receives KPI guidance, preserving current weekly steering behavior.

**UI impact**

* UI affected: No direct UI change

**Non-UI behavior (if applicable)**

* Components involved: `src/rps/orchestrator/plan_week.py`
* Contracts touched: prompt/orchestrator input composition only

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/orchestrator/plan_week.py`: remove direct KPI-selection injection from `phase_architect` request composition.
* `prompts/agents/phase_architect.md`: clarify that `SEASON_PHASE_FEED_FORWARD` is optional and only applicable when it matches the target phase context.
* `tests/test_plan_pages.py`: assert the phase-architect request omits the KPI guidance text while still executing the task.

**Data flow**

* Inputs: selected KPI guidance from scenario selection, stored Season Plan, optional Season→Phase feed-forward
* Processing: only week-planner requests receive the direct KPI selection block; phase-architect reads KPI context from Season Plan and uses feed-forward only when applicable
* Outputs: phase-architect requests remain KPI-agnostic at orchestration level unless season/feed-forward artefacts encode that intent

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: phase guardrails may no longer STOP on KPI gating derived solely from selected scenario guidance
* Fallback behavior: explicit feed-forward artefacts still remain available as the proper phase-intent steering mechanism

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with the existing `phase_architect` KPI-agnostic rule

**Impacted areas**

* UI: none directly
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: phase artefacts can be stored again in blocked cases
* Validation/tooling: regression test for prompt composition
* Deployment/config: none

**Required refactoring**

* narrow `plan_week(...)` user-input composition by agent role

---

## 6) Options & Recommendation

### Option A — Remove direct KPI-selection injection from Phase-Architect and clarify optional feed-forward

**Summary**

* Keep KPI selection for week planning, but stop sending it directly to phase-architect runs and explicitly mark feed-forward as optional for guardrails.

**Pros**

* Minimal change.
* Matches the prompt’s KPI-agnostic rule.
* Preserves Season Plan as the source of truth for KPI guidance.
* Addresses the concrete storage failure quickly.

**Cons**

* Does not redesign the deeper KPI/feed-forward interaction model.

### Option B — Add conditional KPI injection only when matching season-phase feed-forward exists

**Summary**

* Keep KPI injection for phase-architect, but only when a suitable feed-forward artefact is present.

**Pros**

* More targeted long-term policy shape.

**Cons**

* More logic, more workspace coupling, and still ambiguous without broader contract clarification.

### Recommendation

* Choose: Option A
* Rationale: the prompt already says KPI-agnostic unless explicitly instructed; direct injection was the wrong path, while Season Plan already carries the selected KPI guidance.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `phase_architect` user input in `plan_week(...)` no longer includes the selected KPI guidance block.
* [x] `phase_architect` prompt explicitly states that non-applicable `SEASON_PHASE_FEED_FORWARD` must not block `PHASE_GUARDRAILS`.
* [x] `week_planner` input composition remains unchanged.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: targeted `pytest` for plan-week prompt composition and scoped phase reruns

---

## 8) Migration / Rollout

**Migration strategy**

* None required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: restore the injected KPI block for phase-architect requests

---

## 9) Risks & Failure Modes

* Failure mode: weekly planning loses intended KPI context

  * Detection: week planner no longer receives KPI guidance
  * Safe behavior: guarded by targeted test that week-planner input remains unchanged
  * Recovery: restore KPI block only for week-planner requests

* Failure mode: phase guardrails still STOP for another feed-forward rule

  * Detection: logs still show `STOP` without `store_phase_guardrails`
  * Safe behavior: direct guardrails run fails clearly, without downstream ambiguity
  * Recovery: inspect phase-architect prompt/spec contract next

---

## 10) Observability / Logging

**New/changed events**

* no new event types

**Diagnostics**

* `runtime/athletes/<athlete_id>/logs/rps.log`
* captured `run_agent_multi_output(...)` user input in targeted tests

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_phase_guardrails_kpi_gating_relaxation.md`
* [ ] `CHANGELOG.md`

---

## 12) Link Map (no duplication; links only)

* `doc/specs/features/FEAT_plan_hub_phase_step_isolation.md`
* `doc/specs/features/FEAT_phase_architect_required_knowledge_injection.md`
* `prompts/agents/phase_architect.md`
* `specs/knowledge/_shared/sources/specs/load_estimation_spec.md`
