---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Architecture
---
# Schema Versioning

Version: 1.0  
Status: Updated  
Last-Updated: 2026-01-20

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

---

## Compatibility Rules

- Prefer **backward-compatible** changes (add optional fields).
- Avoid removing fields or tightening constraints without a migration plan.
- Keep `additionalProperties: false` only when you can enforce strict output.

---

## Change Process

1. Update the schema file in `schemas/`.
2. Bump `schema_version` (and update const fields if required).
3. Update producers (agent prompts, pipeline scripts).
4. If needed, provide a migration script for existing artefacts.
5. Rebuild bundled schemas for retrieval (`python scripts/bundle_schemas.py`).

---

## Validation

Use `scripts/validate_outputs.py` to validate pipeline outputs and
`Workspace.put_validated(...)` for agent-produced artefacts.

---

## End
