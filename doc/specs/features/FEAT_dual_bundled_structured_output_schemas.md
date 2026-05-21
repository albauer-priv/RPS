---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-21
Owner: Runtime / Schemas
---
# FEAT: Dual Bundled Structured-Output Schemas

* **ID:** FEAT_dual_bundled_structured_output_schemas
* **Status:** Implemented
* **Owner/Area:** Runtime / Schemas
* **Last-Updated:** 2026-05-21
* **Related:** [ADR-054-dual-bundled-structured-output-schemas](/doc/adr/ADR-054-dual-bundled-structured-output-schemas.md), [FEAT_canonical_phase_taxonomy_migration](/doc/specs/features/FEAT_canonical_phase_taxonomy_migration.md)

---

## 1) Context / Problem

**Current behavior**

* `specs/schemas/*.schema.json` are the normative source schemas.
* `scripts/bundle_schemas.py` resolves them into `specs/knowledge/_shared/sources/schemas/bundled/`.
* Generated CrewAI artifact models expose that bundled schema directly as the structured-output schema and also use it for canonical validation.

**Problem**

* Canonical planning schemas now contain valid repo-side conditionals such as `if` / `then` / `else`.
* OpenAI structured output rejects those constructs in `response_format`.
* The existing runtime conflates two different responsibilities:
  * schema for LLM output generation
  * schema for persisted artifact validation

**Constraints**

* `specs/schemas/` must remain the only hand-maintained schema source.
* Persisted artifact payloads must not change shape.
* Canonical validation rules must stay strict.
* No new dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Keep one normative source schema set.
* [x] Extend the bundler to emit canonical bundled schemas and LLM-safe bundled output schemas.
* [x] Make generated schema-backed artifact models dual-schema-aware.
* [x] Ensure OpenAI/CrewAI sees only the output-safe bundled schema.
* [x] Preserve canonical bundled validation before persistence.

**Non-Goals**

* [x] Hand-maintain a second independent output-schema tree.
* [x] Weaken canonical persisted validation rules.
* [x] Change artifact envelope shape or schema IDs.

---

## 3) Proposed Behavior

**User/System behavior**

* Source schemas remain in `specs/schemas/`.
* The bundler emits:
  * `bundled/` for canonical validation
  * `bundled_output/` for LLM structured output
* Generated artifact models expose:
  * output-safe bundled schema via `model_json_schema()`
  * canonical bundled schema via `json_schema_contract()`
* Parsed payloads are still normalized and validated against the canonical bundled schema before write.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved:
  * schema bundler
  * generated artifact model pipeline
  * CrewAI/OpenAI structured output binding
* Contracts touched:
  * schema publication layout
  * generated artifact model contract

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/schemas/bundler.py`: adds output-schema derivation.
* `scripts/bundle_schemas.py`: publishes `bundled/` and `bundled_output/`.
* `src/rps/crewai_runtime/schema_backed_models.py`: separates output schema exposure from canonical validation.
* `scripts/generate_artifact_models.py`: generates dual-schema-aware artifact models.

**Data flow**

* Inputs: source schemas in `specs/schemas/`
* Processing:
  * resolve refs
  * publish canonical bundled schema
  * derive output-safe bundled schema
  * generate dual-schema-aware artifact models
* Outputs:
  * `bundled/*.schema.json`
  * `bundled_output/*.schema.json`
  * regenerated `generated_artifact_models.py`

**Schema / Artefacts**

* New schema publication target: `specs/knowledge/_shared/sources/schemas/bundled_output/`
* No persisted artifact contract changes.
* Validator implication: canonical validation continues to run against `bundled/`.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for persisted artifacts.
* Breaking changes: Internal runtime contract for generated schema-backed models.
* Fallback behavior: if `bundled_output/` is missing, runtime may fall back to canonical bundled schema, but the intended path is dual-published output schemas.

**Conflicts with ADRs / Principles**

* No conflict with current artifact schema ownership; this reinforces source-schemas-as-truth.

**Impacted areas**

* Validation/tooling: dual schema publication and model generation
* Runtime: structured output binding now uses `bundled_output/`
* Persistence: unchanged

---

## 6) Acceptance Criteria

* `bundle_schemas.py` emits both `bundled/` and `bundled_output/`.
* `bundled_output/` contains no `if` / `then` / `else` for affected schemas.
* Generated artifact models expose output-safe schemas via `model_json_schema()`.
* Canonical bundled schema validation still runs before persisted writes.
* `SEASON_PLAN` writer no longer fails due to `if` in `response_format`.

