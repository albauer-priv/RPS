# Artefact Renderer

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20

---

## 1. Purpose

The artefact renderer converts JSON artifacts into human‑readable Markdown
sidecars for review and QA. The sidecars are **informational only** and never
replace the JSON source of truth.

---

## 2. Location

- Script: `scripts/artefact_renderer.py`
- Templates: `scripts/renderers/*.md.j2`

---

## 3. Usage

```bash
python3 scripts/artefact_renderer.py path/to/artefact.json
```

Optional flags:

- `--out <path>`: write to a specific output file
- `--validate`: validate against JSON schema before rendering
- `--schema-dir <dir>`: override schema directory (default: `SCHEMA_DIR` or `./schemas`)

---

## 4. Supported Artifacts

The renderer supports the following artifact types (meta.artifact_type):

- `SEASON_PLAN`
- `PHASE_GUARDRAILS`
- `PHASE_STRUCTURE`
- `PHASE_PREVIEW`
- `BLOCK_FEED_FORWARD`
- `MACRO_MESO_FEED_FORWARD`
- `DES_ANALYSIS_REPORT`
- `ACTIVITIES_ACTUAL`
- `ACTIVITIES_TREND`
- `ZONE_MODEL`
- `WEEK_PLAN`
- `KPI_PROFILE`

---

## 5. Notes

- Default output location (if `--out` is omitted):
  - `var/athletes/<ATHLETE_ID>/rendered/<filename>.md`
  - `ATHLETE_ID` is loaded from `.env` (Intervals.icu athlete ID).
- Artefacts saved via the runner are auto-rendered using this script.
- If `meta.trace_upstream` is a list of strings, it is rendered directly.
- If `--validate` is enabled, schema validation occurs before rendering.
- Raw payload artifacts (e.g., `INTERVALS_WORKOUTS`) are not rendered.

---

## End
