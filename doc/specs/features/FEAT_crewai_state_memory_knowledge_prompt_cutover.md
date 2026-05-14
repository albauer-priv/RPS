---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-14
Owner: Specs
---
# FEAT: CrewAI State, Memory, Knowledge, Prompt, and Guardrail Cutover

* **ID:** FEAT_crewai_state_memory_knowledge_prompt_cutover
* **Status:** Implemented
* **Owner/Area:** Runtime / Agent Architecture
* **Last-Updated:** 2026-05-14
* **Related:** `doc/adr/ADR-046-crewai-state-memory-knowledge-guardrails.md`

---

## 1) Context / Problem

**Current behavior**

* CrewAI runtime in RPS used minimal flow state, broad prompt injection, and task-level `output_pydantic` without a clear separation between static knowledge, runtime instructions, and output-contract enforcement.
* Static reference material, schemas, contracts, and operational instructions were largely mixed inside `config/agent_knowledge_injection.yaml` and rendered inline through `build_injection_block(...)`.
* Long-running Season/Phase/Week/Report/Feed-Forward flows had only shallow `result` state and no explicit CrewAI persistence policy.

**Problem**

* The runtime mixed four concerns that need different mechanisms:
  * deterministic flow state
  * soft memory
  * static reference retrieval
  * hard output validation
* `mandatory_output_*` docs were acting as both schema reminders and output validators, even where CrewAI already provides task-native structured outputs and guardrails.
* The lack of explicit memory/knowledge/persistence layers made the architecture harder to reason about and harder to extend safely.

**Constraints**

* Authoritative truth remains in validated workspace artifacts.
* No replacement of guarded store, schema validation, or run-store telemetry.
* Current local development runs on Python 3.14, where CrewAI activation is still blocked in this repo; the cutover therefore must remain compatibility-safe when CrewAI is unavailable.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add explicit CrewAI config layers for flow persistence, memory policy, knowledge-source mapping, and task guardrail policy.
* [x] Expand outer flow state models with richer typed state and persist-policy awareness.
* [x] Introduce CrewAI memory wiring for shared crews and scoped agent views.
* [x] Separate static knowledge from prompt-level contract injection.
* [x] Introduce task execution policy with `output_pydantic` / `output_json` / prompt-only modes and function guardrails.

**Non-Goals**

* [x] Do not replace authoritative artifacts with memory or knowledge.
* [x] Do not remove workspace read tools for runtime truth access.
* [x] Do not force all persisted artifact families onto `output_json` / `output_pydantic` when their schemas are not yet safe for strict structured-output use.

---

## 3) Proposed Behavior

**User/System behavior**

* Season, Phase, Week, Report, and Feed-Forward flows now expose richer internal state and are marked with explicit CrewAI persistence policy.
* Conversational Coach and Workout Editor crews now have shared CrewAI memory policies and agent-scoped memory views available at construction time.
* Static domain references are mapped into CrewAI knowledge-source config instead of being assumed to live in prompt injection.
* Prompt injection is narrowed to explicit runtime instructions and hard contract framing.
* Task execution policy now explicitly chooses between `pydantic`, `json`, and `prompt_only` output modes, plus deterministic function guardrails and retry budgets.

**UI impact**

* UI affected: No direct UI layout change.
* Indirectly affected runtime surfaces: Coach and Workout Editor now build their conversational crews with explicit memory/knowledge/contract layers.

**Non-UI behavior**

* Components involved: `crewai_runtime`, `agents.crewai_backend`, `agents.knowledge_injection`, planning/advisory flows.
* Contracts touched: flow-state modeling, prompt-injection boundary, knowledge-source mapping, task guardrail policy.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/crewai_runtime/config.py`: load extended CrewAI config bundle.
* `src/rps/crewai_runtime/guardrails.py`: task-policy + guardrail registry.
* `src/rps/crewai_runtime/knowledge.py`: static knowledge-source resolution and CrewAI knowledge kwargs.
* `src/rps/crewai_runtime/memory.py`: crew and agent memory policy resolution.
* `src/rps/crewai_runtime/flows.py`: richer flow state + persist-policy decorator handling.
* `src/rps/agents/crewai_backend.py`: backend task/crew construction uses new policy layers.
* `src/rps/crewai_runtime/coach_chat.py`: conversational crew uses shared memory + knowledge + contract injection.
* `src/rps/agents/knowledge_injection.py`: adds contract-only injection path.

**Data flow**

* Inputs: YAML config under `config/crewai/`, existing prompts, workspace artifacts, existing task definitions.
* Processing:
  * load config bundle
  * resolve knowledge profile per agent/crew
  * resolve memory profile per crew/agent
  * resolve task execution policy per task
  * build agents/tasks/crews with the appropriate CrewAI-native kwargs when runtime is available
* Outputs:
  * richer flow state at runtime
  * structured task guardrails
  * narrowed prompt-contract injection
  * explicit static knowledge-source mapping

**Schema / Artefacts**

* New artefacts: none in workspace.
* Changed artefacts: none in schema versioning terms.
* Validator implications: persisted artifacts still pass through the same guarded validation boundary.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, with compat-safe fallbacks.
* Breaking changes: none at workspace artifact boundary.
* Fallback behavior: if CrewAI is unavailable, the runtime still reports the current compat blocker; config/guardrail loading remains testable locally.

**Conflicts with ADRs / Principles**

* Potential conflicts: snapshot-based planner memory and bounded coach operations could be undermined if memory became authoritative.
* Resolution: ADR-046 explicitly keeps artifacts authoritative and memory/knowledge assistive only.

**Impacted areas**

* UI: Coach / Workout Editor crew construction path only.
* Pipeline/data: no direct pipeline change.
* Renderer: none.
* Workspace/run-store: no change to authoritative persistence; richer flow state only.
* Validation/tooling: task guardrail registry and task execution policy added.
* Deployment/config: new CrewAI YAML config files required.

**Required refactoring**

* Split full injection vs contract-only injection.
* Add knowledge-source, memory, task-policy, and flow-persistence config files.
* Refactor CrewAI task construction to use execution policy instead of assuming `output_pydantic` everywhere.

---

## 6) Options & Recommendation

### Option A — Separate policy layers over the current runtime

**Summary**

* Keep the current runtime shape, but split concerns into dedicated config and helper layers.

**Pros**

* Smallest safe path from the existing architecture.
* Works even while CrewAI cannot be activated locally in Python 3.14.
* Keeps artifacts, schemas, and guarded store unchanged.

**Cons**

* Does not immediately remove every `mandatory_output_*` prompt contract.
* Leaves some retained prompt-level artifact families until stricter structured-output models are safe.

**Risk**

* Partial migration can create mixed modes if not documented clearly.

### Option B — Full forced migration of all tasks to structured output now

**Summary**

* Replace all mandatory-output prompting with `output_json` / `output_pydantic` immediately.

**Pros**

* Cleaner conceptual model.

**Cons**

* Unsafe for current artifact families with open-ended schema sections.
* Would repeat the strict-schema failures already observed in preview/artifact paths.

### Recommendation

* Choose: Option A
* Rationale: it separates concerns immediately without forcing unstable strict-output semantics on artifact families that still require prompt-level contract retention.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `config/crewai/` contains separate policy files for flow persistence, memory, static knowledge, and task execution policy.
* [x] `build_contract_injection_block(...)` exists and filters out static reference material.
* [x] agent/task blueprints expose knowledge profiles and task execution policies.
* [x] backend task construction uses guardrail policy and explicit output-mode selection.
* [x] conversational Coach runtime wires shared crew memory and agent knowledge profiles.
* [x] outer flow state models carry richer typed state and persist-policy awareness.
* [x] Validation passes: targeted `py_compile`, runtime tests, lint, type check.

---

## 8) Migration / Rollout

**Migration strategy**

* No workspace artifact migration.
* Config-layer migration only: existing full injection config remains, while CrewAI-specific runtime now uses contract-only injection plus separate static knowledge config.

**Rollout / gating**

* Feature flag / config: CrewAI activation remains gated by existing runtime compatibility checks.
* Safe rollback: revert to previous backend/config loader path; artifact contracts remain unchanged.

---

## 9) Risks & Failure Modes

* Failure mode: CrewAI knowledge or memory storage config drifts from expected path.
  * Detection: runtime config inspection, memory/knowledge runbooks, startup logs.
  * Safe behavior: agent still runs with prompt contracts and workspace tools.
  * Recovery: fix config and rerun; no authoritative artifact corruption.
* Failure mode: overly aggressive removal of prompt-level contracts.
  * Detection: guardrail failures, schema validation failures.
  * Safe behavior: persisted write still fails at guarded validation boundary.
  * Recovery: retain or restore prompt-level mandatory output for that family.

---

## 10) Observability / Logging

**New/changed events**

* No new event type required in this slice.
* Flow state now carries explicit persistence summaries for diagnostics.

**Diagnostics**

* Config layer: `config/crewai/*.yaml`
* Runtime: `src/rps/crewai_runtime/*.py`
* Existing run-store telemetry remains canonical for executed runs.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/architecture/crewai_flows.md` — document persistence/memory/knowledge/guardrail layers.
* [x] `doc/architecture/agents.md` — document knowledge and memory boundary rules.
* [x] `doc/architecture/system_architecture.md` — update runtime knowledge/prompt/output enforcement architecture.
* [x] `doc/runbooks/crewai_flow_persistence.md` — persistence and resume/fork notes.
* [x] `doc/runbooks/crewai_memory.md` — memory scope and reset/debug usage.
* [x] `doc/runbooks/crewai_knowledge.md` — static knowledge-source indexing/storage policy.
* [x] `doc/runbooks/crewai_prompt_and_guardrails.md` — prompt debugging and structured-output/guardrail debugging.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Agents: `doc/architecture/agents.md`
* Flow catalog: `doc/architecture/crewai_flows.md`
* ADR: `doc/adr/ADR-046-crewai-state-memory-knowledge-guardrails.md`
* Validation runbook: `doc/runbooks/validation.md`

---

## Out of Scope / Deferred

* Full migration of every persisted artifact family away from retained mandatory-output contracts.
* Removal of `knowledge_search` from runtime-truth access.
* Changing authoritative workspace artifact ownership.
