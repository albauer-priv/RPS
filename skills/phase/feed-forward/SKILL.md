---
name: feed-forward
description: Produce phase feed-forward guidance for downstream week planning as bounded deltas only.
metadata:
  author: rps
  version: "2.0"
---
Write `PHASE_FEED_FORWARD` as a temporary delta layer over baseline phase guardrails.

Method:
1. Preserve baseline phase authority and describe only the temporary adjustment.
2. State the trigger, observed deviation, and intent of adjustment explicitly.
3. Emit adjusted weekly kJ bands, semantic overrides, temporary non-negotiables, and week-planner operating rules.
4. Keep expiry explicit through `valid_until` and `explicit_expiry_condition`.
5. Validate against `phase_feed_forward.schema.json` before storing.

Required content:
- `body_metadata.applies_to_weeks`, `valid_until`, `change_type`, `derived_from`, `upstream_triggers`
- `reason_context.trigger_summary`, `observed_risk_deviation`, `intent_of_adjustment`
- `delta_load_guardrails.adjusted_weekly_kj_bands`
- `temporary_semantic_overrides`
- `temporary_non_negotiables`
- `week_planner_operating_rules`
- `explicit_forbidden_content`
- `self_check`

Hard rules:
- only deltas vs baseline
- keep workouts and intervals in downstream week/workout tasks
- keep day-by-day schedules in downstream week planning
- keep numeric progression instructions in downstream week planning when authorized
- stop if any required field or expiry semantics are missing
- do not ask coworkers to rediscover baseline phase authority or upstream report/feed-forward facts during feed-forward authoring

Output format:
- Return the task expected_output as advisory feed-forward guidance.
- Include evidence summary, affected scope, recommended adjustment theme, warnings, and trace references.
- Keep feed-forward diagnostic or advisory unless the active artifact schema makes it binding.
