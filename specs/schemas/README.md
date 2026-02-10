# Schemas (JSON)

Authoritative JSON Schemas for agent-generated/consumed artefacts.

Conventions:
- All artefacts use the `ArtefactEnvelope` (`meta` + `data`).
- `meta.schema_id` uses the former Interface-ID to preserve continuity.
- `meta.schema_version` is global V1 (currently `1.0`).
- Optional human-readable sidecars use `<basename>.rendered.md` and are non-binding.

Common schemas:
- `artefact_meta.schema.json`
- `artefact_envelope.schema.json`
- `agenda_enum.schema.json`
- `date_range.schema.json`
- `iso_week.schema.json`
- `iso_week_range.schema.json`
- `number_range.schema.json`
- `load_band.schema.json`
- `load_band_kj_per_kg.schema.json`
- `structured_doc.schema.json`
- `trace_reference.schema.json`
- `tabular_data.schema.json`
