# HOW_TO_PLAN.md

Version: 2.3
Status: Updated
Last-Updated: 2026-01-30

---

## Quickstart (UI-first)

1) Add inputs in `var/athletes/<athlete_id>/inputs/`:
   - `season_brief_yyyy.md`
   - `events.md`
2) Copy a KPI profile to `var/athletes/<athlete_id>/latest/kpi_profile.json`.
3) Ensure Intervals data is fresh (zone model + wellness + activities) via
   `python -m rps.main parse-intervals` or UI auto-refresh.
4) Open the **Plan Hub** and confirm Scope (athlete, ISO year/week, phase).
5) Run **Season Scenarios** if missing.
6) Select a scenario on **Plan -> Season** (manual decision).
7) Run **Plan this Week** from Plan Hub (or run scoped steps).
8) Optional: **Post to Intervals** (commit step) after Export.
9) Optional: **Performance Report** (advisory) once activities are available.

Plan Hub is the default orchestration surface. Season/Phase/Week pages remain
available for manual, step-by-step runs.

---

## 1. Screens and Responsibilities

### Home
- Marketing summary + system state table.
- Links into plan/performance pages.

### Plan Hub (primary orchestration)
- Scope panel in header (athlete, ISO year/week, phase).
- Readiness checklist with reasons + fix CTAs.
- Run Planning with Orchestrated or Scoped runs.
- Run Execution table (steps, statuses, outputs, events).
- Latest Outputs + Run History.
- Optional **Post to Intervals after export** toggle.

### Plan -> Season
- Create scenarios (agent).
- Manual scenario selection (user decision).
- Create Season Plan.

### Plan -> Phase
- View phase guardrails/structure/preview.

### Plan -> Week
- Weekly agenda + per-day expanders.
- Actions: Plan Week, Create Report, Post to Intervals.
- Posting status (unposted/conflicts) + conflict resolution.

### Plan -> WoW
- Intervals export view (per-day expanders, descriptions).

---

## 2. Planning Flow (Conceptual)

```mermaid
flowchart TD
  SB[season_brief_yyyy.md] --> SS[Season-Scenario-Agent]
  KP[kpi_profile.json] --> SS
  SS --> SC[season_scenarios]
  SC -. advisory .-> SEASON[Season-Planner]
  EV[events.md] -. info .-> SS
  EV -. info .-> SEASON

  SEASON --> SP[season_plan]
  SEASON -. optional .-> SPFF[season_phase_feed_forward]

  SP --> PHASE[Phase-Architect]
  SPFF -. optional .-> PHASE
  PHASE --> PG[phase_guardrails]
  PHASE --> PS[phase_structure]
  PHASE -. optional .-> PP[phase_preview]

  PG --> WEEK[Week-Planner]
  PS --> WEEK
  WEEK --> WP[week_plan]
  WP --> WB[Workout-Builder]
  WB --> WJ[workouts_yyyy-ww.json]
  WJ --> POST[post_to_intervals (commit)]

  DP[parse-intervals] --> AA[activities_actual]
  DP --> AT[activities_trend]
  DP --> ZM[zone_model]
  DP --> WL[wellness]
  AA --> PA[Performance-Analyst]
  AT --> PA
  PA --> DR[des_analysis_report]
```

---

## 3. Readiness Rules (Plan Hub)

Plan Hub maps readiness to execution steps. Steps become QUEUED if missing or
stale, SKIPPED if fresh, and BLOCKED when upstream fails.

### Required chain (core)
- Season Scenarios -> Selected Scenario -> Season Plan
- Season Plan -> Phase Guardrails + Phase Structure
- Phase Guardrails/Structure -> Week Plan
- Week Plan -> Export Workouts

### Optional chain
- Phase Preview (optional)
- Performance Report (advisory)
- Post to Intervals (commit step; optional toggle)

Scenario selection is always manual; Plan Hub will stop and require user action
if selection is missing.

---

## 4. Run Execution Model

Each run stores:
- `runs/<run_id>/run.json`
- `runs/<run_id>/steps.json`
- `runs/<run_id>/events.jsonl`

Plan Hub displays step status, outputs, and events. Runs are append-only; failed
runs can be superseded by a new run.

Statuses:
- `QUEUED`, `RUNNING`, `DONE`, `FAILED`, `SKIPPED`, `BLOCKED`, `SUPERSEDED`

---

## 5. Intervals Posting (Commit Step)

Export is a build step. Posting is a commit step.

Idempotency is enforced by receipts:
- `receipts/post_to_intervals/<athlete>/<yyyy-Www>/<uid>.json`

Behavior:
- If receipt exists and payload hash matches -> SKIP
- If hash changed -> conflict (manual resolution)

Week page shows unposted count + conflicts and provides a manual resolution
button. Plan Hub offers a toggle to post after export.

---

## 6. CLI (Optional)

### Plan week (orchestrated)

```bash
PYTHONPATH=src python3 -m rps.main plan-week \
  --year 2026 \
  --week 6 \
  --run-id run_2026_06
```

### Agent tasks

```bash
# Season scenarios
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent season_scenario \
  --task CREATE_SEASON_SCENARIOS \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06). Generate pre-decision scenarios."
```

```bash
# Scenario selection (manual choice logged)
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent season_scenario \
  --task CREATE_SEASON_SCENARIO_SELECTION \
  --text "Select Scenario A for ISO week 2026-06. Use latest SEASON_SCENARIOS."
```

```bash
# Season plan
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent season_planner \
  --task CREATE_SEASON_PLAN \
  --text "Scenario A. Create SEASON_PLAN for ISO week 2026-06."
```

```bash
# Phase
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent phase_architect \
  --task CREATE_PHASE_GUARDRAILS CREATE_PHASE_STRUCTURE \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06)."
```

```bash
# Week
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent week_planner \
  --task CREATE_WEEK_PLAN \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06)."
```

```bash
# Export workouts
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent workout_builder \
  --task CREATE_INTERVALS_WORKOUTS_EXPORT \
  --text "Convert week_plan into Intervals.icu workouts JSON for ISO week 2026-06."
```

```bash
# Performance report
PYTHONPATH=src python3 -m rps.main run-agent \
  --agent performance_analysis \
  --task CREATE_DES_ANALYSIS_REPORT \
  --text "Target ISO week: year=2026, week=6 (ISO 2026-06)."
```

---

## 7. Notes

- Inputs are Markdown; artifacts are JSON validated by schema.
- Phase artifacts are derived from season phase ranges (no manual range guessing).
- Exports use `workouts_yyyy-ww.json` version keys.
- Commit steps should be manual or explicitly toggled to avoid unintended side effects.

