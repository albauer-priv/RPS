---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Overview
---
# Artefact Flow

## 1. Flow Overview (End-to-End)

```mermaid
flowchart TD
  %% Actors / Components
  U[User]:::actor
  SS["Season Scenario Surface"]:::agent
  MA["Season Planning Runtime"]:::agent
  ME["Phase Planning Runtime"]:::agent
  MI["Week Planning Runtime"]:::agent
  WB["Local Workout Export"]:::component
  PA["Performance Report Runtime"]:::agent
  I["Intervals.icu"]:::external
  EXP["intervals_data.py"]:::script
  VAL["validate_outputs.py"]:::script
  POST["post_to_intervals (commit)"]:::script
  RCPT["post_receipts_yyyy-ww.json"]:::artefact

  %% Artefacts
  AP["athlete_profile_*.json"]:::artefact
  KP["kpi_profile_des_*.json"]:::artefact
  PE["planning_events_*.json"]:::artefact
  LG["logistics_*.json"]:::artefact
  AV["availability_yyyy-ww.json"]:::artefact
  SC["season_scenarios_yyyy-ww--yyyy-ww.json"]:::artefact
  SEL["season_scenario_selection_yyyy-ww.json"]:::artefact
  MO["season_plan_yyyy-ww--yyyy-ww.json"]:::artefact
  SPFF["season_phase_feed_forward_yyyy-ww.json"]:::artefact
  BG["phase_guardrails_yyyy-ww--yyyy-ww.json"]:::artefact
  BEA["phase_structure_yyyy-ww--yyyy-ww.json"]:::artefact
  BEP["phase_preview_yyyy-ww--yyyy-ww.json"]:::artefact
  BFF["phase_feed_forward_yyyy-ww.json"]:::artefact
  ZM["zone_model_power_<FTP>W.json"]:::artefact
  WP["week_plan_yyyy-ww.json"]:::artefact
  WJ["workouts_yyyy-ww.json"]:::artefact
  CAL["Planned Activities<br/>in Calendar"]:::artefact
  AA["activities_actual_yyyy-ww.json"]:::artefact
  AT["activities_trend_yyyy-ww.json"]:::artefact
  WL["wellness_yyyy-ww.json"]:::artefact
  DR["des_analysis_report_yyyy-ww.json"]:::artefact

  %% Planning chain
  U --> AP
  U --> AV
  AV --> SS
  U --> KP --> SS
  SS --> SC --> SEL --> MA
  KP --> MA
  KP --> PA
  U --> PE --> MA
  U --> LG --> MA
  PE -. info .-> SS
  LG -. info .-> SS
  AV --> MA

  MA --> MO --> ME
  MA -. optional .-> SPFF --> ME

  ME --> BG --> MI
  ME --> BEA --> MI
  ME -. explanatory .-> BEP
  ME -. optional .-> BFF --> MI
  ZM -. info .-> ME
  ZM -. info .-> MI
  AV -. info .-> ME
  AV -. info .-> MI

  MI --> WP --> WB
  WB --> WJ --> POST
  POST --> RCPT --> CAL --> I

  %% Data & analysis loop
  I --> EXP
  EXP --> AA
  EXP --> AT
  EXP --> ZM
  EXP --> WL
  AA --> VAL
  AT --> VAL
  VAL -. validates .-> AA
  VAL -. validates .-> AT
  BG --> PA
  BEA --> PA
  MO --> PA
  AA --> PA
  AT --> PA
  WL --> PA
  WL -. info .-> MA
  WL -. info .-> ME
  PA --> DR --> MA

  %% Events can be used by multiple agents(informational)
  PE -. info .-> MA
  PE -. info .-> ME
  PE -. info .-> MI
  PE -. info .-> PA
  LG -. info .-> MA
  LG -. info .-> ME
  LG -. info .-> MI
  LG -. info .-> PA

  %% Styling
  classDef actor fill:#f6f6f6,stroke:#333,stroke-width:1px;
  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef component fill:#eef8ee,stroke:#2f6b2f,stroke-width:1px;
  classDef external fill:#fff3e6,stroke:#a35b00,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

---

## 2. Detail Flows

### 2.1 Season Scenario Detail Flow

**Inputs (Artefacts)**
- `athlete_profile_*.json` (user-authored profile + goals)
- `availability_*.json` (user-managed availability)
- `kpi_profile_des_*.json`
- `planning_events_*.json` (A/B/C events)
- `logistics_*.json` (contextual)

**Processing (Conceptual)**
- Extract season goals, constraints, and event priorities.
- Propose scenario options with clear trade-offs.
- Store scenarios and selected scenario for season-planning consumption.

**Outputs (Artefacts)**
- `season_scenarios_yyyy-ww--yyyy-ww.json` (informational)
- `season_scenario_selection_yyyy-ww.json` (binding selection state for downstream season planning)

```mermaid
flowchart LR
  U[User]:::actor --> AP["athlete_profile_*.json"]:::artefact --> SS["Season Scenario Surface"]:::agent
  U --> AV["availability_*.json"]:::artefact --> SS
  U --> KP["kpi_profile_des_*.json"]:::artefact --> SS
  U --> PE["planning_events_*.json"]:::artefact --> SS
  U --> LG["logistics_*.json"]:::artefact --> SS
  SS --> SC["season_scenarios_yyyy-ww--yyyy-ww.json"]:::artefact
  SS --> SEL["season_scenario_selection_yyyy-ww.json"]:::artefact
  classDef actor fill:#f6f6f6,stroke:#333,stroke-width:1px;
  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

### 2.2 Season Planning Detail Flow

**Inputs (Artefacts)**
- `athlete_profile_*.json` (user-authored profile + goals)
- `availability_*.json` (user-managed availability)
- `kpi_profile_des_*.json`
- `planning_events_*.json` (A/B/C events)
- `logistics_*.json` (contextual)
- `season_scenarios_yyyy-ww--yyyy-ww.json` (advisory, if available)
- `season_scenario_selection_yyyy-ww.json` (selected scenario intent)
- `des_analysis_report_yyyy-ww.json` (advisory)
- `activities_actual_yyyy-ww.json` / `activities_trend_yyyy-ww.json` (informational, if available)
- `wellness_yyyy-ww.json` (informational; body_mass_kg used for kJ/kg/h corridor math)

**Processing (Conceptual)**
- Determine season intent, priorities, and constraints (8-32 weeks horizon).
- Define phase structure and load corridors.
- Run the internal planning/review/writer chain:
  1) Season planning crew drafts an internal season bundle
  2) Season review crew approves, rejects, or requests bounded replan
  3) Season writer crew serializes the final `SEASON_PLAN`

**Outputs (Artefacts)**
- `season_plan_yyyy-ww--yyyy-ww.json` (binding)
- `season_phase_feed_forward_yyyy-ww.json` (optional)
- `season_phase_feed_forward_yyyy-ww.json` is authored by the season planning runtime; `des_analysis_report` is advisory input only.

**Version-Key Semantics**
- `season_phase_feed_forward_yyyy-ww.json` is selected-week scoped.
- The `yyyy-ww` key must match the completed analysis / selected source week that triggered the Season -> Phase feed-forward.
- Example: a completed DES analysis for `2026-18` produces `season_phase_feed_forward_2026-18.json`.

```mermaid
flowchart LR
  U[User]:::actor --> AP["athlete_profile_*.json"]:::artefact --> MA["Season Planning Runtime"]:::agent
  U --> AV["availability_*.json"]:::artefact --> MA
  U --> KP["kpi_profile_des_*.json"]:::artefact --> MA
  U --> PE["planning_events_*.json"]:::artefact --> MA
  U --> LG["logistics_*.json"]:::artefact --> MA
  SC["season_scenarios_yyyy-ww--yyyy-ww.json"]:::artefact -. advisory .-> MA
  SEL["season_scenario_selection_yyyy-ww.json"]:::artefact --> MA
  DR["des_analysis_report_yyyy-ww.json"]:::artefact -. advisory .-> MA
  AA["activities_actual_yyyy-ww.json"]:::artefact -. info .-> MA
  AT["activities_trend_yyyy-ww.json"]:::artefact -. info .-> MA
  AV["availability_yyyy-ww.json"]:::artefact -. info .-> MA
  WL["wellness_yyyy-ww.json"]:::artefact -. info .-> MA

  MA --> MO["season_plan_yyyy-ww--yyyy-ww.json"]:::artefact
  MA -. optional .-> SPFF["season_phase_feed_forward_yyyy-ww.json"]:::artefact

  classDef actor fill:#f6f6f6,stroke:#333,stroke-width:1px;
  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef component fill:#eef8ee,stroke:#2f6b2f,stroke-width:1px;
```

---

### 2.3 Phase Planning Detail Flow

**Inputs (Artefacts)**
- `season_plan_yyyy-ww--yyyy-ww.json` (binding)
- `season_phase_feed_forward_yyyy-ww.json` (optional, binding if present)
- `planning_events_*.json` (informational)
- `logistics_*.json` (informational)

**Version-Key Semantics**
- `phase_feed_forward_yyyy-ww.json` is phase-anchored, not selected-week scoped.
- The `yyyy-ww` key must be the first ISO week in the covered phase `iso_week_range`.
- Example: for phase range `2026-17--2026-19`, the stored artefact is `phase_feed_forward_2026-17.json` even if the triggering `season_phase_feed_forward` came from selected week `2026-18`.
- `activities_actual_yyyy-ww.json` / `activities_trend_yyyy-ww.json` (informational)
- `availability_yyyy-ww.json` (informational)
- `wellness_yyyy-ww.json` (informational)

**Processing (Conceptual)**
- Convert season phase intent into one exact-range phase bundle.
- Phase range is derived from season phase boundaries.
- Run the internal planning/review/writer chain before persistence.
- Consumes the latest `ZONE_MODEL` when IF defaults are needed.

**Outputs (Artefacts)**
- `phase_guardrails_yyyy-ww--yyyy-ww.json` (binding)
- `phase_structure_yyyy-ww--yyyy-ww.json` (binding)
- `phase_preview_yyyy-ww--yyyy-ww.json` (optional, informational)
- `phase_feed_forward_yyyy-ww.json` (optional)

```mermaid
flowchart LR
  MO["season_plan_yyyy-ww--yyyy-ww.json"]:::artefact --> ME["Phase Planning Runtime"]:::agent
  SPFF["season_phase_feed_forward_yyyy-ww.json"]:::artefact -. optional .-> ME
  PE["planning_events_*.json"]:::artefact -. info .-> ME
  LG["logistics_*.json"]:::artefact -. info .-> ME
  AA["activities_actual_yyyy-ww.json"]:::artefact -. info .-> ME
  AT["activities_trend_yyyy-ww.json"]:::artefact -. info .-> ME
  ZM["zone_model_power_<FTP>W.json"]:::artefact -. info .-> ME
  AV["availability_yyyy-ww.json"]:::artefact -. info .-> ME
  WL["wellness_yyyy-ww.json"]:::artefact -. info .-> ME

  ME --> BG["phase_guardrails_yyyy-ww--yyyy-ww.json"]:::artefact
  ME --> BEA["phase_structure_yyyy-ww--yyyy-ww.json"]:::artefact
  ME -. explanatory .-> BEP["phase_preview_yyyy-ww--yyyy-ww.json"]:::artefact
  ME -. optional .-> BFF["phase_feed_forward_yyyy-ww.json"]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

### 2.4 Week Planning Detail Flow

**Inputs (Artefacts)**
- `phase_guardrails_yyyy-ww--yyyy-ww.json`
- `phase_structure_yyyy-ww--yyyy-ww.json`
- `phase_feed_forward_yyyy-ww.json` (optional)
- `zone_model_power_<FTP>W.json` (informational, from Data-Pipeline)
- `availability_yyyy-ww.json` (informational, user-managed input)
- `wellness_yyyy-ww.json` (informational, from Data-Pipeline)
- `planning_events_*.json` (informational)
- `logistics_*.json` (informational)
- Optional factual data for context

**Processing (Conceptual)**
- Create a weekly agenda aligned to governance and phase structure.
- Build workout-ready week intent.
- Run the internal planning/review/writer chain before persistence.

**Outputs (Artefacts)**
- `week_plan_yyyy-ww.json`

```mermaid
flowchart LR
  BG["phase_guardrails_yyyy-ww--yyyy-ww.json"]:::artefact --> MI["Week Planning Runtime"]:::agent
  BEA["phase_structure_yyyy-ww--yyyy-ww.json"]:::artefact --> MI
  BFF["phase_feed_forward_yyyy-ww.json"]:::artefact -. optional .-> MI
  ZM["zone_model_power_<FTP>W.json"]:::artefact -. info .-> MI
  AV["availability_yyyy-ww.json"]:::artefact -. info .-> MI
  WL["wellness_yyyy-ww.json"]:::artefact -. info .-> MI
  PE["planning_events_*.json"]:::artefact -. info .-> MI
  LG["logistics_*.json"]:::artefact -. info .-> MI
  AA["activities_actual_yyyy-ww.json"]:::artefact -. info .-> MI
  AT["activities_trend_yyyy-ww.json"]:::artefact -. info .-> MI

  MI --> WP["week_plan_yyyy-ww.json"]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

### 2.4a Runtime Memory Snapshot Flow

**Inputs (Authoritative Sources)**
- athlete/profile + availability + logistics + planning events
- KPI / zone model / wellness
- season / phase / week / report / feed-forward artefacts as available

**Processing (Conceptual)**
- Orchestrator resolves deterministic facts into code-owned memory artefacts.
- Binding planner memory is split into:
  - `athlete_state_snapshot_yyyy-ww.json`
  - `planning_context_snapshot_yyyy-ww.json`
- Coach-facing current-week status memory is stored as:
  - `current_week_status_snapshot_yyyy-ww.json`
- Non-binding narrative memory is stored as:
  - `advisory_memory_yyyy-ww.json`
- Planners and Coach consume snapshot memory first and use raw artefacts only for missing detail or traceability.
- Coach-facing advisory memory may include the selected-week objective, planned weekly load, and a compact current-week workout list derived from the latest `WEEK_PLAN`.
- Current-week actuals are fetched separately from Intervals.icu, normalized into the same activity shape as `ACTIVITIES_ACTUAL`, and persisted into `CURRENT_WEEK_STATUS_SNAPSHOT` before Coach consumes them.

**Outputs (Artefacts)**
- `athlete_state_snapshot_yyyy-ww.json` (derived)
- `planning_context_snapshot_yyyy-ww.json` (derived)
- `current_week_status_snapshot_yyyy-ww.json` (derived)
- `advisory_memory_yyyy-ww.json` (advisory)

```mermaid
flowchart LR
  SRC["Authoritative Inputs + Outputs"]:::artefact --> ORCH["Orchestrator Snapshot Builders"]:::component
  ORCH --> ASS["athlete_state_snapshot_yyyy-ww.json"]:::artefact
  ORCH --> PCS["planning_context_snapshot_yyyy-ww.json"]:::artefact
  ORCH --> CWS["current_week_status_snapshot_yyyy-ww.json"]:::artefact
  ORCH --> ADM["advisory_memory_yyyy-ww.json"]:::artefact
  ASS --> PL["Planner / Coach Injection"]:::agent
  PCS --> PL
  CWS --> PL
  ADM -. non-binding .-> PL

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef component fill:#eef8ee,stroke:#2f6b2f,stroke-width:1px;
```

---

### 2.5 Workout Export + Posting Detail Flow

**Inputs (Artefacts)**
- `week_plan_yyyy-ww.json`

**Processing (Conceptual)**
- Deterministic conversion into Intervals.icu JSON payload.
- Optional commit step writes receipts (idempotency) and posts to Intervals.icu.
- Workouts export is optional in readiness (planning can complete without it).

**Outputs**
- `workouts_yyyy-ww.json`
- `receipts/post_to_intervals/<athlete>/<yyyy-Www>/<uid>.json`
- Planned calendar entries in Intervals.icu

```mermaid
flowchart LR
  WP["week_plan_yyyy-ww.json"]:::artefact --> WB["Local Workout Export"]:::component
  WB --> WJ["workouts_yyyy-ww.json"]:::artefact --> POST["post_to_intervals (commit)"]:::script
  POST --> RCPT["post_receipts_yyyy-ww.json"]:::artefact --> CAL["Planned Activities<br/>in Calendar"]:::artefact --> I["Intervals.icu"]:::external

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef external fill:#fff3e6,stroke:#a35b00,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

---

### 2.6 Data Pipeline Detail Flow (Fetch + Compile + Validate)

**Inputs**
- Intervals.icu API data (executed activities and related metrics)
- Intervals.icu calendar state (planned + executed)
- `availability_*.json` (user-managed input, validated alongside outputs)

**Processing (Conceptual)**
- `intervals_data.py`: fetch raw activity data, compile `activities_actual` and `activities_trend`
- `validate_outputs.py`: validate JSON outputs against schemas

**Outputs (Artefacts)**
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `availability_yyyy-ww.json`

```mermaid
flowchart LR
  I["Intervals.icu"]:::external --> EXP["intervals_data.py"]:::script
  EXP --> AA["activities_actual_yyyy-ww.json"]:::artefact
  EXP --> AT["activities_trend_yyyy-ww.json"]:::artefact
  AVI["availability_yyyy-ww.json"]:::artefact --> VAL
  AA --> VAL["validate_outputs.py"]:::script
  AT --> VAL
  VAL -. checks .-> AA
  VAL -. checks .-> AT
  VAL -. checks .-> AVI

  classDef external fill:#fff3e6,stroke:#a35b00,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

---

### 2.7 Artefact Renderer (Sidecars)

**Purpose**
- Produce human-readable `.md` sidecars from JSON artefacts.

**Inputs**
- Any JSON artefact (e.g., `phase_guardrails_yyyy-ww--yyyy-ww.json`)

**Processing**
- `rps.rendering.renderer.render_json_sidecar`
- Templates in `src/rps/rendering/templates/`

**Outputs**
- `<artefact>.md` (informational only)

---

### 2.8 Performance Report Detail Flow

**Inputs (Artefacts)**
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `kpi_profile_des_*.json`
- `planning_events_*.json` (informational)
- `logistics_*.json` (informational)
- `season_plan_yyyy-ww--yyyy-ww.json`
- `phase_guardrails_yyyy-ww--yyyy-ww.json`
- `phase_structure_yyyy-ww--yyyy-ww.json`

**Processing (Conceptual)**
- Extract diagnostic signals (DES/KPI).
- Produce a single dominant interpretation with explicit confidence.

**Outputs (Artefacts)**
- `des_analysis_report_yyyy-ww.json`
- No feed-forward artefact is authored here; feed-forward flows consume this report and then route to the season or phase planning runtime.

```mermaid
flowchart LR
  AA["activities_actual_yyyy-ww.json"]:::artefact --> PA["Performance Report Runtime"]:::agent
  AT["activities_trend_yyyy-ww.json"]:::artefact --> PA
  KP["kpi_profile_des_*.json"]:::artefact --> PA
  BEA["phase_structure_yyyy-ww--yyyy-ww.json"]:::artefact --> PA
  BG["phase_guardrails_yyyy-ww--yyyy-ww.json"]:::artefact --> PA
  MO["season_plan_yyyy-ww--yyyy-ww.json"]:::artefact --> PA
  PE["planning_events_*.json"]:::artefact -. info .-> PA
  LG["logistics_*.json"]:::artefact -. info .-> PA

  PA --> DR["des_analysis_report_yyyy-ww.json"]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

### 2.9 Data Operations (Backup + Restore)

**Inputs (Artefacts)**
- Athlete workspace directory (`runtime/athletes/<athlete_id>/`)

**Processing (Conceptual)**
- Backup is always **full** (no scope selector).
- Restore applies **only the selected scope** from the uploaded archive.

**Outputs (Artefacts)**
- `backup_archive_<athlete_id>_<timestamp>.zip` (full snapshot)
- `backup_manifest.json` (embedded inside the archive)

```mermaid
flowchart LR
  U[User]:::actor --> DO["Data Operations UI"]:::component
  DO --> BK["backup_archive_<athlete_id>_<timestamp>.zip"]:::artefact
  BK --> DO
  DO --> RS["Select Restore Scope"]:::component
  RS --> WR["Write Selected Artefacts"]:::component
  classDef actor fill:#f6f6f6,stroke:#333,stroke-width:1px;
  classDef component fill:#eef8ee,stroke:#2f6b2f,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

## 3. Artefact Index (Quick Reference)

### 3.1 User-Maintained
- `athlete_profile_yyyy.json`
- `planning_events_yyyy.json`
- `logistics_yyyy.json`
- `availability_yyyy-ww.json`
- `kpi_profile_des_*.json`

### 3.2 Season Scenario Surface

See [doc/architecture/agents.md](../architecture/agents.md) for the canonical agent registry.
- `season_scenarios_yyyy-ww--yyyy-ww.json`
- `season_scenario_selection_yyyy-ww.json`

### 3.3 Season Planning Runtime
- `season_plan_yyyy-ww--yyyy-ww.json`
- `season_phase_feed_forward_yyyy-ww.json` (optional)

### 3.4 Phase Planning Runtime
- `phase_guardrails_yyyy-ww--yyyy-ww.json`
- `phase_structure_yyyy-ww--yyyy-ww.json`
- `phase_preview_yyyy-ww--yyyy-ww.json` (optional)
- `phase_feed_forward_yyyy-ww.json` (optional)

### 3.5 Week Planning Runtime
- `week_plan_yyyy-ww.json`

### 3.6 Workout Export / Posting
- `workouts_yyyy-ww.json`
- Planned calendar activities (Intervals.icu)

### 3.7 Data Pipeline
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `zone_model_power_<FTP>W.json`
- `wellness_yyyy-ww.json`
- Raw CSVs (implementation detail)

### 3.8 Performance Report Runtime
- `des_analysis_report_yyyy-ww.json`
- Diagnostic only; does not own `season_phase_feed_forward` or `phase_feed_forward`

### 3.9 Data Operations
- `backup_archive_<athlete_id>_<timestamp>.zip`
- `backup_manifest.json` (embedded)

---

## 4. Notes on Optionality and Authority

- **Binding:** `season_plan`, `phase_guardrails`, `phase_structure`, `week_plan`,
  `activities_actual`, `activities_trend`
- **Informational:** `season_scenarios`, `phase_preview`, `zone_model`, `wellness` (when present)
- **Scoped Override:** feed-forward artefacts (use only within their stated scope)
- **Advisory:** `des_analysis_report`

---

## End of Document
### 4.1 Week Planning / Workout Export Consistency Rule

- `WEEK_PLAN` store is not based on schema validation alone.
- Before a `WEEK_PLAN` is stored, the guarded store normalizes linked workout metadata from deterministic workout-local data where possible:
  - workout duration from `workout_text`
  - agenda duration from linked workout duration
  - agenda mechanical `planned_kj` from linked workout notes when explicitly present
- After normalization, `WEEK_PLAN` must pass cross-field consistency checks before `INTERVALS_WORKOUTS` export is allowed.
- Examples of blocking inconsistencies:
  - linked `workout_id` with `planned_duration = 00:00`
  - linked `workout_id` with `planned_kj = 0`
  - linked workout `duration = 00:00:01`
  - weekly mechanical total statement in summary notes not matching the agenda sum
