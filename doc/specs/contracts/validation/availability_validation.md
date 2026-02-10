---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Specs
---
# AVAILABILITY Validation

## Location
- [ ] File lives in `runtime/athletes/<athlete_id>/inputs/availability_*.json`.
- [ ] Latest copy exists at `runtime/athletes/<athlete_id>/latest/availability.json`.

## Required content
- [ ] Validates against `availability.schema.json`.
- [ ] `meta.schema_id` = `AvailabilityInterface` and `meta.schema_version` is current.
- [ ] `data.source_type` and `data.source_ref` are populated.
- [ ] `availability_table` contains 7 rows (Mon-Sun).
- [ ] `weekly_hours` equals the sum of the daily hours (min/typical/max).
- [ ] `fixed_rest_days` matches `locked=true` rows.
- [ ] `temporal_scope.from` is the generation date or the declared validity window.
- [ ] `temporal_scope.to` is end of season year unless an explicit valid-to is provided.

## Notes
- If any day is missing or not parseable, regenerate the artefact.
