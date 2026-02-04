---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Documentation
---
# System Documentation

This directory contains system-level documentation for the platform.

## Contents

### Overview (orientation)
- `overview/system_overview.md` (to be added)
- `overview/how_to_plan.md`
- `overview/planning_principles.md`
- `overview/artefact_flow.md`
- `overview/recommended_models.md`

### Architecture (system design)
- `architecture/system_architecture.md`
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

## Conventions

- Use clear filenames that mirror the subsystem (e.g. `workspace.md`, `vectorstores.md`).
- Prefer short, actionable docs that link to code references.
