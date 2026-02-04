---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Specs
---
# AVAILABILITY Validation

## Location
- [ ] File lives in `var/athletes/<athlete_id>/data/<yyyy>/<ww>/availability_yyyy-ww.json`.
- [ ] Latest copy exists at `var/athletes/<athlete_id>/latest/availability.json`.

## Required content
- [ ] Validates against `availability.schema.json`.
- [ ] `meta.schema_id` = `AvailabilityInterface` and `meta.schema_version` is current.
- [ ] `data.season_brief_ref` points to the source Season Brief file.
- [ ] `availability_table` contains 7 rows (Mon-Sun).
- [ ] `weekly_hours` equals the sum of the daily hours (min/typical/max).
- [ ] `fixed_rest_days` matches `locked=true` rows.
- [ ] `temporal_scope.from` is the generation date or Season Brief valid-from (if future).
- [ ] `temporal_scope.to` is end of season year unless an explicit valid-to is provided.

## Notes
- If any day is missing or not parseable, regenerate the artefact.
