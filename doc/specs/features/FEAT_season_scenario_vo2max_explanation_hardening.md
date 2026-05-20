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

* The current instruction was not sharp enough to reliably place the explanation in the exact fields inspected by the guardrail.
* In addition, the guardrail only searched `decision_notes` and `constraint_summary`, while the task/skill also allowed the rationale in `kpi_guardrail_notes`.
* The `season_scenarios` task also exposed the full `read_only_workspace` tool surface although the run only needs `workspace_get_input` and `workspace_get_latest`.
* This caused repeated guardrail retries and bloated season-scenario runs.

**Constraints**

* No schema change.
* No schema change.
* Keep Scenario C ambitious through specificity/fatigue exposure first, not through default `VO2MAX`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make `VO2MAX` justification placement explicit in the active task and skill.
* [x] Require the explanation in `decision_notes` and/or `kpi_guardrail_notes`.
* [x] Make the guardrail read `kpi_guardrail_notes` in addition to the existing Scenario C story fields.
* [x] Reduce the `season_scenarios` task tool surface to the two actually needed workspace read tools.
* [x] Reduce avoidable guardrail retries for Scenario C.

**Non-Goals**

* [ ] No change to season-scenario schema.
* [ ] No attempt to force Scenario C to always use `VO2MAX`.

---

## 3) Proposed Behavior

**User/System behavior**

* When Scenario C includes `VO2MAX` in `allowed_domains`, the generated scenario must explicitly state that `VO2MAX` is only a sparse ceiling-support / fresh high-intensity permission.
* That explanation must be placed in `decision_notes` and/or `kpi_guardrail_notes`.
* If the model cannot justify `VO2MAX` that way, it should omit `VO2MAX` from Scenario C.
* The runtime guardrail now accepts the rationale from either field.
* The task receives only `workspace_get_input` and `workspace_get_latest`, not the full read-only workspace tool bundle.

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
  * reduce tool scope
* `skills/season/scenario-generation/SKILL.md`
  * add stronger field-placement rules and explicit wording expectations
* `src/rps/crewai_runtime/guardrails.py`
  * include `kpi_guardrail_notes` in Scenario C story evaluation
* `tests/test_crewai_runtime.py`
  * cover guardrail acceptance from `kpi_guardrail_notes`
  * cover narrow task tool scope

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

* Leaves the field mismatch between task/skill and guardrail unresolved

### Option B — align task/skill, guardrail, and tool scope

**Summary**

* Keep the guardrail intent, but align its searched fields with the prompt contract and remove unnecessary tools from the task.

**Pros**

* Fixes the actual mismatch
* Reduces token/tool noise

**Cons**

* Slightly broader code change than wording-only

### Recommendation

* Choose: Option B
* Rationale: the wording mattered, but the remaining failure came from a real field mismatch plus an unnecessarily broad tool surface.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_scenarios` task text explicitly requires `VO2MAX` explanation placement in `decision_notes`/`kpi_guardrail_notes`.
* [x] `scenario-generation` skill explicitly tells the model to omit `VO2MAX` if it cannot provide that explanation.
* [x] `season_scenarios_profile_quality` accepts a valid Scenario C rationale from `kpi_guardrail_notes`.
* [x] `season_scenarios` task exposes only `workspace_get_input` and `workspace_get_latest`.
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

* Failure mode: tool scope grows again and bloats prompt/tool registration.
  * Detection: task config / runtime telemetry
  * Safe behavior: no correctness loss, but higher noise and token overhead
  * Recovery: keep the task-scoped tools explicit

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
