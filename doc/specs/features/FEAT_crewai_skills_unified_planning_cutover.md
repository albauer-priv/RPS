---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-14
Owner: CrewAI Runtime
---
# FEAT: CrewAI Skills Unified Planning Cutover

* **ID:** FEAT_crewai_skills_unified_planning_cutover
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime / Planning
* **Last-Updated:** 2026-05-14
* **Related:** `doc/adr/ADR-047-crewai-skills-unified-planning.md`

---

## 1) Context / Problem

**Current behavior**

* Agent methodology, guidance, and runtime framing were mixed in prompt markdown, `config/agent_knowledge_injection.yaml`, and ad-hoc injected document bundles.
* Large shared files such as `load_estimation_spec.md` were sliced at runtime by chapter.
* Coach conversational specialists and planning specialists shared domain logic conceptually, but not through one explicit reusable skill layer.

**Problem**

* The old injection path duplicated methodology across prompts and orchestration helpers.
* Runtime heading slicing created hidden coupling between prompts and document layout.
* Coach, Workout Editor, and planning flows could not reuse the same domain-specialist methodology cleanly.

**Constraints**

* Contracts and schemas remain explicit authoritative artefacts.
* Tool authorization remains code/config owned.
* The current local runtime still needs a compatibility path because CrewAI execution is blocked on Python 3.14 in local development.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Remove `agent_knowledge_injection` as the runtime methodology path.
* [x] Introduce a repo-local `skills/` tree and attach skills through explicit CrewAI config.
* [x] Reuse shared week/phase/season methodology across conversational and planning specialists.
* [x] Remove runtime chapter slicing and replace it with decomposed canonical source documents.
* [x] Shift persisted artifact ownership to explicit writer agents.

**Non-Goals**

* [x] This change does not replace schemas or contract files with skills.
* [x] This change does not merge all conversational and planning agents into a single agent.

---

## 3) Proposed Behavior

**User/System behavior**

* Coach, Workout Editor, and planning flows now resolve shared methodology through configured skills instead of injected markdown bundles.
* Week conversational specialists are renamed to shared week-domain specialists and reuse the same skill families as planning agents.
* Season and Phase planning manager roles are split between planning and feed-forward management; persisted artifact writing belongs to dedicated writer agents.
* Runtime document slicing is removed; load-estimation guidance is now stored as decomposed source documents.

**UI impact**

* UI affected: No direct layout change.
* Prompt behavior, preview generation, and planning persistence use the new skill-backed runtime definitions.

**Non-UI behavior (if applicable)**

* Components involved: `src/rps/crewai_runtime/*`, `src/rps/agents/crewai_backend.py`, `src/rps/orchestrator/*`, `config/crewai/*`, `prompts/agents/*`.
* Contracts touched: CrewAI agent/task config, memory/knowledge config, prompt composition, task output policies.

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/skills.yaml`: skill assignment by crew and agent.
* `src/rps/crewai_runtime/skills.py`: skill resolution and native CrewAI skill kwargs.
* `config/crewai/agents.yaml` / `tasks.yaml`: shared specialist renames, writer-agent ownership.
* `src/rps/agents/crewai_backend.py`: writer-task output policies, skill-backed prompt composition, manager/writer orchestration.
* `src/rps/crewai_runtime/coach_chat.py`: conversational crew reuses shared week specialists and skill prompt assembly.

**Data flow**

* Inputs: prompt markdown, skill packages, knowledge bundles, workspace tools, schemas/contracts.
* Processing: resolve crew/agent skill bundles and attach them through native CrewAI `skills=[...]`.
* Outputs: unchanged planning artefacts, but produced by renamed specialists and writer-agent task ownership.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none; task ownership and prompt construction only.
* Validator implications: persisted artifact tasks now prefer `output_json` plus guardrails.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Partially.
* Breaking changes: Agent names, skill config, and prompt/runtime assembly changed. Tests and docs needed coordinated updates.
* Fallback behavior: none. Native CrewAI skill activation is the runtime contract.

**Conflicts with ADRs / Principles**

* Potential conflicts: none unresolved. This extends ADR-046 by separating skill-driven methodology from knowledge and contracts.
* Resolution: recorded in `ADR-047-crewai-skills-unified-planning.md`.

**Impacted areas**

* UI: Coach and Workout Editor use renamed shared specialists.
* Pipeline/data: planning persistence ownership shifts to writer agents.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: task output policy and guardrail enforcement updated.
* Deployment/config: new `config/crewai/skills.yaml`; old injection config removed.

**Required refactoring**

* Replace `knowledge_injection.py` with skill resolution helpers.
* Rewrite CrewAI agent/task config to shared specialist names.
* Decompose load-estimation guidance into atomic source documents.
* Reduce prompts to runtime-local instructions.

---

## 6) Options & Recommendation

### Option A — Skills-first unified planning (implemented)

**Summary**

* Use repo-local CrewAI skills as the primary methodology layer and reuse them across conversational and planning specialists.

**Pros**

* One explicit capability model for methodology.
* Cleaner agent reuse across surfaces.
* No runtime heading slicing.

**Cons**

* Large coordinated refactor.
* Requires compatibility prompt rendering while local CrewAI execution remains blocked.

**Risk**

* Misaligned agent/task names or incomplete doc migration could break runtime wiring.

### Option B — Keep injection and add skills gradually

**Summary**

* Run two methodology systems in parallel.

**Pros**

* Lower short-term churn.

**Cons**

* Preserves duplication and hidden precedence rules.

### Recommendation

* Choose: Option A
* Rationale: the old injection path was the main source of duplication and hidden coupling.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `config/agent_knowledge_injection.yaml` is removed from runtime use.
* [x] `src/rps/agents/knowledge_injection.py` is removed.
* [x] Shared week specialists replace the old coach-only specialist names.
* [x] Dedicated writer agents own persisted artifact task definitions.
* [x] Runtime load-estimation section slicing is removed.
* [x] Validation passes: syntax, lint, typecheck, targeted pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* Rename agents/tasks in CrewAI config.
* Introduce skills and compatibility prompt rendering.
* Migrate runtime references from injection functions to skill helpers.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: restore `agent_knowledge_injection.yaml`, `knowledge_injection.py`, and old config wiring from git history.

---

## 9) Risks & Failure Modes

* Failure mode: missing required skill path.
  * Detection: config validation / runtime error from `resolve_agent_skill_profile`.
  * Safe behavior: fail fast during construction.
  * Recovery: restore missing skill package or config entry.
* Failure mode: writer-agent output no longer conforms to envelope shape.
  * Detection: task guardrails and schema validation.
  * Safe behavior: fail before persistence.
  * Recovery: adjust prompt/skill content or task output mode.

---

## 10) Observability / Logging

**New/changed events**

* Skill resolution failures surface as runtime construction errors.
* Existing CrewAI telemetry remains unchanged.

**Diagnostics**

* `config/crewai/skills.yaml`
* `skills/**/SKILL.md`
* `runtime/athletes/<id>/logs/rps.log`

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/architecture/crewai_flows.md` — note shared specialists and skills-first runtime.
* [x] `doc/architecture/agents.md` — rename shared specialists and writer agents.
* [x] `doc/architecture/system_architecture.md` — document skills as the methodology layer.
* [x] `doc/adr/README.md` — index the new ADR.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* CrewAI flows: `doc/architecture/crewai_flows.md`
* Workspace: `doc/overview/artefact_flow.md`
* ADRs: `doc/adr/ADR-046-crewai-state-memory-knowledge-guardrails.md`, `doc/adr/ADR-047-crewai-skills-unified-planning.md`
