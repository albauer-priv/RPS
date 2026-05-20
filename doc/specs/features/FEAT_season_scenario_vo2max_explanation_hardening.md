---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-20
Owner: Planning
---
# FEAT: Season Scenario VO2max Explanation Hardening

* **ID:** FEAT_season_scenario_vo2max_explanation_hardening
* **Status:** Implemented
* **Owner/Area:** Planning / CrewAI season scenarios
* **Related:** `config/crewai/tasks.yaml`, `skills/season/scenario-generation/SKILL.md`, `src/rps/crewai_runtime/guardrails.py`

---

## 1) Context / Problem

**Current behavior**

* The `season_scenarios` task already tells the model that Scenario C may use `VO2MAX` only if explicitly justified.
* The runtime guardrail rejects Scenario C when `VO2MAX` is allowed but the ceiling-support role is not explained.

**Problem**

* The current instruction is not sharp enough to reliably place the explanation in the exact fields inspected by the guardrail.
* This causes repeated guardrail retries and failed `SEASON_SCENARIOS` runs.

**Constraints**

* No schema change.
* No guardrail logic change in this fix.
* Keep Scenario C ambitious through specificity/fatigue exposure first, not through default `VO2MAX`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make `VO2MAX` justification placement explicit in the active task and skill.
* [x] Require the explanation in `decision_notes` and/or `kpi_guardrail_notes`, which are the fields the guardrail already expects semantically.
* [x] Reduce avoidable guardrail retries for Scenario C.

**Non-Goals**

* [ ] No change to season-scenario schema.
* [ ] No change to the semantic guardrail itself.
* [ ] No attempt to force Scenario C to always use `VO2MAX`.

---

## 3) Proposed Behavior

**User/System behavior**

* When Scenario C includes `VO2MAX` in `allowed_domains`, the generated scenario must explicitly state that `VO2MAX` is only a sparse ceiling-support / fresh high-intensity permission.
* That explanation must be placed in `decision_notes` and/or `kpi_guardrail_notes`.
* If the model cannot justify `VO2MAX` that way, it should omit `VO2MAX` from Scenario C.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * `season_scenarios` task instruction
  * `skills/season/scenario-generation`
* Contracts touched:
  * `SEASON_SCENARIOS`

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/tasks.yaml`
  * sharpen task description for Scenario C + `VO2MAX`
* `skills/season/scenario-generation/SKILL.md`
  * add stronger field-placement rules and explicit wording expectations

**Data flow**

* Inputs: same season scenario context as before
* Processing: same generation path, but stricter instruction wording
* Outputs: same `SEASON_SCENARIOS` schema

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if no explicit `VO2MAX` rationale exists, Scenario C should omit `VO2MAX`

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: reinforces the existing season-scenario authority split

**Impacted areas**

* UI: none
* Pipeline/data: season-scenario generation prompt behavior
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: fewer guardrail retries expected
* Deployment/config: task/skill text only

**Required refactoring**

* None beyond task/skill wording updates.

---

## 6) Options & Recommendation

### Option A — sharpen task/skill wording only

**Summary**

* Keep the guardrail as-is and make the generation instructions more explicit about where and how the explanation must be written.

**Pros**

* Minimal change
* Directly targets the current failure mode

**Cons**

* Still relies on model compliance rather than schema-level enforcement

### Option B — relax or rewrite guardrail

**Summary**

* Make the guardrail broader or more permissive.

**Pros**

* Fewer retries

**Cons**

* Weakens the intended scenario semantics

### Recommendation

* Choose: Option A
* Rationale: the guardrail is correct; the instruction placement was too soft.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_scenarios` task text explicitly requires `VO2MAX` explanation placement in `decision_notes`/`kpi_guardrail_notes`.
* [x] `scenario-generation` skill explicitly tells the model to omit `VO2MAX` if it cannot provide that explanation.
* [x] Config bundle still loads.
* [x] Syntax/lint/type gates stay green.

---

## 8) Migration / Rollout

**Migration strategy**

* No migration needed.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert the task/skill wording.

---

## 9) Risks & Failure Modes

* Failure mode: the model still uses `VO2MAX` without explanation.
  * Detection: existing `season_scenarios_profile_quality` guardrail
  * Safe behavior: task retries then fails without persisting bad scenarios
  * Recovery: further sharpen instruction or adjust guardrail only if needed

---

## 10) Observability / Logging

**New/changed events**

* No new events.

**Diagnostics**

* `events.jsonl`
* `rps.log`
* guardrail failure reason on the season-scenarios step

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record the instruction hardening

---

## 12) Link Map

* Guardrails: [guardrails.py](/Users/alexander/RPS/src/rps/crewai_runtime/guardrails.py)
* Skills attachment: [crewai_skills_attachment.md](/Users/alexander/RPS/doc/architecture/crewai_skills_attachment.md)
