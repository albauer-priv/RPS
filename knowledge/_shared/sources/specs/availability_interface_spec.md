---
Type: InterfaceSpecification
Interface-For: AVAILABILITY
Interface-ID: AvailabilityInterface
Version: 1.0

Scope: Shared
Authority: Binding

Inputs-From:
  - AthleteProfileInterface
  - (Legacy) SeasonBriefInterface (deprecated)
Outputs-To:
  - Season-Scenario-Agent
  - Season-Planner
  - Phase-Architect
  - Week-Planner
---

# Availability Interface Specification

## 1) Purpose (Binding)
Provide a user-managed availability artefact that planners can use for
load plausibility checks and daily constraints. Legacy Season Brief parsing
is supported only for backward compatibility.

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
- `source_type` (`manual|imported|season_brief`)
- `source_ref` (string; may be a UI run_id or legacy Season Brief ref)
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
Note: raw Season Brief source fields are no longer stored in the availability table.

### 3.2 Weekly Hours (Binding)
`weekly_hours` MUST be the sum of daily entries:
- `min` = sum of `hours_min`
- `typical` = sum of `hours_typical`
- `max` = sum of `hours_max`

## 4) Authoring / Parsing Rules (Binding)
- Manual entries MUST be provided by the user via the Availability UI.
- If `source_type=season_brief`, the availability table MUST be parsed from the
  Season Brief “Weekly availability table”.
- Fixed rest days MUST be marked as `0 h / locked` and mapped to `locked=true`.
- If any day is missing or cannot be parsed, the parser MUST STOP.

## 5) Forbidden (Binding)
- Do NOT invent availability data.
- Do NOT infer missing days.
- Do NOT smooth or adjust values beyond numeric parsing of the provided table.

## 6) Traceability (Binding)
- If `source_type=season_brief`, `trace_upstream` MUST reference the Season Brief.
- Otherwise, `trace_upstream` MAY be empty.

## End of Availability Interface Specification v1.0
