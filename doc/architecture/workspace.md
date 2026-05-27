---
Version: 1.2
Status: Updated
Last-Updated: 2026-05-27
Owner: Architecture
---
# Workspace

## Purpose

The workspace is the local, append-only storage for all artefacts and data
related to an athlete. It lives under `runtime/athletes/<athlete_id>/` and is
gitignored.

---

## Layout

```
runtime/athletes/<athlete_id>/
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
- `WEEK_PLAN` writes pass an additional guarded consistency layer before save:
  - deterministic normalization of linked workout duration / agenda duration / agenda mechanical `planned_kj` where derivable
  - cross-field validation for agenda/workout/summary coherence
  - export is blocked if the normalized `WEEK_PLAN` is still inconsistent
- Persisted artefact metadata is owned by the Runtime/Workspace layer:
  - writer agents provide domain `data` and optional trace hints
  - `GuardedValidatedStore` overwrites schema-critical `meta` fields before validation
  - final JSON Schema validation runs against the runtime-built envelope
  - stored `trace_*` entries preserve operational workspace keys in `version_key`

Templates are available under:

- [specs/knowledge/_shared/sources/templates/athlete_profile_template.md](specs/knowledge/_shared/sources/templates/athlete_profile_template.md)
- [specs/knowledge/_shared/sources/templates/planning_events_template.md](specs/knowledge/_shared/sources/templates/planning_events_template.md)
- [specs/knowledge/_shared/sources/templates/logistics_template.md](specs/knowledge/_shared/sources/templates/logistics_template.md)

---

## Index

`index.json` stores:

- version keys
- paths
- run IDs
- producer agent
- ISO week or ISO week range

The index and `latest/` pointers are based on the stored canonical metadata and
derived workspace `version_key`, not on agent-invented metadata.

---

## Directory Ownership & Artefacts

| Directory | Owner | Typical artefacts |
| --- | --- | --- |
| `inputs/` | User / operator | `athlete_profile_*.json`, `planning_events_*.json`, `logistics_*.json`, `availability_*.json`, `kpi_profile_*.json` |
| `data/plans/season/` | Season-Scenario-Agent, Season-Planner | `season_scenarios_*`, `season_scenario_selection_*`, `season_plan_*`, `season_phase_feed_forward_*` |
| `data/plans/phase/` | Phase-Architect (plus Data-Pipeline for `zone_model_*`) | `phase_guardrails_*`, `phase_structure_*`, `phase_preview_*`, `phase_feed_forward_*`, `zone_model_*` |
| `data/plans/week/` | Week-Planner | `week_plan_*` |
| `data/analysis/` | Performance-Analyst | `des_analysis_report_*` |
| `data/context/` | Orchestrator / derived memory | `athlete_state_snapshot_*`, `planning_context_snapshot_*`, `advisory_memory_*` |
| `data/exports/` | Workout Export | `workouts_*` |
| `data/YYYY/WW/` | Data Pipeline | `activities_actual_*`, `activities_trend_*`, `availability_*`, `wellness_*` (+ CSV mirrors) |
| `latest/` | System | Latest copy of each artefact type (mirrors versioned writes) |
| `logs/` | System | Single `rps.log` (rotated) + log sidecars |
| `runs/` | System | Run records (`run.json`, `steps.json`, `events.jsonl`) + queue state |
| `rendered/` | renderer | Markdown sidecars derived from JSON artefacts |

### Repo-Scoped Evidence Library

The evidence registry is intentionally **not** athlete-scoped workspace state.
It lives under:

- `skills/shared/durability-methodology/references/library/`

This registry stores the canonical evidence entries, generated study briefs, and
derived reference tables used by Coach / Season / Phase / Week evidence
surfaces.

Rules:

- The registry is repo-scoped and shared across athletes.
- `literature_refresh` writes status and stage events into the active athlete
  run store, but does not persist the registry under `runtime/athletes/`.
- Only `activation_status == active` evidence may surface in operative
  knowledge injection.
- During migration/backfill, `legacy_active` may remain visible in the library
  until re-curation completes, but it is transitional state rather than a new
  permanent workspace layer.

### Feed-Forward Keying Rules

- `season_phase_feed_forward_<iso_week>.json` is keyed by the selected completed source week.
- `phase_feed_forward_<iso_week>.json` is keyed by the first ISO week in its `meta.iso_week_range`.
- This asymmetry is intentional:
  - Season -> Phase feed-forward answers: "what follows from completed week X?"
  - Phase feed-forward answers: "what guidance applies to the phase that starts in week Y?"
- For example:
  - `season_phase_feed_forward_2026-18.json`
  - `phase_feed_forward_2026-17.json` with `meta.iso_week_range = 2026-17--2026-19`

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
