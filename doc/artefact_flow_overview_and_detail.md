# ARTEFACT_FLOW_OVERVIEW_AND_DETAIL.md

Version: 2.1  
Status: Updated  
Last-Updated: 2026-01-23  
Format: GitHub-renderable Markdown + Mermaid

---

## 1. Flow Overview (End-to-End)

```mermaid
flowchart TD
  %% Actors / Components
  U[User]:::actor
  SS[Season-Scenario-Agent]:::agent
  MA[Macro-Planner]:::agent
  ME[Meso-Architect]:::agent
  MI[Micro-Planner]:::agent
  WB[Workout-Builder]:::agent
  PA[Performance-Analyst]:::agent
  I[Intervals.icu]:::external
  EXP[get_intervals_data.py]:::script
  AVP[parse_season_brief_availability.py]:::script
  VAL[validate_outputs.py]:::script
  POST[post_workout.py]:::script

  %% Artefacts
  SB[season_brief_yyyy.md]:::artefact
  KP[kpi_profile_des_*.json]:::artefact
  EV[events.md]:::artefact
  AV[availability_yyyy-ww.json]:::artefact
  SC[season_scenarios_yyyy-ww--yyyy-ww.json]:::artefact
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
  WL[wellness_yyyy-ww.json]:::artefact
  DR[des_analysis_report_yyyy-ww.json]:::artefact

  %% Planning chain
  U --> SB --> AVP --> AV
  AV --> SS
  U --> KP --> SS
  SS --> SC --> MA
  KP --> MA
  KP --> PA
  U --> EV --> MA
  EV -. info .-> SS
  AV --> MA

  MA --> MO --> ME
  MA -. optional .-> MMFF --> ME

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
  POST --> CAL --> I

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

### 2.1 Season-Scenario Detail Flow

**Inputs (Artefacts)**
- `season_brief_yyyy.md` (user-authored; includes weekday availability table)
- `availability_yyyy-ww.json` (derived from Season Brief)
- `kpi_profile_des_*.json`
- `events.md` (contextual)

**Processing (Conceptual)**
- Extract season goals, constraints, and event priorities.
- Propose three scenario options (A/B/C) with clear trade-offs.
- Store scenarios for Macro-Planner consumption (advisory only).

**Outputs (Artefacts)**
- `season_scenarios_yyyy-ww--yyyy-ww.json` (informational)

```mermaid
flowchart LR
  U[User]:::actor --> SB[season_brief_yyyy.md]:::artefact --> AVP[parse_season_brief_availability.py]:::script --> AV[availability_yyyy-ww.json]:::artefact --> SS[Season-Scenario-Agent]:::agent
  U --> KP[kpi_profile_des_*.json]:::artefact --> SS
  U --> EV[events.md]:::artefact --> SS
  SS --> SC[season_scenarios_yyyy-ww--yyyy-ww.json]:::artefact
  classDef actor fill:#f6f6f6,stroke:#333,stroke-width:1px;
  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

### 2.2 Macro-Planner Detail Flow

**Inputs (Artefacts)**
- `season_brief_yyyy.md` (user-authored; includes weekday availability table)
- `availability_yyyy-ww.json` (derived from Season Brief)
- `kpi_profile_des_*.json`
- `events.md` (contextual)
- `season_scenarios_yyyy-ww--yyyy-ww.json` (advisory, if available)
- `des_analysis_report_yyyy-ww.json` (advisory)
- `activities_actual_yyyy-ww.json` / `activities_trend_yyyy-ww.json` (informational, if available)
- `wellness_yyyy-ww.json` (informational; body_mass_kg used for kJ/kg/h corridor math)

**Processing (Conceptual)**
- Determine season intent, priorities, and constraints (8-32 weeks horizon).
- Define phase structure and load corridors (availability weekly hours + wellness body_mass_kg).
- Emit optional feed-forward if the next block needs explicit guidance.
- Mode A (CLI) is a two-step flow:
  1) `scripts/macro_mode_a.py scenarios` (stores `season_scenarios` and writes the scenario dialogue to `.cache/macro_scenarios/<run-id>.md`)
  2) `scripts/macro_mode_a.py overview` (writes `macro_overview_yyyy-ww--yyyy-ww.json`)

**Outputs (Artefacts)**
- `macro_overview_yyyy-ww--yyyy-ww.json` (binding)
- `macro_meso_feed_forward_yyyy-ww.json` (optional)

```mermaid
flowchart LR
  U[User]:::actor --> SB[season_brief_yyyy.md]:::artefact --> MA[Macro-Planner]:::agent
  U --> KP[kpi_profile_des_*.json]:::artefact --> MA
  U --> EV[events.md]:::artefact --> MA
  SC[season_scenarios_yyyy-ww--yyyy-ww.json]:::artefact -. advisory .-> MA
  DR[des_analysis_report_yyyy-ww.json]:::artefact -. advisory .-> MA
  AA[activities_actual_yyyy-ww.json]:::artefact -. info .-> MA
  AT[activities_trend_yyyy-ww.json]:::artefact -. info .-> MA
  AV[availability_yyyy-ww.json]:::artefact -. info .-> MA
  WL[wellness_yyyy-ww.json]:::artefact -. info .-> MA

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

### 2.3 Meso-Architect Detail Flow

**Inputs (Artefacts)**
- `macro_overview_yyyy-ww--yyyy-ww.json` (binding)
- `macro_meso_feed_forward_yyyy-ww.json` (optional, binding if present)
- `events.md` (informational)
- `activities_actual_yyyy-ww.json` / `activities_trend_yyyy-ww.json` (informational)
- `availability_yyyy-ww.json` (informational)
- `wellness_yyyy-ww.json` (informational)

**Processing (Conceptual)**
- Convert macro phase intent into a block (governance + execution architecture).
- Block range is derived from macro phase boundaries (not calendar-aligned).
- Optional preview or feed-forward on explicit request.
- Consumes the latest `ZONE_MODEL` (Data-Pipeline) when IF/TSS defaults are needed.

**Outputs (Artefacts)**
- `block_governance_yyyy-ww--yyyy-ww.json` (binding)
- `block_execution_arch_yyyy-ww--yyyy-ww.json` (binding)
- `block_execution_preview_yyyy-ww--yyyy-ww.json` (optional, informational)
- `block_feed_forward_yyyy-ww.json` (optional)

```mermaid
flowchart LR
  MO[macro_overview_yyyy-ww--yyyy-ww.json]:::artefact --> ME[Meso-Architect]:::agent
  MMFF[macro_meso_feed_forward_yyyy-ww.json]:::artefact -. optional .-> ME
  EV[events.md]:::artefact -. info .-> ME
  AA[activities_actual_yyyy-ww.json]:::artefact -. info .-> ME
  AT[activities_trend_yyyy-ww.json]:::artefact -. info .-> ME
  ZM[zone_model_power_<FTP>W.json]:::artefact -. info .-> ME
  AV[availability_yyyy-ww.json]:::artefact -. info .-> ME
  WL[wellness_yyyy-ww.json]:::artefact -. info .-> ME

  ME --> BG[block_governance_yyyy-ww--yyyy-ww.json]:::artefact
  ME --> BEA[block_execution_arch_yyyy-ww--yyyy-ww.json]:::artefact
  ME -. explanatory .-> BEP[block_execution_preview_yyyy-ww--yyyy-ww.json]:::artefact
  ME -. optional .-> BFF[block_feed_forward_yyyy-ww.json]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

### 2.4 Micro-Planner Detail Flow

**Inputs (Artefacts)**
- `block_governance_yyyy-ww--yyyy-ww.json`
- `block_execution_arch_yyyy-ww--yyyy-ww.json`
- `block_feed_forward_yyyy-ww.json` (optional)
- `zone_model_power_<FTP>W.json` (informational, from Data-Pipeline)
- `availability_yyyy-ww.json` (informational, from Data-Pipeline)
- `wellness_yyyy-ww.json` (informational, from Data-Pipeline)
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
  ZM[zone_model_power_<FTP>W.json]:::artefact -. info .-> MI
  AV[availability_yyyy-ww.json]:::artefact -. info .-> MI
  WL[wellness_yyyy-ww.json]:::artefact -. info .-> MI
  EV[events.md]:::artefact -. info .-> MI
  AA[activities_actual_yyyy-ww.json]:::artefact -. info .-> MI
  AT[activities_trend_yyyy-ww.json]:::artefact -. info .-> MI

  MI --> WP[workouts_plan_yyyy-ww.json]:::artefact

  classDef agent fill:#e8f2ff,stroke:#1f4b99,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
```

---

### 2.5 Workout-Builder + Posting Detail Flow

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

### 2.6 Data Pipeline Detail Flow (Fetch + Compile + Validate)

**Inputs**
- Intervals.icu API data (executed activities and related metrics)
- Intervals.icu calendar state (planned + executed)
- `season_brief_yyyy.md` (weekday availability table)

**Processing (Conceptual)**
- `get_intervals_data.py`: fetch raw activity data, compile `activities_actual` and `activities_trend`
- `parse_season_brief_availability.py`: normalize Season Brief availability table into `availability`
- `validate_outputs.py`: validate JSON outputs against schemas

**Outputs (Artefacts)**
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `availability_yyyy-ww.json`

```mermaid
flowchart LR
  I[Intervals.icu]:::external --> EXP[get_intervals_data.py]:::script
  EXP --> AA[activities_actual_yyyy-ww.json]:::artefact
  EXP --> AT[activities_trend_yyyy-ww.json]:::artefact
  SB[season_brief_yyyy.md]:::artefact --> AVP[parse_season_brief_availability.py]:::script --> AV[availability_yyyy-ww.json]:::artefact
  AA --> VAL[validate_outputs.py]:::script
  AT --> VAL
  AV --> VAL
  VAL -. checks .-> AA
  VAL -. checks .-> AT
  VAL -. checks .-> AV

  classDef external fill:#fff3e6,stroke:#a35b00,stroke-width:1px;
  classDef artefact fill:#ffffff,stroke:#555,stroke-dasharray: 4 3,stroke-width:1px;
  classDef script fill:#f3f0ff,stroke:#5b4db8,stroke-width:1px,stroke-dasharray: 2 2;
```

---

### 2.7 Artefact Renderer (Sidecars)

**Purpose**
- Produce human-readable `.md` sidecars from JSON artefacts.

**Inputs**
- Any JSON artefact (e.g., `block_governance_yyyy-ww--yyyy-ww.json`)

**Processing**
- `scripts/artefact_renderer.py`
- Templates in `scripts/renderers/`

**Outputs**
- `<artefact>.md` (informational only)

---

### 2.8 Performance-Analyst Detail Flow

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

### 3.2 Season-Scenario-Agent
- `season_scenarios_yyyy-ww--yyyy-ww.json`

### 3.3 Macro-Planner
- `macro_overview_yyyy-ww--yyyy-ww.json`
- `macro_meso_feed_forward_yyyy-ww.json` (optional)

### 3.4 Meso-Architect
- `block_governance_yyyy-ww--yyyy-ww.json`
- `block_execution_arch_yyyy-ww--yyyy-ww.json`
- `block_execution_preview_yyyy-ww--yyyy-ww.json` (optional)
- `block_feed_forward_yyyy-ww.json` (optional)

### 3.5 Micro-Planner
- `workouts_plan_yyyy-ww.json`

### 3.6 Workout-Builder / Posting
- `intervals_workouts_yyyy-ww.json`
- Planned calendar activities (Intervals.icu)

### 3.7 Data Pipeline
- `activities_actual_yyyy-ww.json`
- `activities_trend_yyyy-ww.json`
- `zone_model_power_<FTP>W.json`
- `wellness_yyyy-ww.json`
- Raw CSVs (implementation detail)

### 3.8 Performance-Analyst
- `des_analysis_report_yyyy-ww.json`

---

## 4. Notes on Optionality and Authority

- **Binding:** `macro_overview`, `block_governance`, `block_execution_arch`, `workouts_plan`,
  `activities_actual`, `activities_trend`
- **Informational:** `season_scenarios`, `block_execution_preview`, `zone_model`, `wellness` (when present)
- **Scoped Override:** feed-forward artefacts (use only within their stated scope)
- **Advisory:** `des_analysis_report`

---

## End of Document
