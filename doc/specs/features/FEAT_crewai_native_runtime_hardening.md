---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-18
Owner: CrewAI Runtime
---
# FEAT: CrewAI Native Runtime Hardening

* **ID:** FEAT_crewai_native_runtime_hardening
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime
* **Last-Updated:** 2026-05-18
* **Related:** `config/crewai/*.yaml`, `src/rps/agents/crewai_backend.py`, `src/rps/crewai_runtime/*`

---

## 1) Context / Problem

**Current behavior**

* RPS uses CrewAI agents, tasks, skills, knowledge, memory, planning LLMs, structured outputs, and guardrails.
* Some CrewAI-native task/agent/crew attributes are still hidden in code defaults or not configurable through YAML.
* Task dependency context mostly relies on the current linear "all prior tasks" behavior in internal crews.
* Runtime telemetry exists through CrewAI event listeners, but task callback and guardrail failure summaries are not consistently emitted as RPS-owned events.

**Problem**

* Configuration is less explicit than CrewAI supports.
* Writer and manager defaults are not centrally enforced.
* Persisted artifact tasks are schema-backed, but schema guardrail failures should be visible before persistence and retryable through CrewAI guardrail semantics.
* Flow state classes exist but do not yet expose all cross-flow control refs needed for diagnostics.

**Constraints**

* No new dependencies.
* No artifact schema changes.
* Persisted artifact JSON Schemas remain the storage truth.
* Native CrewAI streaming is not enabled for persisted artifact runs in this pass.
* RPS preview/confirm/apply remains the HITL boundary; native `human_input` is not introduced for persistence.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Support CrewAI-native agent attributes through blueprints/runtime builders.
* [x] Support selected CrewAI-native crew attributes through runtime profiles.
* [x] Support explicit task `context:` dependencies in YAML while retaining linear fallback for existing internal crews.
* [x] Add safe task callback and guardrail failure telemetry without prompt leakage.
* [x] Expand typed flow state with refs, produced artifacts, review decisions, and failure reason.
* [x] Harden memory policy so writers are read-only and memory remains non-authoritative.

**Non-Goals**

* [x] No artifact schema changes.
* [x] No new CrewAI file-processing dependency.
* [x] No native CrewAI streaming for persisted artifact flows.
* [x] No consensual process usage.

---

## 3) Proposed Behavior

**User/System behavior**

* YAML can steer supported CrewAI-native agent and crew attributes.
* Managers remain the only delegating planning agents by default.
* Writers receive constrained iteration/context behavior and read-only memory.
* Explicit task context can be declared in `tasks.yaml`; absent context preserves existing linear context behavior.
* Guardrail failures and task completions are logged as compact run-store events.

**UI impact**

* UI affected: No direct layout change.

**Non-UI behavior**

* Components involved: CrewAI backend, bindings, guardrails, telemetry, memory policy, flow state.
* Contracts touched: CrewAI YAML config only; artifact schemas unchanged.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/bindings.py`: central native config passthrough, task context blueprint support.
* `src/rps/agents/crewai_backend.py`: apply native agent/crew kwargs, configured task context, callbacks, guardrail runtime context.
* `src/rps/crewai_runtime/guardrails.py`: emit compact guardrail failure events.
* `src/rps/crewai_runtime/telemetry.py`: task/step callback builders and normalized event names.
* `src/rps/crewai_runtime/flows.py`: richer Pydantic state fields.
* `src/rps/crewai_runtime/memory.py` and `config/crewai/memory_policy.yaml`: read-only writer memory.

**Data flow**

* Inputs: YAML runtime config, task policies, artifacts, deterministic context blocks.
* Processing: build CrewAI objects with native kwargs; execute tasks/crews; guardrails validate; telemetry records summaries.
* Outputs: artifacts unchanged; run-store gains additional diagnostic events.

**Schema / Artefacts**

* New artefacts: None.
* Changed artefacts: None.
* Validator implications: persisted artifact tasks continue to use generated Pydantic output models and `artifact_schema_valid`.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None intended.
* Fallback behavior: existing tasks without `context:` still use prior-task context in internal linear/hierarchical crew chains.

**Conflicts with ADRs / Principles**

* Potential conflicts: None identified.
* Resolution: No ADR needed because persistence schema and orchestration boundaries are unchanged.

**Impacted areas**

* UI: none.
* Pipeline/data: no schema changes.
* Renderer: none.
* Workspace/run-store: additional safe diagnostic events.
* Validation/tooling: tests cover config passthrough, task context, memory modes, and guardrail telemetry.
* Deployment/config: optional YAML fields become active.

**Required refactoring**

* Centralize CrewAI native config field selection.
* Add explicit context resolution before task construction.

---

## 6) Options & Recommendation

### Option A — Targeted CrewAI-Native Hardening

**Summary**

* Add native feature support at the existing CrewAI binding/backend edges.

**Pros**

* Low-risk, backward compatible, no schema churn.
* Preserves RPS deterministic context and guarded persistence model.

**Cons**

* Does not convert all orchestration into native Flow branching in this pass.

**Risk**

* CrewAI version differences may ignore or reject a native kwarg; tests catch local construction behavior.

### Option B — Full Runtime Rewrite

**Summary**

* Rebuild orchestration around CrewAI-native Flows, Files, and memory patterns.

**Pros**

* Maximal CrewAI feature usage.

**Cons**

* Higher regression risk and unnecessary artifact pipeline churn.

### Recommendation

* Choose: Option A.
* Rationale: RPS already has stable deterministic context, schema validation, and guarded persistence; the correct next step is hardening the CrewAI-native seams.

---

## 7) Acceptance Criteria

* [x] Agent attributes from YAML/config defaults are passed to `Agent(...)`.
* [x] Crew attributes from runtime profiles are passed to `Crew(...)` where safe.
* [x] Writer agents do not delegate and get constrained runtime defaults.
* [x] Manager agents can delegate where configured.
* [x] `context:` in task config maps to native `Task(context=[...])`.
* [x] Persisted artifact tasks keep generated schema-backed output models plus guardrails.
* [x] Guardrail failures emit compact, retry-relevant telemetry.
* [x] Flow state contains ids, refs, produced artifact refs, review decisions, and failure reason.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration.
* Existing YAML remains valid.

**Rollout / gating**

* Optional native fields are inert unless configured.
* Native Crew streaming remains disabled for persisted flows.

---

## 9) Risks & Failure Modes

* Failure mode: CrewAI installed version rejects a newly forwarded kwarg.
  * Detection: unit tests or runtime construction error.
  * Safe behavior: only documented CrewAI attrs are forwarded; absent attrs are not passed.
  * Recovery: remove/disable the YAML attr or adjust compatibility filtering.
* Failure mode: explicit task context references a later or missing task.
  * Detection: runtime `ValueError` before crew kickoff.
  * Safe behavior: fail fast; no partial artifact write.
  * Recovery: fix `tasks.yaml` context order.
* Failure mode: memory stores binding artifact facts as preferences.
  * Detection: memory policy review.
  * Safe behavior: writer memory is read-only; artifact truth remains workspace + schemas.

---

## 10) Observability / Logging

**New/changed events**

* `CREW_TASK_COMPLETED`: emitted by task callback with task label, agent label, and output format.
* `CREW_TASK_GUARDRAIL_FAILED`: emitted when a configured function guardrail returns failure.
* `CREW_AGENT_STEP`: optional debug step callback event with compact step metadata.

**Diagnostics**

* Run-store events under the active run id.
* `rps.log` for construction/runtime exceptions.

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_crewai_native_runtime_hardening.md` — canonical feature spec.
* [ ] `doc/architecture/agents.md` — optional later summary of native config passthrough.
* [ ] `doc/architecture/crewai_flows.md` — optional later update for typed state fields.

---

## 12) Link Map

* Architecture: `doc/architecture/system_architecture.md`
* Agent architecture: `doc/architecture/agents.md`
* CrewAI flows: `doc/architecture/crewai_flows.md`
* Artifact flow: `doc/overview/artefact_flow.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* Feature template: `doc/specs/features/FEAT_TEMPLATE.md`

---

## Open Questions

* Should RPS later expose native CrewAI `human_input` for non-persisted advisory flows, or keep all HITL under the existing preview/confirm/apply UI boundary?
