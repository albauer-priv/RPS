---
Version: 1.0
Status: Draft
Last-Updated: 2026-05-14
Owner: CrewAI Runtime
---
# FEAT: Skills-First Multi-Crew Planning Runtime

* **ID:** FEAT_skills_first_multi_crew_planning_runtime
* **Status:** Draft
* **Owner/Area:** CrewAI Runtime / Planning
* **Last-Updated:** 2026-05-14
* **Related:** `doc/adr/ADR-047-crewai-skills-unified-planning.md`

---

## 1) Context / Problem

**Current behavior**

* Planning methodology has started moving into repo-local skills, but the knowledge migration is incomplete and many skills are still thin wrappers.
* Season, Phase, and Week runtime paths still compress planning, review, and write responsibilities too aggressively.
* Current managers still act as hidden synthesizers, validators, and finalizers.

**Problem**

* Real planning knowledge still lives mainly in legacy prose docs under `specs/knowledge/_shared/sources/`.
* Several agents are still methodologically overloaded.
* Outer flows do not yet implement planning -> review -> writer routing with bounded replan loops.

**Constraints**

* Workspace artifacts remain authoritative truth.
* Contracts and schemas remain explicit machine-layer boundaries.
* The repo must stay compatible with the current test/runtime split where CrewAI may be unavailable locally.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Make skills the primary planning knowledge layer.
* [ ] Split Season, Phase, Week, and Report into planning, review, and writer crews.
* [ ] Add explicit internal bundle/review/replan models.
* [ ] Keep Coach and Workout Editor on the same Week specialist family.

**Non-Goals**

* [ ] Replace JSON schemas or artifact contracts with skills.
* [ ] Remove all legacy source docs in one step; they may remain as migration source until the cutover stabilizes.

---

## 3) Proposed Behavior

**User/System behavior**

* Season, Phase, Week, and Report flows run through explicit planning, review, and writer layers.
* Review layers may request bounded replans before any persistence occurs.
* Skills, not prompt injection, carry the planning methodology.

**UI impact**

* UI affected: No direct layout change.
* Existing Coach / Workout Editor / planning pages keep their current entrypoints but route into the new orchestration.

**Non-UI behavior**

* Components involved: CrewAI runtime flows, backend execution, skill wiring, agent/task config.
* Contracts touched: internal typed outputs, task config, flow routing.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/models.py`: add internal planning/review/replan models.
* `src/rps/crewai_runtime/flows.py`: add multi-crew flow routing and bounded review loops.
* `src/rps/agents/crewai_backend.py`: add planning/review/writer crew execution helpers.
* `config/crewai/agents.yaml`, `config/crewai/tasks.yaml`, `config/crewai/skills.yaml`: recut agents, tasks, and bundles.
* `skills/`: migrate planning knowledge into canonical skill refs.

**Data flow**

* Inputs: athlete workspace context, selected artifacts, user request.
* Processing: planning crew -> review crew -> optional replan -> writer crew.
* Outputs: approved persisted artifacts or bounded failure with review summary.

**Schema / Artefacts**

* New internal models only; no public artifact schema version bump targeted in this change.
* Persisted artifacts continue to pass guarded validation.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: partially.
* Breaking changes: internal agent/task names and crew composition change.
* Fallback behavior: direct non-CrewAI orchestration remains usable in local compatibility paths.

**Conflicts with ADRs / Principles**

* Extends ADR-047 by making skills canonical and adding multi-crew routing.
* Extends ADR-037 / ADR-038 outer-flow layering with explicit review loops.

**Impacted areas**

* UI: no direct layout changes.
* Pipeline/data: none at artifact schema level.
* Renderer: none.
* Workspace/run-store: new runtime events and internal orchestration stages.
* Validation/tooling: new internal typed outputs and guardrails.
* Deployment/config: new agent/task/skill config entries.

**Required refactoring**

* Recut Season/Phase/Week/Report agents.
* Rewire flows to multi-crew routing.
* Populate skill references with actual planning knowledge.

---

## 6) Options & Recommendation

### Option A — Multi-crew routed flows

**Summary**

* Outer flow coordinates planning crew, review crew, and writer crew.

**Pros**

* Clean skill boundaries.
* Explicit review logic.
* Better replan control.

**Cons**

* More config and runtime complexity.

**Risk**

* More moving parts in task/config mapping.

### Option B — Keep one crew and overload manager

**Summary**

* Manager continues to synthesize, validate, and finalize.

**Pros**

* Lower implementation overhead.

**Cons**

* Manager remains overloaded.
* Review logic stays implicit.

### Recommendation

* Choose: Option A
* Rationale: it matches the desired skill-pure runtime shape and removes hidden role blending.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Skills contain the primary planning methodology used by runtime specialists.
* [ ] Season, Phase, Week, and Report outer flows support planning/review/writer routing.
* [ ] New internal bundle/review/replan models exist and are used.
* [ ] Coach and Workout Editor reuse the Week specialist family.
* [ ] Validation passes: syntax, lint, typecheck, relevant pytest suites.

---

## 8) Migration / Rollout

**Migration strategy**

* Migrate knowledge into skills first, then route runtime to use the new agent/task topology.
* Keep legacy prose docs during transition as source material until cleanup is safe.

**Rollout / gating**

* No new feature flag planned.
* Safe rollback: revert to previous agent/task/flow config and backend helpers.

---

## 9) Risks & Failure Modes

* Failure mode: review crew never approves.
  * Detection: bounded replan rounds exhausted.
  * Safe behavior: fail without persistence.
  * Recovery: inspect review decision and specialist outputs.

* Failure mode: skill references drift from runtime expectations.
  * Detection: tests and smoke runs show planning regressions.
  * Safe behavior: writer does not persist invalid outputs.
  * Recovery: adjust skill refs and task mappings.

---

## 10) Observability / Logging

**New/changed events**

* planning crew started/completed
* review crew started/completed
* review requested replan
* writer crew started/completed
* replan rounds exhausted

**Diagnostics**

* runtime telemetry events
* guarded store writes
* per-flow logs

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [ ] `doc/architecture/crewai_flows.md` — document multi-crew routed flows
* [ ] `doc/architecture/agents.md` — update agent taxonomy
* [ ] `doc/architecture/system_architecture.md` — update runtime layering
* [ ] `doc/adr/README.md` — index the new ADR
* [ ] `CHANGELOG.md` — record the runtime cutover

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Flows: `doc/architecture/crewai_flows.md`
* Agents: `doc/architecture/agents.md`
* ADRs: `doc/adr/ADR-037-crewai-flow-outer-orchestration.md`
* ADRs: `doc/adr/ADR-038-crewai-advisory-flows-and-true-hierarchical-crews.md`
* ADRs: `doc/adr/ADR-047-crewai-skills-unified-planning.md`
