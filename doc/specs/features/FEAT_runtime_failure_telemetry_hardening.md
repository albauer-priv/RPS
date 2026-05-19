---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Runtime Telemetry
---
# FEAT: Runtime Failure Telemetry Hardening

* **ID:** FEAT_runtime_failure_telemetry_hardening
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime / Plan Hub Worker
* **Last-Updated:** 2026-05-19

---

## 1) Context / Problem

**Current behavior**

* CrewAI runs write compact lifecycle telemetry into `events.jsonl`.
* When an upstream LLM/provider failure occurs, the final step/run status may only capture a downstream scheduler/runtime exception such as `cannot schedule new futures after shutdown`.

**Problem**

* The run store can lose the true root cause of a failure.
* Operators can see the failure in `rps.log`, but `steps.json` and `events.jsonl` do not consistently preserve the actionable provider error context.

**Constraints**

* No persisted planning schema change.
* Keep telemetry compact and structured.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Emit explicit runtime failure events with structured provider/LLM metadata when available.
* [x] Preserve root-cause failure details in Plan Hub step/run records.
* [x] Keep the existing `events.jsonl` transport and avoid prompt-body logging.

**Non-Goals**

* [x] No full tracing system or distributed span model.
* [x] No logging of raw prompts or full tool arguments.

---

## 3) Proposed Behavior

**User/System behavior**

* When a CrewAI planning run fails because of OpenAI quota/rate/provider issues, `events.jsonl` records a dedicated failure event with fields such as `error_type`, `error_code`, `status_code`, and a compact reason.
* The Plan Hub worker prefers that root cause when filling `STEP_FAILED`/`RUN_FAILED`, especially when the final thrown exception is only a secondary shutdown/scheduler error.

**Non-UI behavior**

* Components involved: CrewAI telemetry, CrewAI backend, Plan Hub worker.
* Contracts touched: run-store telemetry contract only.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/telemetry.py`: exception summarization and structured failure event emission.
* `src/rps/agents/crewai_backend.py`: emit runtime failure events from CrewAI execution catch blocks.
* `src/rps/orchestrator/plan_hub_worker.py`: resolve root-cause failure details from recent runtime events.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none for persisted planning artifacts.

**Impacted areas**

* Run-store telemetry: richer event payloads.
* Plan Hub failure reporting: more accurate `Details`/`reason`.

---

## 6) Recommendation

* Add compact structured runtime failure events and let the worker consume them as the canonical root cause when available.

---

## 7) Acceptance Criteria

* [x] LLM/provider failures emit structured runtime events.
* [x] Worker failure details prefer the root cause over secondary scheduler errors.
* [x] Targeted tests cover event emission and root-cause selection.

---

## 8) Risks & Failure Modes

* Failure mode: exception objects expose little structured metadata.
  * Detection: event still contains compact textual reason only.
  * Safe behavior: fallback to stringified root cause.

---

## 9) Observability / Logging

**New/changed events**

* `LLM_REQUEST_FAILED`
* `CREW_EXECUTION_FAILED`

