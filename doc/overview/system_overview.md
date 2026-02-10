---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Overview
---
# System Overview

RPS is an end-to-end planning system for endurance athletes. It manages the Season → Phase → Week → Workouts pipeline, with Streamlit UI pages as the orchestration surface and a file-based workspace as the source of truth.

Key concepts:
- **Artifacts**: versioned JSON outputs (season/phase/week/workouts, reports, inputs).
- **Workspace**: append-only storage under `runtime/athletes/<athlete_id>/` with `latest/` pointers.
- **Run Store**: per-run status/events for background jobs.
- **Agents**: model-backed planners that write artifacts to the workspace.

See:
- `doc/architecture/system_architecture.md`
- `doc/ui/ui_spec.md`
- `doc/runbooks/validation.md`
