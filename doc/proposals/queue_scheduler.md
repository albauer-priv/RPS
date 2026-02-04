---
Version: 1.0
Status: Superseded
Last-Updated: 2026-02-03
Owner: Proposal
---
# Queue + Scheduler Proposal (File-based)

Superseded by:
- ADR-005: Run Store + Queue + Scheduler Separation

This proposal outlines a minimal, file-based scheduler/queue that complements the Run Store and keeps UI pages thin. The goal is to make run execution reliable, observable, and reusable from any page.

## Goals

- Run Store remains the **single source of truth** for run state.
- Scheduler decides **what to run and when** (priority + blocking rules).
- Workers execute steps and write status/events back to Run Store.
- Compatible with current repo constraints (file-based, no new deps).

## Concepts

### 1) Run Store (State)
- Location: `runs/<run_id>/run.json`, `steps.json`, `events.jsonl`
- Owned by Orchestrators and Workers
- UI pages only read

### 2) Queue (Intent)
- File-based queue under `runs/queue/`
- State markers: `pending/`, `active/`, `done/`, `failed/` (directories)
- Each queue item is a JSON file: `runs/queue/pending/<run_id>.json`

### 3) Scheduler (Decision)
- Periodically scans `queue/pending/` and `queue/active/`
- Enforces guardrails:
  - One active run per athlete
  - Priority by `process_type` / `process_subtype`
  - Blocks low-priority runs if higher-priority run active

### 4) Worker (Execution)
- Claims a queue item by moving it from `pending/` → `active/`
- Executes steps, updates Run Store
- On completion moves queue item to `done/` or `failed/`

## Flow Diagram (Mermaid)

```mermaid
flowchart TD
    A["Plan Hub / UI Action"] --> B["Write run.json + steps.json"]
    B --> C["Enqueue run (queue/pending)"]
    C --> D{ "Scheduler tick" }
    D -- eligible --> E["Move to queue/active"]
    E --> F["Worker executes steps"]
    F --> G["Update Run Store status"]
    G --> H{ "Run finished?" }
    H -- yes --> I["Move to queue/done or queue/failed"]
    H -- no --> F
```

## Data Model (Queue Item)

```json
{
  "run_id": "plan_hub_2026W05",
  "athlete_id": "athlete_01",
  "process_type": "planning",
  "process_subtype": "orchestrated",
  "priority": 3,
  "created_at": "2026-02-01T12:00:00Z"
}
```

## Responsibilities

- **Run Store**: storage of immutable events + current run state.
- **Queue**: only expresses intent to run.
- **Scheduler**: decides eligibility and claim.
- **Worker**: executes, writes status + events.

## Implementation Plan (Incremental)

1) Add queue folders under `runs/queue/{pending,active,done,failed}`
2) Add helper: `enqueue_run(run_id)`
3) Add scheduler loop (file-based) inside orchestrator module
4) Replace Plan Hub worker start with enqueue + scheduler
5) Add System → Status panel for queue states

## Advantages

- Shared execution path from any UI page
- Real queue semantics (retry, cancel, priority)
- Works with current file-based architecture

## Risks / Open Questions

- How often should scheduler tick? (poll vs manual trigger)
- Multi-worker coordination (atomic file move or lock)
- Backward compatibility with existing runs
