---
Version: 1.0
Status: Draft
Last-Updated: 2026-02-06
Owner: Architecture
---
# FEAT: Multi-provider LLM runtime + local vectorstore + orchestration roadmap

* **ID:** FEAT_multi_provider_llm
* **Status:** Draft
* **Owner/Area:** OpenAI/Orchestration
* **Last-Updated:** 2026-02-06
* **Related:** ADR-025-multi-provider-runtime-and-local-vectorstore.md

---

## 1) Context / Problem

**Current behavior**

* RPS uses the OpenAI Responses API directly and OpenAI-managed vectorstores.
* Agent execution assumes OpenAI tooling, response formats, and vectorstore lifecycle.

**Problem**

* The system is locked to one provider path and cannot switch models/providers.
* Vectorstore persistence is remote-only; offline/local usage is not supported.
* Orchestration evolution (CrewAI) cannot be cleanly layered without abstraction.
* Provider credentials are global-only; per-agent API keys/base URLs are not supported.

**Constraints**

* No new dependencies without approval.
* Maintain existing UI behaviors and agent contracts.
* Streaming, compaction, and tool-call semantics must remain intact.
* Vectorstore sync rules (manifest hash) must remain authoritative.
* Compaction for non-OpenAI providers must be handled by a custom strategy (Coach only).

---

## 2) Goals & Non-Goals

**Goals**

* [ ] Replace OpenAI-specific runtime with LiteLLM as the only LLM runtime path.
* [ ] Add embedded ChromaDB as the primary vectorstore (local-first).
* [ ] Preserve current agent UX, tool contracts, and prompt injection behavior.
* [ ] Provide a clear migration path and rollback strategy.
* [ ] Define phase-2 integration path for CrewAI orchestration.
* [ ] Implement custom compaction for non-OpenAI providers in Coach flows.
* [ ] Support per-agent provider config (API key, base URL, model) with clear precedence rules.

**Non-Goals**

* [ ] No immediate migration to CrewAI (phase-2 only).
* [ ] No change to UI flows or planning semantics.
* [ ] No change to artifact schemas in phase-1.
* [ ] No global (all-agent) custom compaction in phase-1.

---

## 3) Proposed Behavior

**User/System behavior**

* Runtime calls route through LiteLLM (single code path).
* Vectorstore uses local embedded Chroma; optional server mode is a later switch.
* Existing UI pages and agents are unchanged from a user perspective.
* Coach uses a custom compaction strategy when non-OpenAI providers are selected.
* Each agent can optionally override provider config (API key, base URL, model) without affecting others.
* Per-agent overrides are supplied via environment variables (container-friendly); changing them requires redeploy.

**Env var naming + precedence (Option 2)**

* Keep existing `RPS_LLM_*` env var family as the canonical config surface in phase-1 (provider-agnostic usage via LiteLLM).
* Per-agent override pattern: `RPS_LLM_<FIELD>_<AGENT>` where `<AGENT>` is normalized (same rules as current `RPS_LLM_MODEL_<AGENT>`).
* Global defaults: `RPS_LLM_API_KEY`, `RPS_LLM_BASE_URL`, `RPS_LLM_MODEL`, `RPS_LLM_TEMPERATURE`, `RPS_LLM_REASONING_EFFORT`, `RPS_LLM_REASONING_SUMMARY`, `RPS_LLM_ORG_ID`, `RPS_LLM_PROJECT_ID`.
* Per-agent overrides: `RPS_LLM_API_KEY_<AGENT>`, `RPS_LLM_BASE_URL_<AGENT>`, `RPS_LLM_MODEL_<AGENT>`, `RPS_LLM_TEMPERATURE_<AGENT>`, `RPS_LLM_REASONING_EFFORT_<AGENT>`, `RPS_LLM_REASONING_SUMMARY_<AGENT>`, `RPS_LLM_ORG_ID_<AGENT>`, `RPS_LLM_PROJECT_ID_<AGENT>`.
* Precedence: per-agent override -> global default -> built-in fallback (model only).
* Backward compatibility: none for `OPENAI_*` env vars (full rename to `RPS_LLM_*`).

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `rps.openai`, `rps.services`, `rps.vectorstores`, `rps.orchestrator`.
* Contracts touched: prompt injection, tool calls, vectorstore sync, run-store logging.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/openai/`:
  * Replace provider-specific client with LiteLLM adapter.
  * Preserve streaming and tool-call parsing interfaces used by UI.
  * Add custom compaction strategy for Coach when provider != OpenAI.
  * Resolve per-agent provider config with explicit precedence (agent override -> global defaults).
  * Read per-agent overrides from env vars (Option 2).
* `src/rps/openai/vectorstores.py`:
  * Swap to Chroma embedded backend.
  * Keep manifest hash + reset semantics.
* `src/rps/ui/`:
  * No functional changes; only instrumentation/logging adjustments if needed.

**Data flow**

* Inputs: prompts, knowledge docs, tool specs, run-store entries.
* Processing: LiteLLM requests, streaming deltas, tool calls, vectorstore search.
* Outputs: agent responses, tool-call outputs, updated run-store logs.

**Schema / Artefacts**

* New artefacts: None (phase-1).
* Changed artefacts: None (phase-1).
* Validator implications: No schema changes; update tests for provider adapters.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes (feature flag not required per decision; LiteLLM is the only path).
* Breaking changes: environment variable namespace renamed from `OPENAI_*` to `RPS_LLM_*` (no backward compatibility).
* Fallback behavior: If LiteLLM fails, surface explicit error and halt runs.
* Compaction fallback: for non-OpenAI providers, use custom Coach compaction strategy.
* Config precedence: agent overrides must not mutate or mask global defaults for other agents.

**Conflicts with ADRs / Principles**

* Potential conflicts: None expected; aligns with provider-agnostic architecture.
* Resolution: ADR-025 defines runtime boundary and vectorstore strategy.

**Impacted areas**

* UI: none (behavior preserved).
* Pipeline/data: vectorstore sync hooks reimplemented for Chroma.
* Renderer: none.
* Workspace/run-store: logs include provider/model metadata.
* Validation/tooling: update smoke tests to use LiteLLM adapter.
* Deployment/config: new env vars for LiteLLM providers + Chroma storage path.
* Agent config: optional per-agent provider config (API key/base URL/model).

**Required refactoring**

* Introduce a provider-agnostic LLM client interface.
* Replace OpenAI vectorstore resolver with Chroma-backed resolver.
* Add a per-agent provider config resolver with explicit precedence and safe redaction in logs.

---

## 6) Options & Recommendation

### Option A (recommended) — LiteLLM-only runtime + embedded Chroma

**Summary**

* Replace OpenAI runtime with LiteLLM as the single path; use embedded Chroma.

**Pros**

* Provider-agnostic, local-first vectorstore.
* Simplifies future multi-model routing.

**Cons**

* Requires re-implementing Responses API features (compaction, tool parsing).
* Introduces new dependency and operational complexity.

**Risk**

* Feature gaps vs Responses API (streaming/tool-call parity).

### Option B — Dual runtime (OpenAI + LiteLLM)

**Summary**

* Keep OpenAI as fallback while introducing LiteLLM.

**Pros**

* Lower migration risk.

**Cons**

* Higher complexity, more test matrix.

### Recommendation

* Choose: Option A + Option B combined, with **Option 2 (env-based per-agent overrides)** as the initial configuration mechanism.
* Rationale: keep runtime path single (LiteLLM-only) while enabling per-agent overrides via container-friendly env vars; accept redeploy requirement for now.
* Follow-up: reevaluate a file-backed or hybrid config if admin editability without redeploy becomes a requirement.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] All LLM calls route through LiteLLM.
* [ ] Embedded Chroma index replaces OpenAI vectorstore usage.
* [ ] Agent tool calls/streaming still pass existing UI and tests.
* [ ] Vectorstore sync/manifest reset behaves as before.
* [ ] Per-agent API key/base URL/model overrides work and do not leak into other agents.
* [ ] Validation passes: `python -m py_compile ...` + relevant smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* Phase-1: introduce LiteLLM adapter + Chroma embedded.
* Rebuild vectorstore from knowledge manifest on first run.
* Per-agent overrides are supplied via env vars; changes require container redeploy.

**Rollout / gating**

* No feature flag (per request).
* Safe rollback: revert to previous OpenAI runtime branch if needed.

---

## 9) Risks & Failure Modes

* Failure mode: LiteLLM provider returns incompatible tool/stream formats.
  * Detection: run-store errors, parsing exceptions.
  * Safe behavior: fail-fast with clear error in run logs.
  * Recovery: revert runtime or adjust adapter.

* Failure mode: Chroma index out of sync with manifest.
  * Detection: manifest hash mismatch.
  * Safe behavior: reset/rebuild index.
  * Recovery: rerun sync.

* Failure mode: custom Coach compaction produces low-quality summaries.
  * Detection: Coach response quality regressions, increased token usage.
  * Safe behavior: disable custom compaction and use full context.
  * Recovery: refine compaction heuristics or re-enable OpenAI compaction for Coach.

---

## 10) Observability / Logging

**New/changed events**

* `llm.request`: provider, model, latency, tokens.
* `vectorstore.sync`: backend=chroma, manifest_hash, reset=true/false.
* `llm.config.resolve`: agent_id, provider, model, base_url (redacted), override_used=true/false.

**Diagnostics**

* Run-store events + `var/athletes/.../logs/rps.log`.

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [ ] `doc/architecture/system_architecture.md` — runtime/provider abstraction.
* [ ] `doc/architecture/vectorstores.md` — Chroma embedded + sync rules.
* [ ] `doc/runbooks/validation.md` — smoke checks for LiteLLM path.
* [ ] `doc/overview/feature_backlog.md` — backlog item status.

---

## 12) Link Map (no duplication; links only)

* UI flows/actions: `doc/ui/ui_spec.md#...`
* UI contract (Streamlit): `doc/ui/streamlit_contract.md#...`
* Architecture: `doc/architecture/system_architecture.md#...`
* Workspace: `doc/architecture/workspace.md#...`
* Schema versioning: `doc/architecture/schema_versioning.md#...`
* Logging policy: `doc/specs/contracts/logging_policy.md#...`
* Validation / runbooks: `doc/runbooks/validation.md#...`
* ADRs: `doc/adr/ADR-025-multi-provider-runtime-and-local-vectorstore.md`

---

## Open Questions (max 5) — optional

* Which LiteLLM providers/models are first-class supported?
* Should Chroma data live under `var/athletes/<id>/vectorstore/` or global?
* Where should per-agent provider overrides live (config file vs. env vars vs. workspace settings)?
* What triggers a switch from env-only overrides to file-backed or hybrid config (admin editability without redeploy)?

---

## Out of Scope / Deferred — optional

* CrewAI integration (phase-2).
* Vectorstore server mode (phase-2).
