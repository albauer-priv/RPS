---
Status: Implemented
Version: 1.0
Last-Updated: 2026-09-16
---
# FEAT_auto_retry_transient

## Problem

Planning steps (Season Scenarios, Season Plan, Phase, Week) occasionally fail due to transient LLM errors — rate limits, network timeouts, model service hiccups — that would succeed on a retry. Previously a single failure immediately marked the step and the whole run as FAILED, requiring the user to manually restart the run from the Plan Hub.

## Goal

Auto-retry failed planning steps up to `MAX_STEP_RETRIES` times before declaring permanent failure. Each retry attempt is logged and emits a `STEP_RETRY` event so it is visible in the run event log.

## Non-Goals

- Distinguishing transient vs. permanent errors (all failures are retried; permanent failures simply exhaust all retries)
- Retrying async response-based steps (the `response_status in {"failed", "cancelled"}` path — those are externally cancelled, not transient)
- Retrying steps that fail due to a missing prerequisite artifact (those are blocked correctly)

## Design

### Constants (plan_hub_worker.py)

| Constant | Value | Meaning |
|---|---|---|
| `MAX_STEP_RETRIES` | 2 | Retry attempts after first failure; total = 3 |
| `STEP_RETRY_DELAY_S` | 30 | Seconds to wait before each retry |

### Retry Logic

In `_run_plan_hub_worker` at the synchronous step failure path (`if step.get("Status") != "DONE"`):

1. Read `step["_retry_count"]` (default 0)
2. If `retry_count < MAX_STEP_RETRIES`:
   - Increment `_retry_count`
   - Reset `step["Status"]` → `"PENDING"`, clear `Started` / `Ended`
   - Log `WARNING: "Step failed (attempt N/M), retrying in 30s: <reason>"`
   - Emit `STEP_RETRY` event with `attempt`, `max_retries`, `reason`
   - `update_run(...)` with current steps
   - `time.sleep(STEP_RETRY_DELAY_S)`
   - (fall through to `break` — outer while loop re-picks up the PENDING step)
3. If retries exhausted: existing FAILED path (mark step FAILED, emit STEP_FAILED, return)

### Visibility

- `STEP_RETRY` events appear in the Run Events expander in Plan Hub
- The step stays visible as PENDING during the retry delay
- The log line shows which attempt is in progress and why

## Files Changed

- `src/rps/orchestrator/plan_hub_worker.py` — constants + retry logic in synchronous failure path
