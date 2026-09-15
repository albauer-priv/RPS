---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: UI / Workouts
---
# FEAT: Workout Editor — Swap Days

* **ID:** FEAT_workout_editor_swap_days
* **Status:** Implemented
* **Owner/Area:** UI / Workouts / Bounded Edits
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/orchestrator/week_plan_edits.py`, `src/rps/ui/pages/plan/workouts.py`, `FEAT_chat_week_plan_edits`

---

## 1) Context / Problem

**Current behavior**

`preview_move_workout()` in `week_plan_edits.py` allows moving a workout to an **empty** target
day only. If the target day already contains a workout, it raises `ValueError`. There is no way
for the Coach or the user to swap two occupied days.

**Problem**

A common edit request is "swap Tuesday and Thursday" — e.g. move the quality session from Thu
to Tue and the endurance session from Tue to Thu because a mid-week conflict changed. This is
blocked by the move guard and requires two manual edits (move A to an empty day, move B to the
freed day, move A again) — or an explicit "swap" operation.

**Constraints**

* The workout's day metadata (day_role, planned_duration, planned_kj) travels with the workout
  when swapping — same behavior as `preview_move_workout`.
* No new artifact schema changes; result is a `WeekPlanEditPreview` like the existing operations.
* The Coach must also be able to invoke the swap (new `preview_swap_workouts` tool).

---

## 2) Goals & Non-Goals

**Goals**

* [x] `preview_swap_workouts(week_plan, *, year, week, source_day, target_day)` in
  `week_plan_edits.py` — swap the workouts (and their agenda metadata) between two days.
* [x] New `preview_swap_workouts` CoachTool in `workouts.py` so the Coach can invoke it.
* [x] Both source and target days must contain a workout; swapping with an empty day is rejected
  (user should use `preview_move_workout` instead).
* [x] Workout dates updated to reflect the new day assignment.
* [x] Tests covering: basic swap, swap with missing workout, swap with empty day (rejected).

**Non-Goals**

* [ ] UI form for direct (non-chat) swap — the Coach drives the operation; no new Streamlit
  form elements beyond what already exist for apply/discard.
* [ ] Swapping across weeks.
* [ ] Bulk swap of multiple days.

---

## 3) Proposed Behavior

The Coach can be asked:

> "Swap Tuesday and Thursday this week."

The Coach calls `preview_swap_workouts(source_day="Tue", target_day="Thu")` and receives a
`WeekPlanEditPreview` with:

```
summary: "Swap 'Threshold Intervals' (w001) on Tue 2026-09-16 with
          'Endurance' (w002) on Thu 2026-09-18."
```

The pending edit is stored in `EDITOR_PENDING_KEY` and shown to the user as normal; apply/discard
work unchanged.

---

## 4) Implementation

### `src/rps/orchestrator/week_plan_edits.py`

Add after `preview_move_workout`:

```python
def preview_swap_workouts(
    week_plan: JsonMap,
    *,
    year: int,
    week: int,
    source_day: str,
    target_day: str,
) -> WeekPlanEditPreview:
    """Preview swapping the workouts on two occupied days within the same week."""
    document = copy.deepcopy(week_plan)
    agenda_rows, workouts, agenda_by_workout = _lookup_rows(document)

    src_label, src_iso_text = _resolve_day(source_day)
    tgt_label, tgt_iso_text = _resolve_day(target_day)
    if src_label == tgt_label:
        raise ValueError("source and target day are the same")

    src_row = next((row for row in agenda_rows if str(row.get("day") or "") == src_label), None)
    tgt_row = next((row for row in agenda_rows if str(row.get("day") or "") == tgt_label), None)
    if src_row is None:
        raise ValueError(f"source agenda day not found: {src_label}")
    if tgt_row is None:
        raise ValueError(f"target agenda day not found: {tgt_label}")

    src_wid = src_row.get("workout_id")
    tgt_wid = tgt_row.get("workout_id")
    if not src_wid:
        raise ValueError(f"source day {src_label} has no workout; use preview_move_workout to move from an empty day")
    if not tgt_wid:
        raise ValueError(f"target day {tgt_label} has no workout; use preview_move_workout to move to an empty day")

    # Swap agenda row payload (workout_id, day_role, planned_duration, planned_kj)
    src_snap = {k: src_row.get(k) for k in ("workout_id", "day_role", "planned_duration", "planned_kj")}
    tgt_snap = {k: tgt_row.get(k) for k in ("workout_id", "day_role", "planned_duration", "planned_kj")}
    for k, v in tgt_snap.items():
        src_row[k] = v
    for k, v in src_snap.items():
        tgt_row[k] = v

    # Update workout dates
    src_date = _date_for_day(year, week, int(src_iso_text))
    tgt_date = _date_for_day(year, week, int(tgt_iso_text))
    src_workout = workouts.get(str(src_wid))
    tgt_workout = workouts.get(str(tgt_wid))
    if src_workout is not None:
        src_workout["date"] = tgt_date
    if tgt_workout is not None:
        tgt_workout["date"] = src_date

    src_title = str((src_workout or {}).get("title") or src_wid)
    tgt_title = str((tgt_workout or {}).get("title") or tgt_wid)
    return _preview(
        "swap_workouts",
        f"Swap '{src_title}' ({src_wid}) on {src_label} {src_date} with '{tgt_title}' ({tgt_wid}) on {tgt_label} {tgt_date}.",
        document,
    )
```

### `src/rps/ui/pages/plan/workouts.py`

1. Add import: `preview_swap_workouts` from `rps.orchestrator.week_plan_edits`.
2. Add handler inside `_build_workout_editor_tools`:
```python
def _preview_swap_workouts(source_day: str, target_day: str) -> str:
    base = _editor_base_document(store, athlete_id, year, week)
    preview = preview_swap_workouts(base, year=year, week=week, source_day=source_day, target_day=target_day)
    st.session_state[EDITOR_PENDING_KEY] = json.loads(preview.to_json())
    append_system_log("workouts", f"Workout editor preview created: swap {source_day} <-> {target_day} ({version_key}).")
    return preview.to_json()
```
3. Add CoachTool:
```python
CoachTool(
    name="preview_swap_workouts",
    description="Preview swapping the workouts on two occupied days within the selected ISO week.",
    parameters={
        "type": "object",
        "properties": {
            "source_day": {"type": "string"},
            "target_day": {"type": "string"},
        },
        "required": ["source_day", "target_day"],
        "additionalProperties": False,
    },
    handler=_preview_swap_workouts,
),
```
4. Add `preview_swap_workouts` to the `preview` list in `_workout_editor_toolsets`.

### Tests: `tests/test_workout_editor_swap_days.py` (new)

* `test_swap_workouts_exchanges_workout_data` — basic swap, verify workout IDs and dates swapped.
* `test_swap_workouts_rejects_empty_source_day` — source has no workout → ValueError.
* `test_swap_workouts_rejects_empty_target_day` — target has no workout → ValueError.
* `test_swap_workouts_rejects_same_day` — same source and target → ValueError.

---

## 5) Acceptance Criteria

* [x] `preview_swap_workouts` in `week_plan_edits.py` swaps workout IDs and dates between two
  occupied days.
* [x] Swapping with an empty day raises `ValueError` with a clear message.
* [x] `preview_swap_workouts` CoachTool registered in `workouts.py` (preview toolset).
* [x] Tests pass: `pytest tests/test_workout_editor_swap_days.py -x`
* [x] Validation: `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`

---

## 6) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.

---

## 7) Link Map

* `src/rps/orchestrator/week_plan_edits.py`
* `src/rps/ui/pages/plan/workouts.py`
* `tests/test_workout_editor_swap_days.py`
