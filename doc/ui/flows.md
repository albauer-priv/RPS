---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-11
Owner: UI
---
# UI Action & Flow Catalog

This document captures **action specifications** and **flow diagrams** referenced
by the UI spec. It is the canonical place for detailed UI action behavior.

See [doc/ui/ui_spec.md](ui_spec.md) for the overall UI spec and page
responsibilities.

## Action Specification Template

For each UI action, document:
- **Action name**
- **Page**
- **Preconditions**
- **Orchestrator call**
- **Writes/side-effects**
- **UI feedback**

## Action Specifications

### Plan Hub — Orchestrated Run
- **Preconditions:** readiness not blocked (inputs present, within Season Plan range)
- **Orchestrator call:** enqueue run via queue scheduler
- **Writes:** Run Store (`run.json`, `steps.json`, `events.jsonl`)
- **UI feedback:** status banner + run table
- **Agents:** season_scenario, season_planner, phase_architect, week_planner, workout_builder

### Plan Hub — Scoped Run
- **Preconditions:** readiness not blocked (inputs present, within Season Plan range)
- **Orchestrator call:** enqueue scoped run with `process_subtype`
- **Writes:** Run Store
- **UI feedback:** status banner + run table
- **Agents:** subset depending on scope

### Plan → Season — Create Scenarios
Handled by **Plan Hub — Scoped Run** (scope: Season Scenarios). The Season page no longer triggers this action.

### Plan → Season — Select Scenario
- **Preconditions:** scenarios exist
- **Orchestrator call:** `select_season_scenario(...)`
- **Writes:** `season_scenario_selection`
- **UI feedback:** success banner + rerun
- **Agent:** season_scenario

### Plan → Season — Create Season Plan
Handled by **Plan Hub — Scoped Run** (scope: Season Plan). The Season page no longer triggers this action.

### Plan → Week — Plan Week
Handled by **Plan Hub — Orchestrated Run** (or Scoped: Week Plan). The Week page is view-only.

### Plan → Workouts — Post to Intervals
- **Preconditions:** workouts export exists
- **Orchestrator call:** `post_to_intervals_commit(...)`
- **Writes:** posting receipts
- **UI feedback:** success/error banner + status update
- **Agent:** none (commit step)

### Plan → Workouts — Revise Week Plan
- **Preconditions:** coach message provided
- **Orchestrator call:** `revise_week_plan(...)`
- **Writes:** `week_plan`
- **UI feedback:** output expander + status banner
- **Agent:** week_planner
- **Prompt requirement:** include user input text in the prompt

### Athlete Profile — Data Operations — Create Backup
- **Preconditions:** athlete workspace exists
- **Orchestrator call:** none (local archive creation)
- **Writes/side-effects:** creates a full in-memory archive for download (no scope selector)
- **UI feedback:** success banner + download button

### Athlete Profile — Data Operations — Validate Backup (Dry-Run)
- **Preconditions:** archive uploaded
- **Orchestrator call:** none (local validation)
- **Writes/side-effects:** none
- **UI feedback:** validation status + file count by category

### Athlete Profile — Data Operations — Restore Backup
- **Preconditions:** archive uploaded + restore scope selected + user confirmation; target workspace empty unless force
- **Orchestrator call:** none (local restore)
- **Writes/side-effects:** writes files into `runtime/athletes/<athlete_id>/` per selected restore scope
- **UI feedback:** success/error banner + count of restored files

#### Flow: Data Operations (Backup & Restore)

```mermaid
flowchart TD
    A["Open Data Operations Page"] --> B["Create Full Backup"]
    B --> C["Download Backup"]
    A --> D["Upload Backup Archive"]
    D --> E["Validate Backup (Dry-Run)"]
    E --> F["Select Restore Scope"]
    F --> G{"Confirmation Provided?"}
    G -- "No" --> H["Show Error"]
    G -- "Yes" --> I["Restore Selected Scope"]
    I --> J["Show Restore Summary"]
```

## Flow Catalog (Detailed)

### Flow: Plan (Orchestrated)

- **Entry:** Plan Hub → “Plan this Week”
- **Preconditions:** readiness not blocked (includes KPI Profile present)
- **Steps:** Scenarios → Selection → Season Plan → Phase → Week → Export
- **Orchestrator:** queue scheduler (planning run)
- **Outputs:** `season_scenarios`, `season_scenario_selection`, `season_plan`, `phase_guardrails`, `phase_structure`, `phase_preview`, `week_plan`, `workouts_yyyy-ww.json`
- **Writes:** replace all relevant `latest/` artefacts on each step
- **UI feedback:** status banner + execution table

#### Diagram (Plan Orchestrated)

```mermaid
flowchart TD

    subgraph "Plan Hub"
        A["Open Plan Hub Page"]:::page --> B["Load Athlete + ISO Week"]:::step
        B --> C{"Readiness OK?"}:::step
        C -- "No" --> C1["Show Missing Inputs + Links"]:::page
        C -- "Yes" --> D{"Season Scenarios Exist?"}:::step
        D -- "No" --> D1["Run Scenario Generator<br>Replace latest: season_scenarios"]:::orch
        D -- "Yes" --> F{"Season Plan Current?"}:::step
        F -- "No" --> F1["Run Season Plan<br>Replace latest: season_plan"]:::orch
        F1 --> G
        F -- "Yes" --> G{"Phase Guardrails + Structure Current?"}:::step
        G -- "No" --> G1["Run Phase Planning<br>Replace latest: phase_guardrails,<br>phase_structure,<br>phase_preview"]:::orch
        G1 --> H
        G -- "Yes" --> H{"Week Plan Current?"}:::step
        H -- "No" --> H1["Run Week Planning<br>Replace latest: week_plan"]:::orch
        H1 --> I
        H -- "Yes" --> I{"Workouts Export Current?"}:::step
        I -- "No" --> I1["Run Workout Export<br>Replace latest: workouts_yyyy-ww.json"]:::orch
        I1 --> J
        I -- "Yes" --> J["Planning Done"]:::step
        J --> L["Show Status"]:::page
    end

    subgraph "Plan > Season"
        D1 --> D2["Present Scenario Summary"]:::page
        D2 --> E1["Select Scenario<br>(Choose A/B/C + optional rationale))<br>Writes: season_scenario_selection"]:::page
        E1 --> E2["Save Selection"]:::orch
        E2 --> F
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Plan (Scoped)

- **Entry:** Plan Hub → “Run scoped”
- **Preconditions:** readiness not blocked (includes KPI Profile present)
- **Steps:** select scope → optional override (only when modifying existing artefacts) → re-plan selected scope + all lower levels
- **Orchestrator:** queue scheduler (planning run)
- **Outputs:** scope-level artefacts + lower-level artefacts
- **Writes:** replace all affected `latest/` artefacts
- **UI feedback:** status banner + execution table

#### Diagram (Plan Scoped)

```mermaid
flowchart TD
    subgraph "Plan Scoped"
        S1["Open Plan Hub Page"]:::page --> S2["Select Run Mode: Scoped"]:::page
        S2 --> S3["Select Scope"]:::page
        S3 --> S4{"Override Needed?"}:::step
        S4 -- "Yes" --> S5["Enter Override"]:::page
        S4 -- "No" --> S6["Skip Override"]:::step
        S5 --> S7["Enqueue Scoped Run<br>Scope + Override"]:::orch
        S6 --> S7
        S7 --> S8["Re-plan Scope + Lower Levels"]:::orch
        S8 --> S9["Show Status"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Reset/Delete Season Plan

- **Entry:** Plan Hub → “Season Plan: Delete or Reset”
- **Reset removes:** `season_plan`, `phase_*`, `week_plan`, `workouts_yyyy-ww.json`
- **Delete removes:** reset artefacts + `season_scenarios`, `season_scenario_selection`
- **Writes:** delete `latest/` artefacts listed above before re-planning
- **UI feedback:** removed artefacts list + status banner

#### Diagram (Reset/Delete Season Plan)

```mermaid
flowchart TD
    subgraph "Reset/Delete Season Plan"
        R1["Open Plan Hub Page"]:::page --> R2["Season Plan: Delete or Reset"]:::page
        R2 --> R3{"Choose Action"}:::step
        R3 -- "Reset" --> R4["Remove latest: season_plan,<br>phase_*, week_plan,<br>workouts_yyyy-ww.json"]:::orch
        R3 -- "Delete" --> R5["Remove latest: season_plan,<br>phase_*, week_plan,<br>workouts_yyyy-ww.json,<br>season_scenarios,<br>season_scenario_selection"]:::orch
        R4 --> R6["Show Status"]:::page
        R5 --> R6
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Workouts Adapt + Post

- **Entry:** Plan → Workouts
- **Preconditions:** week plan exists, within Season Plan range
- **Outputs:** updated `week_plan`, `workouts_yyyy-ww.json`, posting receipts
- **Writes:** replace `latest/` week plan + workouts export when updated
- **UI feedback:** output expander + status banner

#### Diagram (Workouts Adapt + Post)

```mermaid
flowchart TD
    subgraph "Adapt + Post Workouts"
        A1["Open Workouts Page"]:::page --> A2{"Week Plan OK?"}:::step
        A2 -- "No" --> A3["Enter Coach Message"]:::page
        A3 --> A4["Send to Week Planner<br>Mode: revise_week_plan"]:::orch
        A4 --> A5["Write week_plan (replace latest)"]:::orch
        A5 --> A2
        A2 -- "Yes" --> A6{"Workouts Exist?"}:::step
        A6 -- "Yes" --> A8{"Workouts Posted to Intervals?"}:::step
        A6 -- "No" --> A11["Delete workouts_yyyy-ww.json (latest)"]:::orch
        A8 -- "Yes" --> A9["Delete Posted Workouts (Intervals)"]:::orch
        A8 -- "No" --> A10["Skip Intervals Delete"]:::step
        A9 --> A11
        A10 --> A11
        A11 --> A13["Review Updated Workouts"]:::page
        A13 --> A14{"OK to Post?"}:::step
        A14 -- "No" --> A3
        A14 -- "Yes" --> A15["Run Workout Builder"]:::orch
        A15 --> A16["Write workouts_yyyy-ww.json (replace latest)"]:::orch
        A16 --> A17["Post Workouts to Intervals"]:::orch
        A17 --> A18["Show Status"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Plan Week (Scoped, Recommended)

- **Entry:** Plan Hub → “Run scoped” (Week Plan)
- **Preconditions:** current or next ISO week; within Season Plan range
- **Behavior:** generates any missing upstream artefacts (Phase Guardrails/Structure) before week plan
- **Outputs:** `week_plan`, `workouts_yyyy-ww.json`
- **Writes:** replace `latest/` week plan + workouts export (and upstream artefacts if regenerated)
- **UI feedback:** status banner + execution table

#### Diagram (Plan Week Scoped)

```mermaid
flowchart TD
    subgraph "Plan Week(Scoped)"
        W1["Open Plan Hub Page"]:::page --> W2{"Week In Scope?<br>Current or Next ISO Week"}:::step
        W2 -- "No" --> W3["Show Blocked: Out of Scope"]:::page
        W2 -- "Yes" --> W4{"Season Plan Covers Week?"}:::step
        W4 -- "No" --> W5["Show Blocked: Missing Season Plan"]:::page
        W4 -- "Yes" --> W6["Enqueue Scoped Run<br>Scope: Week Plan"]:::orch
        W6 --> W7{"Phase Artefacts Present?"}:::step
        W7 -- "No" --> W8["Run Phase Planning<br>Replace latest: phase_guardrails,<br>phase_structure,<br>phase_preview"]:::orch
        W7 -- "Yes" --> W9["Run Week Planning<br>Replace latest: week_plan"]:::orch
        W8 --> W9
        W9 --> W10["Run Workout Export<br>Replace latest: workouts_yyyy-ww.json"]:::orch
        W10 --> W11["Show Status"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Feed Forward

- **Entry:** Analyse → Feed Forward
- **Preconditions:** KPI Profile present
- **Steps:** DES Report → Season→Phase feed forward → Phase→Week feed forward
- **Outputs:** `des_analysis_report`, `season_phase_feed_forward`, `phase_feed_forward`
- **UI feedback:** status banner + summary table

#### Diagram (Feed Forward)

```mermaid
flowchart TD
    subgraph "Feed Forward"
        F1["Open Analyse → Feed Forward"]:::page --> F2["Run DES Report"]:::orch
        F2 --> F3["Season → Phase Feed Forward"]:::orch
        F3 --> F4["Phase → Week Feed Forward"]:::orch
        F4 --> F5["Show Status"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Performance Report

- **Entry:** Analyse → Report
- **Outputs:** `des_analysis_report`
- **UI feedback:** status banner + reasoning log

#### Diagram (Performance Report)

```mermaid
flowchart TD
    subgraph "Performance Report"
        R1["Open Analyse → Report"]:::page --> R2["Create Report"]:::page
        R2 --> R3["Run DES Report"]:::orch
        R3 --> R4["Show Status + Reasoning"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Data Pipeline Refresh

- **Entry:** Data & Metrics → “Refresh Intervals Data”
- **Outputs:** `activities_actual`, `activities_trend`, `zone_model`, `wellness`, `availability`
- **Writes:** replace `latest/` activities + wellness/zone model outputs
- **UI feedback:** status banner + System → Status updates

#### Diagram (Data Pipeline Refresh)

```mermaid
flowchart TD
    subgraph "Data Pipeline Refresh"
        D1["Run Intervals Pipeline"]:::orch --> D2["Write activities_* + zone_model + wellness<br>(replace latest)"]:::orch
        D2 --> D3["Show Status"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

### Flow: Inputs Update

- **Entry:** Athlete Profile pages (About You & Goals, Planning Events, Logistics, KPI, Availability)
- **Outputs:** input artefacts in `latest/`
- **Writes:** replace `latest/` input artefacts
- **UI feedback:** readiness reflects staleness in Plan Hub

#### Diagram (Inputs Update)

```mermaid
flowchart TD
    subgraph "Inputs Update"
        I1["Open Athlete Profile Page"]:::page --> I2["Edit Inputs"]:::page
        I2 --> I3["Write latest input artefact<br>(replace latest)"]:::orch
        I3 --> I4["Show Status"]:::page
    end

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

```mermaid
flowchart TD
    L1["Page (UI)"]:::page
    L2["Orchestrator"]:::orch
    L3["Agent"]:::agent
    L4["Flow Step"]:::step

    classDef page fill:#f8e79a,stroke:#8c7a2b,stroke-width:1px,color:#1f1a0a;
    classDef orch fill:#b7d7f2,stroke:#2f5b8a,stroke-width:1px,color:#0f2233;
    classDef agent fill:#c9f2c7,stroke:#2f7a2a,stroke-width:1px,color:#10340f;
    classDef step fill:#efefef,stroke:#8a8a8a,stroke-width:1px,color:#111;
```

## Related References

- [Streamlit Contract](streamlit_contract.md) — global UI layout + readiness behavior
- [Plan Hub Page Spec](pages/plan_hub.md) — readiness rules + run panel layout
- [Feature Backlog](../overview/feature_backlog.md) — queued enhancements and refactors
