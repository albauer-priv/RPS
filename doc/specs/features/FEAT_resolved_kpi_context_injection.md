---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-24
Owner: Planning
---
# FEAT: Resolved KPI Context Injection

* **ID:** FEAT_resolved_kpi_context_injection
* **Status:** Implemented
* **Owner/Area:** Planning / Orchestrator
* **Last-Updated:** 2026-04-24
* **Related:** `FEAT_week_planner_wellness_body_mass_resolution`

---

## 1) Context / Problem

**Current behavior**

* Planner agents can read `KPI_PROFILE` and `SEASON_SCENARIO_SELECTION`, but deterministic KPI facts are only injected in a minimal free-text form.

**Problem**

* The agent still has to search, reconstruct, or re-interpret KPI bands that are already known in code.
* This creates avoidable STOPs and prompt drift.

**Constraints**

* No schema changes.
* Keep `KPI_PROFILE` as the canonical source for moving-time-rate bands.
* Keep `SEASON_SCENARIO_SELECTION` as the canonical source for the selected segment.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Resolve KPI bands in code and pass them directly to planner agents.
* [x] Include both the selected band and the available `KPI_PROFILE` bands in deterministic planner context.

**Non-Goals**

* [ ] Remove `KPI_PROFILE` from workspace tools.
* [ ] Change KPI profile schema semantics.

---

## 3) Proposed Behavior

**User/System behavior**

* The orchestrator constructs a `Resolved KPI Context` block from:
  * latest `KPI_PROFILE.data.durability.moving_time_rate_guidance`
  * latest `SEASON_SCENARIO_SELECTION.data.kpi_moving_time_rate_guidance_selection`
* Planner agents receive:
  * selected segment
  * selected `w_per_kg`
  * selected `kj_per_kg_per_hour`
  * available KPI bands from `KPI_PROFILE`
  * source metadata like `derived_from` and `notes`

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `season_flow.py`, `plan_week.py`
* Contracts touched: `load_estimation_spec.md`, `season_scenario_selection_interface_spec.md`, `kpi_profile.schema.json`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/orchestrator/resolved_context.py`: shared resolved KPI context builder
* `src/rps/orchestrator/season_flow.py`: inject shared KPI context into season planning
* `src/rps/orchestrator/plan_week.py`: inject shared KPI context into week planning

**Data flow**

* Inputs: latest `KPI_PROFILE`, latest `SEASON_SCENARIO_SELECTION`
* Processing: resolve structured bands and selected segment into plain deterministic planner text
* Outputs: richer planner prompt context; no new artefacts

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if profile/selection is missing or malformed, inject nothing and preserve current planner behavior

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with the “code resolves facts, agents reason within facts” direction

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: read latest `KPI_PROFILE` and `SEASON_SCENARIO_SELECTION`
* Validation/tooling: prompt/orchestrator tests
* Deployment/config: none

**Required refactoring**

* Centralize KPI context resolution instead of duplicating partial free-text builders

---

## 6) Options & Recommendation

### Option A — Shared resolved KPI context block

**Summary**

* Build a structured plain-text context block in code and inject it into planners.

**Pros**

* Deterministic
* Reusable across planners
* Removes needless agent search/reconstruction

**Cons**

* Slightly larger prompt context

**Risk**

* Low

### Option B — Keep only selected-segment text

**Summary**

* Preserve current narrow injection and rely on tool usage for detail.

**Pros**

* Smaller prompts

**Cons**

* Keeps current ambiguity and search burden

### Recommendation

* Choose: Option A
* Rationale: deterministic values should be resolved in code, not rediscovered by the model.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_planner` receives resolved KPI context directly from code
* [x] `week_planner` receives resolved KPI context directly from code
* [x] Selected `kj_per_kg_per_hour` range is explicitly injected
* [x] Validation passes: targeted pytest, `py_compile`, lint, type check
* [x] No regressions in season/week orchestrator tests

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert shared resolved-context helper and callers

---

## 9) Risks & Failure Modes

* Failure mode: malformed `KPI_PROFILE` lacks valid bands
  * Detection: missing resolved KPI block in tests/log-driven debugging
  * Safe behavior: planners fall back to current behavior
  * Recovery: refresh/fix `KPI_PROFILE`

---

## 10) Observability / Logging

**New/changed events**

* None

**Diagnostics**

* Captured orchestrator `user_input` in tests

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_resolved_kpi_context_injection.md` — rationale and scope
* [x] `CHANGELOG.md` — planner context injection update

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Planning flow: `doc/overview/how_to_plan.md`
* KPI schema: `specs/schemas/kpi_profile.schema.json`
* Selection schema: `specs/schemas/season_scenario_selection.schema.json`
* Load estimation: `specs/knowledge/_shared/sources/specs/load_estimation_spec.md`
