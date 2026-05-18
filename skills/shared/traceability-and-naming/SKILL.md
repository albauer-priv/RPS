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
2. Keep `run_id` unique per generation run and bind it to exactly one artefact.
3. Preserve explicit upstream lineage in `trace_upstream`. For artefacts without upstream lineage, emit `trace_upstream: []` rather than omitting it.
4. Use canonical filename/version-key patterns and exact type labels expected by the workspace and schemas.
5. Keep confidence claims proportional to the evidence actually available.

Naming rules:
- ISO weeks always use `YYYY-WW` with a two-digit week.
- Phase ranges use `YYYY-WW--YYYY-WW`.
- Persisted JSON artefacts use lowercase, digits, underscore, dash, and plus only.
- Human-readable sidecars are informational only; use canonical JSON artefacts as planning inputs.

Trace rules:
- Season outputs must reference athlete profile, planning events, and logistics when used.
- Phase outputs must reference exactly one season plan.
- Week outputs must reference exactly one phase guardrails artefact and any applied phase feed-forward.
- Workout exports must reference the week plan they came from.
- Published artefacts are immutable. Any change requires a new artefact with a new `run_id`, new `created_at`, and updated upstream trace.

Confidence rules:
- `HIGH`: full interpretation allowed.
- `MEDIUM`: interpretation allowed, but limitations must be named explicitly.
- `LOW` or `UNKNOWN`: informational only; use higher-confidence data for progression, deload, or governance decisions.
- Upgrade confidence downstream only when new source data supports it.

Hard rules:
- preserve lineage from available upstream references and mark missing lineage explicitly
- preserve canonical artefact types and schema identifiers
- use current and sufficiently confident data as strategic authority
- emit persisted artefacts only when required trace and naming fields are present

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output without adding a separate artifact or unrelated prose.
- Include only the runtime-boundary, context-consumption, traceability, or naming guidance needed for the current task.
- Keep the contribution concise and directly usable by downstream tasks.
