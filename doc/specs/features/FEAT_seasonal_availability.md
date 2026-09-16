---
Status: Planned
Version: 0.1
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

## Planned Files

- `src/rps/ui/pages/athlete_inputs/availability.py` (or equivalent) — new Streamlit form section
  for `seasonal_context`.
- `specs/schemas/availability.schema.json` — add optional `seasonal_context` object.
- `src/rps/workspace/models.py` (or Availability model) — typed `SeasonalContext` dataclass/model.
- `src/rps/orchestrator/season_flow.py` — inject `seasonal_context` into `guardrail_runtime_context`.
- `skills/season/scenario-generation/SKILL.md` — read `seasonal_context`; use `indoor_dominant_months`
  to describe winter phases with lower volume ceiling and higher intensity density.
- `skills/season/macrocycle-architecture/SKILL.md` — use `seasonal_context` to flag which phase
  slots fall inside indoor-dominant months and adjust phase narrative accordingly.
