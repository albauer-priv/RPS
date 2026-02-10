---
Version: 1.0
Status: Accepted
Last-Updated: 2026-02-10
Owner: Architecture
---
# ADR-027: Consolidate Repo Layout into Runtime + Specs Roots

## Context
The repository has accumulated many top-level directories, mixing runtime state (artifacts, logs, run queues) with static specs and knowledge. This increases navigation overhead, makes ownership unclear, and encourages hardcoded paths. The repo also contains unused scaffolding (`evals/`).

## Decision
Adopt a **hard cut-over** layout change:

- Introduce **`runtime/`** as the root for all local runtime state.
  - Move athlete workspaces to `runtime/athletes/`.
  - Co-locate run queues/states under `runtime/athletes/runs/` (consistent with existing code expectations).
- Introduce **`specs/`** as the root for static specs/knowledge/spec material.
  - Move `knowledge/` → `specs/knowledge/`.
  - Move `schemas/` → `specs/schemas/`.
  - Move `kpi_profiles/` → `specs/kpi_profiles/`.
- Remove `evals/` (unused; only `.gitkeep`).
- Keep `legacy/` at top-level (explicitly retained).

No legacy path shims are provided; all references are updated at once.

## Consequences
- **Breaking change:** any hardcoded references to old roots must be updated.
- Documentation, scripts, and config defaults must be updated to new roots.
- Environment variables should allow overrides (`ATHLETE_WORKSPACE_ROOT`, `SCHEMA_DIR`, etc.) but default to new paths.

## Alternatives Considered
- Staged migration with shims (rejected): adds complexity and delays cleanup.
- Documentation-only (rejected): does not reduce clutter or enforce clearer ownership.

## Implementation Notes
- Update code defaults for workspace root and schema dir.
- Update vectorstore manifest path.
- Update scripts that bundle/check schemas.
- Update docs/runbooks.

## Rollback Plan
Revert commits and restore previous directory layout.
