---
Version: 1.0
Status: Approved
Last-Updated: 2026-05-21
Owner: Planning Semantics
---
# FEAT: Canonical Phase Taxonomy Migration

* **ID:** FEAT_canonical_phase_taxonomy_migration
* **Status:** Approved
* **Owner/Area:** Planning Semantics
* **Last-Updated:** 2026-05-21
* **Related:** [FEAT_phase_intent_semantic_backbone](/doc/specs/features/FEAT_phase_intent_semantic_backbone.md), [FEAT_auditable_week_workout_selection](/doc/specs/features/FEAT_auditable_week_workout_selection.md), [ADR-053-canonical-phase-taxonomy-and-build-subtypes](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md)

---

## 1) Context / Problem

**Current behavior**

* RPS persists a normalized `phase_intent`, but the current taxonomy is repo-specific and mixes macro-period semantics, block purposes, and week-shape ideas.
* Season phases still use `cycle` with legacy values such as `Base`, `Build`, `Peak`, and `Transition`.
* Build-focus semantics such as `ceiling_support`, `build_progression`, and `general_build` are not standard-first and are difficult to audit across Season -> Phase -> Week -> Workout selection.

**Problem**

* The current contract is semantically ambiguous for planners and reviewers.
* Legacy intent values do not map cleanly to common periodization language.
* Build-specific selector behavior is under-specified because the active contract lacks an explicit Build selector key.
* Unknown legacy values could be misread or normalized too loosely during migration.

**Constraints**

* This is a breaking semantic migration for new writes.
* Legacy artifacts must remain readable through explicit normalization only.
* Unknown legacy taxonomy values must fail closed.
* No new dependencies.
* Week workout selection matrix remains a combination-policy layer, not a dose-policy layer.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Replace the old `phase_intent` taxonomy with a canonical, standard-first model.
* [x] Introduce canonical persisted `phase_type`, `phase_intent`, and `build_subtype`.
* [x] Make `phase_intent` the primary downstream planning signal.
* [x] Make `build_subtype` an explicit selector/audit key for Build phases.
* [x] Persist a taxonomy version in `data.body_metadata.phase_taxonomy_version` where body metadata exists.
* [x] Make legacy normalization explicit, auditable, and fail-closed for unknown values.

**Non-Goals**

* [x] Introduce a canonical `week_role` taxonomy in the same migration.
* [x] Collapse Workout selection and TiZ/dose rules into one spec.
* [x] Preserve legacy phase-taxonomy values for new writes.

---

## 3) Proposed Behavior

**User/System behavior**

* Season, Phase, and Week planning use a canonical semantic model:
  * `phase_type` = macro-period container
  * `phase_intent` = primary methodological purpose
  * `build_subtype` = explicit Build selector key
* `phase_type` is canonical and uppercase:
  * `TRANSITION`, `PREPARATION`, `BASE`, `BUILD`, `PEAK`, `TAPER`, `RACE`
* `phase_intent` is constrained by `phase_type`.
* For `phase_type = BUILD`, `build_subtype` is required and must equal `phase_intent`.
* Legacy values remain readable only through an explicit normalization layer.
* Unknown legacy values block migration instead of being guessed or defaulted.

**UI impact**

* UI affected: Yes.
* Season / Phase / Week displays may show canonical `phase_type` and intent labels.
* No UI flow redesign is required in this feature.

**Non-UI behavior**

* Components involved: season derivation, workspace normalization helpers, contract validators, guarded store checks, workout selector inputs, schema-backed artifact models.
* Contracts touched:
  * `SEASON_PLAN`
  * `PHASE_GUARDRAILS`
  * `PHASE_STRUCTURE`
  * `PHASE_PREVIEW`

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/phase_intents.py`
  * canonical enums
  * normalization helpers
  * legacy mapping
  * compatibility checks
* `src/rps/planning/load_bands.py`
  * deterministic `phase_type` / `phase_intent` / `build_subtype` derivation
* `src/rps/planning/contracts.py`
  * season semantic validation against the new contract
* `src/rps/workspace/season_plan_service.py`
  * downstream phase lookup should expose `build_subtype`
* `src/rps/crewai_runtime/guardrails.py`
  * internal candidate checks must validate `phase_type`
* `specs/schemas/*.schema.json`
  * migrate artifact contract fields and enums

**Data flow**

* Inputs: selected scenario, phase slots, event windows, existing season/phase artifacts.
* Processing:
  * derive canonical phase semantics
  * normalize legacy reads when present
  * validate canonical writes
  * propagate canonical fields downstream
* Outputs:
  * canonical artifacts
  * normalization metadata for migration diagnostics

**Schema / Artefacts**

* Changed artefacts:
  * `SEASON_PLAN`
  * `PHASE_GUARDRAILS`
  * `PHASE_STRUCTURE`
  * `PHASE_PREVIEW`
* New semantic fields:
  * `phase_type`
  * `build_subtype`
  * `phase_taxonomy_version`
* Validator implications:
  * `phase_type -> legal phase_intent set`
  * `BUILD -> build_subtype required`
  * `non-BUILD -> build_subtype must be null`
  * `BUILD -> build_subtype == phase_intent`

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes for reads, No for new writes.
* Breaking changes:
  * season and downstream artifacts must emit canonical fields
  * legacy `phase_intent` and `cycle` values are no longer valid for new writes
* Fallback behavior:
  * runtime may normalize known legacy values when reading old artifacts
  * unknown legacy values fail validation and must not be guessed

**Conflicts with ADRs / Principles**

* Potential conflicts:
  * the previous phase-intent backbone used repo-specific enums
* Resolution:
  * supersede that semantic backbone with canonical phase taxonomy plus explicit Build subtype

**Impacted areas**

* UI: canonical phase labels become the authoritative display input
* Pipeline/data: season and downstream artifacts gain canonical semantic fields
* Renderer: season-phase rows and phase summaries should read `phase_type`
* Workspace/run-store: semantic version marker added to body metadata
* Validation/tooling: schema validation, bundling, and normalized-reader tests
* Deployment/config: no env/config changes

**Required refactoring**

* Replace legacy intent enums in helper modules and schemas.
* Replace `cycle`-based reasoning with `phase_type`-based reasoning on canonical writes.
* Introduce explicit legacy-normalization helpers and rollout diagnostics.

---

## 6) Options & Recommendation

### Option A — Canonical taxonomy with explicit Build subtype

**Summary**

* Persist standard-first `phase_type`, canonical `phase_intent`, and explicit `build_subtype`.

**Pros**

* Stronger planner semantics.
* Cleaner audit contract.
* Deterministic Build selector behavior.
* Safer migration boundaries.

**Cons**

* Cross-layer refactor touching schemas, derivation logic, and validation.

**Risk**

* Legacy mapping mistakes can silently distort plan semantics if not audited carefully.

### Option B — Keep old taxonomy and add labels only

**Summary**

* Preserve the current repo-specific enums and only improve docs/audit labels.

**Pros**

* Smaller short-term refactor.

**Cons**

* Keeps semantic drift and ambiguous Build meaning.
* Does not solve the core contract problem.

### Recommendation

* Choose: Option A.
* Rationale: the migration is justified because the semantic boundary is now a first-class planning contract, not just prompt prose.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Canonical `phase_type` / `phase_intent` / `build_subtype` helpers exist in code.
* [ ] Known legacy values normalize to the approved canonical taxonomy.
* [ ] Unknown legacy values fail closed.
* [ ] New writes using legacy taxonomy values fail validation.
* [ ] `SEASON_PLAN` and downstream phase schemas require canonical semantic fields.
* [ ] `data.body_metadata.phase_taxonomy_version` is persisted where body metadata exists.
* [ ] Deterministic season derivation emits only canonical semantics.
* [ ] Validation passes:
  * `python3 scripts/check_schema_required.py`
  * `python3 scripts/bundle_schemas.py`
  * `python3 -m py_compile $(git ls-files '*.py')`
  * targeted tests
  * lint
  * typecheck

---

## 8) Migration / Rollout

**Migration strategy**

* Legacy reads pass through an explicit mapping layer.
* New writes must emit canonical taxonomy only.
* During migration, normalization trace fields may be emitted in audit/context payloads:
  * `legacy_phase_intent_raw`
  * `normalized_phase_intent`
  * `normalization_source`
  * `normalization_warning`

**Rollout / gating**

* No feature flag.
* Safe rollback:
  * restore old schema enums and helper mappings
  * keep canonical spec/ADR for rework history

---

## 9) Risks & Failure Modes

* Failure mode: legacy mapping for `general_build`, `build_progression`, or `transition_coupling` is semantically wrong.
  * Detection: rollout validation against existing generated plans and planner prompt semantics.
  * Safe behavior: block cutover until mapping is corrected.
  * Recovery: adjust mapping, rerun schema validation and plan-level regression tests.

* Failure mode: a new write still emits legacy values.
  * Detection: schema validation / guarded store rejection.
  * Safe behavior: reject artifact write.
  * Recovery: update writer prompt/runtime to emit canonical values only.

* Failure mode: unknown legacy value appears in a migrated read path.
  * Detection: normalization returns invalid and raises a validation error.
  * Safe behavior: fail closed, do not default.
  * Recovery: inspect source artifact and add an explicit migration rule only if justified.

---

## 10) Observability / Logging

**New/changed events**

* normalization warnings should include:
  * raw legacy value
  * normalized target value
  * mapping source
* validation failures should include:
  * offending field
  * expected canonical set

**Diagnostics**

* schema validation errors
* guarded-store write failures
* migration trace fields in normalized context payloads

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [ ] [doc/specs/features/FEAT_phase_intent_semantic_backbone.md](/doc/specs/features/FEAT_phase_intent_semantic_backbone.md) — mark superseded
* [ ] [doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md) — final decision record
* [ ] [specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md](/specs/knowledge/_shared/sources/specs/mandatory_output_season_plan.md) — canonical semantic fields
* [ ] [specs/knowledge/_shared/sources/specs/mandatory_output_phase_guardrails.md](/specs/knowledge/_shared/sources/specs/mandatory_output_phase_guardrails.md) — canonical semantic fields
* [ ] [specs/knowledge/_shared/sources/specs/mandatory_output_phase_structure.md](/specs/knowledge/_shared/sources/specs/mandatory_output_phase_structure.md) — canonical semantic fields
* [ ] [specs/knowledge/_shared/sources/specs/mandatory_output_phase_preview.md](/specs/knowledge/_shared/sources/specs/mandatory_output_phase_preview.md) — canonical semantic fields
* [ ] [CHANGELOG.md](/CHANGELOG.md) — record migration

---

## 12) Link Map (no duplication; links only)

* Architecture: [doc/architecture/system_architecture.md](/doc/architecture/system_architecture.md)
* Workspace: [doc/architecture/workspace.md](/doc/architecture/workspace.md)
* Schema versioning: [doc/architecture/schema_versioning.md](/doc/architecture/schema_versioning.md)
* Review matrix: [doc/overview/week_workout_selection_review_matrix.md](/doc/overview/week_workout_selection_review_matrix.md)
* Workout selection audit: [doc/overview/week_workout_selection_audit_guide.md](/doc/overview/week_workout_selection_audit_guide.md)
* ADR: [doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md](/doc/adr/ADR-053-canonical-phase-taxonomy-and-build-subtypes.md)

---

## Open Questions (max 5) — optional

* Should future `week_role` canonicalization persist a separate taxonomy version or extend this one?

---

## Out of Scope / Deferred — optional

* Canonical `week_role` taxonomy
* Full prompt-surface cleanup across every planning prompt in the same change
