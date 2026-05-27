---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-27
Owner: Planning Runtime
---
# FEAT: Evidence Curation Pipeline

* **ID:** FEAT_evidence_curation_pipeline
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-27
* **Related:** `src/rps/evidence`, `config/crewai`, `skills/evidence/source-curation`

---

## Canonical Scope

Together with `FEAT_repo_wide_evidence_library_and_refresh`, this is the
**current canonical feature specification** for the evidence system.

Use this document for:
- the mandatory evidence curation agent / task / skill
- native Pydantic structured output
- deterministic quality gate and activation
- `legacy_active` migration semantics

Use `FEAT_repo_wide_evidence_library_and_refresh` for:
- repo-wide evidence-library structure
- weekly refresh/discovery process
- decommission of legacy bibliography inputs

---

## 1) Context / Problem

**Current behavior**

* The evidence library is a structured YAML registry with generated markdown views.
* Weekly refresh discovers new PubMed-backed sources and activates them immediately after bibliographic verification.
* No dedicated curation agent exists between verification and activation.

**Problem**

* Bibliographic verification is not the same as agent-ready evidence curation.
* New sources can become operative without a structured RPS-specific summary, safe-use boundaries, or relevance assessment.
* The current markdown summaries are generated from short registry fields and are too thin for stable agent use.

**Constraints**

* No new dependencies.
* Keep YAML compact as registry; long summaries belong in generated markdown briefs.
* Use native CrewAI structured outputs via Pydantic models.
* Activation must remain fail-closed.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Add a mandatory Evidence Curation Agent / Task / Skill.
* [x] Require native Pydantic structured output for curation results.
* [x] Insert deterministic quality gate and activation stages after curation.
* [x] Keep the curation agent self-contained with explicit RPS goals, relevance logic, and authority boundaries.
* [x] Preserve the YAML library as the canonical registry while rendering long-form markdown briefs from structured curation output.

**Non-Goals**

* [x] No free agent web search for reference discovery.
* [x] No unrestricted fulltext ingestion or local mirroring of restricted papers.
* [x] No change to planner authority; evidence remains support, not governance.

---

## 3) Proposed Behavior

**User/System behavior**

* Weekly evidence refresh now runs `discover -> verify -> classify -> curate -> quality_gate -> activate -> render`.
* New evidence is only operative after a successful curation pass and deterministic gate.
* Existing evidence remains visible through `legacy_active` until re-curated into the new model.
* Long study markdown pages include source-basis provenance, RPS relevance, practical implications, and explicit non-justified inferences.

**UI impact**

* UI affected: Yes
* System → Status continues to expose evidence refresh status, but refresh results now reflect curation and activation outcomes rather than verification only.

**Non-UI behavior**

* Components involved: evidence refresh, evidence library loader/renderer, CrewAI task binding, background run tracking
* Contracts touched: evidence registry shape, generated study-brief shape, evidence refresh result schema

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/evidence/library.py`: expanded registry schema, rendering, legacy visibility rules
* `src/rps/evidence/refresh.py`: primary-source discovery and orchestration handoff
* `src/rps/evidence/curation.py`: source-package construction and CrewAI curation execution
* `src/rps/evidence/quality_gate.py`: deterministic completeness/authority/provenance checks
* `src/rps/evidence/trusted_sources.py`: author/outlet normalization and fast-lane policy
* `src/rps/evidence/pipeline.py`: end-to-end staged orchestration

**Data flow**

* Inputs: canonical registry entries, PubMed discovery metadata, optional abstract/fulltext text, trusted-source policy
* Processing: build deterministic source package -> run evidence curation task -> validate typed output -> apply quality gate -> persist activation state -> regenerate markdown views
* Outputs: updated registry YAML, long-form study briefs, generated tables, run-store stage events, discovery state

**Schema / Artefacts**

* New registry fields: `activation_status`, `brief_status`, `brief_path`, `relevance_assessment`, `evidence_posture`, `curation_schema_version`, `trusted_source_match`, `trusted_match_reason`, `curated_at`, `activated_at`
* New config artefact: `config/evidence/trusted_sources.yaml`
* New agent artefacts: evidence curation prompt and skill

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Partially
* Breaking changes: evidence refresh no longer auto-activates verified-but-uncurated sources
* Fallback behavior: existing registry entries remain visible as `legacy_active` until re-curated

**Conflicts with ADRs / Principles**

* No conflict with planner authority; this strengthens structured-output and evidence-boundary ADRs.

**Impacted areas**

* UI: evidence refresh status semantics
* Pipeline/data: refresh stage ordering, activation logic
* Renderer: study-detail markdown becomes provenance-aware and more structured
* Workspace/run-store: stage events for evidence refresh
* Validation/tooling: new tests for curation model, gate, trusted matching, activation
* Deployment/config: new CrewAI agent/task/skill/runtime profile and trusted-source config

**Required refactoring**

* Replace the old `verified == active` assumption inside evidence refresh.
* Promote current YAML summary fields into registry defaults plus rendered brief sections.

---

## 6) Options & Recommendation

### Option A — Mandatory curation agent with deterministic gate

**Summary**

* Insert an LLM curation step with strict structured output before activation.

**Pros**

* Aligns evidence quality with the existing structured-output runtime design.
* Separates bibliographic verification from content readiness.
* Supports richer briefs without bloating YAML.

**Cons**

* Higher implementation complexity and longer refresh runs.

### Option B — Deterministic registry only with richer manual summaries

**Summary**

* Keep refresh deterministic and rely on manually curated registry content.

**Pros**

* Simpler runtime path.

**Cons**

* Does not scale to ongoing discovery.
* Leaves the curation bottleneck manual.

### Recommendation

* Choose: Option A
* Rationale: the repo already has the structured-output runtime needed for this safely, and the user requirement is explicitly for automated but bounded curation.

---

## 7) Acceptance Criteria

* [x] Evidence curation agent/task/skill exist and load through CrewAI config.
* [x] The curation task returns a native Pydantic model.
* [x] New evidence activation requires curation + quality gate.
* [x] Generated study briefs render provenance, RPS relevance, and non-justified inferences.
* [x] Trusted-source matching is deterministic and policy-driven.
* [x] Validation passes: syntax, lint, typecheck, targeted tests, refresh smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* Existing entries load with `legacy_active` defaults.
* New refresh runs can gradually re-curate legacy entries into `active`.
* Generated views remain stable during migration.

**Rollout / gating**

* No feature flag; the new pipeline replaces the old refresh path directly.
* Safe rollback is to restore the prior library/refresh files and regenerate markdown views.

---

## 9) Risks & Failure Modes

* Failure mode: structured curation output is invalid
  * Detection: CrewAI typed-output guardrails and explicit retry
  * Safe behavior: source remains non-active
  * Recovery: retry after prompt/skill/policy adjustment

* Failure mode: summary is structurally valid but too generic
  * Detection: deterministic quality gate
  * Safe behavior: source stays non-active
  * Recovery: improved source basis or revised curation instructions

* Failure mode: legacy sources disappear from active evidence abruptly
  * Detection: rendered tables and tests
  * Safe behavior: `legacy_active` keeps them visible until backfill
  * Recovery: run re-curation or temporarily preserve legacy visibility

---

## 10) Observability / Logging

**New/changed events**

* `DISCOVERED`, `VERIFIED`, `CURATION_STARTED`, `CURATION_FAILED`, `QUALITY_GATE_FAILED`, `ACTIVATED`, `REJECTED`
* curation schema version and source-material level in study briefs

**Diagnostics**

* run-store `events.jsonl`
* `discovery_state.json`
* rendered study briefs under `library/studies/`

---

## 11) Documentation Updates

* [x] `CHANGELOG.md`
* [x] `doc/architecture/agents.md`
* [x] new ADR for evidence curation pipeline
* [x] evidence skill and prompt documentation

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* ADR process: `doc/adr/README.md`
* Runtime structured-output model pattern: `src/rps/crewai_runtime/models.py`
* Existing evidence library spec: `doc/specs/features/FEAT_repo_wide_evidence_library_and_refresh.md`
