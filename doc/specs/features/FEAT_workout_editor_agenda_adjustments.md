---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: UI / Workouts
---
# FEAT: Workout Editor — Agenda Adjustments

* **ID:** FEAT_workout_editor_agenda_adjustments
* **Status:** Implemented
* **Owner/Area:** UI / Workouts / Bounded Edits
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/orchestrator/week_plan_edits.py`, `src/rps/ui/pages/plan/workouts.py`

---

## 1) Context / Problem

**Current behavior**

Bounded edits for an existing week plan cover: moving a workout to an empty day
(`preview_move_workout`), swapping two occupied days (`preview_swap_workouts`),
changing a workout's start time (`preview_change_start_time`), and replacing a
workout's text block (`preview_update_workout_text`). None of these touch the
agenda row's `planned_kj`, `planned_duration`, or `day_role` fields directly —
the only way to adjust these is through a full week re-plan.

**Problem**

A common lightweight edit request is:
* "Increase Tuesday's planned kJ from 400 to 500 — training went better than expected."
* "Change Thursday to a recovery day instead of quality."
* "Shorten Wednesday's planned duration to 1:15."

These don't require re-running the full planner; they are bounded adjustments the
Coach should be able to preview and apply directly.

**Constraints**

* `normalize_week_plan_consistency` will override `planned_duration` if the linked
  workout's `workout_text` encodes a different duration — this is noted as a preview
  warning, not blocked.
* `planned_kj` set to a positive value is safe: normalization only fills kj from notes
  when the current value is ≤ 0.
* `day_role` is not touched by normalization — safe to update directly.
* No new artifact schema changes; result is a `WeekPlanEditPreview`.

---

## 2) Goals & Non-Goals

**Goals**

* [x] `preview_update_agenda_day(week_plan, *, day, planned_kj, planned_duration, day_role)`
  in `week_plan_edits.py` — update one or more of the three agenda fields for a given day.
* [x] At least one field must be provided; all three are optional individually.
* [x] `planned_kj` must be a non-negative integer.
* [x] `planned_duration` must be HH:MM format.
* [x] `day_role` must be a non-empty string.
* [x] New `preview_update_agenda_day` CoachTool in `workouts.py`.
* [x] Tests covering: single-field updates, multi-field update, missing day, all-None rejection.

**Non-Goals**

* [ ] Enforcing `day_role` against the phase's `allowed_day_roles` list — the preview
  normalization flags structural issues; the edit function stays permissive.
* [ ] Modifying workout record fields (title, workout_text) — use existing tools for those.
* [ ] Bulk multi-day updates.

---

## 3) Proposed Behavior

The Coach can be asked:

> "Change Tuesday's planned kJ to 550 and make it a recovery day."

The Coach calls:
```
preview_update_agenda_day(day="Tue", planned_kj=550, day_role="RECOVERY")
```

Preview summary:
```
Update agenda for Tue 2026-09-15: day_role → RECOVERY, planned_kj → 550.
```

Pending edit stored and shown via the existing apply/discard flow.

---

## 4) Implementation

### `src/rps/orchestrator/week_plan_edits.py`

Add after `preview_swap_workouts`:

```python
def preview_update_agenda_day(
    week_plan: JsonMap,
    *,
    day: str,
    planned_kj: int | None = None,
    planned_duration: str | None = None,
    day_role: str | None = None,
) -> WeekPlanEditPreview:
    """Preview updating agenda-level fields (planned_kj, planned_duration, day_role) for one day."""
    if planned_kj is None and planned_duration is None and day_role is None:
        raise ValueError("at least one of planned_kj, planned_duration, or day_role must be provided")

    document = copy.deepcopy(week_plan)
    agenda_rows, _workouts, _agenda_by_workout = _lookup_rows(document)

    day_label, _iso_text = _resolve_day(day)
    row = next((r for r in agenda_rows if str(r.get("day") or "") == day_label), None)
    if row is None:
        raise ValueError(f"agenda day not found: {day_label}")

    if planned_kj is not None:
        if planned_kj < 0:
            raise ValueError("planned_kj must be non-negative")
        row["planned_kj"] = planned_kj

    if planned_duration is not None:
        if not _TIME_RE.fullmatch(planned_duration.strip()):
            raise ValueError("planned_duration must be HH:MM")
        row["planned_duration"] = planned_duration.strip()

    if day_role is not None:
        if not day_role.strip():
            raise ValueError("day_role must not be empty")
        row["day_role"] = day_role.strip().upper()

    changes: list[str] = []
    if day_role is not None:
        changes.append(f"day_role → {row['day_role']}")
    if planned_kj is not None:
        changes.append(f"planned_kj → {planned_kj}")
    if planned_duration is not None:
        changes.append(f"planned_duration → {planned_duration.strip()}")
    day_date = str(row.get("date") or "")
    date_label = f" {day_date}" if day_date else ""
    return _preview(
        "update_agenda_day",
        f"Update agenda for {day_label}{date_label}: {', '.join(changes)}.",
        document,
    )
```

### `src/rps/ui/pages/plan/workouts.py`

1. Add import: `preview_update_agenda_day` from `rps.orchestrator.week_plan_edits`.
2. Add handler inside `_build_workout_editor_tools`:
```python
def _preview_update_agenda_day(
    day: str,
    planned_kj: int | None = None,
    planned_duration: str | None = None,
    day_role: str | None = None,
) -> str:
    base = _editor_base_document(store, athlete_id, year, week)
    preview = preview_update_agenda_day(
        base, day=day, planned_kj=planned_kj,
        planned_duration=planned_duration, day_role=day_role,
    )
    st.session_state[EDITOR_PENDING_KEY] = json.loads(preview.to_json())
    append_system_log("workouts", f"Workout editor preview created: agenda update {day} ({version_key}).")
    return preview.to_json()
```
3. Add CoachTool:
```python
CoachTool(
    name="preview_update_agenda_day",
    description="Preview updating planned_kj, planned_duration, and/or day_role for one agenda day.",
    parameters={
        "type": "object",
        "properties": {
            "day": {"type": "string"},
            "planned_kj": {"type": ["integer", "null"]},
            "planned_duration": {"type": ["string", "null"]},
            "day_role": {"type": ["string", "null"]},
        },
        "required": ["day"],
        "additionalProperties": False,
    },
    handler=_preview_update_agenda_day,
),
```
4. Add to the `preview` toolset list.

### Tests: `tests/test_workout_editor_agenda_adjustments.py` (new)

* `test_update_planned_kj` — updates kj, other fields unchanged.
* `test_update_planned_duration` — updates duration in HH:MM.
* `test_update_day_role` — updates day_role, uppercased.
* `test_update_multiple_fields` — updates all three at once; summary lists all changes.
* `test_update_rejects_all_none` — all optional → ValueError.
* `test_update_rejects_unknown_day` — ValueError.
* `test_update_rejects_negative_kj` — ValueError.
* `test_update_rejects_invalid_duration` — ValueError.

---

## 5) Acceptance Criteria

* [x] `preview_update_agenda_day` updates agenda row fields; `_preview` normalizes and validates.
* [x] All-None input rejected with ValueError.
* [x] Invalid duration format rejected with ValueError.
* [x] Negative kj rejected with ValueError.
* [x] `preview_update_agenda_day` CoachTool in preview toolset.
* [x] Tests pass: `pytest tests/test_workout_editor_agenda_adjustments.py -x`
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
* `tests/test_workout_editor_agenda_adjustments.py`
