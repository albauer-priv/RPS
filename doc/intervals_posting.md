# intervals_posting.md

Version: 1.0
Status: Draft
Last-Updated: 2026-01-30

---

## Purpose

Define how RPS posts workouts to Intervals.icu with safe, idempotent semantics.
This document covers external_id strategy, receipt format, hashing, and
create/update/delete reconciliation. Posting is a **commit step** distinct from
export/build.

---

## 1) Build vs Commit

- **Build**: Export workouts (`workouts_yyyy-ww.json`) from `week_plan`.
- **Commit**: Post to Intervals using receipts + external_id.

Default policy:
- Orchestrated planning runs build steps only.
- Posting is optional (toggle) or a dedicated scoped action.

CLI helper (legacy-compatible):

```bash
PYTHONPATH=src python3 scripts/data_pipeline/post_workout.py \
  --json var/athletes/<athlete_id>/latest/workouts.json
```

---

## 2) External ID Strategy (Canonical Key)

Use `external_id` as the canonical primary key for Intervals events. This enables
clean upserts and deletes.

### Preferred scheme (stable UID)

If a stable `workout_uid` exists:

```
external_id = "rps:<athlete_id>:<workout_uid>"
```

### Alternative (slot-based)

If no stable UID, use ISO week + date + slot key:

```
external_id = "rps:<athlete_id>:<iso_year>-W<iso_week>:<local_date>:<slot_key>"
```

### Fallback (hash-based)

```
external_id = "rps:<athlete_id>:" + sha1("<iso_week>|<date>|<type>|<title>|<slot>")[:16]
```

**Recommendation:** Prefer stable UID, otherwise slot-based.

---

## 3) Receipt Format

Receipts are the authoritative record of posted events.

**Location:**

```
var/athletes/<athlete_id>/receipts/intervals/<external_id>.json
```

**Receipt JSON (example):**

```json
{
  "external_id": "rps:i150546:2026-W05:2026-02-02:wed_quality_1",
  "intervals_event_id": 33375903,
  "intervals_uid": "e2597b1c-9ca8-4156-8737-4251e6bbb313",
  "intervals_calendar_id": 1,
  "intervals_athlete_id": "2049151",
  "category": "WORKOUT",
  "start_date_local": "2026-02-02T00:00:00",
  "filename": "W05_Wed_Quality.fit",
  "payload_hash": "sha256:9dd2...f3a1",
  "payload_format": "fit_base64",
  "payload_size_bytes": 48231,
  "plan_ref": {
    "week_plan_version": "week_plan_2026-05.json",
    "export_version": "workouts_2026-05.json",
    "run_id": "plan_2026W05_i150546_1730"
  },
  "posted_at": "2026-01-30T17:31:12Z",
  "last_seen_in_plan_at": "2026-01-30T17:31:12Z",
  "status": "POSTED"
}
```

**Delete tombstone:**

```json
{
  "external_id": "...",
  "status": "DELETED",
  "deleted_at": "...",
  "last_payload_hash": "sha256:...",
  "plan_ref": { "run_id": "..." }
}
```

**Always store:**
- `external_id`
- `intervals_event_id` and `intervals_uid` (for recovery and diagnostics)

---

## 4) Payload Hashing

Only change the hash when the event meaningfully changes.

Recommended inputs:
- `category`
- `start_date_local`
- `description` (or file bytes)
- `filename` (if used)

If posting files:
- hash raw file bytes + `start_date_local`.

If posting text:
- normalize whitespace and hash `description + start_date_local`.

---

## 5) Reconciliation (Create/Update/Delete)

Given:
- `desired` from export payload, keyed by `external_id`
- `known` receipts for the same athlete/week scope

Actions:
- **Upsert** if no receipt, or payload hash differs.
- **Delete** if receipt exists but `external_id` missing from `desired` and policy allows delete.

### Counts for UI

Show before commit:
- Creates/Updates
- Deletes
- Unchanged

---

## 6) External API Usage

- Use bulk upsert keyed by `external_id` (`/events/bulk?upsert=true`).
- Use bulk delete by `external_id` (`/events/bulk-delete`).
- Persist returned Intervals `id` + `uid`.

---

## 7) Safety Policies

- Commit steps are **manual** by default.
- Auto-retry only for build steps.
- Delete only events created by RPS (managed receipts) unless user opts in.

---

## 8) Recovery (Receipt Loss)

If receipts are lost:
1) List Intervals events for date range.
2) Filter to your client id (events created by your app).
3) Rebuild receipts by `external_id`.

---

## 9) Plan Hub UX

Execution steps:
1) Export Workouts (build)
2) Post to Intervals (commit)

Plan Hub should surface:
- Post toggle
- Delete-removed toggle (optional)
- Counts (create/update/delete)
- Link to Week page for posting status
