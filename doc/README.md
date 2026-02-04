---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Documentation
---
# System Documentation

This directory contains the canonical documentation for the platform. It is a navigation hub and does not duplicate content.

## Where to start

- `overview/system_overview.md`
- `architecture/system_architecture.md`
- `ui/ui_spec.md`

## Documentation index

### Overview (explanation)
- `overview/system_overview.md`
- `overview/how_to_plan.md`
- `overview/planning_principles.md`
- `overview/artefact_flow.md`
- `overview/recommended_models.md`
- `overview/feature_backlog.md`

### Architecture (system design)
- `architecture/system_architecture.md`
- `architecture/agents.md`
- `architecture/workspace.md`
- `architecture/schema_versioning.md`
- `architecture/deployment.md`
- `architecture/vectorstores.md`
- `architecture/renderer.md`
- `architecture/subsystems/data_pipeline.md`
- `architecture/subsystems/intervals_posting.md`

### UI (flows + Streamlit contract)
- `ui/ui_spec.md`
- `ui/streamlit_contract.md`
- `ui/pages/plan_hub.md`
- `ui/pages/home.md`
- `ui/pages/coach.md`
- `ui/pages/plan_season.md`
- `ui/pages/plan_phase.md`
- `ui/pages/plan_week.md`
- `ui/pages/plan_workouts.md`
- `ui/pages/performance_data_metrics.md`
- `ui/pages/performance_report.md`
- `ui/pages/performance_feed_forward.md`
- `ui/pages/system_status.md`
- `ui/pages/system_history.md`
- `ui/pages/system_log.md`
- `ui/pages/athlete_profile.md`

### Specs (normative contracts)
- `specs/contracts/logging_policy.md`
- `specs/contracts/validation/` (artifact validation references)

### Runbooks (ops)
- `runbooks/validation.md`
- `runbooks/data_ops.md`

### ADRs
- `adr/README.md`

### Proposals
- `proposals/queue_scheduler.md` (superseded proposal)

## Conventions (short)

- Doc-writing rules live in `AGENTS.md`.
- Every doc must have Version/Status/Last-Updated/Owner header.
