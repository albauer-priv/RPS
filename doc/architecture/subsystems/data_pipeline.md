---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-04
Owner: Architecture
---
# Data Pipeline

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20

---

## Purpose

The data pipeline fetches factual activity data from Intervals.icu and produces:

- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`

Outputs are stored under:

- `var/athletes/<athlete_id>/data/`
- mirrored into `var/athletes/<athlete_id>/latest/`

Parquet caches are written alongside CSV/JSON outputs and are **non-canonical**.

---

## Entry Points

### Fetch + Compile + Validate

```bash
python -m rps.main parse-intervals --year 2026 --week 6
python scripts/validate_outputs.py --year 2026 --week 6
```

With an explicit athlete id:

```bash
python -m rps.main parse-intervals --year 2026 --week 6 --athlete ath_001
python scripts/validate_outputs.py --year 2026 --week 6 --athlete ath_001
```

### Post planned workouts

```bash
python scripts/data_pipeline/post_workout.py \  # Deprecated; prefer Plan → Workouts UI
  --json var/athletes/<athlete_id>/latest/workouts.json
```

With an explicit athlete id:

```bash
python scripts/data_pipeline/post_workout.py --athlete ath_001  # Deprecated; prefer Plan → Workouts UI
```

---

## Defaults

If no range is provided, the pipeline exports the **last 24 complete weeks**
ending at the most recent completed week. If the export day is Sunday, the
current week is treated as complete.

---

## Inputs

- Intervals.icu API access (`ATHLETE_ID`, `API_KEY`, `BASE_URL` in `.env`)
- Optional planned workouts JSON for calendar posting

---

## Outputs

Per ISO week:

- `activities_actual_yyyy-ww.json` + `.csv`
- `activities_trend_yyyy-ww.json` + `.csv`
- `.parquet` cache mirrors for both artefacts

---

## Validation

Use `scripts/validate_outputs.py` to validate JSON outputs against schemas
in `schemas/`.

---

## Troubleshooting

- Ensure `ATHLETE_ID`, `API_KEY`, and `BASE_URL` are set.
- Check network access to `intervals.icu`.
- Run with a smaller date range if exports are too large.

---

## End
