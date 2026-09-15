---
Version: 1.0
Status: Draft
Last-Updated: 2026-09-15
Owner: UI / Data Model
---
# FEAT: User Inputs I/O (Export / Import per Input Type)

* **ID:** FEAT_user_inputs_io
* **Status:** Draft
* **Owner/Area:** UI / Data Model
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/ui/pages/athlete_profile/`, `src/rps/workspace/local_store.py`, `FEAT_user_inputs_modular`

---

## 1) Context / Problem

**Current behavior**

* Modular inputs (Athlete Profile, Availability, Events, Logistics) are edited via form pages and saved as versioned artifacts in the workspace.
* The Data Operations page offers a full workspace backup/restore (zip archive) but no per-input-type file operations.

**Problem**

* Moving inputs between athletes or environments requires a full backup/restore, which is all-or-nothing and destructive.
* Coaches or athletes cannot easily share a single input file (e.g., a template availability schedule or a reference logistics setup).
* There is no lightweight way to checkpoint a single input before making changes to it.

**Constraints**

* Import must not bypass the store's versioning contract — imported inputs must go through `save_version` with proper metadata.
* Export must produce a self-identifying file (includes artifact type) so imports can validate the correct type.
* No new artifact types or schema changes.
* Must work within existing Streamlit page structure (file uploader / download button widgets).

---

## 2) Goals & Non-Goals

**Goals**

* [x] Export any of the four modular input artifacts (ATHLETE_PROFILE, AVAILABILITY, PLANNING_EVENTS, LOGISTICS) as a JSON file from its editor page.
* [x] Import a previously exported input JSON file via the same page, saving it as a new version.
* [x] Shared `input_io.py` helper module usable from all input pages without duplication.
* [x] Import validates artifact type header before writing.
* [x] Tests for export, import, and type-mismatch rejection.

**Non-Goals**

* [ ] Bulk import/export of multiple input types at once (covered by backup/restore).
* [ ] Editing the imported data in the form before saving (import goes directly to store; the user can then edit in the form as usual).
* [ ] Schema migration or transformation during import.
* [ ] Importing artifacts other than the four modular inputs.

---

## 3) Proposed Behavior

**Export**

* On each input editor page (About You & Goals, Availability, Events, Logistics), an "Export / Import" expander appears at the bottom.
* Clicking "Download as JSON" downloads the latest saved input as a file named `<athlete_id>_<ARTIFACT_TYPE>_<YYYYMMDD>.json`.
* If no input is saved yet, the button is disabled with a caption explaining that saving a value first is required.
* Export format:
  ```json
  {
    "artifact_type": "ATHLETE_PROFILE",
    "exported_at": "2026-09-15T10:00:00Z",
    "athlete_id": "athlete_1",
    "data": { ... }
  }
  ```

**Import**

* The same expander shows a file uploader accepting `.json` files.
* After upload, the page shows a preview of the `artifact_type` and a button "Save imported input".
* On save: validates `artifact_type` matches the page's expected type; if mismatch, shows an error.
* On success: saves via `save_version` with the same authority/metadata as a normal form save; reloads the form.
* Import does **not** overwrite existing versions — it adds a new version (same behavior as a normal form save).

**UI placement**

* Expander at the bottom of each input editor page, below the Save button.
* Title: "Export / Import".
* Collapsed by default.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/workspace/input_io.py` (new):
  * `INPUT_IO_TYPES: frozenset[ArtifactType]` — the four supported types.
  * `INPUT_META: dict[ArtifactType, dict]` — per-type schema_id, schema_version, authority defaults.
  * `export_input(store, athlete_id, artifact_type) -> bytes | None` — returns JSON bytes of the export envelope, or None if no artifact is saved.
  * `import_input(store, athlete_id, artifact_type, raw_bytes) -> str` — parses, validates type header, writes via save_version; returns version_key on success; raises ValueError on type mismatch or parse error.
  * `suggest_export_filename(athlete_id, artifact_type) -> str` — `<athlete_id>_<type>_<YYYYMMDD>.json`.

* Input editor pages (4 files modified):
  * `src/rps/ui/pages/athlete_profile/about_you.py`
  * `src/rps/ui/pages/athlete_profile/availability.py`
  * `src/rps/ui/pages/athlete_profile/events.py`
  * `src/rps/ui/pages/athlete_profile/logistics.py`
  * Each gains an "Export / Import" expander at the bottom using the shared helper.

* `tests/test_input_io.py` (new): unit tests for the helper, independent of Streamlit.

**Data flow**

* Export: `store.latest_path(athlete_id, artifact_type)` → read file → extract `data` key → wrap in envelope → encode JSON → download.
* Import: upload bytes → parse JSON → check `artifact_type` → extract `data` → `store.save_version(...)` with authority=BINDING, producer_agent="ui_import".

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none (import adds a new version like any form save).

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* No existing behavior changed.

**Impacted areas**

* UI: 4 input editor pages gain an export/import expander.
* Workspace: no contract change; new versions written via existing `save_version`.
* Tests: new test file.

---

## 6) Options & Recommendation

### Option A (recommended) — Shared helper + per-page expander

* Thin shared module, minimal per-page code (3–5 lines each).
* Type header in export file enables validation on import.

### Option B — Form-mediated import (populate form, user saves)

* Upload populates form fields before save → user reviews then saves.
* More complex: each page has a different form structure, requires a separate "load from import" branch on every page.

### Recommendation

Option A — direct save is simpler and consistent with the backup/restore pattern; the user can always re-edit after import.

---

## 6a) Implementation Readiness Review

* [x] Scope completeness: 4 pages + shared helper + tests named.
* [x] Decision completeness: export format, import validation, metadata shape all specified.
* [x] Architecture conformity: uses existing save_version path, no schema changes.
* [x] Execution readiness: can implement without inventing missing behavior.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `export_input` returns a JSON-parseable byte string containing `artifact_type`, `data`, `exported_at`, `athlete_id`.
* [x] `import_input` writes a new version when artifact type matches; raises ValueError on mismatch.
* [x] Each of the four input pages shows an "Export / Import" expander with working download and upload paths.
* [x] Import of a file with a wrong `artifact_type` shows an error in the UI (does not save).
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `./scripts/run_lint.sh`
* [x] Validation passes: `./scripts/run_typecheck.sh`
* [x] Validation passes: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_input_io.py -x`

---

## 8) Migration / Rollout

* No data migration required.
* Safe to deploy immediately.

---

## 9) Risks & Failure Modes

* **Risk**: import writes malformed data to store.
  * Mitigation: `import_input` checks that the parsed `data` value is a dict/list (matching the existing artifact type's shape); invalid JSON raises ValueError before any write.
* **Risk**: type mismatch not caught (user uploads wrong file).
  * Mitigation: `artifact_type` header in export file is checked against the page's expected type on every import attempt.

---

## 10) Observability / Logging

* Import and export log at INFO level in the existing workspace logger.
* No new event types needed.

---

## 11) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.

---

## 12) Link Map

* `doc/overview/feature_backlog.md`
* `src/rps/workspace/input_io.py`
* `src/rps/ui/pages/athlete_profile/about_you.py`
* `src/rps/ui/pages/athlete_profile/availability.py`
* `src/rps/ui/pages/athlete_profile/events.py`
* `src/rps/ui/pages/athlete_profile/logistics.py`
* `tests/test_input_io.py`
