---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Runtime / Planning
---
# FEAT: Specialist Execution And Model Telemetry

* **ID:** FEAT_specialist_execution_and_model_telemetry
* **Status:** Implemented
* **Owner/Area:** CrewAI runtime / planning orchestration
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_hierarchical_crewai_execution, FEAT_crewai_event_listener_runtime_telemetry

---

## 1) Context / Problem

**Current behavior**

* Season, Phase, and Week planning use a hierarchical CrewAI execution path with a manager agent and manager LLM.
* Runtime profiles assign cheaper models to specialists, but task execution frequently appears under the manager agent in telemetry and provider usage.

**Problem**

* The configured specialist model profiles do not reliably determine actual cost, because hierarchical execution lets the manager absorb specialist work.
* Runtime telemetry shows task and agent names, but not enough model detail to explain real provider usage.

**Constraints**

* No schema changes.
* Existing planning contracts, review loops, and artifact writers must remain stable.
* Runtime telemetry must stay compact and safe for run-store storage.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make Season, Phase, and Week planning execute specialist tasks on their assigned specialist agents.
* [x] Keep manager agents focused on final synthesis rather than general task execution.
* [x] Add compact telemetry fields that reveal assigned agent and actual model per task.

**Non-Goals**

* [x] No rewrite of review crews in this step.
* [x] No change to planning artifact schemas or contract validators.

---

## 3) Proposed Behavior

**User/System behavior**

* Season, Phase, and Week planning crews run as explicit sequential multi-agent crews.
* Each specialist task is executed by its configured task agent.
* Manager agents still own the final synthesis task, but no longer serve as the hierarchical execution brain for the whole planning crew.
* `events.jsonl` and normal logs include compact model detail for task execution.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `crewai_backend`, `telemetry`, runtime profiles, tests
* Contracts touched: runtime telemetry event payloads only

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/crewai_backend.py`: switch planning crews from hierarchical manager-driven execution to sequential specialist execution.
* `src/rps/crewai_runtime/telemetry.py`: add compact runtime metadata for assigned agent and model.
* `tests/test_crewai_runtime.py`: lock down execution mode and telemetry payload expectations.

**Data flow**

* Inputs: existing task blueprints, agent blueprints, runtime profiles, task contexts
* Processing: build specialist agents, attach runtime metadata, run sequential planning crew, emit enriched telemetry
* Outputs: unchanged planning bundles/artifacts; richer run-store telemetry events

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, for artifact outputs and public task behavior
* Breaking changes: telemetry payloads gain new optional fields; planning crew execution mode changes internally
* Fallback behavior: review crews stay on current execution path

**Conflicts with ADRs / Principles**

* Potential conflicts: none; this preserves current planning ownership and contract boundaries
* Resolution: manager authority remains only on final synthesis tasks

**Impacted areas**

* UI: none directly
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: telemetry event rows gain model/assigned-agent fields
* Validation/tooling: runtime tests updated
* Deployment/config: no env changes

**Required refactoring**

* Introduce a generic multi-agent execution mode flag in CrewAI backend.
* Track runtime metadata on task and agent objects for telemetry enrichment.

---

## 6) Options & Recommendation

### Option A — Keep hierarchical crews and only lower manager model

**Summary**

* Leave execution architecture unchanged and reduce manager cost by changing model profiles.

**Pros**

* Smaller code change

**Cons**

* Specialist model profiles still do not reliably control actual execution cost
* Root cause remains

**Risk**

* Continued mismatch between configured and real runtime behavior

### Option B (recommended) — Sequential specialist execution for planning crews

**Summary**

* Keep the same planning task graph, but execute it as a sequential multi-agent crew so specialist agents really run their assigned tasks.

**Pros**

* Runtime profiles start to matter in practice
* Lower cost concentration in manager roles
* Clearer telemetry

**Cons**

* Slightly less “autonomous” CrewAI manager behavior

### Recommendation

* Choose: Option B
* Rationale: it addresses the actual cost/control problem instead of only masking it with profile changes

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season planning no longer injects `manager_agent` / `manager_llm` into the planning crew execution path.
* [x] Phase planning no longer injects `manager_agent` / `manager_llm` into the planning crew execution path.
* [x] Week planning no longer injects `manager_agent` / `manager_llm` into the planning crew execution path.
* [x] Telemetry includes compact `model` and `assigned_agent` fields for task execution events when available.
* [x] Validation passes: `py_compile`, lint, typecheck, targeted CrewAI tests
* [x] No regressions in persisted planning outputs and review/writer handoff

---

## 8) Migration / Rollout

**Migration strategy**

* None required; runtime-only behavior change

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: restore hierarchical execution mode for planning crews

---

## 9) Risks & Failure Modes

* Failure mode: sequential execution loses required context between tasks
  * Detection: planning review failures or missing context task assertions
  * Safe behavior: task creation raises on missing context dependencies
  * Recovery: revert affected crew to hierarchical mode while investigating

* Failure mode: telemetry logs empty or misleading model fields
  * Detection: targeted runtime telemetry tests
  * Safe behavior: keep existing agent/task labels even if model is unavailable
  * Recovery: fall back to label-only telemetry

---

## 10) Observability / Logging

**New/changed events**

* `CREW_TASK_PREPARED`: may include `model`
* `CREW_TASK_STARTED`: may include `assigned_agent` and `model`
* `CREW_TASK_FINISHED`: may include `assigned_agent` and `model`
* `CREW_TASK_FAILED`: may include `assigned_agent` and `model`

**Diagnostics**

* `runtime/athletes/<athlete>/runs/<run_id>/events.jsonl`
* `rps.log`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `CHANGELOG.md` — record planning execution strategy and telemetry enrichment
