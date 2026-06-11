---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-11
Owner: Planning Runtime
---
# FEAT: Season Semantic Contract Hardening

* **ID:** FEAT_season_semantic_contract_hardening
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-06-11
* **Related:** [ADR-053-canonical-phase-taxonomy-and-build-subtypes](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md), [ADR-054-dual-bundled-structured-output-schemas](/doc/adr/ADR-054-dual-bundled-structured-output-schemas.md)

---

## 1) Context / Problem

**Current behavior**

* Season planning already uses canonical `phase_type`, `phase_intent`, and `build_subtype`.
* Deterministic phase-slot and phase-load contracts already exist and are injected into Season planning/review.
* The final `SEASON_PLAN` writer still receives too much methodology as prose instead of structured, code-owned contract fields.

**Problem**

* Season bundle phase blueprints did not carry a complete semantics contract.
* Review/guardrails validated corridor and slot coherence, but not the full methodology contract.
* The writer was still reconstructing season load-envelope and method framing from prose.

This allowed structurally wrong but superficially plausible outputs:

* illegal `phase_type` / `phase_intent` combinations,
* overly broad phase domain allowances,
* threshold-led wording in durability phases,
* taper/reload ambiguity,
* season objective framing drift,
* avoidable writer retries on `season_load_envelope`.

**Constraints**

* No persisted `SEASON_PLAN` schema migration in this pass.
* Canonical phase taxonomy remains the semantic source of truth.
* The fix must be generic for the Season pipeline, not tailored to one runtime instance.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make Season methodology code-owned and deterministic where it affects downstream legality and serialization.
* [x] Carry structured phase semantics and season envelope through the internal Season bundle.
* [x] Block semantic drift during bundle/review, before writer execution.
* [x] Make the Season writer copy bundle-owned semantics instead of inferring them.

**Non-Goals**

* [x] No persisted `SEASON_PLAN` schema redesign.
* [x] No change to the current 5-phase season structure assumption.

---

## 3) Proposed Behavior

**User/System behavior**

* Season planning now enriches the internal Season bundle with deterministic semantic-contract fields before review.
* Phase blueprints now carry canonical taxonomy version, deterministic allowed/forbidden domains, and structured method notes.
* The bundle now carries an exact deterministic `season_load_envelope` and season-level semantic notes for writer framing.
* Review and guardrails now reject semantic mismatches before the writer starts.
* The writer is expected to serialize the approved bundle, not reinterpret it.
* Final season normalization strips positive forbidden-domain prose from phase narratives and rewrites it into legal, intent-coherent wording before store validation.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * `workspace.phase_intents`
  * `agents.crewai_backend`
  * `crewai_runtime.guardrails`
  * `planning.contracts`
* Contracts touched:
  * internal `SeasonPlanBundleModel`
  * internal `SeasonPhaseBlueprintModel`
  * Season writer guardrails

---

## 4) Implementation Analysis

**Components / Modules**

* `phase_intents.py`: add code-owned phase semantic profiles and deterministic allowed/forbidden-domain helpers.
* `models.py`: extend internal Season bundle and phase-blueprint models with semantic-contract fields and load-envelope structure.
* `crewai_backend.py`: enrich the Season bundle deterministically before review/writer handoff.
* `contracts.py`: validate Season bundle semantics and tighten Season Plan semantic validation.
* `guardrails.py`: enforce bundle completeness and writer copy-exact behavior.
* Final season normalization additionally sanitizes phase narrative fields when they drift into forbidden-domain-positive prose.

**Data flow**

* Inputs: selected-scenario authority, deterministic phase-slot contract, deterministic phase-load contract, Season specialist bundle.
* Processing:
  * normalize/enrich phase blueprints with code-owned semantic contract,
  * derive deterministic allowed/forbidden domains,
  * derive deterministic season load-envelope,
  * attach season-level semantic notes,
  * validate before review/writer.
* Outputs:
  * writer-safe internal `SeasonPlanBundle`,
  * unchanged persisted `SEASON_PLAN` envelope shape.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: internal Pydantic bundle models only
* Validator implications: Season bundle guardrails and Season Plan guardrails become stricter on semantic legality

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for persisted artefacts
* Breaking changes: internal Season bundle outputs now require more fields
* Fallback behavior: fail fast in review/guardrails instead of allowing writer retries to repair semantic drift

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: extends ADR-053 by making canonical phase semantics code-owned in Season bundle propagation

**Impacted areas**

* UI: none
* Pipeline/data: Season planning/review/writer handoff is stricter
* Renderer: none directly
* Workspace/run-store: unchanged persisted storage shape
* Validation/tooling: stronger season bundle and season writer guardrails
* Deployment/config: Season prompts/skills/task descriptions updated

**Required refactoring**

* Internal Season bundle contract had to become structured enough for deterministic serialization.
* Semantic legality checks had to move earlier in the Season pipeline.

---

## 6) Options & Recommendation

### Option A — prompt-only hardening

**Summary**

* Tighten prompts and skills without changing code-owned Season contracts.

**Pros**

* Small change surface

**Cons**

* Leaves the root cause in place
* Still relies on the writer/finalizer to behave correctly from prose

### Option B — deterministic Season semantic contract

**Summary**

* Move methodology-critical Season semantics into code-owned internal contract fields.

**Pros**

* Deterministic
* Testable
* Catches drift before writer execution

**Cons**

* Requires internal model and guardrail expansion

### Recommendation

* Choose: Option B
* Rationale: Season methodology errors were structural, not prompt-local. The fix must be code-owned.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season bundle carries `season_load_envelope` and `season_semantic_notes`.
* [x] Season phase blueprints carry `phase_taxonomy_version`, `forbidden_domains`, and `semantic_contract`.
* [x] Season bundle guardrails reject semantic mismatches before writer execution.
* [x] Season writer guardrails reject envelope or phase-semantics drift from the approved bundle.
* [x] Validation passes: syntax, lint, typecheck, targeted runtime/planning tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted artefact migration.
* Internal Season bundle model grows stricter immediately.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert the internal contract/guardrail changes

---

## 9) Risks & Failure Modes

* Failure mode: finalizer still emits semantically weak blueprints
  * Detection: season bundle guardrails fail before writer execution
  * Safe behavior: block and replan instead of writing a drifting `SEASON_PLAN`
  * Recovery: adjust Season specialist/finalizer outputs and rerun

* Failure mode: writer tries to widen envelope or domains
  * Detection: `season_writer_bundle_match`
  * Safe behavior: writer retry/failure before persistence
  * Recovery: inspect approved bundle vs written output

---

## 10) Observability / Logging

**New/changed events**

* Existing `CREW_TASK_GUARDRAIL_FAILED` events now fire earlier for Season bundle semantic drift.

**Diagnostics**

* `events.jsonl`
* `rps.log`
* Season review/bundle guardrail failures

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] [ADR-053-canonical-phase-taxonomy-and-build-subtypes.md](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md) — clarify deterministic propagation through Season bundle/review/writer
* [x] [CHANGELOG.md](/CHANGELOG.md) — record deterministic Season semantic-contract hardening

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Artefact flow: `doc/overview/artefact_flow.md`
* Validation / runbooks: `doc/runbooks/`
* ADRs: [ADR-053-canonical-phase-taxonomy-and-build-subtypes.md](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md), [ADR-054-dual-bundled-structured-output-schemas.md](/doc/adr/ADR-054-dual-bundled-structured-output-schemas.md)
