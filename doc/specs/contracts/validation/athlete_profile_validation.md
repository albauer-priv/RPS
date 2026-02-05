---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-04
Owner: Specs
---
# ATHLETE_PROFILE Validation

## Location
- [ ] File lives in `var/athletes/<athlete_id>/inputs/athlete_profile_*.json`.
- [ ] Latest copy exists at `var/athletes/<athlete_id>/latest/athlete_profile.json`.

## Required content
- [ ] Validates against `athlete_profile.schema.json`.
- [ ] `meta.schema_id` = `AthleteProfileInterface` and `meta.schema_version` is current.
- [ ] `data.profile.athlete_id` and `data.profile.year` are populated.
- [ ] `data.objectives.primary` is populated.

## Notes
- Optional fields may be empty, but arrays should be present when provided.
