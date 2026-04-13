---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-13
Owner: Agents
---
# FEAT: Phase Architect Required Knowledge Injection

* **ID:** FEAT_phase_architect_required_knowledge_injection
* **Status:** Implemented
* **Owner/Area:** Agents / Planning Runtime
* **Last-Updated:** 2026-04-13
* **Related:** `prompts/agents/phase_architect.md`, `src/rps/agents/multi_output_runner.py`

---

## 1) Context / Problem

**Current behavior**

* `run_agent_multi_output()` injects the mandatory output chapter for the requested schema.
* `season_planner` additionally receives a special injected season section from `load_estimation_spec.md`.
* `phase_architect` relies on `knowledge_search` for the knowledge files listed in its binding prompt.

**Problem**

* `phase_architect` declares a binding load order that requires several knowledge files to be read in full before producing `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, or `PHASE_PREVIEW`.
* When the model cannot prove that these files were made available in full, it stops with a no-tool-call response instead of storing artefacts.
* This blocks the whole Phase -> Week -> Workouts planning chain even when the local knowledge store is healthy.

**Constraints**

* No new dependency may be introduced.
* The fix must preserve the current mandatory-output injection behavior.
* The change must remain local to the planning runtime and avoid UI-specific fallback logic.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Ensure `phase_architect` receives its binding required knowledge files in full without depending on retrieval success.
* [x] Keep the injection logic deterministic and testable.
* [x] Preserve existing `season_planner` special-case behavior while reducing one-off prompt assembly drift.

**Non-Goals**

* [x] Redesign `phase_architect.md` binding rules.
* [x] Replace the knowledge store or remove `knowledge_search`.

---

## 3) Proposed Behavior

**User/System behavior**

* When `phase_architect` runs, the runtime injects the mandatory output chapter plus a curated required-knowledge bundle covering the files named as binding prerequisites in the prompt.
* If one of the required files is missing on disk, the runtime continues to surface the failure clearly through logs and agent STOP behavior rather than silently degrading.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: `multi_output_runner`, agent prompt assembly, phase planning orchestration
* Contracts touched: Prompt/runtime contract between `phase_architect` and the local planning runtime

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/agents/knowledge_injection.py`: shared YAML-backed injection loader and section extractor.
* `src/rps/agents/multi_output_runner.py`: consume the shared injection loader instead of a local hard-coded bundle.
* `config/agent_knowledge_injection.yaml`: define the injected `phase_architect` and `season_planner` bundles, including required section slicing for `load_estimation_spec.md`.
* `tests/test_multi_output_runner.py`: verify injected knowledge contains the required `phase_architect` docs.

**Data flow**

* Inputs: agent name, requested output specs, repo knowledge source files
* Processing: resolve configured required file paths, load file contents, append injected sections to `system_prompt`
* Outputs: enriched system prompt for `responses.create`

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none; downstream artefact validation remains unchanged

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if a configured knowledge file is missing, it is not injected and the agent still fails safely under existing STOP rules

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: aligns with existing architecture guidance that prompt and knowledge delivery are part of the runtime contract

**Impacted areas**

* UI: none directly
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: adds unit coverage for prompt assembly
* Deployment/config: none

**Required refactoring**

* Extract prompt-injection helpers instead of keeping agent-specific inline special cases only.

---

## 6) Options & Recommendation

### Option A — Inject required knowledge bundle in runtime

**Summary**

* The runner appends the exact required knowledge documents for `phase_architect` into the system prompt before execution.

**Pros**

* Deterministic and independent of vector-store recall quality
* Matches the binding prompt expectation of full-document availability
* Small, local code change

**Cons**

* Increases prompt size for phase planning runs

**Risk**

* Prompt growth must stay within practical limits for the configured models

### Option B — Relax the prompt and rely only on `knowledge_search`

**Summary**

* Remove or weaken the “must read in full” requirement inside `phase_architect.md`.

**Pros**

* Smaller prompts

**Cons**

* Weakens the contract instead of satisfying it
* Makes agent behavior more dependent on retrieval behavior and store state

### Recommendation

* Choose: Option A
* Rationale: the prompt already defines full-read knowledge as binding. The runtime should satisfy that contract directly instead of asking the model to infer whether retrieval was sufficient.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `phase_architect` prompt assembly injects `file_naming_spec.md` and the other configured required files from YAML config.
* [x] Existing mandatory output injection remains intact.
* [x] `season_planner` uses the YAML-configured Season-only `load_estimation_spec.md` section.
* [x] Unit tests cover the shared required-knowledge injection helper.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] No regressions in: multi-output runner prompt assembly
* [x] Performance guardrail: only `phase_architect` receives the larger required-knowledge bundle

---

## 8) Migration / Rollout

**Migration strategy**

* No workspace migration required.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the prompt injection helper changes

---

## 9) Risks & Failure Modes

* Failure mode: a referenced required knowledge file is moved or deleted
  * Detection: agent logs still show missing required knowledge / no-tool-call STOP
  * Safe behavior: planning run stops before storing invalid artefacts
  * Recovery: restore the file or update the runtime file mapping

* Failure mode: prompt size becomes too large for future agent bundles
  * Detection: model latency or context-limit errors in runner logs
  * Safe behavior: run fails without persisting invalid artefacts
  * Recovery: narrow bundle scope or move to structured runtime attachments

---

## 10) Observability / Logging

**New/changed events**

* No new log event names required for this change.
* Existing `responses.create` and no-tool-call diagnostics remain the primary detection path.

**Diagnostics**

* Check `runtime/athletes/<athlete_id>/logs/rps.log` for phase-architect STOP messages.
* Use unit tests in `tests/test_multi_output_runner.py` to validate prompt assembly behavior.

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_phase_architect_required_knowledge_injection.md` — feature spec for this behavior change
* [ ] `CHANGELOG.md` — summarize the phase-architect knowledge injection fix

---

## 12) Link Map

* `doc/architecture/system_architecture.md`
* `doc/overview/artefact_flow.md`
* `prompts/agents/phase_architect.md`
* `src/rps/agents/multi_output_runner.py`
