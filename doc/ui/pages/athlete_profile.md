---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-05
Owner: UI
---
# Athlete Profile Pages
All input guidance is provided on the pages themselves; templates are not used.

## About You & Goals
- Athlete profile, goals, and constraints (authoritative input)

## Availability
- Editable weekly availability table and hours

## Events
- Planning events used for season planning (Type A/B/C + Priority rank, event type, time limits)
- A-events must be spaced at least 12 weeks apart

## Logistics
- Context events (travel, work constraints, non-A/B/C events)
- Event IDs are generated on save; status/impact use uppercase enums.

## Historic Data
- Yearly activity summary derived from full-year Intervals data
- Refresh triggers the Intervals pipeline to recompute the yearly summary
- Yearly activity summary table (activities, moving time, km, kJ/year, kJ/activity, kJ/hour)

## Zones
- Zone model view

## KPI Profile
- Select + view KPI profile

## Data Operations
- Backup/restore actions (see `doc/runbooks/data_ops.md`)
