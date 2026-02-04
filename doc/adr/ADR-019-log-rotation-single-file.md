---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-019: Single Log File with Rotation

**Status:** Accepted  
**Date:** 2026-02-02  

## Context

Multiple timestamped log files per run make it hard to find the right log for UI and worker activity. We want a single, stable log target while still preventing unbounded growth.

## Decision

- Write all UI/CLI/worker logs to a single per-athlete file:
  `var/athletes/<athlete_id>/logs/rps.log`.
- Rotate the file:
  - on day change, or
  - when it exceeds `RPS_LOG_ROTATE_MB` (default 50 MB).
- Rotated files follow: `rps-YYYYMMDD-NNN.log` where `NNN` is a daily counter starting at `000`.
- A background cleanup deletes rotated logs older than `RPS_LOG_RETENTION_DAYS` (default 7).

## Consequences

- Easier log discovery (single known filename).
- Rotation keeps disk usage bounded and preserves history.
- Log handlers must enforce rotation and naming consistently across UI, CLI, and workers.

## Exceptions

- Explicit `APP_LOG_FILE` overrides continue to be honored for CLI runs (e.g., ad-hoc debugging).
