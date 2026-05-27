---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-27
Owner: Planning Runtime
---
# FEAT: Repo-Wide Evidence Library and Weekly Refresh

* **ID:** FEAT_repo_wide_evidence_library_and_refresh
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-27
* **Related:** `skills/shared/durability-methodology/references/library`, `src/rps/evidence`, `config/crewai/knowledge_sources.yaml`

---

## Canonical Scope

Together with `FEAT_evidence_curation_pipeline`, this is the **current
canonical feature specification** for the evidence system.

Use this document for:
- repo-wide evidence-library structure
- weekly refresh / discovery behavior
- decommission status of legacy bibliography inputs

Use `FEAT_evidence_curation_pipeline` for:
- mandatory curation agent
- quality gate
- activation semantics
- trusted-source fast-lane

---

## 1) Context / Problem

**Current behavior**

* RPS already has curated core/applied durability reference tables.
* Older bibliography and evidence-manifest files still exist in active repo paths.
* Some runtime/spec/test surfaces still contain hard-coded literature locators.
* There is no periodic mechanism to discover and integrate new relevant literature.

**Problem**

* Reference truth is split across markdown tables, legacy bibliographies, tests, and runtime constants.
* Agents can be instructed not to invent citations, but there is no single canonical library with verification state.
* New relevant literature does not enter the system automatically.

**Constraints**

* Fail closed on uncertain bibliographic matches.
* Keep evidence below governance and planner contracts.
* Use primary sources only for verification and discovery.
* Avoid new third-party dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Create one canonical local evidence library with structured metadata and verification status.
* [x] Decommission legacy bibliography/manifest files as operative sources.
* [x] Route active evidence usage through the canonical library and generated tables.
* [x] Add a weekly background literature refresh with automatic activation of verified new sources.
* [x] Keep agent-facing citation behavior fail-closed: omit uncertain locators rather than invent them.

**Non-Goals**

* [x] No full-text mirroring of restricted/paywalled sources.
* [x] No general-purpose web crawler outside primary-source discovery.
* [x] No schema change for persisted planning artefacts beyond using the new lookup path for canonical references.

---

## 3) Proposed Behavior

**User/System behavior**

* Active prompts/skills/runtime use one evidence library as the operative source of truth.
* Evidence locators are only emitted when verified.
* Weekly background refresh searches primary sources for new relevant literature, verifies it, and activates only high-confidence additions.
* Open-access fulltext support is optional and only used when legal and directly available.

**UI impact**

* UI affected: Yes
* System → Status shows current evidence-library refresh status and offers a manual refresh trigger.

**Non-UI behavior**

* Components involved: evidence library loader, markdown sync, season scientific-foundation normalization, background refresh, knowledge-source config, active skills/prompts/tests.
* Contracts touched: evidence-use contract only; planning authority remains unchanged.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/evidence/library.py`: canonical evidence library loading, lookup, rendering, sync helpers
* `src/rps/evidence/refresh.py`: discovery, verification, dedupe, state update
* `scripts/refresh_evidence_library.py`: manual/admin sync and refresh entrypoint
* `src/rps/ui/streamlit_app.py`: weekly automatic refresh hook
* `src/rps/ui/pages/system/status.py`: manual trigger + visibility

**Data flow**

* Inputs: structured YAML library files, primary-source discovery results, existing curated reference data
* Processing: load library -> verify/dedupe -> update YAML -> regenerate markdown views -> expose through knowledge sources and runtime lookups
* Outputs: synced markdown tables, study detail sheets, refreshed discovery state, visible background run status

**Schema / Artefacts**

* New library artefacts:
  * `core_studies.yaml`
  * `applied_sources.yaml`
  * `discovery_state.json`
* Changed supporting artefacts:
  * generated core/applied markdown tables
  * generated study detail markdown
  * decommissioned legacy bibliography/manifest files

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Mostly yes
* Breaking changes: legacy bibliography/manifest files stop being operative sources
* Fallback behavior: if verification is uncertain, the locator remains empty and the candidate is not auto-activated

**Conflicts with ADRs / Principles**

* No architecture conflict; this strengthens the existing “evidence is justification-only” rule.

**Impacted areas**

* UI: System Status manual refresh + state visibility
* Pipeline/data: evidence refresh background process
* Renderer: generated markdown views for library content
* Workspace/run-store: evidence refresh run records
* Validation/tooling: new tests for library sync and refresh behavior
* Deployment/config: knowledge source bundle changes and new optional env vars

**Required refactoring**

* Replace hard-coded publication canonicalization with library-backed lookup
* Remove active dependencies on legacy bibliography/manifest content

---

## 6) Options & Recommendation

### Option A — Canonical structured library with generated markdown and weekly refresh

**Summary**

* Keep one structured source of truth and derive readable markdown and runtime lookups from it.

**Pros**

* Deterministic
* Testable
* Supports fail-closed verification and background discovery

**Cons**

* More moving parts than a static markdown table

### Option B — Keep markdown as source of truth and add ad-hoc refresh

**Summary**

* Patch the current tables and fetch new sources directly into them.

**Pros**

* Smaller initial code change

**Cons**

* Weak verification model
* Harder to dedupe, test, and automate

### Recommendation

* Choose: Option A
* Rationale: it closes the hallucination problem and gives the weekly refresh a stable interface.

---

## 7) Acceptance Criteria

* [x] Canonical evidence library files exist and load correctly.
* [x] Core/applied markdown tables are generated from the library source of truth.
* [x] Legacy bibliography/manifest files are decommissioned and removed from active knowledge injection.
* [x] Runtime publication canonicalization uses the library instead of only local hard-coded tuples.
* [x] Weekly evidence refresh exists as a background process and can also be triggered manually.
* [x] Active evidence-using prompts/skills/runtime instructions explicitly say omit uncertain locators instead of inventing them.
* [x] Validation passes: syntax, lint, typecheck, targeted tests, smoke run.

---

## 8) Migration / Rollout

**Migration strategy**

* Introduce library files and generated markdown first.
* Repoint active knowledge/config/runtime paths.
* Decommission legacy bibliography/manifest files in-place with clear notices.

**Rollout / gating**

* Weekly refresh enabled by default.
* Refresh can be disabled through env if needed.

---

## 9) Risks & Failure Modes

* Failure mode: automatic discovery adds a wrong source
  * Detection: fail-closed verification, tests, state counters
  * Safe behavior: unresolved or ambiguous candidates are not activated
  * Recovery: remove the bad entry from library YAML and rerun sync

* Failure mode: background refresh writes no changes but marks success
  * Detection: run-store message and discovery-state counters
  * Safe behavior: no active library corruption
  * Recovery: run manual refresh

* Failure mode: legacy path still leaks into active instructions
  * Detection: regression tests and repo search
  * Safe behavior: active knowledge bundle no longer injects legacy files
  * Recovery: patch the remaining prompt/skill/doc reference

---

## 10) Observability / Logging

**New/changed events**

* background run: `process_type=evidence`, `process_subtype=literature_refresh`
* discovery-state timestamps and counters in library state

**Diagnostics**

* System → Status
* run store history
* `discovery_state.json`

---

## 11) Documentation Updates

* [x] `CHANGELOG.md`
* [x] active shared durability skill evidence rules
* [x] coach/recommendation evidence guidance
* [x] legacy bibliography/manifest decommission notices
