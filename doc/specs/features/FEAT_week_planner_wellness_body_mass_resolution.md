---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-24
Owner: Planning
---
# FEAT: Week Planner Wellness Body-Mass Resolution

* **ID:** FEAT_week_planner_wellness_body_mass_resolution
* **Status:** Implemented
* **Owner/Area:** Planning / Week Orchestrator
* **Last-Updated:** 2026-04-24
* **Related:** `ccb055f`, `0c5e6d3`

---

## 1) Context / Problem

**Current behavior**

* `week_planner` receives KPI-rate guidance and latest `WELLNESS`, but the agent can still STOP claiming `body_mass_kg` is semantically unusable.

**Problem**

* The contracts require `wellness.body_mass_kg` as the sole body-mass source for kJ/kg/h gating, but the week-planning prompt and orchestrator input do not name that field strongly enough.

**Constraints**

* No schema changes.
* Keep KPI gating enabled when valid `WELLNESS.data.body_mass_kg` exists.
* Preserve current STOP behavior when `body_mass_kg` is truly absent.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make `WELLNESS.data.body_mass_kg` explicit and authoritative in the week-planner path.
* [x] Prevent false STOPs when the latest `WELLNESS` artefact already contains usable body mass.

**Non-Goals**

* [ ] Rework KPI gating semantics.
* [ ] Change `WELLNESS` schema or data-pipeline write logic.

---

## 3) Proposed Behavior

**User/System behavior**

* When KPI gating is active, `plan_week(...)` resolves the latest `WELLNESS` artefact and injects an explicit instruction naming `WELLNESS.data.body_mass_kg` and its current numeric value.
* `week_planner` is instructed to use `WELLNESS.data.body_mass_kg` before emitting any STOP for missing body mass.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `src/rps/orchestrator/plan_week.py`, `prompts/agents/week_planner.md`
* Contracts touched: `data_pipeline__week_contract.md`, `load_estimation_spec.md`

---

## 4) Implementation Analysis

**Components / Modules**

* `plan_week.py`: resolve the latest `WELLNESS.data.body_mass_kg` and add a deterministic user-input hint.
* `week_planner.md`: make the field path and required handling explicit.

**Data flow**

* Inputs: latest `WELLNESS`, selected KPI guidance, current week request
* Processing: extract `data.body_mass_kg`, inject explicit instruction text
* Outputs: tighter week-planner prompt context; no new artefacts

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if `WELLNESS.data.body_mass_kg` is absent, the previous STOP path remains valid

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: reinforce existing data-pipeline contract rather than change it

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: read latest `WELLNESS`
* Validation/tooling: prompt and orchestrator tests
* Deployment/config: none

**Required refactoring**

* Add a small helper for resolving the latest `WELLNESS.data.body_mass_kg`

---

## 6) Options & Recommendation

### Option A — Explicit orchestrator + prompt guidance

**Summary**

* Resolve `body_mass_kg` in code and tell the agent exactly where to use it.

**Pros**

* Small change
* Deterministic
* Keeps KPI gating intact

**Cons**

* Still relies on the agent following prompt instructions

**Risk**

* Low; scoped to week-planner context text

### Option B — Disable KPI gating whenever body mass is not pre-confirmed

**Summary**

* Downgrade to non-KPI week planning more often.

**Pros**

* Avoids STOPs

**Cons**

* Loses valid KPI governance even when `WELLNESS` already contains body mass

### Recommendation

* Choose: Option A
* Rationale: it preserves the existing contract and fixes the actual discovery failure.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `plan_week(...)` injects explicit `WELLNESS.data.body_mass_kg` guidance when available.
* [x] `week_planner.md` states that `WELLNESS.data.body_mass_kg` is the authoritative KPI-gating field.
* [x] Validation passes: targeted pytest, `py_compile`, lint, type check
* [x] No regressions in phase/week orchestration tests
* [x] Performance guardrail: no additional heavy IO beyond one latest-artifact read

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert prompt/orchestrator change

---

## 9) Risks & Failure Modes

* Failure mode: latest `WELLNESS` lacks `data.body_mass_kg`
  * Detection: week-planner still STOPs for missing body mass
  * Safe behavior: STOP remains explicit and actionable
  * Recovery: refresh data pipeline or add body mass to `WELLNESS`

---

## 10) Observability / Logging

**New/changed events**

* None; existing week-planner STOP text remains the primary diagnostic signal.

**Diagnostics**

* `rps.log` week-planner STOP text
* Captured orchestrator input in tests

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_week_planner_wellness_body_mass_resolution.md` — capture rationale and scope
* [x] `CHANGELOG.md` — record the orchestration/prompt hardening

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Validation / runbooks: `doc/overview/how_to_plan.md`
* Contracts: `specs/knowledge/_shared/sources/contracts/data_pipeline__week_contract.md`
* Load estimation: `specs/knowledge/_shared/sources/specs/load_estimation_spec.md`
