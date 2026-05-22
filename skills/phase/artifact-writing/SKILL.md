---
name: artifact-writing
description: Serialize approved phase artifacts without adding planning content.
metadata:
  author: rps
  version: "3.1"
---
Write approved phase artefact data only: `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`.

Method:
1. Prefer emitting the approved `data` payload per artefact. If the active task still requires an envelope, emit exactly one `{meta,data}` envelope per artefact.
2. Preserve approved phase content faithfully and write only the approved planning decisions.
3. Do not invent persisted `meta`. Runtime owns `artifact_type`, `schema_id`, `schema_version`, `authority`, `owner_agent`, `run_id`, and `created_at`.
4. Validate each artefact against its own schema before any store call.

`PHASE_GUARDRAILS` rules:
- `iso_week` is the first week of `iso_week_range`.
- `temporal_scope` must be copied from upstream, not computed.
- propagate season global constraints exactly where required.
- `weekly_kj_bands` must be the final approved S5 output band, not a widened or re-expanded corridor.
- `explicit_forbidden_content` must contain exactly the required six strings.
- all required self-check booleans must be present and true.
- `body_metadata.phase_type`, `body_metadata.phase_intent`, and `body_metadata.phase_taxonomy_version` must match inherited upstream authority exactly.
- `body_metadata.build_subtype` must match inherited upstream authority exactly for `BUILD` phases and stay `null` otherwise.

`PHASE_STRUCTURE` rules:
- `load_ranges.weekly_kj_bands` must copy phase-guardrails bands exactly.
- `load_ranges.source` must be the actual stored phase-guardrails filename.
- week-role coverage must match the full phase range.
- `upstream_intent.phase_type`, `upstream_intent.phase_intent`, and `upstream_intent.phase_taxonomy_version` must match inherited Season Plan / PHASE_GUARDRAILS semantics exactly.
- `upstream_intent.build_subtype` must match inherited authority exactly for `BUILD` phases and stay `null` otherwise.
- keep workouts, interval structures, zones, %FTP, and day-by-day kJ targets in downstream artifacts.

`PHASE_PREVIEW` rules:
- derive from stored `PHASE_STRUCTURE` for the exact range.
- `traceability` may contain only `derived_from` and `conflict_resolution`.
- `derived_from` must include the stored phase-structure filename.
- `phase_intent_summary.phase_type`, `phase_intent_summary.phase_intent`, and `phase_intent_summary.phase_taxonomy_version` must match `PHASE_STRUCTURE.upstream_intent` exactly.
- `phase_intent_summary.build_subtype` must match `PHASE_STRUCTURE.upstream_intent.build_subtype` exactly for `BUILD` phases.
- preview remains semantic and structural, not workout-detailed.

Hard rules:
- stop on any schema error
- stop if a required upstream stored filename cannot be resolved
- stop if verbatim propagated season constraints are missing where mandated
- align narrative with the emitted numeric and semantic content
- do not repair unresolved phase semantics in the writer; fail rather than reinterpret

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return only the schema-compliant object required by the active task expected_output.
- Focus on `data`; if an envelope is requested, `meta` is a runtime-overwritten placeholder/hint.
- Preserve approved bundle content, review decisions, deterministic context, and trace references.
- Emit only the artifact object.
