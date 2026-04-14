---
Version: 1.0
Status: Updated
Last-Updated: 2026-04-14
Owner: UI
---
# Plan Hub Proposal (UI + Readiness Rules)

This document captures the proposed **Plan Hub** layout and readiness logic, and frames the decision of **central Plan page** vs. **separate Plan subpages**.

---

## Implementation status (as of 2026-04-14)

**Implemented**

- Plan Hub page with readiness checklist, direct card actions, advanced manual run, run execution table, latest outputs, and run history.
- KPI Profile is a readiness prerequisite for planning and feed-forward flows.
- Run store (`runtime/athletes/<athlete_id>/runs/<run_id>/run.json`, `steps.json`, `events.jsonl`) with async worker execution.
- Manual scenario selection handoff + restart run (superseded runs tracked).
- Export/post separation with receipts and Intervals commit support.
- Planning actions are blocked while the required local knowledge store is unavailable.
- Phase readiness is shown as one user-facing `Phase` card; `Run Phase` creates Guardrails, Structure, and Preview together.

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
- status banner + knowledge-store state
- `Context` expander (athlete, ISO year/week, selected phase)
- `Quick Actions` with primary `Plan Week` CTA
- `Advanced manual run` expander for generic scoped/orchestrated execution
- Bottom full-width: Run Execution / Latest Outputs / Run History

This follows the current UI contract: global sidebar + always-visible status banner, with the Hub as Summary/Orchestration Layer.

---

### B) Left Column: **Readiness Checklist** (Pipeline)

**Widget structure:**

- `st.subheader("Readiness")`
- `st.container()` → list of `st.expander(step_name, expanded=…)`
  - per step: Status chip + “View” link + “Fix/Run” CTA

**Steps (athlete-facing names | internal keys):**

1. Inputs (Athlete Profile, Planning Events, Logistics, KPI, Availability, Zones, Wellness)
2. Season Scenarios (`season_scenarios`)
3. Scenario Selection (`season_scenario_selection`)
4. **Season Plan** (`season_plan`)
5. **Phase** (`phase`) user-facing combined card backed by:
   - `phase_guardrails`
   - `phase_structure`
   - `phase_preview`
6. **Week Plan** (`week_plan`)
7. Build Workouts (Intervals export) (`workouts_yyyy-ww.json`) *(optional)*

**Per-step display:**

- `status_badge` (✅ ready, ⚠️ stale, ❌ missing, 🔒 blocked)
- “Latest version”: timestamp, run_id, iso_week / iso_week_range
- “Upstream depends on”: short text (“requires Season Plan”, etc.)
- Direct action buttons where applicable (`Run Phase`, `Run Week`, `Run Workouts`)

---

### C) Quick Actions (routine path) + **Advanced Manual Run**

**Widget structure:**

- `st.subheader("Quick Actions")`
- Primary one-click CTA for `Plan Week` / `Plan Next Week`
- Routine planning is expected to happen from:
  - readiness-card direct action buttons
  - the primary `Plan Week` CTA
- `st.expander("Advanced manual run")`
  - `st.radio("Run mode", ["Orchestrated", "Scoped"])`
  - if scoped: `st.selectbox("Scope", ["Season Scenarios", "Selected Scenario", "Season Plan", "Phase", "Week Plan", "Build Workouts"])`
  - optional override text
  - custom `Run ID`
  - `Validate only (no write)`
  - `Run scoped` / `Run orchestrated`

**Design intent**

- The generic run builder remains available, but it is no longer the primary visible control surface.
- The page should emphasize direct artifact actions because Plan Hub already knows readiness, dependencies, and next valid steps.

---

### D) Latest Outputs

**Widget structure:**

- `st.subheader("Latest outputs")`
- current implementation is a latest-outputs table
- richer cards remain a future refinement

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

- Week Plan requires: Phase artefacts (internally Guardrails + Structure; Preview is informational)
- Phase artefacts require: Season Plan
- Season Plan requires: scenario selection (or latest selection) + inputs
- Scenario selection requires KPI guidance segment selection from the KPI Profile.
- Export requires: Week Plan

**Optional (soft)**

- Season Scenarios optional, but recommended when Season changes
- Phase Preview optional/informational
- `season_phase_feed_forward` optional scoped override

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

- `athlete_profile_*.json`
- `planning_events_*.json`
- `logistics_*.json`
- `latest/kpi_profile.json`
- `availability_yyyy-ww.json` (for target year)
- `zone_model` (latest)
- `wellness_yyyy-ww.json` (latest)

**Stale** if:

- availability does not match target year
- wellness/zone_model too old vs target week (policy defines threshold)

#### Step 2: Season Scenarios

- **missing**: no `season_scenarios_yyyy-ww--yyyy-ww`
- **stale**: athlete_profile/planning_events/logistics/kpi_profile newer than scenarios

#### Step 3: Scenario Selection

- **blocked**: scenarios missing
- **stale**: selection older than scenarios (or references a different scenario set)

#### Step 4: Season Plan (`season_plan`)

- **blocked**: selection missing (when required)
- **stale**: selection newer than season overview, or inputs newer (athlete_profile / wellness)

#### Step 5: Phase

- user-facing card is **combined**
- internal readiness sources:
  - `phase_guardrails`
  - `phase_structure`
  - `phase_preview`
- **blocked**: season overview missing or does not cover target week
- **stale**: any required internal phase artefact is stale
- `Run Phase` queues all internal phase artefacts together

#### Step 6: Week Plan

- **blocked**: guardrails or structure missing
- **stale**: guardrails/structure newer, or week mismatch

#### Step 7: Export (workouts_yyyy-ww.json)

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
