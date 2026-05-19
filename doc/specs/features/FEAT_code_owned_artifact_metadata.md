---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Workspace
---
# FEAT: Code-Owned Artifact Metadata

* **ID:** FEAT_code_owned_artifact_metadata
* **Status:** Implemented
* **Owner/Area:** Workspace / CrewAI Runtime / Schemas
* **Last-Updated:** 2026-05-19
* **Related:** ADR-051 Code-Owned Artifact Metadata and Trace References

---

## 1) Context / Problem

**Current behavior**

* CrewAI writer tasks may return full persisted artefact envelopes with `meta` and `data`.
* The final workspace store validates the complete envelope against JSON Schema before saving.
* Writer-produced metadata has repeatedly failed persistence for deterministic fields such as `schema_id`, `owner_agent`, and trace `version`.

**Problem**

* Schema-critical metadata is currently partly agent-owned even though it is runtime policy, not domain reasoning.
* Trace `version` mixes schema version semantics with workspace/file version keys such as `20260315_091949`.
* A good domain artefact can be lost because non-domain metadata was invented or formatted incorrectly by the model.

**Constraints**

* Persisted envelopes keep `meta` for traceability, rendering, latest/index handling, and audit.
* JSON Schema validation remains strict.
* Existing runtime artefacts must remain readable without in-place migration.
* No new dependencies.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make schema-critical persisted metadata code-owned before final validation.
* [x] Preserve strict schema validation of final stored envelopes.
* [x] Separate trace schema version from workspace version key.
* [x] Keep legacy trace references readable.
* [x] Cover the recurring Season Plan save failure with a regression test.

**Non-Goals**

* [x] Remove artifact metadata entirely.
* [x] Implement an in-place migration of existing runtime workspaces.
* [x] Relax validation broadly or accept arbitrary persisted envelopes.

---

## 3) Proposed Behavior

**User/System behavior**

* Writer agents focus on artefact `data` and may provide non-authoritative trace hints.
* The Runtime/Workspace layer builds canonical persisted `meta` before validation and save.
* If an agent still emits `{ "meta": ..., "data": ... }`, deterministic fields in `meta` are overwritten from code and schema constants.
* Store validation runs against the runtime-built final envelope.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: CrewAI schema-backed validation, guarded workspace store, local store legacy read normalization, schema bundler/codegen.
* Contracts touched: `trace_reference.schema.json`, all artefact envelopes embedding trace references.

---

## 4) Implementation Analysis

**Components / Modules**

* `rps.workspace.artifact_metadata`: central metadata and trace-reference canonicalization.
* `rps.workspace.guarded_store`: canonicalizes envelopes before schema validation and persistence.
* `rps.crewai_runtime.schema_backed_models`: uses the same canonicalization before generated Pydantic model validation.
* `rps.workspace.local_store`: normalizes legacy trace references when loading old documents.

**Data flow**

* Inputs: writer output envelope or data-bearing document, output spec, schema file, run id.
* Processing: load schema constants, overwrite deterministic `meta`, normalize trace references, round numeric fields, validate final envelope.
* Outputs: persisted canonical envelope, rendered sidecar, workspace index/latest pointers.

**Schema / Artefacts**

* Changed artefact: `trace_reference.schema.json`.
* Trace references now include `schema_version` and `version_key`.
* `version` remains as a backwards-compatible semver alias during migration.
* Bundled schemas and generated schema-backed models are regenerated.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes for reads and new writes.
* Breaking changes: External producers that validate against source schemas must now include `schema_version` and `version_key`, or pass through the runtime canonicalizer.
* Fallback behavior: legacy trace refs loaded from disk are normalized in memory.

**Conflicts with ADRs / Principles**

* Potential conflicts: none.
* Resolution: ADR-051 records the ownership boundary and trace-reference model.

**Impacted areas**

* UI: none.
* Pipeline/data: producers should use runtime store/canonicalization for persisted envelopes.
* Renderer: continues using canonical stored `meta`.
* Workspace/run-store: final store owns persisted metadata.
* Validation/tooling: schema bundling and generated artifact models reflect the new trace schema.
* Deployment/config: none.

**Required refactoring**

* Centralize metadata normalization instead of local one-off fixes.
* Update artifact-writing skills and mandatory-output docs to stop treating persisted `meta` as an agent decision.

---

## 6) Options & Recommendation

### Option A (recommended) — Runtime-Owned Metadata

**Summary**

* Runtime builds persisted `meta` from schema constants and workspace context; agents provide domain `data`.

**Pros**

* Eliminates recurrent LLM formatting failures for schema-critical fields.
* Keeps strict validation and traceability.
* Creates a single boundary for metadata policy.

**Cons**

* Requires schema/codegen updates and docs changes.
* External direct schema validators must use the new trace reference shape.

**Risk**

* Some producer paths may still validate raw envelopes directly and need follow-up if discovered.

### Option B — Loosen Metadata Validation

**Summary**

* Allow looser schema IDs, owner agents, and trace versions.

**Pros**

* Smaller immediate change.

**Cons**

* Weakens auditability and makes stored envelopes less canonical.
* Does not clarify ownership.

### Recommendation

* Choose: Option A.
* Rationale: metadata is infrastructure state; the model should not own it.

---

## 7) Acceptance Criteria

* [x] Bad writer `schema_id` is replaced with schema-constant `schema_id`.
* [x] Bad writer `owner_agent` is replaced with canonical writer.
* [x] Trace entries preserve operative workspace keys in `version_key`.
* [x] Legacy trace entries with operative `version` still validate after runtime canonicalization.
* [x] Problematic Season Plan payload shape saves through `GuardedValidatedStore`.
* [x] Validation passes: schema required check, schema bundler/codegen, py_compile, lint, typecheck, pytest.

---

## 8) Migration / Rollout

**Migration strategy**

* No in-place workspace migration.
* `LocalArtifactStore` continues to normalize legacy trace references during reads.
* New writes use `schema_version`, `version`, and `version_key`.

**Rollout / gating**

* Feature flag / config: none.
* Safe rollback: revert schema and canonicalization changes before writing new trace-reference shape.

---

## 9) Risks & Failure Modes

* Failure mode: a producer bypasses `GuardedValidatedStore` and validates raw legacy trace references directly.
  * Detection: schema validation error mentioning missing `schema_version` or `version_key`.
  * Safe behavior: fail before persistence.
  * Recovery: route producer through runtime canonicalization or include new trace fields.
* Failure mode: runtime cannot infer optional context fields.
  * Detection: persisted fallback context values in logs/tests.
  * Safe behavior: schema-valid envelope with conservative defaults.
  * Recovery: pass richer workspace context into the metadata builder.

---

## 10) Observability / Logging

**New/changed events**

* Existing `Store failed` logs now report validation against the runtime-canonicalized envelope.
* Existing `Stored artifact` logs continue to show canonical artifact type, version key, path, and run id.

**Diagnostics**

* Inspect `runtime/athletes/<athlete>/logs/rps.log` for store attempts/failures.
* Inspect saved artifact `meta.trace_*` for `schema_version`, `version`, and `version_key`.

---

## 11) Documentation Updates

* [x] `doc/architecture/schema_versioning.md` — distinguish schema version, artifact version, and version key.
* [x] `doc/architecture/workspace.md` — document runtime-owned persisted metadata.
* [x] `specs/knowledge/_shared/sources/specs/traceability_spec.md` — document trace-reference fields.
* [x] `skills/shared/traceability-and-naming/SKILL.md` — runtime owns persisted metadata.
* [x] Artifact-writing skills — writers do not invent persisted metadata.
* [x] Mandatory-output docs — persisted metadata examples are non-authoritative/runtime-owned.

---

## 12) Link Map

* `doc/adr/ADR-051-code-owned-artifact-metadata.md`
* `doc/architecture/schema_versioning.md`
* `doc/architecture/workspace.md`
* `specs/schemas/trace_reference.schema.json`
* `specs/knowledge/_shared/sources/specs/traceability_spec.md`
