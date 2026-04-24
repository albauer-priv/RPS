---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-24
Owner: Planning
---
# FEAT: Resolved Context Prompt Alignment

* **ID:** FEAT_resolved_context_prompt_alignment
* **Status:** Implemented
* **Owner/Area:** Planning / Agent Prompts
* **Last-Updated:** 2026-04-24
* **Related:** `FEAT_resolved_kpi_context_injection`, `FEAT_resolved_planner_context_expansion`

---

## 1) Context / Problem

**Current behavior**

* Orchestrators now inject deterministic planner facts as resolved context blocks.
* Planner prompts still emphasize raw artefact loading and local re-derivation.

**Problem**

* Agents can still waste tool calls reloading artefacts just to rediscover already-resolved facts.
* Some STOP paths remain too eager because prompts do not clearly state that resolved context satisfies deterministic fact lookup.

**Constraints**

* Keep raw workspace tools available for traceability and non-resolved details.
* Do not weaken binding requirements for true missing artefacts.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make resolved context authoritative in planner prompts.
* [x] Reduce needless raw artefact search for already-resolved facts.
* [x] Expand resolved context with zone-model and logistics summaries where deterministic.

**Non-Goals**

* [ ] Remove raw workspace tools from prompts.
* [ ] Replace all artefact reads with resolved context in one step.

---

## 3) Proposed Behavior

**User/System behavior**

* Planner prompts now state:
  * if a `Resolved ... Context` block is present, use it directly
  * do not search, infer, or reinterpret the same facts again
  * raw workspace calls are for non-resolved details, traceability, and truly missing information
* Orchestrators additionally inject:
  * `Resolved Zone Model Context`
  * `Resolved Logistics Context`

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `resolved_context.py`, `season_flow.py`, `plan_week.py`, planner prompt files
* Contracts touched: none beyond clarified prompt handling

---

## 4) Implementation Analysis

**Components / Modules**

* `resolved_context.py`
  * add zone-model summary
  * add logistics summary
* `season_flow.py` / `plan_week.py`
  * inject the new summaries
* `prompts/agents/*.md`
  * align tool guidance with resolved context authority

**Data flow**

* Inputs: latest `ZONE_MODEL`, latest `LOGISTICS`
* Processing: summarize deterministic fields in code
* Outputs: planner prompt blocks; fewer agent-side rediscovery steps

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if a resolved block is missing, planners continue to use raw artefacts

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: consistent with deterministic orchestration and reduced model guesswork

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: latest `ZONE_MODEL` / `LOGISTICS` reads
* Validation/tooling: prompt tests and orchestrator tests
* Deployment/config: none

**Required refactoring**

* Consolidate more planner-facing summaries under `resolved_context.py`

---

## 6) Options & Recommendation

### Option A — Align prompts to resolved context and expand deterministic summaries

**Summary**

* Treat resolved context as authoritative and add zone/logistics facts.

**Pros**

* Fewer redundant tool calls
* Fewer false STOPs
* Clearer planner responsibility boundary

**Cons**

* Prompts become a bit more explicit and longer

### Option B — Keep prompts unchanged and rely only on orchestration text

**Summary**

* Let raw artefact loading remain the dominant prompt pattern.

**Pros**

* Smaller prompt diff

**Cons**

* Keeps the main ambiguity unresolved

### Recommendation

* Choose: Option A
* Rationale: the prompts must explicitly recognize the resolved context architecture or the code refactor stays only half-effective.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_planner`, `phase_architect`, and `week_planner` prompts explicitly honor resolved context blocks
* [x] zone-model and logistics summaries are injected in orchestrator planner inputs
* [x] Validation passes: targeted pytest, `py_compile`, lint, type check

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert prompt and `resolved_context` additions

---

## 9) Risks & Failure Modes

* Failure mode: prompts still over-read raw artefacts despite resolved context
  * Detection: future logs still show avoidable search/STOP behavior
  * Safe behavior: planners still function; this is optimization/robustness rather than correctness loss
  * Recovery: tighten prompt language further or move more resolution into code

---

## 10) Observability / Logging

**New/changed events**

* None

**Diagnostics**

* Captured orchestrator `user_input` in tests
* Remote run logs for planner tool-call patterns

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_resolved_context_prompt_alignment.md`
* [x] `CHANGELOG.md`

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Planning flow: `doc/overview/how_to_plan.md`
* Zone model schema: `specs/schemas/zone_model.schema.json`
* Logistics schema: `specs/schemas/logistics.schema.json`
