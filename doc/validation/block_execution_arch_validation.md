# BLOCK_EXECUTION_ARCH Validation

## Schema & meta
- [ ] Validates against `block_execution_arch.schema.json`.
- [ ] `meta.iso_week` and `meta.iso_week_range` match the target block.
- [ ] `meta.trace_upstream` includes `macro_overview` and `block_governance`.

## Macro constraint propagation
- [ ] `upstream_intent.constraints` includes macro availability and risk constraints.
- [ ] `load_ranges.weekly_kj_bands` matches block_governance weekly bands (same weeks, min/max, notes).
- [ ] `load_ranges.source` references the block governance filename.
- [ ] `execution_principles.recovery_protection.fixed_non_training_days` derives from macro fixed rest days (or parsed from availability assumptions).
- [ ] Recovery spacing rules reflect upstream recovery protection notes (no new rules).

## Governance alignment
- [ ] `load_intensity_handling` matches block_governance domains and max quality days.
- [ ] `relationships.guides` references the block governance file.
- [ ] Execution principles and quality density reflect the macro intensity distribution choice (Principles section 4.6).
- [ ] No workouts or day-by-day prescriptions.
