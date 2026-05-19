---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Macrocycle Task Runtime Semantics

* **ID:** FEAT_macrocycle_task_runtime_semantics
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19
* **Related:** `season_macrocycle_draft`, `macrocycle_architect`

---

## 1) Context / Problem

**Current behavior**

* `season_macrocycle_draft` runs as an internal reasoning specialist step inside the season planning crew.
* The task returns a typed internal draft and is not responsible for writing a persisted workspace artefact.
* The current runtime profile leaves `macrocycle_architect` reasoning enabled.

**Problem**

* In runtime conversation logs, the macrocycle step is observed and judged as if it were a file-writing worker step.
* The framework-level observer marks the step unsuccessful because no write-and-verify artefact is created, despite the task having enough planning facts to produce a structured macrocycle draft.
* The task itself also lacks a direct read-tool surface if it needs to reload event/snapshot/phase-slot context.

**Constraints**

* No change to the public season artefact contract.
* Keep `season_macrocycle_draft` as an internal typed draft step.
* Do not widen tool scope beyond what the macrocycle step actually needs.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Treat `season_macrocycle_draft` as a response-only internal reasoning step, not a write-and-verify worker step.
* [x] Give `macrocycle_architect` the minimal read-tool surface needed to reload event/snapshot/phase-slot context when necessary.
* [x] Remove aggressive reasoning-agent behavior that introduces framework observer/replan prompts for this bounded specialist.

**Non-Goals**

* [ ] Change the final `SEASON_PLAN` artefact writer contract.
* [ ] Introduce new persisted intermediate artefacts for the macrocycle step.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_macrocycle_draft` should succeed by returning a structured typed macrocycle draft.
* The specialist should not interpret its job as creating or verifying a workspace file unless the task explicitly exposes write-capable tools and requires a persisted artefact.
* If the step needs more context, it should use its bounded workspace read tools.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  * `config/crewai/tasks.yaml`
  * `config/crewai/runtime_profiles.yaml`
  * `src/rps/agents/crewai_backend.py`
* Contracts touched:
  * internal specialist task prompt contract
  * season planning specialist tool scope

---

## 4) Implementation Analysis

**Components / Modules**

* `tasks.yaml`: add explicit macrocycle tool guidance and read tools.
* `runtime_profiles.yaml`: disable reasoning for `macrocycle_architect`.
* `crewai_backend.py`: state plainly that internal reasoning tasks do not create workspace files unless explicitly configured to do so.
* `tests/test_crewai_runtime.py`: assert the new task scope and runtime profile behavior.

**Data flow**

* Inputs: selected scenario context, planning events, athlete state snapshot, deterministic phase-slot context.
* Processing: macrocycle specialist builds the typed internal draft directly from prompt/runtime context and bounded read tools.
* Outputs: typed `season_macrocycle_draft` only.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: existing typed-output validation remains unchanged

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: macrocycle step can still operate from injected deterministic context if it does not need tool reloads

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with the existing contract-consumption hardening direction

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: no new files; read-tool access only
* Validation/tooling: test expectations updated
* Deployment/config: crew runtime profile and task config updated

**Required refactoring**

* Add explicit non-write rule to internal specialist task wrapper
* Normalize macrocycle task config with the rest of bounded season specialists

---

## 6) Options & Recommendation

### Option A — Disable macrocycle reasoning and add bounded read tools

**Summary**

* Keep the task bounded, remove framework observer/replan behavior, and let the step operate as a typed-response specialist.

**Pros**

* Removes the observed failure mode directly
* Keeps specialist behavior aligned with the rest of the hardened planning chain
* Reduces unnecessary meta-planning/token overhead

**Cons**

* Slightly less agentic exploration if the task truly needed it

**Risk**

* If the macrocycle step actually depended on broader autonomous exploration, draft quality could drop

### Option B — Keep reasoning enabled and only add tools

**Summary**

* Preserve agentic behavior and hope the larger tool surface is enough

**Pros**

* Minimal model-behavior change

**Cons**

* The framework observer/write-semantics mismatch likely remains
* Higher token cost and more runtime variance

### Recommendation

* Choose: Option A
* Rationale: the observed failure is caused by mismatched runtime semantics, and the macrocycle step is still a bounded specialist rather than a final manager/writer.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `season_macrocycle_draft` declares explicit bounded read-tool usage in task config.
* [x] `macrocycle_architect` no longer has runtime reasoning enabled.
* [x] Internal specialist prompt wrapper states that internal reasoning tasks do not create workspace files unless explicitly configured.
* [x] Validation passes: `py_compile`, lint, type check, targeted tests
* [x] No regressions in season planning config loading and task tool binding tests

---

## 8) Migration / Rollout

**Migration strategy**

* None required

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert task/runtime-profile/prompt-wrapper changes

---

## 9) Risks & Failure Modes

* Failure mode: macrocycle step still blocks on missing context

  * Detection: conversation logs still report missing inputs or write-and-verify failure
  * Safe behavior: step returns compact blocked typed output instead of inventing files
  * Recovery: extend only the needed read-tool scope or preserve additional deterministic runtime blocks

---

## 10) Observability / Logging

**New/changed events**

* No new event types

**Diagnostics**

* Inspect specialist conversation logs for `macrocycle_architect`
* Inspect season run `events.jsonl` for task start/finish and model usage

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [CHANGELOG.md](/Users/alexander/RPS/CHANGELOG.md) — record macrocycle runtime-semantics hardening
