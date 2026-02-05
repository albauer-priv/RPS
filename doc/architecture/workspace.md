---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Architecture
---
# Workspace

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20

---

## Purpose

The workspace is the local, append-only storage for all artefacts and data
related to an athlete. It lives under `var/athletes/<athlete_id>/` and is
gitignored.

---

## Layout

```
var/athletes/<athlete_id>/
  inputs/
  data/
    plans/season/
    plans/phase/
    plans/week/
    analysis/
    exports/
    YYYY/WW/        # data pipeline snapshots (CSV + JSON)
  latest/
  index.json
  logs/
  runs/
    queue/{pending,active,done,failed}/
```

---

## Rules

- Every write creates a **versioned file**.
- `latest/` holds the most recent version per artefact type.
- `index.json` tracks version metadata for routing and lookups.
- No edits in place; new versions are appended.
- User inputs (athlete_profile, planning_events, logistics, availability) live under `inputs/` and are read via `workspace_get_input`.

Templates are available under:

- `knowledge/_shared/sources/templates/athlete_profile_template.md`
- `knowledge/_shared/sources/templates/planning_events_template.md`
- `knowledge/_shared/sources/templates/logistics_template.md`

---

## Index

`index.json` stores:

- version keys
- paths
- run IDs
- producer agent
- ISO week or ISO week range

---

## Directory Ownership & Artefacts

| Directory | Owner | Typical artefacts |
| --- | --- | --- |
| `inputs/` | User / operator | `athlete_profile_*.json`, `planning_events_*.json`, `logistics_*.json`, `availability_*.json`, `kpi_profile_*.json` |
| `data/plans/season/` | Season-Scenario-Agent, Season-Planner | `season_scenarios_*`, `season_scenario_selection_*`, `season_plan_*`, `season_phase_feed_forward_*` |
| `data/plans/phase/` | Phase-Architect (plus Data-Pipeline for `zone_model_*`) | `phase_guardrails_*`, `phase_structure_*`, `phase_preview_*`, `phase_feed_forward_*`, `zone_model_*` |
| `data/plans/week/` | Week-Planner | `week_plan_*` |
| `data/analysis/` | Performance-Analyst | `des_analysis_report_*` |
| `data/exports/` | Workout-Builder | `workouts_*` |
| `data/YYYY/WW/` | Data Pipeline | `activities_actual_*`, `activities_trend_*`, `availability_*`, `wellness_*` (+ CSV mirrors) |
| `latest/` | System | Latest copy of each artefact type (mirrors versioned writes) |
| `logs/` | System | Single `rps.log` (rotated) + log sidecars |
| `runs/` | System | Run records (`run.json`, `steps.json`, `events.jsonl`) + queue state |
| `rendered/` | renderer | Markdown sidecars derived from JSON artefacts |

---

## Rendering (Optional)

Use `rps.rendering.renderer.render_json_sidecar` to generate human-readable
sidecars from JSON artefacts. These are informational and never authoritative.

---

## Cleanup

If workspace grows large:

- archive old versions in `data/plans/`, `data/analysis/`, and `data/exports/`
- keep `latest/` intact
- avoid deleting files referenced in `index.json`

---

## End
