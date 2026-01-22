# WORKOUTS_PLAN Validation

## Schema & meta
- [ ] Validates against `workouts_plan.schema.json`.
- [ ] `meta.iso_week` matches the target week.
- [ ] `meta.trace_upstream` references `block_governance` and `block_execution_arch`.

## Governance alignment
- [ ] Weekly load stays inside kJ/TSS bands from block governance.
- [ ] Allowed day roles and intensity domains match execution architecture.
- [ ] Quality density limits are respected.
