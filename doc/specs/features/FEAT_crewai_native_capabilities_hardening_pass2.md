---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-18
Owner: CrewAI Runtime
---
# FEAT: CrewAI Native Capabilities Hardening Pass 2

* **ID:** FEAT_crewai_native_capabilities_hardening_pass2
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime
* **Last-Updated:** 2026-05-18
* **Related:** `config/crewai/tasks.yaml`, `src/rps/agents/crewai_backend.py`, `src/rps/crewai_runtime/flows.py`, `src/rps/crewai_runtime/telemetry.py`

---

## 1) Context / Problem

**Current behavior**

* CrewAI agents, tasks, structured outputs, task context, guardrails, callbacks, skills, knowledge, memory, and planning profiles are active.
* Runtime read tools are constructed as one broad tool list and attached broadly.
* Flow wrappers carry typed state, but some failure paths still depend on caller-side exception handling.

**Problem**

* CrewAI-native task capability scoping should be stricter: context reader tasks need read tools; writer and synthesis tasks usually do not.
* Persisted artifact tasks need explicit task-level callbacks in addition to crew-level lifecycle events.
* Flow state should capture failure reasons and produced refs consistently for missing upstream, rejected review, and store-failed paths.

**Constraints**

* No new dependencies.
* No artifact schema changes.
* No native CrewAI file-processing activation in this pass.
* Existing deterministic context and guarded persistence remain authoritative.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add task-level CrewAI callbacks for persisted artifact and internal tasks.
* [x] Scope CrewAI tools at Task level using `tasks.yaml`.
* [x] Keep agents narrowly scoped; do not attach the full read-tool suite to every agent.
* [x] Expand Flow failure recording so failures are visible in typed state.
* [x] Add future CrewAI-native opportunities to the backlog.

**Non-Goals**

* [x] No CrewAI Files dependency.
* [x] No broad MCP/App activation.
* [x] No change to artifact schemas.
* [x] No replacement of RPS preview/confirm/apply with native `human_input`.

---

## 3) Proposed Behavior

**System behavior**

* `tasks.yaml` can define `tools:` per task. Supported values:
  * `read_only_workspace`: all existing workspace read tools plus knowledge search.
  * explicit list of tool names.
  * empty list for no task tools.
* Agents are constructed without the broad runtime tool list; tools are attached to individual CrewAI tasks.
* Every runtime-built task receives a task callback that emits compact telemetry without prompt/output leakage.
* Flow wrappers convert caught execution exceptions into `ok=false`, `failure_reason`, and `errors[]` state.

**UI impact**

* UI affected: No.

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/tasks.yaml`: task-specific tool declarations.
* `src/rps/agents/crewai_backend.py`: tool map construction, task tool filtering, task callback wiring.
* `src/rps/crewai_runtime/telemetry.py`: callback supports explicit task labels and callback event type.
* `src/rps/crewai_runtime/flows.py`: result/failure state helpers.
* `doc/overview/feature_backlog.md`: deferred CrewAI-native features.

**Data flow**

* Inputs: task blueprint config, runtime tool registry, flow runner result.
* Processing: select tools per task; execute; callbacks and guardrails emit compact events; Flow stores result/failure refs.
* Outputs: artifacts unchanged; run-store diagnostics improved.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: Tasks without `tools:` default to no task tools, while existing deterministic prompt/context injection remains intact.

**Impacted areas**

* Workspace/run-store: more task callback events.
* CrewAI runtime: tighter capability scoping.
* Tests: expanded runtime tests.

---

## 6) Options & Recommendation

### Option A — Task-Scoped Native Tools

**Summary**

* Attach tools at CrewAI Task construction using declarative `tasks.yaml`.

**Pros**

* Least privilege per task.
* Matches CrewAI task capability semantics.

**Cons**

* Tasks that truly need tools must declare them.

### Recommendation

* Choose: Option A.
* Rationale: deterministic context already carries most planning facts; tool access should be explicit and task-bounded.

---

## 7) Acceptance Criteria

* [x] Context-reader tasks receive read-only workspace tools.
* [x] Writer tasks receive no read tools.
* [x] Task-level callbacks emit compact telemetry.
* [x] Flow wrappers record failure reasons in typed state.
* [x] Tests cover task tool filtering and callback wiring.

---

## 8) Migration / Rollout

* No data migration.
* Additive YAML config.
* Safe rollback: remove/adjust `tools:` declarations or disable callback wiring.

---

## 9) Risks & Failure Modes

* Failure mode: a specialist unexpectedly needed a read tool.
  * Detection: task failure or explicit missing-context error.
  * Safe behavior: no partial artifact persistence.
  * Recovery: add the specific tool to that task's `tools:` list.
* Failure mode: callback payload differs by CrewAI version.
  * Detection: compact fallback labels in run-store.
  * Safe behavior: callback never logs raw prompt/output.

---

## 10) Observability / Logging

**New/changed events**

* `CREW_TASK_CALLBACK_COMPLETED`: task-level callback event with crew, task, agent, and output format.
* Flow state `failure_reason`: set when a runner raises or returns `ok=false`.

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_crewai_native_capabilities_hardening_pass2.md`
* [x] `doc/overview/feature_backlog.md`
* [x] `CHANGELOG.md`

---

## 12) Link Map

* Previous hardening: `doc/specs/features/FEAT_crewai_native_runtime_hardening.md`
* Runtime architecture: `doc/architecture/crewai_flows.md`
* Agent architecture: `doc/architecture/agents.md`
* Backlog: `doc/overview/feature_backlog.md`
