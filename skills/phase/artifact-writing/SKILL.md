---
name: artifact-writing
description: Serialize approved phase artifacts without adding planning content.
metadata:
  author: rps
  version: "3.0"
---
Write approved phase artefacts only: `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`.

Method:
1. Emit exactly one `{meta,data}` envelope per artefact.
2. Preserve approved phase content faithfully and write only the approved planning decisions.
3. Use exact constants and range semantics expected by each schema.
4. Validate each artefact against its own schema before any store call.

`PHASE_GUARDRAILS` rules:
- `iso_week` is the first week of `iso_week_range`.
- `temporal_scope` must be copied from upstream, not computed.
- propagate season global constraints exactly where required.
- `weekly_kj_bands` must be the final approved S5 output band, not a widened or re-expanded corridor.
- `explicit_forbidden_content` must contain exactly the required six strings.
- all required self-check booleans must be present and true.

`PHASE_STRUCTURE` rules:
- `load_ranges.weekly_kj_bands` must copy phase-guardrails bands exactly.
- `load_ranges.source` must be the actual stored phase-guardrails filename.
- week-role coverage must match the full phase range.
- keep workouts, interval structures, zones, %FTP, and day-by-day kJ targets in downstream artifacts.

`PHASE_PREVIEW` rules:
- derive from stored `PHASE_STRUCTURE` for the exact range.
- `traceability` may contain only `derived_from` and `conflict_resolution`.
- `derived_from` must include the stored phase-structure filename.
- preview remains semantic and structural, not workout-detailed.

Hard rules:
- stop on any schema error
- stop if a required upstream stored filename cannot be resolved
- stop if verbatim propagated season constraints are missing where mandated
- align narrative with the emitted numeric and semantic content

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return only the schema-compliant artifact envelope required by the active task expected_output.
- Include top-level `meta` and `data` content exactly as required by the artifact schema.
- Preserve approved bundle content, review decisions, deterministic context, and trace references.
- Emit only the artifact object.
