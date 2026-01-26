# HOW_TO_PLAN.md

Version: 2.1  
Status: Updated  
Last-Updated: 2026-01-22

---

## Quickstart (1-page)

1) Create `season_brief_yyyy.md`.  
2) Select a `kpi_profile_des_*.json`, copy it to `var/athletes/<athlete_id>/latest/`, and rename to `kpi_profile.json`.  
3) Update `events.md`.  
4) Run **Season-Scenario-Agent** (generates `season_scenarios`).  
5) Run **Macro** (Mode A uses selected scenario).  
6) Run **Meso** -> `block_governance_yyyy-ww--yyyy-ww.json` + `block_execution_arch_yyyy-ww--yyyy-ww.json`.  
7) Run **Micro** -> `workouts_plan_yyyy-ww.json`.  
8) Run **Workout-Builder** -> `intervals_workouts_yyyy-ww.json`.  
9) Post workouts: `python scripts/data_pipeline/post_workout.py`.  
10) Run data pipeline: `python -m rps.main parse-intervals`.  
11) Validate outputs: `python scripts/validate_outputs.py`.  
12) Run **Performance-Analyst** -> `des_analysis_report_yyyy-ww.json`.  

Macro changes are rare (months). Meso every block. Micro weekly. Analysis weekly.

Place `season_brief_yyyy.md` and `events.md` under:

```
var/athletes/<athlete_id>/inputs/
```

Templates (copy and fill):

- `knowledge/_shared/sources/templates/season_brief_yyyy_template.md`
- `knowledge/_shared/sources/templates/events_template.md`

Place the selected KPI profile at:

```
var/athletes/<athlete_id>/latest/kpi_profile.json
```

Predefined KPI profiles live under `kpi_profiles/` at repo root.

Macro Mode A CLI (two-step, scenario generation via Season-Scenario-Agent):

```bash
python3 scripts/macro_mode_a.py scenarios \
  --year 2026 \
  --week 6 \
  --run-id macro_scenarios_2026_w06
```

This stores `season_scenarios_yyyy-ww--yyyy-ww.json` under `data/plans/macro/` and
writes the human-readable scenario dialogue to `.cache/macro_scenarios/`.

Select scenario (stores `season_scenario_selection`):

```bash
python3 scripts/macro_mode_a.py select \
  --year 2026 \
  --week 6 \
  --run-id macro_select_2026_w06 \
  --scenario A \
  --scenario-run-id macro_scenarios_2026_w06
```

Macro overview (scenario optional if selection exists):

```bash
python3 scripts/macro_mode_a.py overview \
  --year 2026 \
  --week 6 \
  --run-id macro_overview_2026_w06 \
  --scenario-run-id macro_scenarios_2026_w06
```

Optional KPI moving-time rate band override (affects kJ corridor derivation):

```bash
python3 scripts/macro_mode_a.py overview \
  --year 2026 \
  --week 6 \
  --run-id macro_overview_2026_w06 \
  --scenario-run-id macro_scenarios_2026_w06 \
  --moving-time-rate-band fast_competitive
```

Available bands are read from the KPI profile (`data.durability.moving_time_rate_guidance.bands`):
`brevet_ultra_sustainable`, `fast_competitive`, `top_record_oriented`.
The override selects the W/kg and kJ/kg/h window used to derive weekly planned_Load_kJ corridors.

```bash
python3 scripts/macro_mode_a.py overview \
  --year 2026 \
  --week 6 \
  --run-id macro_overview_2026_w06 \
  --scenario-run-id macro_scenarios_2026_w06
```

Macro, Meso, Micro cycles (concrete CLI):

```bash
# Macro cycle (Mode A, two-step)
python3 scripts/macro_mode_a.py scenarios \
  --year 2026 \
  --week 6 \
  --run-id macro_scenarios_2026_w06 \
  --athlete ath_001

python3 scripts/macro_mode_a.py overview \
  --year 2026 \
  --week 6 \
  --run-id macro_overview_2026_w06 \
  --scenario-run-id macro_scenarios_2026_w06 \
  --athlete ath_001
```

```bash
# Meso cycle (target ISO week = 2026-06)
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent meso_architect \
  --athlete ath_001 \
  --task CREATE_BLOCK_GOVERNANCE CREATE_BLOCK_EXECUTION_ARCH \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06). Create block_governance and block_execution_arch for the block covering ISO week 2026-06."
```

```bash
# Micro cycle (target ISO week = 2026-06)
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent micro_planner \
  --athlete ath_001 \
  --task CREATE_WORKOUTS_PLAN \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06). Create workouts_plan for ISO week 2026-06."
```

```bash
# Workout-Builder (target ISO week = 2026-06)
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent workout_builder \
  --athlete ath_001 \
  --task CREATE_INTERVALS_WORKOUTS_EXPORT \
  --text "Convert workouts_plan into Intervals.icu workouts JSON for ISO week 2026-06."
```

```bash
# Performance-Analyst (target ISO week = 2026-06)
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent performance_analysis \
  --athlete ath_001 \
  --task CREATE_DES_ANALYSIS_REPORT \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06). Create des_analysis_report for ISO week 2026-06."
```

Note: `run-agent` defaults to strict tool mode for JSON-producing agents. Use `--non-strict` only for text-only outputs.

---

## 1. Overview

This guide explains the planning sequence, artefacts, and cadence.

**Governance and cycles**
- **Season-Scenario**: generates advisory A/B/C scenarios from the season brief.
- **Macro**: long-horizon intent (8-32 weeks), phases, load corridors.
- **Meso**: phase-aligned blocks (default 4 weeks).
- **Micro**: weekly plan and sessions.
- **Workout-Builder**: deterministic conversion to Intervals.icu JSON.
- **Performance-Analyst**: diagnostic report (advisory).
- **Data Pipeline**: factual activity data (actual + trend).

**Artefact types**
- **Binding**: must be followed (macro, governance, execution arch, workouts plan).
- **Informational**: context only (season_scenarios, events, previews).
- **Advisory**: analysis report (macro may use to adjust later).

**Formats**
- Agent artefacts are JSON and validated by schema.
- User inputs remain Markdown (`season_brief_yyyy.md`, `events.md`).

---

## 2. Planning cycles and cadence

### 2.1 Cadence summary

- Athlete writes season brief first (macro input).
- Macro: when goals or A/B events change.
- Meso: every block (default 4 weeks).
- Micro: weekly.
- Analysis: weekly after data pipeline outputs exist.

### 2.2 Overview diagram

```mermaid
flowchart TD
  SB[season_brief_yyyy.md] --> SS[Season-Scenario]
  KP[kpi_profile_des_*.json] --> SS
  SS --> SC[season_scenarios_yyyy-ww--yyyy-ww.json]
  SC -. advisory .-> MA[Macro cycle]
  KP --> MA
  EV[events.md] -. info .-> SS
  EV -. info .-> MA

  MA --> MO[macro_overview_yyyy-ww--yyyy-ww.json]
  MA -. optional .-> MMFF[macro_meso_feed_forward_yyyy-ww.json]

  MO --> ME[Meso cycle]
  MMFF -. optional .-> ME

  ME --> BG[block_governance_yyyy-ww--yyyy-ww.json]
  ME --> BEA[block_execution_arch_yyyy-ww--yyyy-ww.json]
  ME -. optional .-> BFF[block_feed_forward_yyyy-ww.json]

  BG --> MI[Micro cycle]
  BEA --> MI
  BFF -. optional .-> MI

  MI --> WP[workouts_plan_yyyy-ww.json]
  WP --> WB[Workout-Builder]
  WB --> WJ[intervals_workouts_yyyy-ww.json]
  WJ --> POST[post_workout.py] --> IC[Intervals.icu]

  IC --> EXP[parse-intervals]
  EXP --> AA[activities_actual_yyyy-ww.json]
  EXP --> AT[activities_trend_yyyy-ww.json]
  AA --> VA[validate_outputs.py]
  AT --> VA

  AA --> PA[Performance-Analyst]
  AT --> PA
  PA --> DR[des_analysis_report_yyyy-ww.json]
  DR -. advisory .-> MA
```

---

## 3. Macro vs Meso boundaries

- `macro_overview` defines **phases** with `iso_week_range`.
- Macro must not define meso blocks.
- Meso block ranges are derived **inside** a macro phase.

Agents resolve the phase and block range internally via workspace tools
(no user prompt hints required):

- `workspace_get_block_context({ "year": YYYY, "week": WW })`

---

## 4. Agent modes (summary)

### Macro-Planner
- Create or update macro overview.
- Optional feed-forward when a block needs explicit guidance.

### Meso-Architect
- Create block governance + execution architecture.
- Optional preview and feed-forward when requested.

### Micro-Planner
- Always outputs one `workouts_plan` per target week.

### Workout-Builder
- Deterministic conversion only.

### Performance-Analyst
- Diagnostic only; advisory report.

---

## 5. Common pitfalls

- Do not create meso blocks in Macro.
- Always set `meta.iso_week` or `meta.iso_week_range`.
- Ensure `latest/` reflects the current version for downstream agents.

---

## End
