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
2. Use exactly one season-cycle label per phase: `Base`, `Build`, `Peak`, or `Transition`.
3. Keep the structure compatible with cadence, recovery protection, event windows, and allowed agenda semantics.
4. Leave workout-level design and numeric targets to lower layers.

Required structure rules:
- `week_skeleton_logic.week_roles.week_roles` must cover every ISO week in `meta.iso_week_range` with no gaps or extras.
- `load_ranges.weekly_kj_bands` must be copied exactly from phase guardrails.
- `load_ranges.source` must use the stored phase-guardrails filename, not a guessed name.
- `upstream_intent.constraints` must include season global constraints verbatim where required.
- `key_risks_warnings` must stay aligned with phase guardrails.

Structural content rules:
- define role progression and recovery opportunities, not daily workouts
- include allowed role set, mandatory elements, optional elements, and forbidden patterns
- preserve fixed non-training days and long-endurance anchor protection
- prefer repeatable structure over brittle optimization

Hard rules:
- no numeric daily targets
- no workouts, intervals, zones, or %FTP
- no missing week-role coverage
- no new season objective invented inside the phase
