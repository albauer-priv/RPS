---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-04
Owner: Specs
---
# LOGISTICS Validation

## Location
- [ ] File lives in `runtime/athletes/<athlete_id>/inputs/logistics_*.json`.
- [ ] Latest copy exists at `runtime/athletes/<athlete_id>/latest/logistics.json`.

## Required content
- [ ] Validates against `logistics.schema.json`.
- [ ] `meta.schema_id` = `LogisticsInterface` and `meta.schema_version` is current.
- [ ] `data.events` entries describe non‑training constraints (travel/work/weather/etc.).

## Notes
- Logistics is informational input used to contextualize planning decisions.
