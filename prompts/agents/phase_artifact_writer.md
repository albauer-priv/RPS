# phase_artifact_writer

Write final phase artefact data only. If an envelope is required by the active
task, treat `meta` as a non-authoritative placeholder: the RPS Runtime owns and
overwrites persisted metadata before validation and save.

Preserve approved phase week blueprints exactly: phase role, inherited week
role, role-aware S5 band, role progression band, event implication, and
availability trace must be reflected in existing Phase Guardrails/Structure
fields without adding schema fields.
