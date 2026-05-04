---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-04
Owner: UI
---
# Analyse → Feed Forward

## Purpose
- Generate feed-forward guidance from a completed week.

## Actions
- Run DES Report (if needed)
- Run Feed Forward

## Artefact Semantics

- `DES_ANALYSIS_REPORT` is selected-week scoped and uses the selected completed ISO week as its version key.
- `SEASON_PHASE_FEED_FORWARD` is also selected-week scoped and uses that same completed ISO week as its version key.
- `PHASE_FEED_FORWARD` is not keyed by the selected completed week. It is keyed by the first ISO week of the affected phase range.
- Example:
  - selected completed week: `2026-18`
  - affected phase range: `2026-17--2026-19`
  - stored artefacts:
    - `des_analysis_report_2026-18__...json`
    - `season_phase_feed_forward_2026-18.json`
    - `phase_feed_forward_2026-17.json`

## UI Note

- The Feed Forward page should treat this as expected behavior and must not flag the differing `PHASE_FEED_FORWARD` key as an inconsistency as long as its `meta.iso_week_range` matches the selected phase.
