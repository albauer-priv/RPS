# HOW_TO_PLAN.md

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20

---

## Quickstart (1-page)

1) Create `season_brief_yyyy.md`.  
2) Select or create `kpi_profile_des_*.json`.  
3) Update `events.md`.  
4) Run **Macro** -> `macro_overview_yyyy-ww--yyyy-ww.json`.  
5) Run **Meso** -> `block_governance_yyyy-ww--yyyy-ww.json` + `block_execution_arch_yyyy-ww--yyyy-ww.json`.  
6) Run **Micro** -> `workouts_plan_yyyy-ww.json`.  
7) Run **Workout-Builder** -> `intervals_workouts_yyyy-ww.json`.  
8) Post workouts: `python scripts/data_pipeline/post_workout.py`.  
9) Run data pipeline: `python scripts/data_pipeline/get_intervals_data.py`.  
10) Validate outputs: `python scripts/validate_outputs.py`.  
11) Run **Performance-Analyst** -> `des_analysis_report_yyyy-ww.json`.  

Macro changes are rare (months). Meso every block. Micro weekly. Analysis weekly.

---

## 1. Overview

This guide explains the planning sequence, artefacts, and cadence.

**Governance and cycles**
- **Macro**: long-horizon intent (8-32 weeks), phases, load corridors.
- **Meso**: phase-aligned blocks (default 4 weeks).
- **Micro**: weekly plan and sessions.
- **Workout-Builder**: deterministic conversion to Intervals.icu JSON.
- **Performance-Analyst**: diagnostic report (advisory).
- **Data Pipeline**: factual activity data (actual + trend).

**Artefact types**
- **Binding**: must be followed (macro, governance, execution arch, workouts plan).
- **Informational**: context only (events, previews).
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
  SB[season_brief_yyyy.md] --> MA[Macro cycle]
  KP[kpi_profile_des_*.json] --> MA
  EV[events.md] -. info .-> MA

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

  IC --> EXP[get_intervals_data.py]
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

Use the workspace tools to resolve the phase and block range when needed:

- `workspace_resolve_macro_phase(year, week)`
- `workspace_resolve_block_range(year, week, block_len=4)`

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
