---
Version: 1.0
Status: Done
Last-Updated: 2026-09-15
Owner: Planning Runtime
---
# FEAT: Run Scheduler Resilience

* **ID:** FEAT_run_scheduler_resilience
* **Status:** Done
* **Owner/Area:** Planning Runtime / Queue Scheduler
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/orchestrator/queue_scheduler.py`, `src/rps/orchestrator/plan_hub_worker.py`, `src/rps/ui/run_store.py`

---

## 1) Context / Problem

**Current behavior**

* `queue_scheduler.py` pulls items from `pending/`, starts a `PlanHubWorker` thread, and polls the run store until the run reaches a terminal status.
* `acquire_athlete_lock()` in `run_store.py` creates a file-based lock (`<root>/<athlete_id>/locks/athlete_<athlete_id>.lock`). The lock is released in a `finally` block inside `run_plan_hub_worker`.
* When the scheduler claims a pending item it moves it to `active/`. When the run completes it moves the item to `done/` or `failed/`.

**Problem**

Three failure modes leave athletes permanently blocked after a process crash (SIGKILL, OOM, forced app restart):

1. **Stale lock file.** If the process is killed while a run is active the lock file is never released. All subsequent `acquire_athlete_lock()` calls fail immediately with "Athlete lock busy." The RUNNING/QUEUED run in the run store is never transitioned to FAILED, so the athlete cannot start a new run.

2. **Orphaned `active/` queue items.** If the scheduler process dies after moving an item from `pending/` to `active/` but before completing the run, the item is stranded. On restart the scheduler only polls `pending/`, so the orphaned item and its run are never resolved. `_eligible()` sees the RUNNING run-store entry and blocks all new items for the same athlete.

3. **Stuck RUNNING/QUEUED runs with no worker.** After a crash a run may show as RUNNING or QUEUED in the run store with no active lock and no worker thread. `_eligible()` considers these as blocking active runs, preventing new scheduling.

All three cases share the same observable outcome: planning is permanently blocked for the affected athlete until someone manually deletes the lock file or run records.

**Constraints**

* No schema migration to run records or artifacts.
* Recovery must be conservative (fail-closed): prefer marking a stuck run FAILED over silently discarding it.
* Lock and queue recovery must be idempotent — safe to call multiple times.
* Must not interfere with a legitimately running worker thread.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Detect and recover stale lock files on lock acquisition (stale = run is terminal or missing, or lock age > threshold).
* [x] Recover orphaned `active/` queue items on scheduler startup — fail their runs and move items to `failed/`.
* [x] Detect and fail RUNNING/QUEUED runs that have no corresponding lock file on scheduler startup.
* [x] Emit structured run-store events for all recovery actions so history/audit is preserved.
* [x] Add focused unit tests for each recovery path.

**Non-Goals**

* [x] Watchdog thread that interrupts a running LLM call (thread-killing is unsafe; out of scope).
* [x] Distributed locking or cross-host coordination.
* [x] Automatic retry of failed runs (existing manual retry UX is sufficient).
* [x] Changing artifact schemas or run-store record shapes.

---

## 3) Proposed Behavior

**Stale lock recovery (on every `acquire_athlete_lock` attempt)**

1. If lock acquisition succeeds, continue normally.
2. If it fails (`FileExistsError`), read the lock file and check staleness:
   * The `run_id` in the lock no longer exists in the run store, OR
   * The run's status is already terminal (DONE / FAILED / CANCELLED), OR
   * The lock file mtime is older than `STALE_LOCK_AGE_SECONDS` (default: 4 h = 14400 s).
3. If stale: delete the lock file, transition the stuck run to FAILED with reason "Recovered: stale lock detected", emit `RUN_FAILED` event, then retry the acquisition.
4. If not stale (run is genuinely RUNNING with a recent lock): return False as before.

**Startup orphan recovery (on `start_queue_scheduler`)**

Before the scheduler's main poll loop begins:

1. Scan `active/` for all `*.json` items.
2. For each orphaned item:
   a. Load the item, extract `run_id` and `athlete_id`.
   b. Load the run record.
   c. If the run is already terminal → move the item to `done/` or `failed/` without touching the run.
   d. If the run is RUNNING/QUEUED or missing → transition the run to FAILED ("Recovered: orphaned queue item on startup"), emit `RUN_FAILED`, move the item to `failed/`.
3. Release any stale lock that matches a run just failed in step 2d.

**Stuck-run sweep (on `start_queue_scheduler`)**

After orphan recovery, scan runs for each athlete that has a lock file whose run is RUNNING/QUEUED but for which no `active/` queue item exists:
* Treat these as orphaned workers: fail the run, release the lock.

This handles the case where the lock file exists but no `active/` item does (e.g., item was already moved to `done/` by a previous session but the lock was never released).

**UI impact**

* No direct UX change. Recovered runs appear in History as FAILED with a descriptive reason, same as any other failure.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/ui/run_store.py`:
  * `STALE_LOCK_AGE_SECONDS: int = 14400` — module constant.
  * `_read_lock_run_id(root, athlete_id) -> str | None` — private helper, reads `run_id` from lock file.
  * `_lock_is_stale(root, athlete_id) -> bool` — returns True when the lock exists but is stale.
  * `_recover_stale_lock(root, athlete_id) -> bool` — clears stale lock + fails stuck run; returns True when recovery happened.
  * `acquire_athlete_lock(...)` — updated to call `_recover_stale_lock` on `FileExistsError` and retry once.

* `src/rps/orchestrator/queue_scheduler.py`:
  * `_recover_orphaned_active_items(paths, root)` — private startup helper, resolves `active/` orphans.
  * `_recover_stuck_runs(root)` — private startup helper, sweeps lock files without matching active queue items.
  * `start_queue_scheduler(...)` — calls both recovery helpers before entering the main loop.

* `tests/test_run_scheduler_resilience.py` (new) — focused unit tests for all recovery paths.

**Data flow**

* Recovery reads/writes only to: lock files, run-store `run.json`, run-store `events.jsonl`, and queue folder items.
* No artifact writes. No workspace index changes.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* New run-store events emitted during recovery: `RUN_FAILED` (with `reason` = "Recovered: stale lock detected" / "Recovered: orphaned queue item on startup" / "Recovered: stuck run on startup").

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None.
* Fallback: recovery functions are purely additive; if they fail they log a warning and continue.

**Conflicts with ADRs / Principles**

* None. Aligns with fail-closed, no-silent-failure design principle.

**Impacted areas**

* UI: History page shows recovered runs as FAILED (already the expected behavior for lock-busy failures).
* Pipeline/data: no change.
* Workspace/run-store: new RUN_FAILED events on recovery only.
* Validation/tooling: new test file.
* Deployment/config: none.

---

## 6) Options & Recommendation

### Option A (recommended) — Recovery at acquisition time + startup sweep

* Stale-lock detection on every `acquire_athlete_lock` call.
* Orphan recovery + stuck-run sweep on scheduler startup.
* No background daemon needed.

**Pros**: minimal footprint, conservative, idempotent.  
**Cons**: startup sweep adds one filesystem scan per restart (fast, O(athletes with locks)).

### Option B — Periodic background watchdog thread

* Separate thread running every N minutes to detect and recover stuck runs.

**Cons**: adds concurrent lock-file access risk; harder to test; not needed given acquisition-time recovery.

### Recommendation

Option A. The scenarios all resolve at one of two deterministic moments: lock acquisition or scheduler restart.

---

## 6a) Implementation Readiness Review

* [x] Scope completeness: all affected modules and helpers named.
* [x] Decision completeness: stale threshold, recovery reason strings, and idempotency rules explicit.
* [x] Architecture conformity: no authority boundary changes, no artifact schema changes.
* [x] Execution readiness: implementation can proceed from this spec without inventing behavior.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `_lock_is_stale` returns True when run is terminal or missing, or lock age > threshold.
* [x] `acquire_athlete_lock` succeeds after recovering a stale lock in a single call.
* [x] Recovering a stale lock transitions the stuck RUNNING run to FAILED and emits `RUN_FAILED`.
* [x] `_recover_orphaned_active_items` resolves all items in `active/` on startup without touching items already terminal.
* [x] Stuck RUNNING runs without a lock file are failed by `_recover_stuck_runs`.
* [x] All recovery functions are idempotent (safe to call twice).
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `./scripts/run_lint.sh`
* [x] Validation passes: `./scripts/run_typecheck.sh`
* [x] Validation passes: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_run_scheduler_resilience.py -x`

---

## 8) Migration / Rollout

* No artifact or schema migration required.
* Safe to deploy immediately; recovery only activates when stale state is detected.
* No feature flag needed.

---

## 9) Risks & Failure Modes

* **Risk**: recovery incorrectly clears a live lock if clock skew causes mtime to appear stale.
  * Mitigation: `STALE_LOCK_AGE_SECONDS` defaults to 4 hours — far beyond any legitimate run duration.
  * The `run_id` check (run status terminal/missing) provides a second independent gate.

* **Risk**: recovery function itself throws an exception during startup and prevents the scheduler from starting.
  * Mitigation: both recovery helpers are wrapped in `try/except`; on failure they log a warning and return without aborting the scheduler.

* **Risk**: concurrent schedulers (multi-process restart) race on the same lock or active item.
  * Mitigation: `acquire_athlete_lock` uses `open("x")` (exclusive create) which is atomic on POSIX. Items are moved via `Path.replace()`, also atomic. A double-recovery attempt is a no-op.

---

## 10) Observability / Logging

* Recovery events logged at WARNING level (not ERROR — the system is self-healing).
* Structured `RUN_FAILED` events with recovery-specific reason strings allow filtering in History UI.
* No new event types; uses existing `RUN_FAILED` shape.

---

## 11) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark FEAT_run_scheduler_resilience as implemented.
* [x] `CHANGELOG.md` — record the feature when implementation lands.
* [x] This spec — update Goals checklist and add post-implementation audit section.

---

## 12) Link Map

* `doc/overview/feature_backlog.md`
* `src/rps/orchestrator/queue_scheduler.py`
* `src/rps/orchestrator/plan_hub_worker.py`
* `src/rps/ui/run_store.py`
* `tests/test_run_store.py`
* `tests/test_run_scheduler_resilience.py`
