# PHASE_STRUCTURE Validation

## Schema & meta
- [ ] Validates against `phase_structure.schema.json`.
- [ ] `meta.iso_week` and `meta.iso_week_range` match the target block.
- [ ] `meta.trace_upstream` includes `season_plan` and `phase_guardrails`.

## Macro constraint propagation
- [ ] `upstream_intent.constraints` includes macro availability and risk constraints.
- [ ] `load_ranges.weekly_kj_bands` matches phase_guardrails weekly bands (same weeks, min/max, notes).
- [ ] `weekly_kj_bands` are interpreted as **planned_Load_kJ** (stress‑weighted kJ).
- [ ] `week_roles` length matches the block `iso_week_range` length.
- [ ] `load_ranges.source` references the phase guardrails filename.
- [ ] `execution_principles.recovery_protection.fixed_non_training_days` derives from macro fixed rest days (or parsed from availability assumptions).
- [ ] Recovery spacing rules reflect upstream recovery protection notes (no new rules).

## Governance alignment
- [ ] `load_intensity_handling` matches phase_guardrails domains and max quality days.
- [ ] `relationships.guides` references the phase guardrails file.
- [ ] Execution principles and quality density reflect the macro intensity distribution choice (Principles section 4.6).
- [ ] No workouts or day-by-day prescriptions.
