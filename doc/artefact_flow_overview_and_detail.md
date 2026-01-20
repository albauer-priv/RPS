# ARTEFACT_FLOW_OVERVIEW_AND_DETAIL.md

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20  
Format: GitHub-renderable Markdown + Mermaid

---

## 1. Flow Overview (End-to-End)

```mermaid
flowchart TD
  %% Actors / Components
  U[User]:::actor
  MA[Macro-Planner]:::agent
  ME[Meso-Architect]:::agent
  MI[Micro-Planner]:::agent
  WB[Workout-Builder]:::agent
  PA[Performance-Analyst]:::agent
  I[Intervals.icu]:::external
  EXP[get_intervals_data.py]:::script
  VAL[validate_outputs.py]:::script
  POST[post_workout.py]:::script

  %% Artefacts
  SB[season_brief_yyyy.md]:::artefact
  KP[kpi_profile_des_*.json]:::artefact
  EV[events.md]:::artefact
  MO[macro_overview_yyyy-ww--yyyy-ww.json]:::artefact
  MMFF[macro_meso_feed_forward_yyyy-ww.json]:::artefact
  BG[block_governance_yyyy-ww--yyyy-ww.json]:::artefact
  BEA[block_execution_arch_yyyy-ww--yyyy-ww.json]:::artefact
  BEP[block_execution_preview_yyyy-ww--yyyy-ww.json]:::artefact
  BFF[block_feed_forward_yyyy-ww.json]:::artefact
  ZM[zone_model_power_<FTP>W.json]:::artefact
  WP[workouts_plan_yyyy-ww.json]:::artefact
  WJ[intervals_workouts_yyyy-ww.json]:::artefact
  CAL[Planned Activities<br/>in Calendar]:::artefact
  AA[activities_actual_yyyy-ww.json]:::artefact
  AT[activities_trend_yyyy-ww.json]:::artefact
  DR[des_analysis_report_yyyy-ww.json]:::artefact

  %% Planning chain
  U --> SB --> MA
  U --> KP --> MA
  KP --> PA
  U --> EV --> MA

  MA --> MO --> ME
  MA -. optional .-> MMFF --> ME

  ME --> BG --> MI
  ME --> BEA --> MI
  ME -. explanatory .-> BEP
  ME -. optional .-> BFF --> MI
  ME -. optional .-> ZM

  MI --> WP --> WB
  WB --> WJ --> POST
  POST --> CAL --> I

  %% Data & analysis loop
  I --> EXP
  EXP --> AA
  EXP --> AT
  AA --> VAL
  AT --> VAL
  VAL -. validates .-> AA
  VAL -. validates .-> AT
  BG --> PA
  BEA --> PA
  MO --> PA
  AA --> PA
  AT --> PA
  PA --> DR --> MA

  %% Events can be used by multiple agents (informational)
  EV -. info .-> MA
  EV -. info .-> ME
  EV -. info .-> MI
  EV -. info .-> PA

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

### 2.1 Macro-Planner Detail Flow

**Inputs (Artefacts)**
- `season_brief_yyyy.md` (user-authored)
- `kpi_profile_des_*.json`
- `events.md` (contextual)
- `des_analysis_report_yyyy-ww.json` (advisory)
- `activities_actual_yyyy-ww.json` / `activities_trend_yyyy-ww.json` (informational, if available)

**Processing (Conceptual)**
- Determine season intent, priorities, and constraints (8-32 weeks horizon).
- Define phase structure and load corridors.
- Emit optional feed-forward if the next block needs explicit guidance.
- Mode A (CLI) is a two-step flow:
  1) `scripts/macro_mode_a.py scenarios` (scenario dialogue saved to `.cache/macro_scenarios/<run-id>.md`)
  2) `scripts/macro_mode_a.py overview` (writes `macro_overview_yyyy-ww--yyyy-ww.json`)

**Outputs (Artefacts)**
- `macro_overview_yyyy-ww--yyyy-ww.json` (binding)
- `macro_meso_feed_forward_yyyy-ww.json` (optional)

```mermaid
flowchart LR
  U[User]:::actor --> SB[season_brief_yyyy.md]:::artefact --> MA[Macro-Planner]:::agent
  U --> KP[kpi_profile_des_*.json]:::artefact --> MA
  U --> EV[events.md]:::artefact --> MA
  DR[des_analysis_report_yyyy-ww.json]:::artefact -. advisory .-> MA
  AA[activities_actual_yyyy-ww.json]:::artefact -. info .-> MA
  AT[activities_trend_yyyy-ww.json]:::artefact -. info .-> MA

  S1[macro_mode_a.py scenarios]:::script --> MA
  MA --> SCN[scenario_dialogue<br/>.cache/macro_scenarios]:::component --> U
  U --> S2[macro_mode_a.py overview]:::script --> MA

  MA --> MO[macro_overview_yyyy-ww--yyyy-ww.json]:::artefact
  MA -. optional .-> MMFF[macro_meso_feed_forward_yyyy-ww.json]:::artefact

  classDef actor fill:#f6f6f6,stroke:#333,stroke-width:1px;
  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
  classDef component fill:#eef8ee,stroke:#2f6b2f,stroke-width:1px;
```

---

### 2.2 Meso-Architect Detail Flow

**Inputs (Artefacts)**
- `macro_overview_yyyy-ww--yyyy-ww.json` (binding)
- `macro_meso_feed_forward_yyyy-ww.json` (optional, binding if present)
- `events.md` (informational)
- `activities_actual_yyyy-ww.json` / `activities_trend_yyyy-ww.json` (informational)

**Processing (Conceptual)**
- Convert macro phase intent into a block (governance + execution architecture).
- Block range is derived from macro phase boundaries (not calendar-aligned).
- Optional preview, feed-forward, or zone model on explicit request.

**Outputs (Artefacts)**
- `block_governance_yyyy-ww--yyyy-ww.json` (binding)
- `block_execution_arch_yyyy-ww--yyyy-ww.json` (binding)
- `block_execution_preview_yyyy-ww--yyyy-ww.json` (optional, informational)
- `block_feed_forward_yyyy-ww.json` (optional)
- `zone_model_power_<FTP>W.json` (optional)

```mermaid
flowchart LR
  MO[macro_overview_yyyy-ww--yyyy-ww.json]:::artefact --> ME[Meso-Architect]:::agent
  MMFF[macro_meso_feed_forward_yyyy-ww.json]:::artefact -. optional .-> ME
  EV[events.md]:::artefact -. info .-> ME
  AA[activities_actual_yyyy-ww.json]:::artefact -. info .-> ME
  AT[activities_trend_yyyy-ww.json]:::artefact -. info .-> ME

  ME --> BG[block_governance_yyyy-ww--yyyy-ww.json]:::artefact
  ME --> BEA[block_execution_arch_yyyy-ww--yyyy-ww.json]:::artefact
  ME -. explanatory .-> BEP[block_execution_preview_yyyy-ww--yyyy-ww.json]:::artefact
  ME -. optional .-> BFF[block_feed_forward_yyyy-ww.json]:::artefact
  ME -. optional .-> ZM[zone_model_power_<FTP>W.json]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

### 2.3 Micro-Planner Detail Flow

**Inputs (Artefacts)**
- `block_governance_yyyy-ww--yyyy-ww.json`
- `block_execution_arch_yyyy-ww--yyyy-ww.json`
- `block_feed_forward_yyyy-ww.json` (optional)
- `events.md` (informational)
- Optional factual data for context

**Processing (Conceptual)**
- Create a weekly agenda aligned to governance and execution architecture.
- Define sessions and constraints; avoid violating block rules.

**Outputs (Artefacts)**
- `workouts_plan_yyyy-ww.json`

```mermaid
flowchart LR
  BG[block_governance_yyyy-ww--yyyy-ww.json]:::artefact --> MI[Micro-Planner]:::agent
  BEA[block_execution_arch_yyyy-ww--yyyy-ww.json]:::artefact --> MI
  BFF[block_feed_forward_yyyy-ww.json]:::artefact -. optional .-> MI
  EV[events.md]:::artefact -. info .-> MI
  AA[activities_actual_yyyy-ww.json]:::artefact -. info .-> MI
  AT[activities_trend_yyyy-ww.json]:::artefact -. info .-> MI

  MI --> WP[workouts_plan_yyyy-ww.json]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

### 2.4 Workout-Builder + Posting Detail Flow

**Inputs (Artefacts)**
- `workouts_plan_yyyy-ww.json`

**Processing (Conceptual)**
- Deterministic conversion into Intervals.icu JSON payload.
- Optional posting to Intervals.icu calendar.

**Outputs**
- `intervals_workouts_yyyy-ww.json`
- Planned calendar entries in Intervals.icu

```mermaid
flowchart LR
  WP[workouts_plan_yyyy-ww.json]:::artefact --> WB[Workout-Builder]:::agent
  WB --> WJ[intervals_workouts_yyyy-ww.json]:::artefact --> POST[post_workout.py]:::script
  POST --> CAL[Planned Activities<br/>in Calendar]:::artefact --> I[Intervals.icu]:::external

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef external fill:#fff3e6,stroke:#a35b00,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

---

### 2.5 Data Pipeline Detail Flow (Fetch + Compile + Validate)

**Inputs**
- Intervals.icu API data (executed activities and related metrics)
- Intervals.icu calendar state (planned + executed)

**Processing (Conceptual)**
- `get_intervals_data.py`: fetch raw activity data, compile `activities_actual` and `activities_trend`
- `validate_outputs.py`: validate JSON outputs against schemas

**Outputs (Artefacts)**
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`

```mermaid
flowchart LR
  I[Intervals.icu]:::external --> EXP[get_intervals_data.py]:::script
  EXP --> AA[activities_actual_yyyy-ww.json]:::artefact
  EXP --> AT[activities_trend_yyyy-ww.json]:::artefact
  AA --> VAL[validate_outputs.py]:::script
  AT --> VAL
  VAL -. checks .-> AA
  VAL -. checks .-> AT

  classDef external fill:#fff3e6,stroke:#a35b00,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

---

### 2.6 Artefact Renderer (Sidecars)

**Purpose**
- Produce human-readable `.rendered.md` sidecars from JSON artefacts.

**Inputs**
- Any JSON artefact (e.g., `block_governance_yyyy-ww--yyyy-ww.json`)

**Processing**
- `scripts/artefact_renderer.py`
- Templates in `scripts/renderers/`

**Outputs**
- `<artefact>.rendered.md` (informational only)

---

### 2.7 Performance-Analyst Detail Flow

**Inputs (Artefacts)**
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `kpi_profile_des_*.json`
- `events.md` (informational)
- `macro_overview_yyyy-ww--yyyy-ww.json`
- `block_governance_yyyy-ww--yyyy-ww.json`
- `block_execution_arch_yyyy-ww--yyyy-ww.json`

**Processing (Conceptual)**
- Extract diagnostic signals (DES/KPI).
- Produce a single dominant interpretation with explicit confidence.

**Outputs (Artefacts)**
- `des_analysis_report_yyyy-ww.json`

```mermaid
flowchart LR
  AA[activities_actual_yyyy-ww.json]:::artefact --> PA[Performance-Analyst]:::agent
  AT[activities_trend_yyyy-ww.json]:::artefact --> PA
  KP[kpi_profile_des_*.json]:::artefact --> PA
  BEA[block_execution_arch_yyyy-ww--yyyy-ww.json]:::artefact --> PA
  BG[block_governance_yyyy-ww--yyyy-ww.json]:::artefact --> PA
  MO[macro_overview_yyyy-ww--yyyy-ww.json]:::artefact --> PA
  EV[events.md]:::artefact -. info .-> PA

  PA --> DR[des_analysis_report_yyyy-ww.json]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

## 3. Artefact Index (Quick Reference)

### 3.1 User-Maintained
- `season_brief_yyyy.md`
- `events.md`
- `kpi_profile_des_*.json`

### 3.2 Macro-Planner
- `macro_overview_yyyy-ww--yyyy-ww.json`
- `macro_meso_feed_forward_yyyy-ww.json` (optional)

### 3.3 Meso-Architect
- `block_governance_yyyy-ww--yyyy-ww.json`
- `block_execution_arch_yyyy-ww--yyyy-ww.json`
- `block_execution_preview_yyyy-ww--yyyy-ww.json` (optional)
- `block_feed_forward_yyyy-ww.json` (optional)
- `zone_model_power_<FTP>W.json` (optional)

### 3.4 Micro-Planner
- `workouts_plan_yyyy-ww.json`

### 3.5 Workout-Builder / Posting
- `intervals_workouts_yyyy-ww.json`
- Planned calendar activities (Intervals.icu)

### 3.6 Data Pipeline
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- Raw CSVs (implementation detail)

### 3.7 Performance-Analyst
- `des_analysis_report_yyyy-ww.json`

---

## 4. Notes on Optionality and Authority

- **Binding:** `macro_overview`, `block_governance`, `block_execution_arch`, `workouts_plan`,
  `activities_actual`, `activities_trend`
- **Informational:** `block_execution_preview`, `zone_model` (when present)
- **Scoped Override:** feed-forward artefacts (use only within their stated scope)
- **Advisory:** `des_analysis_report`

---

## End of Document
