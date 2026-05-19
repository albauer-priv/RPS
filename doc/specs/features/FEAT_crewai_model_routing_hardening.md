---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: CrewAI Runtime
---
# FEAT: CrewAI Model Routing Hardening

* **ID:** FEAT_crewai_model_routing_hardening
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime
* **Last-Updated:** 2026-05-19
* **Related:** `config/crewai/runtime_profiles.yaml`, `src/rps/agents/crewai_backend.py`, `src/rps/core/config.py`

---

## 1) Context / Problem

**Current behavior**

* Streamlit passes `SETTINGS.model_for_agent(...)` into planning flows as a generic `model_override`.
* Without `RPS_LLM_MODEL`, the app-level fallback model was `gpt-4.1`.
* CrewAI agent construction preferred the generic override over the role-specific `runtime_profiles.yaml` model.

**Problem**

* A global UI/default model can override specialist CrewAI runtime profiles.
* Season/Phase/Week specialist routing can unintentionally run on a legacy model instead of the configured GPT-5.4-family profile.

**Constraints**

* No new dependencies.
* No persisted artifact schema change.
* Existing explicit CrewAI runtime profiles remain the source of truth for specialist model routing.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Runtime profiles win over generic app-level defaults for CrewAI agents.
* [x] The non-Groq app fallback uses the GPT-5.4 family instead of `gpt-4.1`.
* [x] Only GPT-5.4-family models are allowed in CrewAI runtime profiles.

**Non-Goals**

* [x] No full model-cost optimization pass.
* [x] No change to persisted planning schemas.

---

## 3) Proposed Behavior

**User/System behavior**

* Planning crews use role-specific model profiles unless no profile exists.
* A global app model fallback no longer drags specialist planning agents onto `gpt-4.1`.

**UI impact**

* UI affected: No direct UI layout change.

**Non-UI behavior**

* Components involved: app settings, CrewAI backend, CrewAI runtime profiles.
* Contracts touched: runtime model-routing contract only.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/core/config.py`: switch non-Groq app fallback to `gpt-5.4-mini`.
* `src/rps/agents/crewai_backend.py`: prefer agent runtime profile model before generic override.
* `config/crewai/runtime_profiles.yaml`: restrict allowed runtime profile models to the GPT-5.4 family and move writer/syntax roles to `gpt-5.4-mini`.

**Data flow**

* Inputs: environment variables, runtime profile YAML, UI model resolver.
* Processing: CrewAI agent construction resolves model from runtime profile first.
* Outputs: LLM kwargs passed to CrewAI agent instances.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: runtime profile model validation still applies.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for persisted data.
* Breaking changes: non-GPT-5.4-family models can no longer be used as configured CrewAI runtime profile models.
* Fallback behavior: non-Groq app default becomes `gpt-5.4-mini`.

**Conflicts with ADRs / Principles**

* Potential conflicts: none.
* Resolution: aligns with explicit runtime profile ownership.

**Impacted areas**

* UI: no visual change.
* Pipeline/data: no artifact change.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: runtime profile validation disallows non-GPT-5.4-family models.
* Deployment/config: operators should use explicit GPT-5.4-family overrides if needed.

**Required refactoring**

* Adjust model precedence in CrewAI backend.
* Update tests that used `gpt-4.1` as a planning-model override example.

---

## 6) Options & Recommendation

### Option A — Runtime profiles first

**Summary**

* Keep UI resolver wiring intact, but make CrewAI agent runtime profiles take precedence over generic overrides.

**Pros**

* Small change.
* Preserves role-specific model routing.
* Prevents global defaults from changing specialist behavior.

**Cons**

* Generic model overrides no longer override profiled CrewAI agents.

**Risk**

* Operators expecting one global override for all CrewAI specialists must use profile-specific configuration instead.

### Option B — Remove UI model resolver from planning flows

**Summary**

* Stop passing the UI resolver into all planning flows.

**Pros**

* Strong boundary.

**Cons**

* Larger refactor across Season/Phase/Week/Report/Coach paths.

### Recommendation

* Choose: Option A.
* Rationale: It fixes the observed leak while preserving the existing runtime profile system.

---

## 7) Acceptance Criteria

* [x] Non-Groq app fallback is `gpt-5.4-mini`.
* [x] A generic `model_override` does not override an agent runtime profile model.
* [x] Only GPT-5.4-family models are listed in CrewAI runtime `allowed_models`.
* [x] Validation passes for targeted CrewAI runtime tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted migration.
* Runtime operators should replace any intentional non-GPT-5.4-family profile usage with GPT-5.4-family models.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: restore the previous fallback and precedence if needed.

---

## 9) Risks & Failure Modes

* Failure mode: a profile references a removed model.
  * Detection: CrewAI config validation fails on startup/tests.
  * Safe behavior: fail fast before planning.
  * Recovery: update `runtime_profiles.yaml`.

* Failure mode: operators expect global model override to apply to profiled agents.
  * Detection: model telemetry shows runtime-profile models.
  * Safe behavior: explicit profile remains authoritative.
  * Recovery: change the runtime profile for the target agent.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Inspect CrewAI telemetry plus provider/model error messages in `runtime/athletes/<athlete_id>/logs/rps.log`.

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — record runtime model-routing hardening.

---

## 12) Link Map

* `config/crewai/runtime_profiles.yaml` — canonical specialist model routing.
* `src/rps/agents/crewai_backend.py` — CrewAI agent construction.
* `src/rps/core/config.py` — app-level environment defaults.
