---
name: structure-authoring
description: Define week roles and structural skeleton for the exact phase range.
metadata:
  author: rps
  version: "3.0"
---
Author the phase structure after guardrails are known.

Method:
1. Translate phase purpose into week roles and structural sequence covering every ISO week in the exact phase range.
2. Use injected `week_role_by_iso_week` exactly; week roles come from the selected scenario cadence and role-aware S5 context, not from structure authoring.
3. Use inherited canonical `phase_type` as the semantic container; do not invent or rename phase semantics during structure authoring.
4. Keep the structure compatible with cadence, recovery protection, event windows, phase role, weekly S5 bands, and allowed agenda semantics.
4a. Keep the structure explicitly compatible with inherited `phase_type`, `phase_intent`, and `build_subtype`; structure must narrow around intent, not reinterpret it.
5. Leave workout-level design and numeric targets to lower layers.

Required structure rules:
- `week_skeleton_logic.week_roles.week_roles` must cover every ISO week in `meta.iso_week_range` exactly.
- `week_skeleton_logic.week_roles.week_roles` must match the injected inherited week roles.
- `load_ranges.weekly_kj_bands` must be copied exactly from phase guardrails.
- `load_ranges.source` must use the stored phase-guardrails filename, not a guessed name.
- `upstream_intent.constraints` must include season global constraints verbatim where required.
- `key_risks_warnings` must stay aligned with phase guardrails.

Structural content rules:
- define role progression and recovery opportunities, not daily workouts
- include allowed role set, mandatory elements, optional elements, and excluded patterns
- preserve fixed non-training days and long-endurance anchor protection
- prefer repeatable structure over brittle optimization
- `specificity_build` must push structure toward pacing/fueling/terrain/logistics realism
- `durability_build` must emphasize B2B, preload, hard-late, and long-ride protection rather than rehearsal semantics
- `vo2_build` must keep VO2 weeks fresh and bounded rather than broad mixed-density
- `threshold_build` must center sustained-power structure
- `sst_build` must keep moderate density bounded
- `taper_freshening` must preserve freshness and reduce accumulation patterns
- `race_execution` must keep event logistics and recovery runway explicit

Hard rules:
- keep numeric daily targets in downstream week artifacts
- keep workouts, intervals, zones, and %FTP in downstream week/workout artifacts
- provide complete week-role coverage
- preserve the season objective inside the phase
- emit `upstream_intent.phase_type`, `upstream_intent.phase_intent`, and `upstream_intent.phase_taxonomy_version` explicitly and keep them identical to upstream authority
- emit `upstream_intent.build_subtype` explicitly for `BUILD` phases and keep it identical to upstream authority

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
