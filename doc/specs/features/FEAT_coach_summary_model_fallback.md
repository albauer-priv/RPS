---
Version: 1.1
Status: Implemented
Last-Updated: 2026-02-08
Owner: UI
---
# FEAT: Coach Summary Model Fallback

* **ID:** FEAT_coach_summary_model_fallback
* **Status:** Implemented
* **Owner/Area:** Coach chat runtime
* **Last-Updated:** 2026-02-08
* **Related:** FEAT_multi_provider_llm

---

## 1) Context / Problem

**Current behavior**

* Coach summary uses `RPS_LLM_MODEL_COACH_SUMMARY` or `RPS_LLM_MODEL_SUMMARY`, falling back to `gpt-5-nano`.

**Problem**

* When using non-OpenAI providers (e.g., Groq), the hardcoded fallback can select an unavailable model and break summaries.

**Constraints**

* No new dependencies.
* Must respect per-agent overrides.

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Remove the hardcoded `gpt-5-nano` fallback for coach summaries.
* [ ] Default summary model to the active coach model when no summary override is set.

**Non-Goals**

* [ ] No change to summary prompt content.
* [ ] No change to storage format.

---

## 3) Proposed Behavior

**User/System behavior**

* If `RPS_LLM_MODEL_COACH_SUMMARY` or `RPS_LLM_MODEL_SUMMARY` is not set, coach summaries use the same model configured for the coach chat (`RPS_LLM_MODEL_COACH`).

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `rps.ui.rps_chatbot.Chat.summarize`.
* Contracts touched: none.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/ui/rps_chatbot.py`: adjust summary model selection.

**Data flow**

* Inputs: environment variables.
* Processing: model selection for summary requests.
* Outputs: summary response.

**Schema / Artefacts**

* None.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none.

**Conflicts with ADRs / Principles**

* None.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: none.
* Deployment/config: none.

**Required refactoring**

* None.

---

## 6) Options & Recommendation

### Option A — Fallback to coach model

**Summary**

* Use `RPS_LLM_MODEL_COACH` when no summary override is set.

**Pros**

* Avoids provider mismatch errors.

**Cons**

* Summary may be more expensive if coach model is large.

### Option B — Keep hardcoded OpenAI fallback

**Summary**

* Retain `gpt-5-nano`.

**Pros**

* Cheap and fast on OpenAI.

**Cons**

* Breaks non‑OpenAI setups.

### Recommendation

* Choose: Option A
* Rationale: Correctness across providers.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Coach summaries default to `RPS_LLM_MODEL_COACH` when no summary override exists.
* [ ] No regression in coach chat.
* [ ] Validation passes: `python -m py_compile $(git ls-files '*.py')`

---

## 8) Migration / Rollout

**Migration strategy**

* None.

**Rollout / gating**

* None.

---

## 9) Risks & Failure Modes

* Failure mode: Summary uses a large model, increasing cost.
  * Detection: usage logs.
  * Safe behavior: still produces a summary.
  * Recovery: set `RPS_LLM_MODEL_COACH_SUMMARY` to a smaller model.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Check coach logs for summary model selection (if added).

---

## 11) Documentation Updates

* [ ] `CHANGELOG.md` — note summary model fallback change.

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: [[doc/ui/ui_spec.md](doc/ui/ui_spec.md)](doc/ui/ui_spec.md)
* UI contract (Streamlit): [[doc/ui/streamlit_contract.md](doc/ui/streamlit_contract.md)](doc/ui/streamlit_contract.md)
* Architecture: [[doc/architecture/system_architecture.md](doc/architecture/system_architecture.md)](doc/architecture/system_architecture.md)
* Workspace: [[doc/architecture/workspace.md](doc/architecture/workspace.md)](doc/architecture/workspace.md)
* Schema versioning: [[doc/architecture/schema_versioning.md](doc/architecture/schema_versioning.md)](doc/architecture/schema_versioning.md)
* Logging policy: [[doc/specs/contracts/logging_policy.md](doc/specs/contracts/logging_policy.md)](doc/[specs/contracts/logging_policy.md](specs/contracts/logging_policy.md))
* Validation / runbooks: [[doc/runbooks/validation.md](doc/runbooks/validation.md)](doc/runbooks/validation.md)
* ADRs: n/a
