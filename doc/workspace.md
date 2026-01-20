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
  plans/macro/
  plans/meso/
  plans/micro/
  workouts/
  analysis/
  exports/
  data/
  latest/
  index.json
```

---

## Rules

- Every write creates a **versioned file**.
- `latest/` holds the most recent version per artefact type.
- `index.json` tracks version metadata for routing and lookups.
- No edits in place; new versions are appended.
- User inputs (season brief, events) live under `inputs/` and are read via `workspace_get_input`.

Templates are available under:

- `knowledge/_shared/sources/templates/season_brief_yyyy_template.md`
- `knowledge/_shared/sources/templates/events_template.md`

---

## Index

`index.json` stores:

- version keys
- paths
- run IDs
- producer agent
- ISO week or ISO week range

---

## Rendering (Optional)

Use `scripts/artefact_renderer.py` to generate human-readable sidecars from
JSON artefacts. These are informational and never authoritative.

---

## Cleanup

If workspace grows large:

- archive old versions in `plans/`, `analysis/`, and `data/`
- keep `latest/` intact
- avoid deleting files referenced in `index.json`

---

## End
