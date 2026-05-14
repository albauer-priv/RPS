---
name: traceability-and-naming
description: Apply traceability, naming, versioning, and data-confidence conventions to planning outputs.
metadata:
  author: rps
  version: "2.0"
---
Apply naming, traceability, and confidence rules exactly.

Method:
1. Treat the artefact envelope as binding. Preserve canonical `artifact_type`, `schema_id`, `schema_version`, `authority`, `owner_agent`, `scope`, `iso_week`, `iso_week_range`, and `temporal_scope`.
2. Keep `run_id` unique per generation run. Never reuse a `run_id` for a different artefact.
3. Preserve explicit upstream lineage in `trace_upstream`. If an artefact has no upstream, emit `trace_upstream: []` rather than omitting it.
4. Use canonical filename/version-key patterns and exact type labels expected by the workspace and schemas.
5. Keep confidence claims proportional to the evidence actually available.

Naming rules:
- ISO weeks always use `YYYY-WW` with a two-digit week.
- Phase ranges use `YYYY-WW--YYYY-WW`.
- Persisted JSON artefacts use lowercase, digits, underscore, dash, and plus only. No spaces.
- Human-readable sidecars are informational only and must never become planning inputs.

Trace rules:
- Season outputs must reference athlete profile, planning events, and logistics when used.
- Phase outputs must reference exactly one season plan.
- Week outputs must reference exactly one phase guardrails artefact and any applied phase feed-forward.
- Workout exports must reference the week plan they came from.
- Published artefacts are immutable. Any change requires a new artefact with a new `run_id`, new `created_at`, and updated upstream trace.

Confidence rules:
- `HIGH`: full interpretation allowed.
- `MEDIUM`: interpretation allowed, but limitations must be named explicitly.
- `LOW` or `UNKNOWN`: informational only; do not use these data to justify progression, deload avoidance, or governance overrides.
- Never upgrade confidence downstream without new source data.

Hard rules:
- do not guess missing lineage
- do not rename artefact types or schema identifiers
- do not treat stale or low-confidence data as strategic authority
- do not emit a persisted artefact if required trace or naming fields are missing
