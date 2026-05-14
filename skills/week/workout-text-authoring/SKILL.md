---
name: workout-text-authoring
description: Author workout text that matches planned role, duration, load, and export constraints.
metadata:
  author: rps
  version: "2.0"
---
Use the canonical workout references:
- `references/workout_intent_mapping.md`
- `references/workout_section_structure.md`
- `references/warmup_activation_addon_cooldown_rules.md`
- `references/workout_text_allowed_subset.md`
- `references/workout_text_forbidden_patterns.md`
- `references/intervals_export_constraints.md`

Rules:
- workout text must be executable, role-consistent, and aligned with planned duration and load
- syntax must stay inside the project subset and remain export-safe
- avoid decorative detail that changes the workout meaning
