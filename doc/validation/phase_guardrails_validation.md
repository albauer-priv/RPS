# PHASE_GUARDRAILS Validation

## Schema & meta
- [ ] Validates against `phase_guardrails.schema.json`.
- [ ] `meta.iso_week_range` matches the resolved block range.
- [ ] `meta.trace_upstream` includes the latest `season_plan` (and feed-forward if used).

## Macro constraint propagation
- [ ] Availability assumptions are reflected in `execution_non_negotiables` and `block_summary.non_negotiables`.
- [ ] Risk constraints are reflected in `block_summary.key_risks_warnings`.
- [ ] Planned event windows are reflected in `events_constraints` or `block_summary` notes.

## Guardrails
- [ ] `weekly_kj_bands` has one entry per week in `meta.iso_week_range`.
- [ ] `weekly_kj_bands` represent **planned_Load_kJ** (stress‑weighted kJ), not mechanical kJ.
- [ ] Weekly bands show a progression pattern (e.g., build→build→peak→deload) unless macro explicitly requires steady-state load.
- [ ] Weekly band notes reflect the overload intent (build/peak/deload) consistent with Principles section 5.
- [ ] Allowed/forbidden semantics match `agenda_enum_spec.md`.
- [ ] Allowed intensity domains and quality density align with the macro intensity distribution choice (Principles section 4.6).
- [ ] No workouts, day-by-day plans, or session prescriptions.
