---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Phase and Week Contract Context Hardening

* **ID:** FEAT_phase_week_contract_context_hardening
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_season_contract_context_hardening, FEAT_planning_chain_contract_hardening

---

## 1) Context / Problem

**Current behavior**

* Phase and Week planning already compute deterministic execution contracts in code:
  * `phase_execution_context`
  * `week_calendar_context`
* Those contracts are bound into runtime guardrail context, but finalizing managers can still behave exploratorily or delegate.

**Problem**

* `phase_bundle_manager` and `week_plan_manager` can lose deterministic contract semantics when they re-discover or re-delegate what should be direct contract consumption.
* The result is the same class of failure seen in season planning: phase/week roles, active bands, or availability can degrade into prose interpretation.

**Constraints**

* No persisted schema changes.
* Existing phase/week hierarchical crews stay in place.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Expose deterministic phase and week execution contracts through read-only tools.
* [x] Inject structured contract JSON into phase/week finalizer task descriptions.
* [x] Disable free delegation for the phase/week finalizing managers.

**Non-Goals**

* [ ] Re-architect phase/week crews.
* [ ] Add new persisted contract artifacts.

---

## 3) Proposed Behavior

**User/System behavior**

* `phase_bundle_finalize` can read:
  * `workspace_get_phase_execution_context`
  * `workspace_get_phase_slot_contract`
* `week_plan_finalize` can read:
  * `workspace_get_week_calendar_context`
  * `workspace_get_phase_execution_context`
* Both finalizers also receive the same contracts as structured JSON blocks in their task descriptions.
* Both managers are configured as integrators, not free delegators.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * workspace tool modules
  * CrewAI task construction
  * agent/task config
  * phase/week skills and prompts

---

## 4) Implementation Analysis

**Components / Modules**

* `workspace_read_tools.py` / `workspace_tools.py`: add phase/week contract accessors.
* `crewai_backend.py`: extend contract-block injection to phase/week crews.
* `agents.yaml`: disable free delegation for `phase_bundle_manager` and `week_plan_manager`.
* `tasks.yaml`: scope finalizers to deterministic contract tools.

**Data flow**

* Inputs: `phase_execution_context`, `week_calendar_context`, `phase_slot_context`
* Processing: direct contract consumption in finalizer tasks
* Outputs: unchanged `PhaseBundleModel` and `WeekPlanBundleModel`

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: existing phase/week contract guardrails become easier to satisfy deterministically

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none at storage/schema level
* Fallback behavior: missing bound contract returns explicit `ok=false`

**Conflicts with ADRs / Principles**

* None; reinforces code-owned planning contracts.

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: new contract-tool usage visible in task events
* Validation/tooling: expanded read-only tool surface

**Required refactoring**

* Extend task-description contract injection to multiple crews.

---

## 6) Options & Recommendation

### Option A — Dedicated contract tools + non-delegating finalizers

**Summary**

* Give phase/week finalizers direct access to deterministic contracts and stop free rediscovery.

**Pros**

* Keeps structural semantics code-owned.
* Prevents phase/week managers from drifting into prose-only reinterpretation.

**Cons**

* Slightly more tool/config surface.

### Option B — Prompt-only tightening

**Summary**

* Keep delegation/tooling as-is and rely on stricter instructions.

**Cons**

* Same structural failure mode remains available.

### Recommendation

* Choose: Option A

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Deterministic phase/week contract tools exist.
* [x] Phase/week finalizers are scoped to those contract tools.
* [x] Phase/week finalizers receive structured JSON contract blocks in their task descriptions.
* [x] `phase_bundle_manager` and `week_plan_manager` do not allow free delegation.
* [x] Regression tests cover tool/config/contract-block behavior.

---

## 8) Migration / Rollout

**Migration strategy**

* None required.

**Rollout / gating**

* No feature flag.

---

## 9) Risks & Failure Modes

* Failure mode: runtime contract not bound
  * Detection: contract tool returns explicit missing-context error
  * Safe behavior: planner blocks instead of inventing values

---

## 10) Observability / Logging

**New/changed events**

* No new event types; existing tool-call telemetry captures contract-tool access.

**Diagnostics**

* Check run `events.jsonl` for contract-tool calls and absence of exploratory rediscovery.

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_phase_week_contract_context_hardening.md`

