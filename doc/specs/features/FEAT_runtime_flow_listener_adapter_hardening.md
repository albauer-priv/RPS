---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-09
Owner: CrewAI Runtime
---
# FEAT: Runtime Flow and Listener Adapter Hardening

* **ID:** FEAT_runtime_flow_listener_adapter_hardening
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime / Telemetry
* **Last-Updated:** 2026-06-09
* **Related:** [FEAT_runtime_compat_boundary_reduction](/Users/alexander/RPS/doc/specs/features/FEAT_runtime_compat_boundary_reduction.md), [ADR-040-crewai-event-listener-runtime-telemetry](/Users/alexander/RPS/doc/adr/ADR-040-crewai-event-listener-runtime-telemetry.md), [ADR-046-crewai-state-memory-knowledge-guardrail-separation](/Users/alexander/RPS/doc/adr/ADR-046-crewai-state-memory-knowledge-guardrail-separation.md), [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)

---

## 1) Context / Problem

**Current behavior**

* Active runtime modules still rely on dynamic CrewAI classes for `Flow[...]` and `BaseEventListener`.
* Those third-party symbols are loaded lazily at runtime, but the active repo modules still model them too directly.

**Problem**

* The active runtime surface still leaks CrewAI dynamic typing into core modules such as `flows.py` and `telemetry.py`.
* This keeps the runtime boundary weak and leaves mypy/runtime adapter debt unresolved in the current Wave 2 area.

**Constraints**

* No authority-model redesign.
* No schema change.
* No telemetry contract redesign.
* Existing Flow/Crew/Task event semantics must remain stable for Plan Hub / Status / History consumers.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Encapsulate dynamic CrewAI `Flow` construction at a repo-owned adapter boundary inside `flows.py`.
* [x] Encapsulate dynamic CrewAI `BaseEventListener` subclassing at a repo-owned adapter boundary inside `telemetry.py`.
* [x] Remove the remaining Wave-2 mypy debt from the active CrewAI runtime adapter surface without widening `Any` use through unrelated modules.

**Non-Goals**

* [x] No rewrite of planning flow behavior or step ordering.
* [x] No new telemetry event types or payload redesign.
* [x] No repo-wide typecheck cleanup outside the targeted active runtime boundary slice.

---

## 3) Proposed Behavior

**User/System behavior**

* Season/Phase/Week/Report/Feed-Forward/Coach flows behave as before.
* CrewAI lifecycle listener behavior remains unchanged for runtime telemetry output.
* The repo-owned runtime boundary now constructs dynamic CrewAI Flow and listener classes internally instead of exposing invalid static typing patterns to active modules.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * `src/rps/crewai_runtime/flows.py`
  * `src/rps/crewai_runtime/telemetry.py`
  * `src/rps/crewai_runtime/bindings.py`
  * `src/rps/crewai_runtime/knowledge.py`
  * `src/rps/crewai_runtime/guardrails.py`
* Contracts touched:
  * internal runtime adapter boundary only

---

## 4) Implementation Analysis

**Components / Modules**

* `flows.py`
  * replace invalid static `Flow[...]` subclass patterns with repo-owned dynamic class creation at the load boundary
* `telemetry.py`
  * replace invalid static `BaseEventListener` subclass pattern with dynamic adapter construction
* `bindings.py`, `knowledge.py`, `guardrails.py`
  * close adjacent typing debt exposed by the same runtime adapter slice

**Data flow**

* Inputs: runtime-loaded CrewAI Flow/listener classes, existing planning run inputs
* Processing: repo-owned adapter wraps dynamic CrewAI symbols before active runtime usage
* Outputs: unchanged runtime behavior, cleaner typed adapter boundary

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none expected
* Fallback behavior: runtime still fail-closed if CrewAI symbols are unavailable or malformed

**Conflicts with ADRs / Principles**

* Potential conflicts: none expected
* Resolution: aligns with keeping third-party dynamism inside explicit runtime boundaries

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: targeted mypy/runtime cleanup for CrewAI runtime boundary
* Deployment/config: none

**Required refactoring**

* Replace invalid generic/subclass syntax on runtime-loaded CrewAI types
* Normalize nearby helper typing so the active runtime slice passes curated typecheck

---

## 6) Options & Recommendation

### Option A — Dynamic adapter hardening at the repo boundary

**Summary**

* Keep CrewAI dynamic symbols inside local adapter construction and expose only repo-owned stable behavior to the rest of the runtime.

**Pros**

* Matches the Wave-2 boundary goal
* Fixes current mypy debt at the real source
* Avoids broad `Any` spread

**Cons**

* Requires slightly more explicit adapter code in `flows.py` and `telemetry.py`

**Risk**

* Incorrect dynamic class assembly could break flow/listener wiring if not regression-tested

### Option B — Suppress the type errors and keep direct subclass patterns

**Summary**

* Add ignores/casts around the current invalid static patterns.

**Pros**

* Smaller code diff

**Cons**

* Leaves the boundary semantically weak
* Preserves the exact debt Wave 2 is supposed to reduce

### Recommendation

* Choose: Option A
* Rationale: Wave 2 is specifically about reducing runtime/compat debt at adapter boundaries; suppressing the errors would miss the point.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Active runtime flow wrappers no longer use invalid static subclass patterns on runtime-loaded CrewAI `Flow`.
* [x] Active telemetry listener setup no longer uses invalid static subclass patterns on runtime-loaded `BaseEventListener`.
* [x] Targeted mypy passes for the active CrewAI runtime adapter slice.
* [x] Targeted CrewAI runtime tests still pass.
* [x] No regressions in runtime telemetry emission or flow execution entrypoints.

---

## 8) Migration / Rollout

**Migration strategy**

* No data migration
* Internal runtime adapter refactor only

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the adapter-construction changes in runtime modules

---

## 9) Risks & Failure Modes

* Failure mode: dynamic Flow/listener assembly is structurally valid for mypy but wrong at runtime

  * Detection: targeted runtime tests and scoped flow smoke runs
  * Safe behavior: flow call fails loudly rather than silently misrouting planning steps
  * Recovery: revert the affected adapter function and reintroduce prior runtime path

---

## 10) Observability / Logging

**New/changed events**

* none

**Diagnostics**

* targeted runtime tests around flow execution and event listener initialization
* existing runtime logs for Flow/Crew/Task events remain the diagnostic surface

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [doc/overview/feature_backlog.md](/Users/alexander/RPS/doc/overview/feature_backlog.md) — add/mark this second Wave-2 slice
* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record runtime boundary hardening

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* ADRs:
  * [ADR-040-crewai-event-listener-runtime-telemetry](/Users/alexander/RPS/doc/adr/ADR-040-crewai-event-listener-runtime-telemetry.md)
  * [ADR-046-crewai-state-memory-knowledge-guardrail-separation](/Users/alexander/RPS/doc/adr/ADR-046-crewai-state-memory-knowledge-guardrail-separation.md)
  * [ADR-056-upstream-first-planning-pipeline](/Users/alexander/RPS/doc/adr/ADR-056-upstream-first-planning-pipeline.md)
