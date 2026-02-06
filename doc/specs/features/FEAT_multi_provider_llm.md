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
* Breaking changes: Provider-specific config and environment variables.
* Fallback behavior: If LiteLLM fails, surface explicit error and halt runs.
* Compaction fallback: for non-OpenAI providers, use custom Coach compaction strategy.

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

**Required refactoring**

* Introduce a provider-agnostic LLM client interface.
* Replace OpenAI vectorstore resolver with Chroma-backed resolver.

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

* Choose: Option A.
* Rationale: user requested single runtime path; keeps architecture clean.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] All LLM calls route through LiteLLM.
* [ ] Embedded Chroma index replaces OpenAI vectorstore usage.
* [ ] Agent tool calls/streaming still pass existing UI and tests.
* [ ] Vectorstore sync/manifest reset behaves as before.
* [ ] Validation passes: `python -m py_compile ...` + relevant smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* Phase-1: introduce LiteLLM adapter + Chroma embedded.
* Rebuild vectorstore from knowledge manifest on first run.

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

---

## Out of Scope / Deferred — optional

* CrewAI integration (phase-2).
* Vectorstore server mode (phase-2).
