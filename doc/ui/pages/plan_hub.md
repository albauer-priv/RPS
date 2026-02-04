---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: UI
---
# Plan Hub Proposal (UI + Readiness Rules)

This document captures the proposed **Plan Hub** layout and readiness logic, and frames the decision of **central Plan page** vs. **separate Plan subpages**.

---

## Implementation status (as of 2026-01-31)

**Implemented**

- Plan Hub page with readiness checklist, run controls, run execution table, latest outputs, and run history.
- KPI Profile is a readiness prerequisite for planning and feed-forward flows.
- Run store (`runs/<run_id>/run.json`, `steps.json`, `events.jsonl`) with async worker execution.
- Manual scenario selection handoff + restart run (superseded runs tracked).
- Export/post separation with receipts and Intervals commit support.

**Partially implemented**

- Readiness reasons + fix CTAs are present; refine reason granularity and upstream diffs as needed.
- Run scope summaries exist; expand with binding/informational/advisory grouping where helpful.

**Not implemented (still proposed)**

- Latest outputs card layout with per-card key metrics (currently a table).
- Optional "Run Execution" live polling tied to worker events (events table available; live polling tuning remains).
- Rich per-step dependency viewer (upstream “why” drilldown).

---

## 1) Streamlit component structure (layout + widgets)

### A) Page skeleton (top-level)

**Layout:**

- `st.title("Plan Hub")`
- `st.caption(context pills: athlete_id, ISO year/week, selected phase, run mode)`
- `st.columns([1, 2])`
  - **Left column:** Readiness Checklist + “Next action”
  - **Right column:** Runner Panel + Latest Artefacts Cards
- Bottom full-width: Run History / Activity Feed

This follows the current UI contract: global sidebar + always-visible status banner, with the Hub as Summary/Orchestration Layer.

---

### B) Left Column: **Readiness Checklist** (Pipeline)

**Widget structure:**

- `st.subheader("Readiness")`
- `st.container()` → list of `st.expander(step_name, expanded=…)`
  - per step: Status chip + “View” link + “Fix/Run” CTA

**Steps (athlete-facing names | internal keys):**

1. Inputs (Season Brief, Events, KPI, Availability, Zones, Wellness)
2. Season Scenarios (`season_scenarios`)
3. Scenario Selection (`season_scenario_selection`)
4. **Season Plan** (`season_plan`)
5. **Phase Guardrails** (`phase_guardrails`)
6. **Phase Structure** (`phase_structure`)
7. **Phase Preview** (`phase_preview`) *(optional / informational)*
8. **Week Plan** (`week_plan`)
9. Build Workouts (Intervals export) (`workouts_yyyy-ww.json`) *(optional)*

**Per-step display:**

- `status_badge` (✅ ready, ⚠️ stale, ❌ missing, 🔒 blocked)
- “Latest version”: timestamp, run_id, iso_week / iso_week_range
- “Upstream depends on”: short text (“requires Season Plan”, etc.)

---

### C) Right Column: **Runner Panel** (Orchestrator + Scoped Runs)

**Widget structure:**

- `st.subheader("Run Planning")`
- `st.radio("Run mode", ["Orchestrated (recommended)", "Scoped"])`
- If Scoped:
  - `st.selectbox("Scope", ["Season Scenarios", "Scenario Selection", "Season Plan", "Phase (Guardrails + Structure)", "Week Plan", "Build Workouts"])`
  - `st.text_area("Override", ...)`
- `st.text_input("Run ID", value=auto_run_id())`
- `st.checkbox("Validate only (no write)", value=False)` → mapped to `validate_outputs.py`
- `st.button("Run")` (run control + cancellation are handled from System → Status)

**Run Scope Summary (read-only)**

- `st.info()` text: “This run will create new versions of: … (Binding/Informational/Advisory)”
- Important for append‑only + latest pointers.

---

### D) Right Column: **Latest Artefacts Cards**

**Widget structure:**

- `st.subheader("Latest outputs")`
- grid with `st.columns(2)` and per card:
  - Title (Season Plan, Phase Guardrails, …)
  - Badge: Binding / Informational / Advisory
  - Key metrics (e.g., total kJ corridor / key sessions / build:deload pattern)
  - Buttons: “Open” (deep link) + “Diff” + “Versions”

Authority labels come directly from the artefact model.

---

### E) Bottom: **Run History / Activity Feed**

**Widget structure:**

- `st.subheader("Run History")`
- `st.dataframe(run_table)` or feed view
- per row: timestamp, run_id, scope, result, artefacts_written_count + links (“Logs”, “Outputs”, “Diff”)

---

## 2) Readiness rules (missing / stale / blocked / ready)

### Core idea

Pipeline with hard dependencies (Binding) → deterministic UI checks:

**Season → Phase → Week → Builder → Analysis**

- Season outputs: `season_plan`
- Phase outputs: `phase_guardrails`, `phase_structure` (+ optional preview)
- Week outputs: `week_plan`
- Builder outputs: `workouts_yyyy-ww.json`
- Analysis outputs: `des_analysis_report`

---

### A) Dependency graph (for the Hub)

**Required (hard)**

- Week Plan requires: Phase Guardrails + Phase Structure (+ availability, zones as info)
- Phase artefacts require: Season Plan
- Season Plan requires: scenario selection (or latest selection) + inputs
- Scenario selection requires KPI guidance segment selection from the KPI Profile.
- Export requires: Week Plan

**Optional (soft)**

- Season Scenarios optional, but recommended when Season changes
- Phase Preview optional/informational
- `macro_meso_feed_forward` / `block_feed_forward` optional scoped override

---

### B) Status definitions (precise)

For each artefact `A` and context (athlete_id, ISO year/week, selected phase):

#### 1) **missing (❌)**

- No matching artefact exists:
  - week artefacts: `meta.iso_week == target`
  - range artefacts: `meta.iso_week_range` covers target week
  - “latest/” pointer missing

#### 2) **blocked (🔒)**

- Artefact missing **and** at least one *required upstream* is missing/blocked
  - e.g. `workouts_plan` blocked when `block_governance` or `block_execution_arch` is missing

#### 3) **stale (⚠️)**

At least one of:

- Upstream is **newer** than artefact (by `meta.created_at` / index timestamp / version ordering)
- Artefact does not match context:
  - week mismatch: `workouts_plan` exists, but different `iso_week`
  - range mismatch: `block_execution_arch` does not cover target week
- Schema validation fails (`validate_outputs.py`)

#### 4) **ready (✅)**

- Present, validated, matches context, and no required upstream is newer

---

### C) Step-specific rules (Pipeline checklist)

#### Step 1: Inputs (Ready when minimum set exists)

**Required inputs (pragmatic):**

- `season_brief_yyyy.md`
- `events.md`
- `latest/kpi_profile.json`
- `availability_yyyy-ww.json` (for target year)
- `zone_model` (latest)
- `wellness_yyyy-ww.json` (latest)

**Stale** if:

- availability does not match target year
- wellness/zone_model too old vs target week (policy defines threshold)

#### Step 2: Season Scenarios

- **missing**: no `season_scenarios_yyyy-ww--yyyy-ww`
- **stale**: season_brief/events/kpi_profile newer than scenarios

#### Step 3: Scenario Selection

- **blocked**: scenarios missing
- **stale**: selection older than scenarios (or references a different scenario set)

#### Step 4: Season Plan (`season_plan`)

- **blocked**: selection missing (when required)
- **stale**: selection newer than macro_overview, or inputs newer (season_brief / wellness)

#### Step 5/6: Phase Guardrails + Phase Structure

- **blocked**: macro_overview missing or does not cover target week
- **stale**: macro_overview newer or zone_model newer (when relevant)

#### Step 7: Phase Preview (optional)

- **never blocks** downstream
- **stale** only cosmetic (when arch/governance newer)

#### Step 8: Week Plan

- **blocked**: guardrails or structure missing
- **stale**: guardrails/structure newer, or week mismatch

#### Step 9: Export (workouts_yyyy-ww.json)

- **blocked**: week plan missing
- **stale**: workouts_plan newer than export

---

## 3) Pseudocode (Streamlit)

```python
st.title("Plan Hub")

# Context strip from global sidebar selections
ctx = get_ctx_from_sidebar()  # athlete_id, year, week, phase_id

left, right = st.columns([1, 2])

with left:
    st.subheader("Readiness")
    readiness = compute_readiness(ctx)
```
