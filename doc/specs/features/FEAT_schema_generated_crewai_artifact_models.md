---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-17
Owner: CrewAI Runtime
---
# FEAT: Schema-Generated CrewAI Artifact Models

* **ID:** FEAT_schema_generated_crewai_artifact_models
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime / Workspace Validation
* **Last-Updated:** 2026-05-17
* **Related:** `scripts/bundle_schemas.py`, `src/rps/crewai_runtime/generated_artifact_models.py`

---

## 1) Context / Problem

**Current behavior**

* Persisted CrewAI artifact tasks request an `artifact_envelope` output, but the direct task path historically parsed raw JSON for artifact envelopes.
* Final validation happens in `GuardedValidatedStore` against the canonical JSON schemas.

**Problem**

* Generic artifact-envelope structure is weaker than the concrete artifact schemas.
* Schema violations such as invalid `meta.scope`, non-semver `meta.version`, or wrong nested field types can reach the store instead of being caught as retryable CrewAI task validation errors.

**Constraints**

* JSON schemas under `specs/schemas/` remain the canonical artifact contracts.
* Do not duplicate full schema logic manually in handwritten Pydantic classes.
* Do not introduce a new dependency for schema-to-model generation.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Generate artifact-specific CrewAI output models from the canonical JSON schema inventory.
* [x] Re-run model generation automatically when the JSON schema bundler runs.
* [x] Keep JSON Schema validation as the hard source of truth.
* [x] Let CrewAI persisted artifact tasks use artifact-specific models where possible.

**Non-Goals**

* [x] No new artifact schema fields.
* [x] No manual nested Pydantic model rewrite of every schema.
* [x] No new third-party code generator dependency.

---

## 3) Proposed Behavior

**User/System behavior**

* When schemas are bundled, CrewAI artifact output models are regenerated from the current schema set.
* Persisted CrewAI tasks use the generated model matching their task/schema when available.
* Generated models validate the full artifact payload against the corresponding JSON schema during Pydantic validation.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved: schema bundler, generated CrewAI artifact models, CrewAI backend task construction.
* Contracts touched: persisted artifact task output validation.

---

## 4) Implementation Analysis

**Components / Modules**

* `scripts/generate_artifact_models.py`: generates artifact-specific model classes and task/schema mappings.
* `scripts/bundle_schemas.py`: runs model generation after schema bundling.
* `src/rps/crewai_runtime/schema_backed_models.py`: validates generated model instances against canonical JSON Schema.
* `src/rps/crewai_runtime/generated_artifact_models.py`: generated artifact model registry.
* `src/rps/crewai_runtime/guardrails.py`: `artifact_schema_valid` function guardrail validates persisted artifact task output before persistence.
* `src/rps/agents/crewai_backend.py`: selects generated artifact models for persisted CrewAI tasks.

**Data flow**

* Inputs: `specs/schemas/*.schema.json`, `config/crewai/tasks.yaml`.
* Processing: bundle schemas, generate model registry, use generated model in CrewAI task `output_json` / `output_pydantic`, validate with `artifact_schema_valid`.
* Outputs: regenerated `generated_artifact_models.py`.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: Pydantic validation and explicit CrewAI function guardrails now call JSON Schema validation before store persistence.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none expected.
* Fallback behavior: if a task has no generated model, it falls back to the generic `ArtifactEnvelopeModel`.

**Conflicts with ADRs / Principles**

* Potential conflicts: none.
* Resolution: JSON Schema remains single source of truth.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: validation is stricter earlier and retry-capable through CrewAI guardrails; final store validation remains unchanged.
* Validation/tooling: schema bundler also refreshes generated CrewAI artifact models.
* Deployment/config: no new dependency.

---

## 6) Options & Recommendation

### Option A — Handwritten Pydantic Models

**Summary**

* Maintain concrete Pydantic models manually for every artifact.

**Pros**

* Strong Python types.

**Cons**

* Duplicates JSON Schema truth and is likely to drift.

### Option B — Schema-Backed Generated Models

**Summary**

* Generate artifact model classes from schema inventory, with JSON Schema as runtime validator.

**Pros**

* Schema-first, no new dependency, low drift risk.

**Cons**

* Python field typing remains envelope-level (`meta`, `data`) while concrete validation is delegated to JSON Schema.

### Recommendation

* Choose: Option B.
* Rationale: preserves JSON Schema as canonical truth and gives CrewAI artifact-specific structured output without handwritten schema duplication.

---

## 7) Acceptance Criteria

* [x] `scripts/bundle_schemas.py` triggers artifact model generation.
* [x] Generated models include concrete classes for persisted artifact schemas.
* [x] CrewAI persisted artifact tasks select generated models where available.
* [x] Generated model validation rejects schema-invalid payloads.
* [x] Persisted artifact tasks include an explicit `artifact_schema_valid` function guardrail.
* [x] Validation passes: targeted tests, `py_compile`, lint, typecheck, full pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* No workspace migration. Regenerate models whenever schemas change.

**Rollout / gating**

* Feature flag: none.
* Safe rollback: use generic artifact envelope fallback by removing generated model mapping.

---

## 9) Risks & Failure Modes

* Failure mode: generated model file is stale.
  * Detection: codegen test or bundler diff.
  * Safe behavior: rerun `python3 scripts/bundle_schemas.py`.
  * Recovery: commit regenerated file.
* Failure mode: generated JSON schema validation rejects a formerly accepted invalid artifact.
  * Detection: CrewAI guardrail/task failure before store.
  * Safe behavior: no invalid artifact is persisted.
  * Recovery: fix prompt/normalizer/schema.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Schema/model generation messages are printed by `scripts/bundle_schemas.py`.
* Runtime validation errors surface through CrewAI task errors or guarded-store validation.

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — document generated CrewAI artifact model pipeline.
