---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-28
Owner: Planning / Workspace
---
# FEAT: Central Planner Context Snapshots

* **ID:** FEAT_central_planner_context_snapshots
* **Status:** Implemented
* **Owner/Area:** Planning / Workspace / Orchestrator
* **Last-Updated:** 2026-04-28
* **Related:** `FEAT_resolved_kpi_context_injection`, `FEAT_resolved_planner_context_expansion`, `FEAT_resolved_athlete_context`, `ADR-028-snapshot-based-planner-memory`

---

## 1) Context / Problem

**Current behavior**

* Planner orchestrators resolve many deterministic facts in code and inject them as multiple `Resolved ... Context` blocks.
* These facts come from athlete inputs, Intervals-derived pipeline artefacts, and planning predecessors.
* The logic is already more deterministic than earlier prompt-only behavior, but the resolved state is still assembled ad hoc per orchestrator call.

**Problem**

* The same deterministic facts are repeatedly rebuilt and injected separately across `season_scenario`, `season_planner`, `phase_architect`, and `week_planner`.
* There is no first-class, persisted, traceable snapshot representing the current authoritative planning memory for an athlete or for a specific target week.
* Agents still receive many separate resolved sections instead of a consolidated runtime snapshot owned by code.

**Constraints**

* Source-of-truth artefacts must remain authoritative.
* No agent may directly mutate the shared snapshot state.
* Planner prompts must continue to work with current validation and predecessor rules.
* The solution must remain append-only and traceable in the workspace.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Introduce a persisted, code-owned snapshot layer for planner context.
* [x] Separate stable athlete/data-pipeline memory from target-week planning memory.
* [x] Inject consolidated snapshots into planners instead of hand-assembling many context blocks inline.
* [x] Keep source artefacts authoritative and snapshots purely derived.

**Non-Goals**

* [x] Replacing planning artefacts (`SEASON_PLAN`, `PHASE_*`, `WEEK_PLAN`) as the source of truth.
* [x] Allowing agents to free-write a shared mutable memory file.
* [x] Removing workspace tools for exact predecessor reads and fallback detail access.

---

## 3) Proposed Behavior

**User/System behavior**

* The system maintains two derived runtime snapshot artefacts:
  * `ATHLETE_STATE_SNAPSHOT`
  * `PLANNING_CONTEXT_SNAPSHOT`
* `ATHLETE_STATE_SNAPSHOT` captures deterministic athlete/input/pipeline facts such as athlete profile, KPI guidance, availability, logistics, planning events, zone model, wellness, and recent historical activity signals.
* `PLANNING_CONTEXT_SNAPSHOT` captures target-week planning facts such as phase identity, recovery/load governance, event priority, feed-forward applicability, and target-week-specific historical references.
* Planner orchestrators rebuild and persist these snapshots before agent calls, then inject the snapshot content as the authoritative runtime memory for the run.
* Raw artefact reads remain available for exact predecessors, traceability, and unresolved details.

**UI impact**

* UI affected: No direct page changes in this implementation.
* If Yes: none; snapshots are runtime/workspace internals.

**Non-UI behavior (if applicable)**

* Components involved: `resolved_context.py`, new snapshot builder module, `season_flow.py`, `plan_week.py`, workspace artefact registry.
* Contracts touched: workspace artefact catalogue, planner runtime injection contract.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/orchestrator/context_snapshots.py`
  * build/save athlete-state snapshots
  * build/save planning-context snapshots
  * render snapshot prompt blocks from stored snapshots
* `src/rps/workspace/types.py`
  * add snapshot artefact types
* `src/rps/workspace/paths.py`
  * add context artefact storage paths
* `src/rps/workspace/versioning.py`
  * treat snapshots as week-scoped artefacts
* `src/rps/workspace/schema_map.py` + new schemas
  * register snapshot schemas
* `src/rps/orchestrator/season_flow.py`
  * replace ad hoc resolved-block composition with snapshot-first injection
* `src/rps/orchestrator/plan_week.py`
  * replace ad hoc resolved-block composition with snapshot-first injection for phase/week planning

**Data flow**

* Inputs:
  * athlete inputs (`ATHLETE_PROFILE`, `AVAILABILITY`, `PLANNING_EVENTS`, `LOGISTICS`, `KPI_PROFILE`)
  * pipeline artefacts (`WELLNESS`, `ZONE_MODEL`, `ACTIVITIES_ACTUAL`, `ACTIVITIES_TREND`)
  * planning predecessors (`SEASON_PLAN`, `PHASE_*`, feed-forward artefacts)
* Processing:
  * resolve deterministic context from authoritative artefacts
  * persist two derived snapshots
  * inject snapshot prompt blocks into planner requests
* Outputs:
  * `ATHLETE_STATE_SNAPSHOT`
  * `PLANNING_CONTEXT_SNAPSHOT`
  * unchanged planner artefacts

**Schema / Artefacts**

* New artefacts:
  * `ATHLETE_STATE_SNAPSHOT`
  * `PLANNING_CONTEXT_SNAPSHOT`
* Changed artefacts: none
* Validator implications:
  * snapshots are code-owned derived envelopes with their own schemas
  * no guarded-store write path required for this implementation

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none for planner outputs
* Fallback behavior: if snapshot build fails, orchestrators may still inject empty snapshot blocks while existing planner logic remains functional

**Conflicts with ADRs / Principles**

* Potential conflicts: risk of creating a second source of truth
* Resolution: snapshots remain strictly derived from append-only authoritative artefacts and are never directly edited by agents

**Impacted areas**

* UI: none directly
* Pipeline/data: new derived snapshot writes in workspace
* Renderer: none required
* Workspace/run-store: new artefact types and paths
* Validation/tooling: snapshot schema registration and tests
* Deployment/config: none

**Required refactoring**

* Consolidate planner-facing resolved-context assembly behind snapshot builders
* Move orchestrator prompt composition from many inline blocks to snapshot-first blocks

---

## 6) Options & Recommendation

### Option A — Snapshot artefacts as derived runtime memory

**Summary**

* Persist deterministic planner context into first-class workspace snapshot artefacts and inject those into planners.

**Pros**

* Centralized and traceable
* Reuses existing append-only workspace architecture
* Keeps code, not agents, responsible for memory updates
* Enables future tooling/UI inspection of runtime planning memory

**Cons**

* Adds two new artefact types and schemas
* Slightly more orchestration code

**Risk**

* Moderate if snapshots drift from sources; mitigated by rebuilding from latest artefacts on each run.

### Option B — Single mutable `memory.md` maintained by agents

**Summary**

* Create one central memory file that agents read and update directly.

**Pros**

* Very simple mental model

**Cons**

* Weak traceability
* High staleness/drift risk
* Competes with authoritative artefacts
* Harder concurrency story

### Recommendation

* Choose: Option A
* Rationale: it fits the current workspace and deterministic-orchestrator architecture without turning memory into a second uncontrolled truth source.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `ATHLETE_STATE_SNAPSHOT` is persisted as a workspace artefact.
* [x] `PLANNING_CONTEXT_SNAPSHOT` is persisted as a workspace artefact.
* [x] `season_scenario` and `season_planner` receive athlete-state snapshot injection.
* [x] `phase_architect` and `week_planner` receive athlete-state plus planning-context snapshot injection.
* [x] Existing resolved facts remain present to planners through the snapshot content.
* [x] Validation passes: targeted pytest, `py_compile`, lint, type check.

---

## 8) Migration / Rollout

**Migration strategy**

* No migration of historical artefacts is required.
* Snapshots are generated lazily on new planner runs.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: stop writing/injecting snapshot artefacts and revert to direct resolved-block assembly

---

## 9) Risks & Failure Modes

* Failure mode: snapshot content becomes stale relative to source artefacts
  * Detection: snapshot `created_at` or trace refs older than upstream artefacts
  * Safe behavior: rebuild snapshot on each planner run
  * Recovery: rerun planning entrypoint

* Failure mode: snapshot exists but omits required deterministic facts
  * Detection: planner input tests fail or prompts STOP on missing known facts
  * Safe behavior: raw workspace tools still exist for fallback detail reads
  * Recovery: extend snapshot builder

* Failure mode: snapshots are mistaken for source-of-truth planning artefacts
  * Detection: code begins to read snapshots instead of season/phase/week artefacts for binding decisions
  * Safe behavior: keep binding logic explicitly tied to original artefact types
  * Recovery: enforce derived-only read role in code review and docs

---

## 10) Observability / Logging

**New/changed events**

* standard workspace artefact writes for snapshot artefacts

**Diagnostics**

* `runtime/athletes/<athlete_id>/data/context/`
* workspace `latest/`
* planner request capture tests
* `rps.log` artefact-write lines for snapshot artefacts

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_central_planner_context_snapshots.md` — feature spec
* [x] `doc/adr/ADR-028-snapshot-based-planner-memory.md` — architectural decision
* [ ] `doc/architecture/workspace.md` — optional follow-up to mention `data/context/` explicitly in narrative prose

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: `doc/ui/flows.md`
* UI contract (Streamlit): `doc/ui/streamlit_contract.md`
* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Schema versioning: `doc/architecture/schema_versioning.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* ADRs: `doc/adr/ADR-013-data-ownership.md`, `doc/adr/ADR-028-snapshot-based-planner-memory.md`
