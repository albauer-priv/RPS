---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-10
Owner: Architecture
---
# Data Pipeline

Version: 2.0  
Status: Updated  
Last-Updated: 2026-02-10

---

## Purpose

The data pipeline fetches factual activity data from Intervals.icu and produces:

- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `historical_baseline_yyyymmdd_hhmmss.json` (yearly activity summary + baseline metrics)

Outputs are stored under:

- `var/athletes/<athlete_id>/data/`
- mirrored into `var/athletes/<athlete_id>/latest/`

Parquet caches are written alongside CSV/JSON outputs and are **non-canonical**.

---

## Entry Points

### Fetch + Compile + Validate

```bash
PYTHONPATH=src python3 src/rps/data_pipeline/intervals_data.py --year 2026 --week 6
PYTHONPATH=src python3 scripts/validate_outputs.py --year 2026 --week 6
```

With an explicit athlete id:

```bash
PYTHONPATH=src python3 src/rps/data_pipeline/intervals_data.py --year 2026 --week 6 --athlete ath_001
PYTHONPATH=src python3 scripts/validate_outputs.py --year 2026 --week 6 --athlete ath_001
```

---

## Defaults

If no range is provided, the pipeline exports the **last 24 complete weeks**
ending at the most recent completed week. If the export day is Sunday, the
current week is treated as complete.

The pipeline also compiles historical baseline summaries for the most recent
N years (default 3, configurable via `--historical-years`).

Historical baseline aggregation uses the most recent N calendar years
(default 3, configurable via `--historical-years` or `RPS_HISTORICAL_YEARS`).

---

## Inputs

- Intervals.icu API access (`ATHLETE_ID`, `API_KEY`, `BASE_URL` in `.env`)
- Planned workouts are posted from the UI (Plan → Workouts).

---

## Outputs

Per ISO week:

- `activities_actual_yyyy-ww.json` + `.csv`
- `activities_trend_yyyy-ww.json` + `.csv`
- `.parquet` cache mirrors for both artefacts

Per run:

- `historical_baseline_yyyymmdd_hhmmss.json` in `data/analysis/`

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
