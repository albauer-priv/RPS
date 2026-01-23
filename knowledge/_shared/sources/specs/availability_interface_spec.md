---
Type: InterfaceSpecification
Interface-For: AVAILABILITY
Interface-ID: AvailabilityInterface
Version: 1.0

Scope: Shared
Authority: Binding

Inputs-From:
  - SeasonBriefInterface
Outputs-To:
  - Season-Scenario-Agent
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
---

# Availability Interface Specification

## 1) Purpose (Binding)
Normalize the Season Brief weekday availability table into a machine-readable
artefact that planners can use for load plausibility checks and daily constraints.

## 2) Required Meta (Binding)
The artefact MUST include a valid `meta` envelope (`artefact_meta.schema.json`) with:
- `artifact_type`: `AVAILABILITY`
- `schema_id`: `AvailabilityInterface`
- `schema_version`: `1.0`
- `authority`: `Binding`
- `owner_agent`: `Data-Pipeline`
- `iso_week`, `iso_week_range`, `temporal_scope`, `trace_upstream`

## 3) Required Data Fields (Binding)
`data` MUST include:
- `season_brief_ref` (string; source Season Brief filename or ID)
- `availability_table` (array of 7 entries; one per weekday)
- `weekly_hours` (object: `min`, `typical`, `max`)
- `fixed_rest_days` (array of weekday enums)
- `notes` (string; may be empty)

### 3.1 Availability Table Entry (Binding)
Each entry MUST include:
- `weekday`: `Mon|Tue|Wed|Thu|Fri|Sat|Sun`
- `hours_min` (number >= 0)
- `hours_typical` (number >= 0)
- `hours_max` (number >= 0)
- `indoor_possible` (boolean)
- `travel_risk` (`low|med|high`)
- `locked` (boolean; true for fixed rest days)
- `source_hours_text` (string; raw cell text)
- `source_indoor_text` (string; raw cell text)
- `source_travel_text` (string; raw cell text)

### 3.2 Weekly Hours (Binding)
`weekly_hours` MUST be the sum of daily entries:
- `min` = sum of `hours_min`
- `typical` = sum of `hours_typical`
- `max` = sum of `hours_max`

## 4) Parsing Rules (Binding)
- The availability table MUST be parsed from the Season Brief table
  “Weekly availability table”.
- Fixed rest days MUST be marked as `0 h / locked` in the Season Brief and
  mapped to `locked=true` in the artefact.
- `temporal_scope.from` SHOULD default to the generation date if the Season Brief
  validity range is missing or in the past; `temporal_scope.to` SHOULD default to
  the end of the season year.
- If any day is missing or cannot be parsed, the parser MUST STOP.

## 5) Forbidden (Binding)
- Do NOT invent availability data.
- Do NOT infer missing days.
- Do NOT smooth or adjust values beyond numeric parsing of the provided table.

## 6) Traceability (Binding)
`trace_upstream` MUST reference the Season Brief source.

## End of Availability Interface Specification v1.0
