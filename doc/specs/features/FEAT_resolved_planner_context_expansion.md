---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-24
Owner: Planning
---
# FEAT: Resolved Planner Context Expansion

* **ID:** FEAT_resolved_planner_context_expansion
* **Status:** Implemented
* **Owner/Area:** Planning / Orchestrator
* **Last-Updated:** 2026-04-24
* **Related:** `FEAT_resolved_kpi_context_injection`

---

## 1) Context / Problem

**Current behavior**

* Planners were already receiving resolved KPI and body-mass context, but still had to infer other deterministic planning facts from raw artefacts.

**Problem**

* Fixed rest days, weekly hours, target-week/phase-range events, and exact phase identity were still being rediscovered by the model even though code can resolve them deterministically.

**Constraints**

* No schema changes.
* Keep raw artefact reads available where still needed.
* Prefer explicit, compact summaries over dumping full artefacts into prompts.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Resolve availability summaries in code and inject them directly.
* [x] Resolve planning-event membership for target week and phase range in code.
* [x] Resolve phase identity/range facts in code for phase/week planners.

**Non-Goals**

* [ ] Remove raw workspace tools.
* [ ] Eliminate all planner prompt guidance in this change.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_planner` receives:
  * resolved KPI context
  * resolved availability summary
  * resolved planning-event summary
* `phase_architect` receives:
  * resolved phase context
  * resolved availability summary
  * resolved planning-event summary
  * historical activity versions
* `week_planner` receives:
  * resolved phase context
  * resolved availability summary
  * resolved planning-event summary
  * resolved KPI context
  * resolved body mass
  * historical activity versions

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `resolved_context.py`, `season_flow.py`, `plan_week.py`
* Contracts touched: availability, planning events, season-phase, phase-week

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/orchestrator/resolved_context.py`
  * add resolved availability block
  * add resolved planning-event block
  * add resolved phase block
* `src/rps/orchestrator/season_flow.py`
  * inject resolved availability + planning events
* `src/rps/orchestrator/plan_week.py`
  * inject resolved phase + availability + planning events

**Data flow**

* Inputs: latest `AVAILABILITY`, latest `PLANNING_EVENTS`, target week, resolved phase info
* Processing: summarize and normalize deterministic facts
* Outputs: compact planner input blocks

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: missing artefacts yield empty resolved blocks without aborting unrelated context injection

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with deterministic orchestration and reduced model guesswork

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: read latest availability/planning-events artefacts
* Validation/tooling: orchestrator tests only
* Deployment/config: none

**Required refactoring**

* Centralize planner-facing deterministic summaries in `resolved_context.py`

---

## 6) Options & Recommendation

### Option A — Expand resolved context blocks

**Summary**

* Move more deterministic interpretation into code and inject compact summaries.

**Pros**

* Less agent search
* More reproducible
* Reusable across planners

**Cons**

* Slightly larger planner prompts

### Option B — Leave non-KPI facts in raw artefact interpretation

**Summary**

* Keep only KPI/body-mass direct injection and let the model infer the rest.

**Pros**

* Smaller prompt

**Cons**

* Keeps avoidable ambiguity and repeated failures

### Recommendation

* Choose: Option A
* Rationale: deterministic summaries are cheaper and more reliable than repeated model reconstruction.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season planning input includes resolved availability and planning-event context
* [x] Phase planning input includes resolved phase, availability, and planning-event context
* [x] Week planning input includes resolved phase, availability, and planning-event context
* [x] Validation passes: targeted pytest, `py_compile`, lint, type check

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert `resolved_context.py` callers

---

## 9) Risks & Failure Modes

* Failure mode: malformed availability or planning-events payload
  * Detection: missing resolved block in captured-input tests
  * Safe behavior: affected block omitted; unrelated blocks still injected
  * Recovery: refresh/fix input artefact

---

## 10) Observability / Logging

**New/changed events**

* None

**Diagnostics**

* Captured planner `user_input` in tests

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_resolved_planner_context_expansion.md`
* [x] `CHANGELOG.md`

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Planning flow: `doc/overview/how_to_plan.md`
* Availability schema: `specs/schemas/availability.schema.json`
* Planning events schema: `specs/schemas/planning_events.schema.json`
* Season/phase contract: `specs/knowledge/_shared/sources/contracts/season__phase_contract.md`
* Phase/week contract: `specs/knowledge/_shared/sources/contracts/phase__week_contract.md`
