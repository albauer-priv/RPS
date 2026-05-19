---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Season Specialist Scope Separation

* **ID:** FEAT_season_specialist_scope_separation
* **Status:** Implemented
* **Owner/Area:** Season Planning
* **Last-Updated:** 2026-05-19
* **Related:** `season_constraint_review`, `season_historical_context_review`, `season_kpi_guidance_review`

---

## 1) Context / Problem

**Current behavior**

* The season constraint, historical-context, and KPI-guidance specialists all complete successfully and have the right tools.
* Their outputs overlap heavily, especially around fatigue risk, event handling, phase corridor reminders, and fixed-rest-day constraints.

**Problem**

* The overlapping outputs make specialist boundaries fuzzy and reduce the value of the specialist-first sequential season crew.
* KPI guidance in particular drifts into constraint and progression authority that should stay with other specialists.

**Constraints**

* No schema changes.
* No new dependencies.
* Keep the existing specialist tool surface stable unless a concrete retrieval gap exists.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Narrow the written scope of season constraint, historical, and KPI specialists so each role produces distinct output.
* [x] Encode the separation consistently in task descriptions, prompts, and skills.
* [x] Add regression checks that keep those boundaries from regressing silently.

**Non-Goals**

* [x] Do not redesign season schemas or output models.
* [x] Do not change the season planning crew topology or tool surface for these roles.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_constraint_specialist` owns binding athlete, availability, logistics, and event constraints.
* `season_historical_context_specialist` owns recent load/recovery/re-entry evidence only.
* `season_kpi_guidance_specialist` owns KPI-band, moving-time-rate, and pacing-semantics interpretation only.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `config/crewai/tasks.yaml`
  * `prompts/agents/*.md`
  * `skills/season/*.md`
  * `tests/test_crewai_runtime.py`
* Contracts touched:
  * internal specialist task contracts only

---

## 4) Implementation Analysis

**Components / Modules**

* `tasks.yaml`: tighten specialist descriptions and make exclusions explicit.
* agent prompts: narrow role-specific hard rules.
* season skills: make method boundaries explicit and retrieval policy consistent.
* tests: assert the role wording does not drift back into overlap-heavy language.

**Data flow**

* Inputs: existing injected season context and current workspace tools.
* Processing: no pipeline change; only specialist instruction scope changes.
* Outputs: same structured review payloads, but with cleaner topical separation.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: existing specialist outputs still validate if wording is broader

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: n/a

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: regression tests only
* Deployment/config: task/prompt/skill text only

**Required refactoring**

* clarify season specialist ownership in task descriptions
* align prompts and skills with the same boundary language

---

## 6) Options & Recommendation

### Option A — Tight instruction separation

**Summary**

* Keep the same architecture and tools, but make specialist ownership explicit.

**Pros**

* Minimal blast radius
* Cheap to validate
* Preserves the current specialist-first flow

**Cons**

* Relies on prompt/task discipline rather than structural model changes

**Risk**

* Some overlap can still happen if downstream managers compress specialist outputs too aggressively

### Option B — New specialist schemas per role

**Summary**

* Introduce narrower models for constraint/history/KPI roles.

**Pros**

* Stronger structural enforcement

**Cons**

* Larger schema and normalization change
* Much higher regression risk

### Recommendation

* Choose: Option A
* Rationale: the problem is role drift, not missing structure or missing tools

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_constraint_review` explicitly prioritizes athlete/availability/logistics/event constraints rather than KPI semantics.
* [x] `season_historical_context_review` explicitly prioritizes recent load/recovery/re-entry evidence and avoids authoring season governance directly.
* [x] `season_kpi_guidance_review` explicitly excludes rest-day, corridor, taper, and event-handling authority as primary content.
* [x] Related prompts and skills use the same separation.
* [x] Validation passes: `py_compile`, lint, typecheck, targeted runtime tests.

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* No feature flag
* Safe rollback: revert task/prompt/skill wording changes

---

## 9) Risks & Failure Modes

* Failure mode: specialists still repeat each other
  * Detection: season run logs and specialist outputs remain overlap-heavy
  * Safe behavior: outputs still stay valid and non-blocking
  * Recovery: further narrow prompts or introduce stronger manager-side consumption rules

---

## 10) Observability / Logging

* No new log events.
* Use existing conversation/completion logs to verify topical separation.

---

## 11) Documentation Updates

* Update task descriptions
* Update agent prompts
* Update season skills
* Update changelog

---

## 12) Link Map

* [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
* [tasks.yaml](/Users/alexander/RPS/config/crewai/tasks.yaml)
* [constraint_specialist.md](/Users/alexander/RPS/prompts/agents/constraint_specialist.md)
* [historical_context_specialist.md](/Users/alexander/RPS/prompts/agents/historical_context_specialist.md)
* [kpi_guidance_specialist.md](/Users/alexander/RPS/prompts/agents/kpi_guidance_specialist.md)
* [constraint-synthesis skill](/Users/alexander/RPS/skills/season/constraint-synthesis/SKILL.md)
* [historical-context skill](/Users/alexander/RPS/skills/season/historical-context/SKILL.md)
* [kpi-guidance skill](/Users/alexander/RPS/skills/season/kpi-guidance/SKILL.md)
