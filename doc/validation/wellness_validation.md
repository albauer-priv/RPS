# WELLNESS Validation

## Schema & meta
- [ ] Validates against `wellness.schema.json`.
- [ ] `meta.owner_agent` is `Data-Pipeline`.
- [ ] `meta.trace_upstream` references Intervals.icu wellness export.
- [ ] `meta.temporal_scope.to` may extend to calendar year end to keep `body_mass_kg` valid for future planning.

## Content
- [ ] Every entry includes a `date` and `source`.
- [ ] Required fields are present (values may be null).
- [ ] No training instructions or prescriptions included.
