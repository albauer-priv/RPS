---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-10
Owner: Runbook
---
# Athlete Backup & Restore (Concept)

Goal: allow an athlete to export all of their data from a running system and restore it into a clean system so the UI/agents see the same artifacts and history.

---

## Scope

This design covers **per‑athlete data** stored under `var/athletes/<athlete_id>/` plus the minimal metadata needed to make those artifacts usable after restore. It does **not** include global system configuration, models, or vector stores. Those are managed separately by the system.

---

## Data to include in the backup

### Required (restore must include)
- `var/athletes/<athlete_id>/inputs/`  
  Athlete Profile, Availability, Planning Events, Logistics, KPI Profile, etc.
- `var/athletes/<athlete_id>/latest/`  
  Latest pointers for all artifact types.
- `var/athletes/<athlete_id>/data/`  
  Versioned artifacts (e.g., plans/season, plans/phase, plans/week, analysis, exports, etc.).
- `var/athletes/<athlete_id>/receipts/`  
  Intervals posting receipts and idempotency records.
- `var/athletes/<athlete_id>/rendered/` (optional but recommended)  
  Rendered artifacts for faster UI load; can be regenerated.

### Excluded
- Global caches, locks, temp files (these must **not** be restored)
- Vector store contents (rebuild via sync)
- System config and secrets (`.env`, `.streamlit/secrets.toml`)
- `var/athletes/<athlete_id>/runs/` (run history)
- `var/athletes/<athlete_id>/logs/` (UI logs)

---

## Backup bundle format

A single archive (zip/tar) with:

```
athlete_backup_<athlete_id>_<timestamp>/
  manifest.json
  checksums.sha256
  athlete/<athlete_id>/
    inputs/
    latest/
    data/
    receipts/
    rendered/        # optional
    runs/            # optional
    logs/            # optional
```

### `manifest.json` (required)
Contains:
- athlete_id
- created_at
- schema_versions (if available)
- list of included paths
- optional: app version / git commit

### `checksums.sha256` (required)
- SHA256 for all files in the bundle for integrity validation.

---

## Backup flow

1. **Lock athlete writes** (short‑lived): prevent concurrent writes while snapshot is created.
2. **Collect files** from required paths.
3. **Write manifest + checksums.**
4. **Package** into archive.
5. **Unlock** athlete writes.

---

## Restore flow

1. **Validate archive** (manifest + checksums).
2. **Verify target athlete** (confirm athlete_id / destination).
3. **Restore files** into `var/athletes/<athlete_id>/`:
   - Ensure `latest/` and `data/` exist before writing.
   - Overwrite allowed (fresh system) or require an empty target.
4. **Rebuild indexes / latest pointers**:
   - Run workspace index maintenance (same logic used at startup).
5. **Invalidate caches / rendered** (optional):
   - If `rendered/` is missing, allow lazy re-render on demand.
6. **Verify** by loading `latest/` artifacts in UI.

---

## UI behavior (Data Operations page)

- **Create Backup** always generates a full archive and provides a download link.
- **Download Last Backup** reuses the most recent bundle in the UI session.
- **Validate Backup** runs checksum validation and reports how many files are in scope (no writes).
- **Show files to restore** lists all files that would be written for the selected restore scope.
- **Summary** shows file counts per top‑level folder (inputs/latest/data/receipts/rendered).
- **Restore Backup** requires a typed confirmation and optional force‑restore into a non‑empty workspace.

---

## Safety & validation rules

- Restore must **reject** if checksums fail.
- Restore should **warn** if:
  - schema versions are ahead of current system
  - required folders are missing
- Restore should **stop** if target athlete dir is non-empty unless `--force`.

---

## UI / CLI entrypoints

- **UI (Athlete Profile → Data Operations)** (implemented)
  - Export button → generates archive
  - Import button → validates + restores

- **CLI (for ops)** (planned)
  - Not implemented yet; use UI for now.

---

## Open decisions

- Encryption at rest for exported bundles (opt-in?).
- (none)

---

## Partial restore modes (supported)

1) **Inputs only**  
   - `inputs/`  
   - Use when re‑planning from scratch.

2) **Plans only**  
   - `data/plans/**` + `latest/` for plan artefacts  
   - Use when migrating plan state without inputs.

3) **Metrics only**  
   - `data/<year>/<week>/activities_actual*`, `latest/activities_trend*`  
   - Use for analysis/reporting without planning data.

4) **Receipts only**  
   - `receipts/`  
   - Preserve Intervals posting history.

5) **Rendered only** (optional)  
   - `rendered/`  
   - UI convenience; safe to omit.
