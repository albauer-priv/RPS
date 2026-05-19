---
Version: 1.0
Status: Accepted
Last-Updated: 2026-05-19
Owner: ADR
---
# ADR-051: Code-Owned Artifact Metadata and Trace References

**Status:** Accepted  
**Date:** 2026-05-19  

## Context

Persisted RPS artefacts use a `{meta, data}` envelope. The `data` portion is domain output; the `meta` portion drives schema validation, traceability, latest pointers, rendering, and audit. Recent CrewAI writer runs repeatedly produced valid-looking domain data but invalid metadata, for example `schema_id: "season_plan.schema.json"` instead of `SeasonPlanInterface`, an invented `owner_agent`, or operative workspace keys such as `20260315_091949` in `trace_upstream[*].version` where schemas expected semantic versions.

Prompt-only correction is not robust because schema-critical metadata is not a reasoning choice. It is runtime policy derived from the output spec, schema constants, workspace context, and run context.

## Decision

RPS persisted artifact metadata is owned by code, not by agents.

The Runtime/Workspace layer must canonicalize artefact envelopes before final validation and save:

- `artifact_type`, `schema_id`, `schema_version`, `authority`, and `owner_agent` are overwritten from schema constants and canonical writer mappings.
- `run_id` and `created_at` are set from runtime context when available.
- `trace_upstream`, `trace_data`, and `trace_events` are normalized centrally.
- JSON Schema validation runs against the final runtime-built envelope.

Trace references distinguish:

- `schema_version`: semantic version of the referenced artefact contract.
- `version_key`: workspace/file version key, such as `20260315_091949` or `2026-21__20260518_190443`.
- `version`: backwards-compatible semantic-version alias retained during migration.

Agent and skill guidance must say that writer tasks focus on `data`; any emitted `meta` is non-authoritative and may be ignored or overwritten by the runtime.

## Consequences

- Positive: a domain-valid artefact no longer fails to persist because a model invented schema-critical metadata.
- Positive: traceability remains strict while accepting realistic workspace version keys.
- Positive: metadata policy has a single implementation surface in the workspace runtime.
- Trade-off: producers that bypass the guarded store and validate raw legacy trace references must be updated or route through canonicalization.
- Trade-off: bundled schemas and generated artifact models must be regenerated when the trace-reference contract changes.

## Exceptions

None. Direct file writes may still exist for legacy/runtime inputs, but persisted planning/report envelopes that go through guarded storage must use code-owned metadata.
