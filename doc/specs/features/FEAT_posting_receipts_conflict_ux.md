---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: UI / Workouts
---
# FEAT: Posting Receipts — Diff & Conflict UX

* **ID:** FEAT_posting_receipts_conflict_ux
* **Status:** Draft
* **Owner/Area:** UI / Workouts
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/ui/intervals_post.py`, `src/rps/ui/pages/plan/workouts.py`, `FEAT_posting_receipts_inspection`

---

## 1) Context / Problem

**Current behavior**

`inspect_intervals_receipts()` and `resolve_receipt_conflict()` exist in
`src/rps/ui/intervals_post.py` and classify each workout into one of four
states: **unposted**, **updates** (hash changed), **conflicts** (invalid receipt
JSON), **posted**. None of this is surfaced in the UI.

The Workouts page shows only a plain "Post to Intervals" button inside an
`Actions` expander; on completion it shows a success/error string. There is no
pre-post status overview, no indication of what will be skipped/reposted, and no
way to resolve a stuck conflict from the UI.

**Problems**

1. The user cannot see before posting which workouts are new, which have changed,
   and which are stuck in conflict.
2. Conflicted receipts (invalid JSON) are silently skipped by
   `post_to_intervals_commit()` — the only signal is an error string buried in
   the result. There is no resolution path in the UI.
3. "Updates" (hash changed since last post) are re-posted automatically but the
   user does not know which workouts were modified.

**Constraints**

* No changes to `intervals_post.py` — the backend logic is complete.
* `inspect_intervals_receipts()` must be called before the post action to display
  a pre-post status panel, and re-called after to refresh it.
* Conflict resolution calls `resolve_receipt_conflict()` per UID.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Receipt status panel in the Workouts page showing counts and per-row
  details for unposted / updates / conflicts / posted.
* [x] Conflict rows: workout name, date, reason, and a per-row "Resolve" button
  that calls `resolve_receipt_conflict()` and reruns.
* [x] Update rows: compact table showing which workouts changed since last post
  (name, date, "payload changed" note).
* [x] Status panel refreshes automatically after a post or resolve action.
* [x] Tests: `AppTest`-based coverage for panel rendering and resolve action.

**Non-Goals**

* [ ] Full payload diff (old vs. new field-level comparison) — receipts do not
  store the old payload, only the hash. A hash-change note is sufficient.
* [ ] Bulk conflict resolution (per-row is enough at current scale).
* [ ] Conflict reason detail beyond what `inspect_intervals_receipts()` already
  returns.

---

## 3) Proposed Behavior

### Receipt status panel

Always rendered on the Workouts page, above the `Actions` expander, when
`INTERVALS_WORKOUTS` exists for the selected week. Hidden (no header shown) when
the artifact is missing.

```
Receipt Status · 2026-W38
✓  3 posted    ↻  1 update    ⚠  1 conflict    ○  2 unposted
```

The summary line uses `st.info` / `st.warning` / `st.error` depending on whether
conflicts are present.

**Posted**: no per-row expansion needed — counts only.

**Unposted**: compact table with name + date columns.

**Updates** (hash changed): compact table with name, date, and a
"Changed since last post" note. These will be re-posted on the next commit.

**Conflicts** (invalid receipt JSON): per-row `st.error` block showing name,
date, reason, and a "Resolve conflict" button. Clicking the button calls
`resolve_receipt_conflict()`, shows `st.success`, then `st.rerun()`.

### After posting

Re-call `inspect_intervals_receipts()` and re-render the panel so counts update
immediately after a post action.

---

## 4) Implementation

### `src/rps/ui/pages/plan/workouts.py`

New function `_show_receipt_status_panel(store, athlete_id, *, year, week)`:

```python
def _show_receipt_status_panel(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    year: int,
    week: int,
) -> None:
    status = inspect_intervals_receipts(store, athlete_id, year=year, week=week)
    if status.error:
        return  # artifact missing — panel hidden
    # summary
    n_posted = len(status.posted)
    n_updates = len(status.updates)
    n_conflicts = len(status.conflicts)
    n_unposted = len(status.unposted)
    # ... render summary badge + per-category tables ...
    for row in status.conflicts:
        ...
        if st.button(f"Resolve conflict – {row['name']}", key=f"resolve_{row['uid']}"):
            ok = resolve_receipt_conflict(store, athlete_id, year=year, week=week,
                                          uid=row["uid"], run_id=f"resolve_{row['uid']}")
            if ok:
                st.success("Conflict resolved.")
            else:
                st.error("Could not resolve conflict.")
            st.rerun()
```

Call site: between `render_status_panel()` and the `Actions` expander, always
evaluated.

Add imports: `inspect_intervals_receipts`, `resolve_receipt_conflict` from
`rps.ui.intervals_post`.

### Tests: `tests/test_workouts_page.py` (new or extend existing)

* Panel hidden when `INTERVALS_WORKOUTS` missing.
* Panel shows correct counts for a mixed status fixture.
* Resolve button calls `resolve_receipt_conflict` and triggers rerun.

---

## 5) Acceptance Criteria

* [x] Receipt status panel rendered on Workouts page when artifact present.
* [x] Conflict row shows name, date, reason, "Resolve" button.
* [x] Resolve button calls `resolve_receipt_conflict` and panel refreshes.
* [x] Update rows shown with "Changed since last post" note.
* [x] Panel hidden (no header) when INTERVALS_WORKOUTS missing or error.
* [x] Validation: `./scripts/run_lint.sh`, `./scripts/run_typecheck.sh`
* [x] Tests pass: `pytest tests/test_workouts_page.py -x`

---

## 6) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.

---

## 7) Link Map

* `src/rps/ui/intervals_post.py`
* `src/rps/ui/pages/plan/workouts.py`
* `tests/test_workouts_page.py`
