---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-24
Owner: Planning
---
# FEAT: Resolved Athlete Context

* **ID:** FEAT_resolved_athlete_context
* **Status:** Implemented
* **Owner/Area:** Planning / Orchestrator
* **Last-Updated:** 2026-04-24

---

## 1) Context / Problem

**Current behavior**

* Athlete facts like `endurance_anchor_w`, `ambition_if_range`, `primary_disciplines`, and `body_mass_kg` exist in `ATHLETE_PROFILE`, but only a narrow subset is injected as generic user data.

**Problem**

* Agents still have to read or infer athlete facts that are already deterministic and immediately usable.

**Constraints**

* No schema changes.
* Keep raw `ATHLETE_PROFILE` access available where deeper detail is still needed.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Resolve athlete profile facts in code and inject them directly as planner/scenario context.
* [x] Reuse the same resolved athlete block across season, phase, and week orchestration.

**Non-Goals**

* [ ] Remove `ATHLETE_PROFILE` tool access entirely.
* [ ] Collapse all athlete profile detail into a single giant prompt dump.

---

## 3) Proposed Behavior

**User/System behavior**

* Orchestrators inject a compact `Resolved Athlete Context` block containing core deterministic athlete facts.
* `season_scenario` now also receives resolved context blocks, not just raw artefact instructions.

**UI impact**

* UI affected: No

---

## 4) Implementation Analysis

**Components / Modules**

* `resolved_context.py`: new athlete context builder
* `season_flow.py`: inject athlete context into season scenario + season planner
* `plan_week.py`: inject athlete context into phase/week planning
* `season_scenario.md`: honor resolved context

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none

**Impacted areas**

* Orchestrators
* Season-scenario prompt
* Planner prompt tests

---

## 6) Recommendation

* Resolve athlete facts in code and pass them directly.

---

## 7) Acceptance Criteria

* [x] `Resolved Athlete Context` injected into season scenario, season planner, and week/phase planning
* [x] `season_scenario` prompt honors resolved context blocks
* [x] Validation passes

---

## 8) Migration / Rollout

* None

---

## 9) Risks & Failure Modes

* Missing or partial athlete profile yields a partial or empty athlete context block.
* Safe behavior: planners fall back to existing raw artefact rules.

---

## 10) Observability / Logging

* Diagnostics through captured orchestrator `user_input` in tests.

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_resolved_athlete_context.md`
* [x] `CHANGELOG.md`

---

## 12) Link Map

* `specs/schemas/athlete_profile.schema.json`
* `doc/overview/how_to_plan.md`
