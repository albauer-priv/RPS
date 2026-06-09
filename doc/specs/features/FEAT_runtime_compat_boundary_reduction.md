---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: CrewAI Runtime
---
# FEAT: Runtime Compat Boundary Reduction

* **ID:** FEAT_runtime_compat_boundary_reduction
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime / Orchestration
* **Last-Updated:** 2026-06-09
* **Related:** [ADR-040-crewai-event-listener-runtime-telemetry](/Users/alexander/RPS/doc/adr/ADR-040-crewai-event-listener-runtime-telemetry.md), [ADR-046-crewai-state-memory-knowledge-guardrail-separation](/Users/alexander/RPS/doc/adr/ADR-046-crewai-state-memory-knowledge-guardrail-separation.md), [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)

---

## 1) Context / Problem

**Current behavior**

* Active runtime entrypoints still imported `crewai_runtime.compat` directly for the basic “can this runtime execute CrewAI?” availability check.
* The `compat.py` helper only exposed runtime-status probing; it was not an actual active behavior boundary.

**Problem**

* `compat.py` remained on the active import path even where no compatibility translation was needed.
* This kept the old transition naming alive in the active runtime surface and made the runtime boundary less explicit than it should be.

**Constraints**

* No runtime-model redesign in this feature.
* No change to Flow or EventListener behavior in this slice.
* Existing imports from `compat.py` outside the active path may continue to work through a shim.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move the active CrewAI availability probe to a repo-owned runtime-status module.
* [x] Point active runtime/orchestrator/chat/binding entrypoints at that new boundary.
* [x] Keep `compat.py` only as a narrow shim for legacy imports.

**Non-Goals**

* [x] No rewrite of `Flow[...]` wrappers.
* [x] No rewrite of `BaseEventListener` integration.
* [x] No removal of all remaining compatibility concepts in a single patch.

---

## 3) Proposed Behavior

**User/System behavior**

* Active code now resolves CrewAI runtime availability through `crewai_runtime.runtime_status`.
* `crewai_runtime.compat` remains importable, but only re-exports the runtime-status helper instead of owning active logic.

**Non-UI behavior**

* Components involved: runtime gateway, season/phase/week orchestrator entrypoints, CrewAI bindings, coach chat runtime, package exports.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/runtime_status.py`
  * new canonical availability boundary for `CrewAIRuntimeStatus` and `crewai_runtime_status()`
* `src/rps/crewai_runtime/compat.py`
  * reduced to a legacy shim re-export
* Active importers updated:
  * `src/rps/agents/runtime.py`
  * `src/rps/orchestrator/season_flow.py`
  * `src/rps/orchestrator/plan_week.py`
  * `src/rps/crewai_runtime/bindings.py`
  * `src/rps/crewai_runtime/coach_chat.py`
  * `src/rps/crewai_runtime/__init__.py`

**Data flow**

* Inputs: current interpreter version and CrewAI package availability
* Processing: runtime-status probe
* Outputs: repo-owned runtime-status object consumed by active entrypoints

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none expected
* Fallback behavior:
  * `compat.py` remains as a shim for existing import sites not yet migrated

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: aligns with runtime-boundary cleanup and keeps third-party concerns away from primary active entrypoints.

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: import-path cleanup only
* Deployment/config: none

---

## 6) Options & Recommendation

### Option A — Introduce runtime-status boundary and keep compat as shim

**Summary**

* Active modules import `runtime_status`; `compat.py` becomes legacy re-export only.

**Pros**

* Low-risk cleanup
* Clarifies the active runtime boundary
* Preserves compatibility

**Cons**

* Does not yet solve the broader dynamic typing debt in Flows/EventListener

### Option B — Leave active imports on compat

**Summary**

* No code movement; keep the transition module active.

**Pros**

* Minimal change

**Cons**

* Preserves naming debt and weak boundary definition

### Recommendation

* Choose: Option A
* Rationale: it is the smallest meaningful Wave-2 slice and leaves a cleaner runtime surface for later Flow/EventListener hardening.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Active runtime/orchestrator/chat/binding entrypoints no longer import `crewai_runtime.compat` directly.
* [x] `runtime_status.py` owns the active availability probe.
* [x] `compat.py` remains only as a narrow shim.
* [x] Existing runtime tests continue to pass.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration.
* Import-path migration only.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert import-path changes and remove the new module

---

## 9) Risks & Failure Modes

* Failure mode: an active importer still points to `compat.py`

  * Detection: grep/test review
  * Safe behavior: compat shim still works
  * Recovery: migrate the remaining importer in a follow-up patch

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* grep for active `compat` imports
* runtime tests around `crewai_runtime_status()`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — record this Wave-2 slice as implemented
