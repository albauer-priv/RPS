---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Documentation
---
# System Documentation

This directory contains the canonical documentation for the platform. It is a navigation hub and does not duplicate content.

## Where to start

- [System Overview](overview/system_overview.md)
- [System Architecture](architecture/system_architecture.md)
- [UI Spec](ui/ui_spec.md)
- [UI Action & Flow Catalog](ui/flows.md)

## Documentation index

### Overview (explanation)
- [System Overview](overview/system_overview.md)
- [How to Plan](overview/how_to_plan.md)
- [Planning Principles](overview/planning_principles.md)
- [Artefact Flow](overview/artefact_flow.md)
- [Feature Backlog](overview/feature_backlog.md)

### Architecture (system design)
- [System Architecture](architecture/system_architecture.md)
- [Agents](architecture/agents.md)
- [Workspace](architecture/workspace.md)
- [Schema Versioning](architecture/schema_versioning.md)
- [Deployment](architecture/deployment.md)
- [Vectorstores](architecture/vectorstores.md)
- [Renderer](architecture/renderer.md)
- [Data Pipeline Subsystem](architecture/subsystems/data_pipeline.md)
- [Intervals Posting Subsystem](architecture/subsystems/intervals_posting.md)

### UI (flows + Streamlit contract)
- [UI Spec](ui/ui_spec.md)
- [UI Action & Flow Catalog](ui/flows.md)
- [Streamlit Contract](ui/streamlit_contract.md)
- [Plan Hub](ui/pages/plan_hub.md)
- [Home](ui/pages/home.md)
- [Coach](ui/pages/coach.md)
- [Plan Season](ui/pages/plan_season.md)
- [Plan Phase](ui/pages/plan_phase.md)
- [Plan Week](ui/pages/plan_week.md)
- [Plan Workouts](ui/pages/plan_workouts.md)
- [Performance Data & Metrics](ui/pages/performance_data_metrics.md)
- [Performance Report](ui/pages/performance_report.md)
- [Performance Feed Forward](ui/pages/performance_feed_forward.md)
- [System Status](ui/pages/system_status.md)
- [System History](ui/pages/system_history.md)
- [System Log](ui/pages/system_log.md)
- [Athlete Profile](ui/pages/athlete_profile.md)

### Specs (normative contracts)
- [Logging Policy](specs/contracts/logging_policy.md)
- [Validation Contracts](specs/contracts/validation/) (artifact validation references)

### Runbooks (ops)
- [Validation Runbook](runbooks/validation.md)
- [Data Ops Runbook](runbooks/data_ops.md)

### ADRs
- [ADR Index](adr/README.md)

### Proposals
- [Queue Scheduler Proposal](proposals/queue_scheduler.md) (superseded proposal)

## Conventions (short)

- Doc-writing rules live in [AGENTS.md](../AGENTS.md).
- Every doc must have Version/Status/Last-Updated/Owner header.
