---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-21
Owner: Runtime / Schemas
---
# ADR-054: Dual Bundled Structured-Output Schemas

## Context

RPS uses `specs/schemas/*.schema.json` as the normative schema source and bundles them for runtime validation. Generated CrewAI artifact models currently use that bundled schema both:

* as the OpenAI/CrewAI structured-output schema
* as the canonical persisted-artifact validation schema

The canonical phase-taxonomy migration introduced valid repo-side JSON Schema conditionals such as `if` / `then` / `else`. These are acceptable for canonical validation but rejected by OpenAI structured output.

## Decision

RPS will publish two bundled schema targets from one source schema set:

* `bundled/` for canonical validation and persistence
* `bundled_output/` for LLM structured output

Generated schema-backed artifact models will become dual-schema-aware:

* `model_json_schema()` returns the LLM-safe bundled output schema
* canonical post-parse validation uses the canonical bundled schema

The source schemas in `specs/schemas/` remain the single hand-maintained truth.

## Consequences

### Positive

* OpenAI/CrewAI receives only supported output schemas.
* Canonical persisted validation stays strict.
* No duplicated hand-maintained output-schema tree is introduced.
* The bundler remains the central schema publication tool.

### Negative

* Schema tooling and generated model behavior become more complex.
* Two bundled schema trees must be kept in sync by tooling.

## Alternatives Considered

### 1. Weaken canonical schemas directly

Rejected. This would remove useful repo-side validation semantics purely to satisfy structured-output constraints.

### 2. Hand-maintain separate output schemas

Rejected. This would create long-term drift risk and duplicate schema maintenance.

