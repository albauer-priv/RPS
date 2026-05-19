---
Version: 1.1
Status: Updated
Last-Updated: 2026-05-19
Owner: Architecture
---
# Schema Versioning

Version: 1.1
Status: Updated
Last-Updated: 2026-05-19

---

## Purpose

This document describes how to evolve JSON schemas without breaking the
planning system or historical artefacts.

---

## Version Fields

Every artefact envelope contains:

- `schema_id`
- `schema_version`
- `version`

Guidelines:

- **schema_version** changes when the schema contract changes.
- **version** changes when the artefact content changes without schema change.
- **version_key** is a workspace/file key used for storage and lookup. It is not
  a semantic schema version and may contain operational timestamps such as
  `20260315_091949` or scoped keys such as `2026-21__20260518_190443`.

Persisted planning/report metadata is code-owned. Writer agents may emit
metadata hints, but the workspace runtime overwrites schema-critical fields
before validation and persistence:

- `artifact_type`
- `schema_id`
- `schema_version`
- `authority`
- `owner_agent`

Trace references use the same distinction:

- `schema_version`: semantic contract version of the referenced artefact.
- `version`: backwards-compatible semantic-version alias.
- `version_key`: exact workspace/file version key of the referenced artefact.

---

## Compatibility Rules

- Prefer **backward-compatible** changes (add optional fields).
- Avoid removing fields or tightening constraints without a migration plan.
- Keep `additionalProperties: false` only when you can enforce strict output.

---

## Change Process

1. Update the schema file in `specs/schemas/`.
2. Bump `schema_version` (and update const fields if required).
3. Update producers or runtime canonicalizers.
4. If needed, provide a migration script for existing artefacts.
5. Rebuild bundled schemas for retrieval (`python scripts/bundle_schemas.py`).

---

## Validation

Use `scripts/validate_outputs.py` to validate pipeline outputs and
`Workspace.put_validated(...)` for agent-produced artefacts.

---

## End
