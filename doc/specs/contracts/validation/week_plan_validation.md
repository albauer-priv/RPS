---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Specs
---
# WEEK_PLAN Validation

## Schema & meta
- [ ] Validates against `week_plan.schema.json`.
- [ ] `meta.iso_week` matches the target week.
- [ ] `meta.trace_upstream` references `phase_guardrails` and `phase_structure`.

## Governance alignment
- [ ] Weekly load stays inside kJ bands from phase guardrails.
- [ ] Allowed day roles and intensity domains match phase structure.
- [ ] Quality density limits are respected.
