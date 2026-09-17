---
Status: Done
Version: 1.0
Last-Updated: 2026-09-16
---
# FEAT_planning_done_notification

## Problem

After a planning run (Season, Phase, Week, or Adjustment) completes, the Plan Hub goes silent. The auto-refresh stops and the page looks the same whether the run succeeded or failed. Users must read the step table or scroll through log output to understand the final outcome. There is no at-a-glance signal that planning is done or that something went wrong.

## Goal

Show a visible banner in Plan Hub immediately after a planning run finishes — green for success, red for failure — with a one-line summary of what happened.

## Non-Goals

- Email / push / browser-native notifications (deferred to later iteration)
- Persistent notification history
- Notifications on pages other than Plan Hub

## Design

### Completion Detection (session-state transition)

Plan Hub already auto-refreshes every 2 s while a run is active. On the render where `run_state` first becomes `False` after being `True`, a run has just transitioned to a terminal state.

Track this via two session-state keys:

| Key | Type | Meaning |
|---|---|---|
| `plan_hub_was_running` | bool | `run_state` value from the *previous* render |
| `plan_hub_completion_shown_for` | str \| None | `run_id` of the run whose completion banner was last shown — avoid re-showing on subsequent re-renders |

Detection logic (executed near the top of hub.py, after `run_state` is known):
```python
was_running = bool(st.session_state.get("plan_hub_was_running", False))
just_completed = was_running and not run_state
```

Show the banner only when `just_completed` is True **and** `active_run` is not None **and** `active_run["run_id"] != plan_hub_completion_shown_for`.

### Banner Content

**Success (status == "DONE")**:
```
st.success(
    f"Planning complete — {steps_done} steps · {artefacts_written} artifacts written"
    + (f" · {elapsed}" if elapsed else "")
)
```

**Failure (status == "FAILED" or any other terminal non-DONE)**:
```
st.error(
    f"Planning failed — {steps_done} done · {steps_failed} failed"
    + (f" · {elapsed}" if elapsed else "")
)
```

Elapsed time is derived from `active_run["started_at"]` vs `active_run["finished_at"]` (or `datetime.now(UTC)` as fallback).

### State Update

At the *end* of each page render (after the `run_state` auto-refresh block):
```python
st.session_state["plan_hub_was_running"] = run_state
```

Set `plan_hub_completion_shown_for` to the run_id as soon as the banner is displayed.

### Placement

The banner is rendered immediately after the "Plan Hub" title and athlete caption, before all other sections, so it is always visible without scrolling.

## Files Changed

- `src/rps/ui/pages/plan/hub.py` — detection logic + banner rendering + `plan_hub_was_running` state update

## Testing

Manual: start a planning run, wait for completion, confirm banner appears once without repeated display on subsequent interactions.
