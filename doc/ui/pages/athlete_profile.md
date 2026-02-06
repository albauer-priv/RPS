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
- Hours use 0.5h increments; travel risk uses uppercase enums (LOW/MED/HIGH).
- Fixed rest days lock the weekday row and force 0h on save.

## Events
- Planning events used for season planning (Type A/B/C + Priority rank, event type, time limits)
- A-events must be spaced at least 12 weeks apart
- Date must be YYYY-MM-DD; ranks must be unique within each priority (1–3)
- Events are sorted newest-first in the table and storage.

## Logistics
- Context events (travel, work constraints, non-A/B/C events)
- Event IDs are generated on save; status/impact use uppercase enums.
- Date required (YYYY-MM-DD); description required; duplicate dates blocked
- Events are sorted by date for display and storage

## Historic Data
- Yearly activity summary derived from full-year Intervals data
- Refresh triggers the Intervals pipeline to recompute the yearly summary
- Yearly activity summary table (activities, moving time, km, kJ/year, kJ/activity, kJ/hour)
- Last refresh timestamp shown from baseline metadata
- Yearly summary rows are sorted newest-first.

## Zones
- Zone model view

## KPI Profile
- Select + view KPI profile

## Data Operations
- Backup/restore actions (see `doc/runbooks/data_ops.md`)
