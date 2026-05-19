---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Season Contract Context Hardening

* **ID:** FEAT_season_contract_context_hardening
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_planning_chain_contract_hardening, FEAT_season_plan_semantic_hardening

---

## 1) Context / Problem

**Current behavior**

* The season flow computes deterministic selected-scenario, phase-slot, and phase-load contracts in code.
* These contracts are injected into the season-plan prompt primarily as prose blocks.
* The hierarchical `season_plan_finalize` manager can still behave exploratorily and try to rediscover deterministic facts through workspace tools or coworker delegation.

**Problem**

* The manager can be asked to populate phase corridors from `recommended_phase_corridor` values that already exist in code-owned deterministic context, but the manager does not receive those values as a structured contract surface.
* This leads to failure modes such as invented artifact types (`PHASE_LOAD_RECOMMENDATION`) or unnecessary coworker/tool calls.

**Constraints**

* No persisted schema change in v1.
* Deterministic season contracts remain code-owned.
* Existing hierarchical CrewAI season flow remains in place.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Expose deterministic season phase-slot and phase-load contracts to CrewAI tasks through a direct read-only tool surface.
* [x] Inject the same contracts into season-planning task descriptions as structured JSON context, not only prose.
* [x] Narrow `season_plan_finalize` so it consumes contract authority instead of searching the workspace for non-persisted recommendations.

**Non-Goals**

* [ ] Replace the existing season hierarchical crew architecture.
* [ ] Introduce new persisted artifacts for phase-load recommendations.

---

## 3) Proposed Behavior

**User/System behavior**

* During season planning, deterministic season contracts are available as code-owned read-only context tools:
  * `workspace_get_phase_slot_contract`
  * `workspace_get_season_phase_load_context`
* The season finalizer receives the same contracts as structured JSON blocks in its task description.
* `season_plan_finalize` is explicitly scoped to these contract tools instead of generic workspace reads.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * `src/rps/tools/workspace_read_tools.py`
  * `src/rps/tools/workspace_tools.py`
  * `src/rps/crewai_runtime/guardrails.py`
  * `src/rps/agents/crewai_backend.py`
  * season planning skill/task config
* Contracts touched:
  * deterministic `phase_slot_context`
  * deterministic `season_phase_load_context`

---

## 4) Implementation Analysis

**Components / Modules**

* `guardrails.py`: expose current runtime context for deterministic contract consumers.
* `workspace_read_tools.py` / `workspace_tools.py`: add read-only contract tools backed by bound runtime context.
* `crewai_backend.py`: append structured deterministic contract blocks to season planning task descriptions.
* `tasks.yaml`: scope `season_plan_finalize` to contract tools.
* `skills/season/plan-synthesis`: explicitly direct the manager to contract tools instead of artifact search.

**Data flow**

* Inputs: bound `guardrail_runtime_context` values from season flow.
* Processing: surface those values to CrewAI as task-visible structured JSON and read-only tools.
* Outputs: unchanged `SeasonPlanBundleModel`; fewer exploratory tool calls; clearer contract consumption.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none beyond existing season bundle contract guardrails

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none at persisted-schema level
* Fallback behavior: if deterministic runtime context is missing, the new tools return `ok=false` with a direct error

**Conflicts with ADRs / Principles**

* Potential conflicts: none; this reinforces existing deterministic-contract direction.
* Resolution: n/a

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: task/tool traces now include deterministic contract tool access when used
* Validation/tooling: workspace read tool surface expands
* Deployment/config: season finalizer task tool scope changes

**Required refactoring**

* Add a public accessor for bound guardrail context.
* Share contract retrieval semantics across both workspace tool modules.

---

## 6) Options & Recommendation

### Option A — Dedicated deterministic contract tool + structured task injection

**Summary**

* Expose code-owned contracts directly and inject them as JSON context into season tasks.

**Pros**

* Keeps authority in code.
* Removes reliance on non-existent artifacts.
* Reduces prompt-only ambiguity.

**Cons**

* Requires small additions in both tool modules and CrewAI task construction.

**Risk**

* Duplicate context if overused; mitigated by scoping to relevant season tasks.

### Option B — Prompt-only hardening

**Summary**

* Keep current tooling and only strengthen prompts/skills.

**Pros**

* Lower code change surface.

**Cons**

* Does not solve the structural absence of a machine-readable contract surface.

### Recommendation

* Choose: Option A
* Rationale: the failure mode is structural, not purely prompt-quality related.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season planning exposes read-only deterministic contract tools for phase slots and season phase load context.
* [x] `season_plan_finalize` is scoped to deterministic contract tools instead of broad workspace reads.
* [x] Season planning task descriptions include structured deterministic contract JSON blocks when bound context exists.
* [x] Regression tests cover contract-tool access and season-manager contract-context injection.
* [x] Validation passes: `py_compile`, lint, typecheck, targeted pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* No migration required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert tool/task-description/task-config changes

---

## 9) Risks & Failure Modes

* Failure mode: deterministic context not bound when tool is called
  * Detection: tool returns `ok=false` with missing-context error
  * Safe behavior: agent stops/escalates instead of inventing values
  * Recovery: ensure season flow binds guardrail runtime context before crew kickoff

* Failure mode: manager still ignores contract tools and explores
  * Detection: run-store `events.jsonl` shows unrelated workspace tool calls
  * Safe behavior: task still sees structured JSON contract blocks in the description
  * Recovery: tighten prompt/task scope further if needed

---

## 10) Observability / Logging

**New/changed events**

* No new event type required; existing tool telemetry covers new contract-tool calls.

**Diagnostics**

* Check season run `events.jsonl` for contract-tool usage versus exploratory workspace reads.
* Check season manager conversation logs for injected JSON contract blocks.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_season_contract_context_hardening.md` — feature scope and rationale
* [ ] `doc/architecture/agents.md` — optional future follow-up if deeper contract-tool surface needs documenting

