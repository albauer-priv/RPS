---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Specs
---
# PHASE_GUARDRAILS Validation

## Schema & meta
- [ ] Validates against `phase_guardrails.schema.json`.
- [ ] `meta.iso_week_range` matches the resolved phase range.
- [ ] `meta.trace_upstream` includes the latest `season_plan` (and feed-forward if used).

## Season constraint propagation
- [ ] Availability assumptions are reflected in `execution_non_negotiables` and `phase_summary.non_negotiables`.
- [ ] Risk constraints are reflected in `phase_summary.key_risks_warnings`.
- [ ] Planned event windows are reflected in `events_constraints` or `phase_summary` notes.

## Guardrails
- [ ] `weekly_kj_bands` has one entry per week in `meta.iso_week_range`.
- [ ] `weekly_kj_bands` represent **planned_Load_kJ** (stress‑weighted kJ), not mechanical kJ.
- [ ] Weekly bands show a progression pattern (e.g., build→build→peak→deload) unless season explicitly requires steady-state load.
- [ ] Weekly band notes reflect the overload intent (build/peak/deload) consistent with Principles section 5.
- [ ] Allowed/forbidden semantics match `agenda_enum_spec.md`.
- [ ] Allowed intensity domains and quality density align with the season intensity distribution choice (Principles section 4.6).
- [ ] No workouts, day-by-day plans, or session prescriptions.
