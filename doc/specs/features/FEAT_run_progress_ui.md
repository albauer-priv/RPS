---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: UI / Plan Hub
---
# FEAT: Run Progress UI

* **ID:** FEAT_run_progress_ui
* **Status:** Implemented
* **Owner/Area:** UI / Plan Hub
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/ui/pages/plan/hub.py`, `src/rps/ui/run_store.py`

---

## 1) Context / Problem

**Current behavior**

When a planning run is active (QUEUED/RUNNING), the Plan Hub auto-refreshes every 2 seconds
and shows the "Run Execution" section with:

* A step table listing all pipeline steps and their status.
* Small `st.caption` lines for current step, pipeline progress (e.g. "Pipeline progress: 2/5"),
  and runtime detail (flow/crew/task/agent).
* The top-level status message reads "Running" with no further context.

**Problems**

1. The progress information is in small captions below the step table — easy to miss, especially
   when the step table itself is long.
2. No visual progress indicator (bar or fraction) is immediately prominent.
3. No elapsed time is shown, so the user has no sense of whether a run is proceeding normally or stuck.
4. The runtime detail captions show detailed CrewAI task info but at the same visual weight as
   log-file captions — nothing signals "this is what is happening right now."

**Constraints**

* Page already auto-refreshes every 2 seconds via `time.sleep(2); st.rerun()` at the bottom —
  no new refresh mechanism needed.
* The `RunRecord` has `started_at` and `created_at` fields; the step table has `Started`/`Ended`
  per step.
* No backend changes — all improvements are in the Plan Hub UI rendering only.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Visual `st.progress()` bar for pipeline step completion (N/M steps done) when a run is active.
* [x] Elapsed time label (e.g. "2 min 15 s") computed from `started_at` or `created_at`.
* [x] Prominent current-operation line (current step + runtime task) as `st.info` instead of
  buried captions when running.
* [x] All existing progress captions remain (or are consolidated); no information is removed.

**Non-Goals**

* [ ] Sub-step progress within a single CrewAI task (not tracked at run-store level).
* [ ] Push notifications or OS-level alerts when a run finishes.
* [ ] New backend telemetry or event types.
* [ ] ETA / time-remaining prediction.

---

## 3) Proposed Behavior

### Run Execution section — while RUNNING/QUEUED

```
[= = = = = = = = = = = = = = = = = ]   3 / 7 steps  ·  2 min 15 s elapsed
ℹ  Phase planning  ·  Crew `phase_specialist_crew`  ·  Task `draft_phase_structure`
```

* `st.progress(pipeline_index / pipeline_total)` — visual bar, fraction displayed to the right.
* Single `st.info` line combining current step label + runtime detail (flow/crew/task when present).
* Existing captions for log file, summary, and manual-missing warnings remain below the step table.

### Run Execution section — after run completes (DONE/FAILED)

No change from current behavior.

---

## 4) Implementation

### `src/rps/ui/pages/plan/hub.py`

Add a helper `_format_elapsed(started: str | None, fallback: str | None) -> str`:

```python
def _format_elapsed(started: str | None, fallback: str | None = None) -> str:
    raw = started or fallback
    if not raw:
        return ""
    try:
        start_dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        seconds = max(0, int((datetime.now(tz=timezone.utc) - start_dt).total_seconds()))
        if seconds < 60:
            return f"{seconds} s"
        return f"{seconds // 60} min {seconds % 60} s"
    except ValueError:
        return ""
```

In the "Run Execution" section, after computing `pipeline_index` / `pipeline_total`:

**Replace**:
```python
    if pipeline_total and pipeline_index:
        st.caption(f"Pipeline progress: {pipeline_index}/{pipeline_total}")
```

**With**:
```python
    if run_state and pipeline_total:
        elapsed = _format_elapsed(
            _as_str(active_run.get("started_at")),
            _as_str(active_run.get("created_at")),
        )
        frac = pipeline_index / pipeline_total if pipeline_index else 0.0
        elapsed_label = f"  ·  {elapsed} elapsed" if elapsed else ""
        st.progress(frac, text=f"{pipeline_index or 0} / {pipeline_total} steps{elapsed_label}")
    elif pipeline_total and pipeline_index:
        st.caption(f"Pipeline progress: {pipeline_index}/{pipeline_total}")
```

Replace the separate current-step + runtime-detail captions:

**Replace**:
```python
    if active_run.get("current_step"):
        st.caption(f"Current step: {active_run.get('current_step')}")
    ...
    if runtime_bits:
        st.caption("Runtime detail: " + " · ".join(runtime_bits))
```

**With**:
```python
    if run_state:
        current_label = _as_str(active_run.get("current_step")) or ""
        all_bits = ([current_label] if current_label else []) + runtime_bits
        if all_bits:
            st.info(" · ".join(all_bits))
    else:
        if active_run.get("current_step"):
            st.caption(f"Current step: {active_run.get('current_step')}")
        if runtime_bits:
            st.caption("Runtime detail: " + " · ".join(runtime_bits))
```

Imports to add: `timezone` from `datetime` (if not already imported).

---

## 5) Acceptance Criteria

* [x] `st.progress()` bar visible and correct when a run is active (N / M steps filled).
* [x] Elapsed time shown next to the progress bar (e.g. "3 / 7 steps · 2 min 15 s elapsed").
* [x] Current step + runtime detail consolidated into `st.info()` while running.
* [x] After run completes, existing caption behavior restored (no regression).
* [x] Validation: `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`
* [x] Existing tests remain green: `pytest tests/test_plan_hub_page.py -x`

---

## 6) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — add and mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.

---

## 7) Link Map

* `src/rps/ui/pages/plan/hub.py`
* `src/rps/ui/run_store.py`
