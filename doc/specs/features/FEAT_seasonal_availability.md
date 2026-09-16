---
Status: Implemented
Version: 1.0
Last-Updated: 2026-09-16
---
# FEAT_seasonal_availability

## Problem

The `AVAILABILITY` artifact captures weekly training availability as a static table (per-weekday
hours). There is no concept of seasonal variation: the planning system cannot distinguish between
summer outdoor riding (up to 8h weekend) and winter indoor trainer riding (practical max 3–4h
weekend on trainer). Season planning currently applies the same load corridors in November/December
as in March/April, ignoring that indoor sessions have different physical and psychological
characteristics.

The planning agents read `availability.json` but receive no signal about which months are
predominantly indoor vs. outdoor, and cannot adjust phase characteristics (load ceilings, intensity
density, session duration) accordingly.

## Goal

1. Extend the `AVAILABILITY` schema with an optional `seasonal_context` block that captures:
   - `outdoor_season_months`: list of months (ISO 1–12) when outdoor riding is the primary mode.
   - `indoor_dominant_months`: list of months when indoor trainer is primary.
   - `indoor_weekend_max_hours`: practical maximum session hours on the trainer (e.g. 4.0).
   - `outdoor_weekend_max_hours`: practical maximum outdoor session hours (e.g. 8.0).
   - `notes`: free-text seasonal context.
2. Surface this data in the Streamlit Availability editor (new UI section).
3. Inject `seasonal_context` into the Season orchestrator's `guardrail_runtime_context` so
   scenario generation and macrocycle architecture can read it.
4. Update the scenario-generation and macrocycle-architecture skills to:
   - Recognize winter/indoor phases and describe lower practical load ceilings.
   - Avoid setting the same weekend-long-ride load bands in December as in April.

## Non-Goals

- No change to how weekly `hours_min/typical/max` are computed. The existing aggregate values
  remain authoritative; `seasonal_context` is advisory shaping context only.
- No automatic re-computation of phase-load corridors. The planning agents use `seasonal_context`
  to shape narrative and phase-level intensity density descriptions; deterministic kJ bands remain
  in their responsible components.

## Changed Files

- `specs/schemas/availability.schema.json` — added optional `seasonal_context` object (new `$defs/seasonal_context` entry; `availability_data` references it).
- `src/rps/ui/pages/athlete_profile/availability.py` — new "Seasonal Context" UI section with outdoor/indoor month selectors and max-hours inputs.
- `src/rps/rendering/templates/availability.md.j2` — new section 5 renders `seasonal_context` fields.
- `src/rps/orchestrator/season_flow.py` — extracts `seasonal_context` from availability payload and passes it as a named key to `guardrail_runtime_context` in both `create_season_scenarios` and `create_season_plan`.
- `skills/season/scenario-generation/SKILL.md` — new "Seasonal availability context" section.
- `skills/season/macrocycle-architecture/SKILL.md` — new "Seasonal availability context" section.
