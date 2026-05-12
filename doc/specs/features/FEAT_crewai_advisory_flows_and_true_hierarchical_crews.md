---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-12
Owner: Agents / Orchestrator
---
# FEAT: CrewAI Advisory Flows and True Hierarchical Crews

* **ID:** FEAT_crewai_advisory_flows_and_true_hierarchical_crews
* **Status:** Implemented
* **Owner/Area:** Agents / Orchestrator
* **Last-Updated:** 2026-05-12
* **Related:** `ADR-038`

---

## 1) Context / Problem

**Current behavior**

* Outer Season and Phase orchestration already runs through CrewAI Flow wrappers.
* Week planning, DES report generation, and feed-forward orchestration still call the backend directly from RPS helpers.
* Inner Season and Phase specialist execution still uses repeated one-task crews instead of one true multi-agent hierarchical crew.

**Problem**

* The architecture is still uneven: outer advisory/week chains are not Flow-owned yet.
* Inner specialist execution is CrewAI-backed but not yet one real hierarchical `Crew` object.
* This leaves the runtime short of the intended Flow-outside / hierarchical-crew-inside target.

**Constraints**

* Public artefact contracts must remain unchanged.
* Guarded store stays the persistence boundary.
* Local Python 3.14 import safety must remain intact.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move outer Week / Report / Feed-Forward orchestration to CrewAI Flow wrappers.
* [x] Execute Season and Phase specialist work as one real hierarchical CrewAI crew per run.
* [x] Preserve existing public artefact contracts and deterministic post-processing.

**Non-Goals**

* [x] No schema-version change for public artefacts.
* [x] No Coach flow redesign in this step.

---

## 3) Proposed Behavior

**User/System behavior**

* Week planning, DES report creation, and feed-forward chaining now route through CrewAI Flow wrappers.
* `SEASON_PLAN` uses one hierarchical CrewAI crew with manager + specialists.
* `PhaseBundle` uses one hierarchical CrewAI crew with manager + specialists + auditors.

**UI impact**

* UI affected: No direct layout change.

**Non-UI behavior (if applicable)**

* Components involved: advisory actions, week revision, week planner orchestration, CrewAI backend, CrewAI Flow wrappers.
* Contracts touched: runtime orchestration only, not persisted schema shape.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/flows.py`: extended to Week, Report, and Feed-Forward.
* `src/rps/agents/crewai_backend.py`: hierarchical crew executor for Season and Phase.
* `src/rps/orchestrator/advisory_actions.py`: feed-forward chain routed through a Flow wrapper.
* `src/rps/orchestrator/plan_week.py`: Week planner step routed through a Flow wrapper.
* `src/rps/orchestrator/week_revision.py`: revision path routed through the Week flow.

**Data flow**

* Inputs: existing orchestrator-built prompts, workspace context, requested tasks.
* Processing: Flow kickoff -> hierarchical crew or single persisted task -> guarded persistence.
* Outputs: unchanged public artefacts and status payloads.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: unchanged guarded store path.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for public artefacts and UI surfaces.
* Breaking changes: runtime orchestration path is now more consistently CrewAI-owned.
* Fallback behavior: none; repository is already on hard CrewAI cutover.

**Conflicts with ADRs / Principles**

* Potential conflicts: none; this completes the next intended CrewAI architecture step.
* Resolution: recorded in `ADR-038`.

**Impacted areas**

* UI: unchanged layout.
* Pipeline/data: advisory/week orchestration routed through Flows.
* Renderer: unchanged.
* Workspace/run-store: unchanged contracts.
* Validation/tooling: unchanged final validators.
* Deployment/config: no new env needed.

**Required refactoring**

* Add generic Week / Report / Feed-Forward Flow wrappers.
* Replace serial specialist-task loops with one hierarchical crew executor.
* Update tests to validate true crew construction and flow routing.

---

## 6) Options & Recommendation

### Option A — Complete the next CrewAI slice now

**Summary**

* Add remaining outer Flow wrappers and replace serial inner specialist execution with one hierarchical crew.

**Pros**

* Architecture becomes consistent.
* Less orchestration duplication.
* Closer to intended CrewAI-first target.

**Cons**

* Slightly larger runtime/test change set.

### Option B — Leave advisory/week direct and only adjust inner crews

**Summary**

* Partial clean-up only.

**Pros**

* Smaller patch.

**Cons**

* Leaves the runtime split-brain in place.

### Recommendation

* Choose: Option A
* Rationale: it completes the next coherent architecture increment instead of another half-step.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Week planning routes through a CrewAI Flow wrapper.
* [x] DES report generation routes through a CrewAI Flow wrapper.
* [x] Feed-forward chaining routes through a CrewAI Flow wrapper.
* [x] Season specialist execution uses one hierarchical CrewAI crew.
* [x] Phase specialist execution uses one hierarchical CrewAI crew.
* [x] Validation passes: `py_compile`, `pytest`, `run_lint.sh`, `run_typecheck.sh`.

---

## 8) Migration / Rollout

**Migration strategy**

* No artefact migration required.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: revert Flow wrapper wiring and hierarchical crew executor.

---

## 9) Risks & Failure Modes

* Failure mode: hierarchical CrewAI API expectations differ in deployed runtime.
  * Detection: runtime failure during kickoff.
  * Safe behavior: no persistence.
  * Recovery: adjust manager/crew construction.
* Failure mode: feed-forward flow stops after report or season delta step.
  * Detection: partial `FeedForwardChainResult` with `ok=False`.
  * Safe behavior: no downstream persistence beyond completed steps.
  * Recovery: rerun after fixing upstream issue.

---

## 10) Observability / Logging

**New/changed events**

* Flow-backed Week / Report / Feed-Forward continue using existing orchestrator logging.
* Hierarchical crew execution remains logged through `rps.agents.crewai_backend`.

**Diagnostics**

* `rps.orchestrator.plan_week`
* `rps.orchestrator.advisory_actions`
* `rps.agents.crewai_backend`

---

## 11) Documentation Updates

* [x] `doc/architecture/system_architecture.md` — note outer advisory/week flow wrappers and true hierarchical crews.
* [x] `doc/architecture/agents.md` — note Week/report/feed-forward flow routing and single-crew specialist execution.
* [x] `CHANGELOG.md` — record the advisory/week flow cutover and true hierarchical crew execution.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Prior flow step: `doc/specs/features/FEAT_crewai_flow_outer_orchestration.md`
* ADR: `doc/adr/ADR-038-crewai-advisory-flows-and-true-hierarchical-crews.md`
