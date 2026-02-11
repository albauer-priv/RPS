---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-10
Owner: UI
---
# UI Flow (Athlete-First)

This document describes the UI flows, pages, and actions aimed at making planning as simple as possible for the athlete. It is the **central UI specification** that implementation should follow.

## Scope

- UI flows and action behavior
- Page responsibilities and required actions
- Orchestrator calls per action
- Global UI contract (sidebar + status)

See [doc/architecture/system_architecture.md](../architecture/system_architecture.md) for C4 diagrams and system-level context.

## Goals

- One primary action: **“Plan my week”**
- Automatic gating: detect missing inputs and offer fix actions
- Safe defaults: run the full chain if ready; otherwise, run only what’s needed
- Clear feedback: show what happened, what changed, and what still needs input

## Global UI Contract

### Page Layout Standard (all non‑Coach pages)
- Order: **Title → Athlete caption → Status panel → Actions/controls → Content/details**.
- Show only one status banner per page.
- Additional captions (scope, ISO range, etc.) belong inside their section, not above the status panel.

### Global Sidebar (non‑Coach pages)
- Inputs: Athlete ID, ISO Year, ISO Week, Phase (if available), Dev Mode
- Purpose: global state only, no heavy IO

### Status Panel (all non‑Coach pages)
- Single banner with state: idle/running/done/error
- Shows last action + run ID (if present)

## Pages and Responsibilities

### Home
- Marketing text (markdown) from `static/marketing/home.md`
- System state table: artifact availability, owner, description, ISO validity
- See [doc/ui/pages/home.md](pages/home.md).

### Plan → Plan Hub
- Orchestration layer: readiness checklist, run planning, execution status
- Actions enqueue runs only (no direct agent calls)
- See [doc/ui/pages/plan_hub.md](pages/plan_hub.md).

### Plan → Season
- Actions: select scenario + KPI segment
- Create Scenarios + Create Season Plan are initiated from Plan Hub
- Reset/Delete handled in Plan Hub
- See [doc/ui/pages/plan_season.md](pages/plan_season.md).

### Plan → Phase
- Phase read-only view (details + preview)
- See [doc/ui/pages/plan_phase.md](pages/plan_phase.md).

### Plan → Week
- Read-only agenda summary + workouts list (planning runs in Plan Hub)
- See [doc/ui/pages/plan_week.md](pages/plan_week.md).

### Plan → Workouts
- Workouts export view, posting actions, history
- Revision requests for week plan
- See [doc/ui/pages/plan_workouts.md](pages/plan_workouts.md).

### Analyse
- Data & Metrics (weekly load + corridor overlays), Report (Narrative/KPI/Trend sections), Feed Forward
- See [doc/ui/pages/performance_data_metrics.md](pages/performance_data_metrics.md), [doc/ui/pages/performance_report.md](pages/performance_report.md), [doc/ui/pages/performance_feed_forward.md](pages/performance_feed_forward.md).

### Athlete Profile
- About You & Goals, Availability, Events, Logistics, Historic Data, Zones, KPI Profile, Data Operations
- See [doc/ui/pages/athlete_profile.md](pages/athlete_profile.md).

### System
- Status (running processes + latest artefacts)
- History, Log
- See [doc/ui/pages/system_status.md](pages/system_status.md), [doc/ui/pages/system_history.md](pages/system_history.md), [doc/ui/pages/system_log.md](pages/system_log.md).

## Action & Flow Catalog

Detailed action specifications and flow diagrams live in:
- [doc/ui/flows.md](flows.md)

## Related Documents

- [Streamlit Contract](streamlit_contract.md) — global UI layout + readiness behavior
- [Plan Hub Page Spec](pages/plan_hub.md) — readiness rules + run panel layout
- [Action & Flow Catalog](flows.md) — action specs and flow diagrams
