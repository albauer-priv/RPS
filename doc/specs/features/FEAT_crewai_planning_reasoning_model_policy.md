---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-14
Owner: Runtime
---
# FEAT: CrewAI Planning, Reasoning, and Model Policy

* **ID:** FEAT_crewai_planning_reasoning_model_policy
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime
* **Last-Updated:** 2026-05-14
* **Related:** `doc/specs/features/FEAT_skills_first_multi_crew_planning_runtime.md`

---

## 1) Context / Problem

**Current behavior**

* CrewAI agent model selection is mostly driven by generic `RPS_LLM_*` environment overrides.
* Crew-level planning and agent-level reasoning are not expressed as one explicit runtime policy layer.
* Cost-sensitive roles such as writers and context readers can drift onto oversized models without a clear repo-owned default.

**Problem**

* Planning, reasoning, and model routing are three separate concerns, but they were not encoded separately.
* The new multi-crew planning runtime needs deterministic defaults for which crews get CrewAI planning, which agents get reasoning, and which model tier each role should use.

**Constraints**

* CrewAI planning is a crew-level feature only.
* CrewAI reasoning is an agent-level feature only.
* Writers must stay non-reasoning.
* Review and writer crews should stay planning-free by default.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add one canonical runtime policy file for crew planning, agent reasoning, and model routing.
* [x] Wire that policy into CrewAI `Crew(...)` and `Agent(...)` construction.
* [x] Preserve environment overrides where they still make sense.

**Non-Goals**

* [x] No dynamic online price discovery at runtime.
* [x] No change to the existing task graph or artifact contracts.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_planning` and `phase_planning` keep CrewAI-native planning disabled by default because RPS already uses explicit YAML task chains for planning, review, and writer steps.
* Review, writer, report, and conversational crews stay planning-free.
* Reasoning is enabled only on the selected planning/review specialists and managers.
* Writers, context readers, and bounded routing/status roles stay non-reasoning.
* Model defaults are role-specific and can still be overridden by environment variables; CrewAI-native planning remains available through env/config overrides for experiments.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `config/crewai/runtime_profiles.yaml`, CrewAI config loader, provider resolution, CrewAI backend.
* Contracts touched: runtime config only.

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/runtime_profiles.yaml`: canonical policy source.
* `src/rps/crewai_runtime/config.py`: load + validate runtime profiles.
* `src/rps/crewai_runtime/provider.py`: planning-LLM override resolution.
* `src/rps/core/config.py`: crew-planning env override parsing.
* `src/rps/agents/crewai_backend.py`: apply planning/reasoning/model policy to live CrewAI objects.

**Data flow**

* Inputs: YAML runtime profile, env overrides, existing agent/task/skill configs.
* Processing: validate names/models -> resolve per-agent/per-crew runtime profile -> build Agent/Crew kwargs.
* Outputs: correctly configured CrewAI runtime objects.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: config validation must fail fast on unknown crew/agent/model names.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes, with additive config.
* Breaking changes: invalid runtime-profile references now fail fast.
* Fallback behavior: env overrides still apply on top of YAML defaults.

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified.
* Resolution: aligns with the multi-crew runtime split already adopted.

**Impacted areas**

* UI: indirect status/model display only.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: new config validation.
* Deployment/config: new `runtime_profiles.yaml` plus optional env overrides.

**Required refactoring**

* Add runtime-profile bundle loading.
* Split crew-planning provider resolution from per-agent LLM routing.
* Attach reasoning/planning kwargs only where policy enables them.

---

## 6) Options & Recommendation

### Option A — Explicit runtime policy file

**Summary**

* Keep planning, reasoning, and model routing in one dedicated config layer.

**Pros**

* Centralized and testable.
* Keeps `agents.yaml` focused on role definitions.
* Makes cost/quality tradeoffs reviewable.

**Cons**

* Adds another YAML config file to maintain.

**Risk**

* Drift between config names and live crews/agents unless validated.

### Option B — Keep everything in env vars or `agents.yaml`

**Summary**

* Continue routing by generic env overrides or overload role config.

**Pros**

* Fewer files.

**Cons**

* Poor visibility.
* Harder validation.
* Mixes role definition with runtime execution policy.

### Recommendation

* Choose: Option A
* Rationale: it is the only option that keeps multi-crew planning policy explicit and auditable.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `runtime_profiles.yaml` exists and validates all referenced crews/agents/models.
* [x] `season_planning` and `phase_planning` build without CrewAI-native `planning=True` by default; configured planning LLMs remain available for explicit override tests.
* [x] Reasoning flags are attached only to the intended agents.
* [x] Writers remain non-reasoning and planning-free.
* [x] Validation passes: syntax, lint, typecheck, pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* Additive runtime policy; no artifact/schema migration required.

**Rollout / gating**

* Feature flag / config: `config/crewai/runtime_profiles.yaml`
* Safe rollback: remove the file and wiring changes together.

---

## 9) Risks & Failure Modes

* Failure mode: runtime profile references a missing agent or crew.
  * Detection: config loader raises `ValueError` during startup/tests.
  * Safe behavior: fail before any live planning run starts.
  * Recovery: fix YAML references.

* Failure mode: planning model override is invalid.
  * Detection: config validation rejects the model string.
  * Safe behavior: startup/test failure instead of silent fallback.
  * Recovery: switch to an allowed model.

---

## 10) Observability / Logging

**New/changed events**

* No new telemetry events required.

**Diagnostics**

* Runtime construction can now be inspected through loaded config and unit tests.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_crewai_planning_reasoning_model_policy.md` — feature definition and rollout.
* [x] `CHANGELOG.md` — unreleased runtime-policy change summary.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* CrewAI flows: `doc/architecture/crewai_flows.md`
* Validation / runbooks: `doc/runbooks/`
* Multi-crew runtime feature: `doc/specs/features/FEAT_skills_first_multi_crew_planning_runtime.md`
