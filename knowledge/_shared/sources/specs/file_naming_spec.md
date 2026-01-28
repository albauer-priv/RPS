---
Type: Specification
Specification-For: FILE_NAMING
Specification-ID: FileNamingSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Data-Pipeline
  - Performance-Analyst
  - Season-Planner
  - Phase-Architect
  - Week-Planner
  - Workout-Builder

Notes: >
  Defines mandatory filename patterns and allowed characters for all artefacts.
  Used for linting, traceability, and CI validation.
---

# File Naming Specification

## 1. Purpose
Define consistent filenames for all artefacts to support:
- predictable interfaces
- bundling
- linting
- traceability

## 2. Common Tokens
- `ww` = ISO week number (01–53), always two digits.
- `yyyy` = four-digit year.
- `yyyy-ww--yyyy-ww` = phase range token for phases (inclusive).

## 3. Required Filename Patterns (Normative)

### User / Context (Human Input)
- `season_brief_yyyy.md`
- `events.md`

### User / Context (Structured JSON)
- `kpi_profile_des_<event>_<distance_or_duration>_<athlete_class>.json`

### Data Pipeline
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `availability_yyyy-ww.json`
- `wellness_yyyy-ww.json`

### Season-Planner
- `season_plan_yyyy-ww--yyyy-ww.json` (range may be 8–32 weeks)
- `season_phase_feed_forward_yyyy-ww.json`

### Phase-Architect
- `phase_guardrails_yyyy-ww--yyyy-ww.json`
- `phase_feed_forward_yyyy-ww.json`
- `phase_structure_yyyy-ww--yyyy-ww.json`
- `phase_preview_yyyy-ww--yyyy-ww.json`
- `zone_model_power_<FTP>W.json`

### Week-Planner
- `week_plan_yyyy-ww.json`

### Workout-Builder (post-workout export)
- `workouts_yyyy-ww.json`

### Performance-Analyst
- `des_analysis_report_yyyy-ww.json`

### KPI Profiles (Policy Specs)
- `kpi_profile_des_<event>_<distance_or_duration>_<athlete_class>.json`
  - Distance tokens use `_km` (example: `200_400_km`).
  - Duration tokens use `h` or `d` (examples: `4-20h`, `3-10d`, `5d`).
  - `multiday` is allowed for events defined primarily by duration rather than range.
  - Examples: `kpi_profile_des_brevet_200_400_km_masters.json`,
    `kpi_profile_des_brevet_1200_km_non_masters.json`,
    `kpi_profile_des_bikepacking_multiday_masters.json`,
    `kpi_profile_des_gravel_4-20h_non_masters.json`

### Optional Human-Readable Sidecars (HITL)
For any JSON artefact, an optional human-readable sidecar is allowed:
- `<basename>.rendered.md`

Examples:
- `phase_guardrails_2026-01--2026-04.rendered.md`
- `activities_actual_2026-01.rendered.md`

Sidecars are informational only and MUST NOT be used as agent inputs.

## 4. Character Rules
- Lowercase letters, digits, underscore, dash, plus are allowed.
- No spaces.
- File extension: `.json` for agent-generated/consumed artefacts.
- File extension: `.md` for human input and optional sidecars.

## 5. Enforcement
Any artefact not matching these rules is invalid.
