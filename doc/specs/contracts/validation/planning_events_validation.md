---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-04
Owner: Specs
---
# PLANNING_EVENTS Validation

## Location
- [ ] File lives in `var/athletes/<athlete_id>/inputs/planning_events_*.json`.
- [ ] Latest copy exists at `var/athletes/<athlete_id>/latest/planning_events.json`.

## Required content
- [ ] Validates against `planning_events.schema.json`.
- [ ] `meta.schema_id` = `PlanningEventsInterface` and `meta.schema_version` is current.
- [ ] `data.events` contains A/B/C events with required fields populated.
- [ ] Event `date` values are valid ISO dates (`YYYY-MM-DD`).

## Notes
- Planning events are binding inputs for season/phase planning.
