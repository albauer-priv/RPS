---
Version: 1.0
Status: Approved
Last-Updated: 2026-04-13
Owner: UI / Orchestration
---
# FEAT: Plan Hub Phase Step Isolation

* **ID:** FEAT_plan_hub_phase_step_isolation
* **Status:** Approved
* **Owner/Area:** Plan Hub UI / Plan Week Orchestrator
* **Last-Updated:** 2026-04-13
* **Related:** `src/rps/ui/pages/plan/hub.py`, `src/rps/orchestrator/plan_week.py`, `tests/test_plan_pages.py`

---

## 1) Context / Problem

**Current behavior**

* Plan Hub direct action buttons for phase artefacts queue regular scoped runs.
* Internal phase artefacts remain split into `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`.
* `plan_week(...)` also auto-escalates from forced phase steps into later phase/week outputs.

**Problem**

* Earlier user-facing phase actions exposed internal artefact boundaries too directly.
* Guardrails-only reruns could fail because downstream phase artefacts were incorrectly pulled in.

**Constraints**

* Direct actions must still use the existing run-store + worker path.
* `Week Plan` and `Build Workouts` may still auto-add required predecessors.
* Orchestrated runs must keep the full cascade semantics.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Internal `PHASE_GUARDRAILS` forced runs stay isolated when explicitly requested by the system.
* [x] User-facing `Phase` reruns create all required phase artefacts together.
* [x] Internal phase dependency handling stays correct for week/workout planning.

**Non-Goals**

* [x] Changing orchestrated full-plan execution semantics.
* [x] Removing prerequisite checks for later phase/week outputs.

---

## 3) Proposed Behavior

**User/System behavior**

* A user-facing scoped run for `Phase` queues `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`.
* A forced internal `PHASE_GUARDRAILS` execution inside `plan_week(...)` still stops successfully after Guardrails exists for the exact phase range.
* Direct actions for week/workout steps remain dependency-aware, but only for prerequisites, not unrelated downstream outputs.

**UI impact**

* UI affected: Yes
* If Yes: `Plan -> Plan Hub` direct action buttons and `Run scoped` step selection behavior

### UI Flow (Mermaid)

```mermaid
flowchart TD
  A["Plan Hub Phase Card"] --> B{"Selected scope"}
  B -->|Phase| C["Queue PHASE_GUARDRAILS, PHASE_STRUCTURE, PHASE_PREVIEW"]
  B -->|Week Plan| D["Queue WEEK_PLAN plus missing phase prerequisites"]
  B -->|Build Workouts| E["Queue WORKOUT_EXPORT plus missing week/phase prerequisites"]
  C --> F["Worker executes isolated phase run"]
  D --> F
  E --> F
```

**Non-UI behavior (if applicable)**

* Components involved: `src/rps/ui/pages/plan/hub.py`, `src/rps/orchestrator/plan_week.py`
* Contracts touched: run-store step composition only

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/ui/pages/plan/hub.py`: present one user-facing `Phase` scope while keeping internal phase readiness available for dependency checks.
* `src/rps/orchestrator/plan_week.py`: treat isolated forced internal phase steps as valid terminal runs once their requested artefacts exist.
* `tests/test_plan_pages.py`: add regression tests for both queue composition and isolated plan-week execution.

**Data flow**

* Inputs: scoped run scope, forced step ids, exact-range artefact existence
* Processing: build only necessary steps, execute only requested phase target, short-circuit success before week planning when appropriate
* Outputs: successful isolated phase reruns without downstream failures

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: scoped phase direct actions become narrower and more correct
* Fallback behavior: downstream planning remains available via explicit later actions or orchestrated runs

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns better with scoped planning semantics in `AGENTS.md`

**Impacted areas**

* UI: direct/scoped phase action behavior
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: scoped runs contain fewer inappropriate steps
* Validation/tooling: regression coverage added
* Deployment/config: none

**Required refactoring**

* isolate phase scope mappings
* add explicit plan-week early-exit logic for isolated phase force runs

---

## 6) Options & Recommendation

### Option A — Isolate phase direct actions and add orchestrator short-circuit

**Summary**

* Keep the existing worker path, but make phase direct actions represent exactly the chosen phase artefact.

**Pros**

* Matches user intent exactly.
* Keeps worker/orchestrator architecture intact.
* Prevents false failures from unrelated downstream artefacts.

**Cons**

* Adds one more branching case inside `plan_week(...)`.

### Option B — Keep broad scoped queues and only change UI labels

**Summary**

* Preserve current cascade semantics and document them better.

**Pros**

* Minimal code change.

**Cons**

* Still wrong for the reported user workflow.

### Recommendation

* Choose: Option A
* Rationale: the bug is semantic, not cosmetic; the execution path must match the button label.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] User-facing `Phase` scoped runs queue `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`.
* [x] Isolated `force_steps=["PHASE_GUARDRAILS"]` runs can succeed without creating structure/preview/week artefacts.
* [x] Existing `Week Plan` and `Build Workouts` dependency behavior remains intact.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `pytest -q tests/test_plan_pages.py -k 'plan_hub or plan_week_force'`

---

## 8) Migration / Rollout

**Migration strategy**

* None required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the scope mapping and isolated force-step logic

---

## 9) Risks & Failure Modes

* Failure mode: isolated phase runs stop too early

  * Detection: requested artefact missing after successful completion
  * Safe behavior: run should fail if the requested exact-range artefact still does not exist
  * Recovery: inspect exact-range success check in `plan_week(...)`

* Failure mode: week/workout scoped runs lose predecessor auto-creation

  * Detection: existing `Week Plan` / `Build Workouts` tests fail
  * Safe behavior: validation blocks merge
  * Recovery: restore prerequisite expansion only for week/workout scopes

---

## 10) Observability / Logging

**New/changed events**

* no new event types
* existing `plan_week` logs should still distinguish isolated internal phase reruns from full user-facing phase runs

**Diagnostics**

* `runtime/athletes/<athlete_id>/logs/rps.log`
* Plan Hub run-store entries in `runtime/athletes/<athlete_id>/runs/`

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_plan_hub_phase_step_isolation.md` — document the scoped isolation fix
* [x] `CHANGELOG.md` — record the bug fix

---

## 12) Link Map (no duplication; links only)

* `doc/specs/features/FEAT_plan_hub_direct_step_actions.md`
* `doc/specs/features/FEAT_plan_hub_scoped_force_reruns.md`
* `doc/overview/how_to_plan.md`
* `doc/overview/artefact_flow.md`
