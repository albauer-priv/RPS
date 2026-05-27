---
Version: 1.1
Status: Updated
Last-Updated: 2026-05-27
Owner: Overview
---
# System Overview

RPS is an end-to-end planning system for endurance athletes. It manages the Season → Phase → Week → Workouts pipeline, with Streamlit UI pages as the orchestration surface and a file-based workspace as the source of truth.

Key concepts:
- **Artifacts**: versioned JSON outputs (season/phase/week/workouts, reports, inputs).
- **Workspace**: append-only storage under `runtime/athletes/<athlete_id>/` with `latest/` pointers.
- **Run Store**: per-run status/events for background jobs.
- **Agents**: model-backed planners that write artifacts to the workspace.
- **Evidence Library**: canonical local evidence registry plus generated markdown briefs/tables, with weekly discovery, structured curation, deterministic gating, and activation before sources become operative.

See:
- [doc/architecture/system_architecture.md](../architecture/system_architecture.md)
- [doc/architecture/agents.md](../architecture/agents.md)
- [doc/ui/ui_spec.md](../ui/ui_spec.md)
- [doc/runbooks/validation.md](../runbooks/validation.md)
