---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Documentation
---
# Logging Policy

This project follows standard logging best practices:
- Logs are event streams (one line per event).
- Log level reflects severity, not verbosity.
- Context is included in the message (run id, athlete, task, artifact).
- Configuration is controlled by environment variables.

## Log Levels

Use these levels consistently:

- DEBUG
  - Use for detailed diagnostics needed when troubleshooting.
  - Examples:
    - counts (rows processed, files scanned)
    - resolved paths and ids
    - timing per step (ms)
    - small samples (first N ids), never full payloads
    - retry decisions

- INFO
  - Use for normal lifecycle milestones.
  - Examples:
    - start/end of a run
    - input/output locations
    - success summaries (items written, duration)
    - key decisions (selected schema, mode, target week)

- WARNING
  - Use for unexpected but recoverable conditions.
  - Examples:
    - missing optional inputs
    - falling back to defaults
    - deprecated script usage
    - soft validation adjustments

- ERROR
  - Use for failed operations that prevent output from being produced.
  - Examples:
    - validation failure (no output)
    - external API error after retries
    - missing required inputs

- CRITICAL
  - Use for unrecoverable failures or corrupted state.
  - Examples:
    - invariants violated
    - write aborted and workflow cannot continue

Do not log secrets (API keys, tokens). Keep payloads out of logs; log sizes and ids instead.

## Format

The default format is:

```
%(asctime)s %(levelname)s %(name)s %(message)s
```

Time is in UTC.

## Configuration

Environment variables:
- APP_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- APP_LOG_STDOUT: if true, also logs to stdout
- APP_LOG_FILE: overrides default log file location (CLI only)
- RPS_LOG_ROTATE_MB: rotate `rps.log` when it exceeds this size in MB (default: 50)
- RPS_LOG_RETENTION_DAYS: delete rotated logs older than this many days (default: 7)
- RPS_RUN_RETENTION_DAYS: delete run history older than N days (default: 7)
- RPS_TPM_WAIT_MULTIPLIER: multiplier applied to TPM retry wait time (default: 2)
- RPS_TPM_RETRY_COUNT: number of TPM retries before failing (default: 1)

## Log Files & Rotation

All app/CLI/UI logs write to a single file per athlete:

```
var/athletes/<athlete_id>/logs/rps.log
```

Rotation:
- On day change, or when `rps.log` exceeds `RPS_LOG_ROTATE_MB`.
- Rotation writes `rps-YYYYMMDD-NNN.log` where `NNN` is a daily counter (000, 001, ...).
- A background cleanup deletes rotated logs older than `RPS_LOG_RETENTION_DAYS`.

Standard events:
- INFO start line includes argv
- CRITICAL unhandled exceptions
- INFO finish line

## Required Context Fields (when applicable)

Include these identifiers in log messages when available:
- run_id
- agent
- task
- athlete
- artifact_type
- version_key
- path
- duration_ms
- counts (items, records, files)

Prefer concise `key=value` pairs (or JSON if a script already uses JSON logging).

## Recommended Message Content

When logging:
- Include identifiers: run_id, athlete, task, artifact_type, version_key.
- Prefer counts over full payloads.
- Log file paths for outputs.
- Log explicit fallbacks (WARNING) and their chosen defaults.
- Log validation outcomes (DEBUG for success, ERROR for failure).
- Every artifact write MUST emit an INFO log with artifact type, version key, and path.

## Examples

INFO:
```
2026-01-24T15:30:12Z INFO week_planner Start week_planner argv=--task CREATE_WEEK_PLAN ...
```

WARNING:
```
2026-01-24T15:30:20Z WARNING scripts.sync_vectorstores Missing optional manifest; skipping.
```

ERROR:
```
2026-01-24T15:30:30Z ERROR scripts.validate_outputs Schema validation failed: ...
```

## Level Mapping Cheat Sheet

- DEBUG: “What exactly happened?”
- INFO: “What happened (normally)?”
- WARNING: “Something odd, but we recovered.”
- ERROR: “We failed this step.”
- CRITICAL: “We cannot continue.”
