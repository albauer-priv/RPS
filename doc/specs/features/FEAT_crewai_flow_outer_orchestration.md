---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-12
Owner: Agents / Orchestrator
---
# FEAT: CrewAI Flow Outer Orchestration

* **ID:** FEAT_crewai_flow_outer_orchestration
* **Status:** Implemented
* **Owner/Area:** Agents / Orchestrator
* **Last-Updated:** 2026-05-12
* **Related:** `ADR-037`

---

## 1) Context / Problem

**Current behavior**

* Season and Phase inner specialist execution already runs through CrewAI-backed typed tasks.
* Outer Season and Phase orchestration still lives in RPS-first helpers and Phase execution can recompute the same internal bundle multiple times for one scoped run.
* Specialist agents still reuse top-level planner prompts instead of role-specific prompt slices.

**Problem**

* Scoped `Run Phase` work is more expensive than necessary because the same internal specialist chain can run once per public phase artefact.
* The runtime is CrewAI-only, but the outer Season/Phase orchestration is not yet expressed as CrewAI Flows.
* Prompt reuse blurs specialist responsibilities and weakens the internal crew split.

**Constraints**

* Persisted artefact contracts must remain unchanged.
* No direct writes outside guarded store.
* Local Python 3.14 remains unsupported for actual CrewAI execution; runtime code must stay import-safe on unsupported interpreters.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Execute outer Season and Phase orchestration through CrewAI Flows.
* [x] Reuse one internal `PhaseBundle` for one scoped Phase run and persist the requested public phase artefacts deterministically.
* [x] Give Season and Phase specialists dedicated prompt slices.

**Non-Goals**

* [x] No schema-version change for persisted public artefacts.
* [x] No Flow conversion yet for Week, Report, or Feed Forward chains.

---

## 3) Proposed Behavior

**User/System behavior**

* Season scenario creation, season scenario selection, and season plan creation are routed through a CrewAI Flow entrypoint.
* Scoped Phase execution computes one internal `PhaseBundle`, then splits and stores the requested phase artefacts without rerunning specialists per artefact.
* Season and Phase specialists use dedicated prompts aligned to their responsibility slice.

**UI impact**

* UI affected: No direct layout change.

**Non-UI behavior (if applicable)**

* Components involved: `season_flow.py`, `plan_week.py`, `crewai_backend.py`, `crewai_runtime/flows.py`, specialist prompts.
* Contracts touched: internal CrewAI routing, prompt loading, Phase bundle persistence reuse.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/flows.py`: defines CrewAI Flow wrappers for outer Season and Phase orchestration.
* `src/rps/agents/crewai_backend.py`: exposes one-shot Phase bundle execution and deterministic multi-artefact persistence.
* `src/rps/orchestrator/season_flow.py`: routes season actions through CrewAI flows.
* `src/rps/orchestrator/plan_week.py`: routes Phase execution through one Flow-backed bundle run.
* `prompts/agents/*.md`: adds role-specific specialist prompt slices.

**Data flow**

* Inputs: existing orchestrator-built user_input blocks, workspace-backed context, requested artefact tasks.
* Processing: outer Flow kickoff -> inner typed CrewAI execution -> guarded persistence.
* Outputs: unchanged public artefacts, reduced duplicate internal Phase execution.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none; internal `PhaseBundle` remains non-persisted.
* Validator implications: same guarded store validation paths apply after Flow execution.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for persisted artefact contracts.
* Breaking changes: no public schema break; runtime path now expects Flow helpers for Season/Phase.
* Fallback behavior: none; repository is already on hard CrewAI cutover.

**Conflicts with ADRs / Principles**

* Potential conflicts: none; this tightens the previously chosen CrewAI-first direction.
* Resolution: recorded in `ADR-037`.

**Impacted areas**

* UI: no direct page change.
* Pipeline/data: Phase execution now persists requested artefacts from one bundle run.
* Renderer: unchanged.
* Workspace/run-store: unchanged contract, fewer duplicate phase internal executions.
* Validation/tooling: unchanged final validators.
* Deployment/config: new specialist prompts and Flow helper module.

**Required refactoring**

* Add Flow wrapper layer.
* Refactor Phase orchestration to batch requested artefacts.
* Split specialist prompt responsibilities into dedicated files.

---

## 6) Options & Recommendation

### Option A — Outer Flow wrappers with existing typed backend

**Summary**

* Keep the proven typed backend, add Flow wrappers for Season/Phase, and batch Phase bundle persistence.

**Pros**

* Low contract risk.
* Directly addresses duplicate Phase execution.
* Incremental toward wider Flow adoption.

**Cons**

* Week/report/feed-forward remain outside Flow scope for now.

**Risk**

* Medium: Flow integration must stay import-safe on unsupported local Python runtimes.

### Option B — Rewrite all planning chains into Flows at once

**Summary**

* Convert every chain immediately.

**Pros**

* Uniform architecture faster.

**Cons**

* Larger risk surface with no user benefit for this step.

### Recommendation

* Choose: Option A
* Rationale: it fixes the current duplication and responsibility gaps without destabilizing Week/advisory flows.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season entrypoints route through CrewAI Flow helpers.
* [x] One scoped Phase run computes one internal bundle and persists all requested public phase artefacts from it.
* [x] Season and Phase specialist agents resolve dedicated prompt files.
* [x] Validation passes: `py_compile`, `pytest`, `run_lint.sh`, `run_typecheck.sh`.
* [x] No regression in public artefact persistence paths.

---

## 8) Migration / Rollout

**Migration strategy**

* No artefact migration required.

**Rollout / gating**

* Feature flag / config: none; CrewAI is already the only runtime.
* Safe rollback: revert Flow helper wiring and prompt mappings.

---

## 9) Risks & Failure Modes

* Failure mode: Flow module import unavailable in unsupported interpreter.
  * Detection: runtime import error.
  * Safe behavior: explicit runtime failure rather than silent fallback.
  * Recovery: run in supported Python 3.13 environment.
* Failure mode: Phase bundle missing nested public document.
  * Detection: backend runtime error before store.
  * Safe behavior: no persistence.
  * Recovery: fix specialist/finalizer output and rerun.

---

## 10) Observability / Logging

**New/changed events**

* Flow-backed Season and Phase runs reuse existing orchestrator and backend logs.
* Phase bundle persistence logs now cover one grouped Phase run instead of one per public artefact.

**Diagnostics**

* `rps.agents.crewai_backend`
* `rps.orchestrator.plan_week`
* `rps.orchestrator.season_flow`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/architecture/system_architecture.md` — note Flow-backed outer Season/Phase orchestration.
* [x] `doc/architecture/agents.md` — note specialist prompt slicing and grouped Phase bundle execution.
* [x] `CHANGELOG.md` — record Flow cutover step.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* ADR: `doc/adr/ADR-037-crewai-flow-outer-orchestration.md`
* Existing hierarchy doc: `doc/specs/features/FEAT_hierarchical_crewai_execution.md`
