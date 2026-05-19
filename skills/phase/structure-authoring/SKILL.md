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
3. Use exactly one season-cycle label per phase: `Base`, `Build`, `Peak`, or `Transition`.
4. Keep the structure compatible with cadence, recovery protection, event windows, phase role, weekly S5 bands, and allowed agenda semantics.
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

Hard rules:
- keep numeric daily targets in downstream week artifacts
- keep workouts, intervals, zones, and %FTP in downstream week/workout artifacts
- provide complete week-role coverage
- preserve the season objective inside the phase

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
