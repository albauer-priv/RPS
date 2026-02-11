---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: UI
---
# Streamlit UI (RPS)

Multi-page Streamlit UI that surfaces planning, performance, and system
operations with a consistent global sidebar and status banner.

## Run

From repo root:

```bash
PYTHONPATH=src python3.14 -m streamlit run src/rps/ui/streamlit_app.py
```

## Notes

- Uses the same `.env` as the CLI (`RPS_LLM_API_KEY` is required).
- Non-Coach pages share a global sidebar for athlete + ISO scope.
- All non-Coach pages render a single status banner for last action/result.
- Plan Hub relies on the run store (`runtime/athletes/<athlete_id>/runs/<run_id>/*`) for execution status.

## Plan UI layout contract

This section defines the **layout contract** for the Plan pages in the Streamlit UI.

### Goals

- Keep Plan pages consistent and predictable across Season, Phase, Week, and Workouts.
- Reduce unintended reruns by using `st.form` for primary actions.
- Surface user-visible status at all times.

### Global sidebar (Plan pages)

All Plan pages should use a shared sidebar block that reads/writes the same
session keys. The sidebar is for **global state** only (not heavy IO).

**Required keys**

- `athlete_id`
- `iso_year`
- `iso_week`
- `selected_phase_label` (optional, if Phase selection is shared)
- `ui_dev_mode`

**Sidebar contents (recommended)**

- Athlete selector/input (if applicable)
- ISO Year / ISO Week inputs
- Phase selectbox (when a Season Plan exists and it applies)
- Dev mode toggle
- Optional read-only: latest artifact timestamp

### Status panel (always visible)

Each Plan page must render a **Status Panel** in the main flow.

**State keys**

- `status_state` (enum: "idle" | "running" | "done" | "error")
- `status_title`
- `status_message`
- `status_last_run_id`
- `status_last_action`

**Placement**

Title -> Context -> Action Panel -> Status Panel -> Main Content -> Details/Debug

### Page layout contracts

#### Plan -> Plan Hub

**Header**

- Scope panel (athlete, ISO year/week, phase) + primary CTA (Plan this Week).
- CTA preselects **Plan Next Week** if the current week is fully ready; otherwise **Plan Week**.
- Status banner summarizing readiness/run state.

**Body**

- Readiness checklist with reasons + fix CTAs (planning-only; performance report readiness is on Performance pages).
- KPI Profile is a readiness prerequisite for planning and feed-forward flows.
- Run planning panel (mode, scope, run id, validate-only, scoped override input).
- Run execution table (steps, status, outputs, events).
- Scheduler guards block overlapping runs (same type/subtype) and prevent lower-priority planning runs while higher-priority runs are active.
- Reset/Delete actions remove latest artefacts; delete also clears scenarios + selection while reset keeps them.

**Readiness + Auto-run rules**

- **Readiness evaluation** is deterministic and based on `latest/` artifacts only.
- **Stale detection** compares timestamps and ISO week ranges.
- **Auto-run safety:** only write missing or outdated artifacts.
- **No dangling artifacts:** every flow must leave `latest/` fully updated for all artifacts it owns.
- **Replace semantics:** when an artifact is regenerated, delete the existing `latest/` copy first, then write the new version.
- **Prerequisites:** planning actions run only when required upstream artifacts exist and the target week is within the active Season Plan ISO range.
- **Simplicity:** prefer a single CTA and minimal decision points; advanced toggles stay in an optional panel (auto-post, allow delete, validation only).

#### Plan -> Season

**Action panel (forms)**

- Form: Scenario Selection (radio + KPI segment selector + rationale + submit)
- Season Plan creation + Reset/Delete are executed from Plan Hub.
- Create Scenarios is initiated from Plan Hub.

**Main content**

- If Season Plan exists: render plan + scenario summary + phase expanders (metadata onward).
- Else: show scenarios list -> selection flow + handoff message to Plan Hub.

#### Plan -> Phase

**Action panel**

- Optional form: phase selectbox + submit (if avoiding rerun on selection).

**Main content**

- Selected phase markdown
- Phase preview table
- Weekly agenda expanders

#### Plan -> Week

**Main content**

- Weekly agenda + workout cards
- System logs expander

#### Plan -> Workouts

**Action panel**

- Form: Post to Intervals, Delete posted, Revise Week Plan
- Posting status: unposted/updates/conflicts

**Main content**

- Current week workouts (from Intervals export)
- History grouped by month -> week -> workouts

### Performance pages

#### Performance -> Feed Forward
- Last-week DES recommendation (Season Planner focus)
- Performance Report readiness (DES analysis availability for last week)
- Trigger Season → Phase and Phase → Week feed-forward
- Feed-forward artefact table + process status

#### Performance -> Report
- Performance Report readiness (DES analysis availability for selected week)
- Report creation action
- Narrative Report + KPI Summary + Trend Analysis expanders (no raw JSON)

#### Performance -> Data & Metrics
- Manual "Refresh Intervals Data" action (background pipeline run)
- Weekly load chart includes season/phase/week corridor min/max overlays
- Charts + tables based on activities/trends

### System pages

#### System -> Status
- Running processes with filters (status/type/subtype)
- Latest artefacts list (latest per type)
- Cancel selected runs + reset controls (queues/locks/logs) live here

#### System -> History
- Latest outputs table (with diff/versions)
- Run history tables (planning + data)
- Historical artefacts grouped by month with Season/Phase/Week focus

#### System -> Log
- System log output + log level selector (persist to .env)
- Live log file tail (rps.log) displayed in the log panel

### Notes

- Use `st.form` for primary actions to prevent unintended reruns.
- Avoid expensive IO in the sidebar; do it after submit.
- Status Panel should show "Idle" when no action is in progress.
