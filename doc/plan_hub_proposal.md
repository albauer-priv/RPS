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

## 1) Streamlit-Komponentenstruktur (Seitenlayout + Widgets)

### A) Page Skeleton (Top-level)

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

**Widget-Struktur:**

- `st.subheader("Readiness")`
- `st.container()` → Liste aus `st.expander(step_name, expanded=…)`
  - pro Step: Status-Chip + “View” Link + “Fix/Run” CTA

**Steps (athlete-facing Names | internal keys):**

1. Inputs (Season Brief, Events, KPI, Availability, Zones, Wellness)
2. Season Scenarios (`season_scenarios`)
3. Scenario Selection (`season_scenario_selection`)
4. **Season Plan** (`season_plan`)
5. **Phase Guardrails** (`phase_guardrails`)
6. **Phase Structure** (`phase_structure`)
7. **Phase Preview** (`phase_preview`) *(optional / informational)*
8. **Week Plan** (`week_plan`)
9. Export (Intervals) (`workouts_yyyy-ww.json`)

**Pro Step anzeigen:**

- `status_badge` (✅ ready, ⚠️ stale, ❌ missing, 🔒 blocked)
- “Latest version”: timestamp, run_id, iso_week / iso_week_range
- “Upstream depends on”: kurzer Text (“requires Season Plan”, etc.)

---

### C) Right Column: **Runner Panel** (Orchestrator + Scoped Runs)

**Widget-Struktur:**

- `st.subheader("Run Planning")`
- `st.radio("Run mode", ["Orchestrated (recommended)", "Scoped"])`
- Wenn Scoped:
  - `st.selectbox("Scope", ["Season Scenarios", "Scenario Selection", "Season Plan", "Phase (Guardrails + Structure)", "Week Plan", "Export Workouts"])`
  - `st.text_area("Override", ...)`
- `st.text_input("Run ID", value=auto_run_id())`
- `st.checkbox("Validate only (no write)", value=False)` → mapped auf `validate_outputs.py`
- `st.button("Run")`

**Run Scope Summary (read-only)**

- `st.info()` mit: “This run will create new versions of: … (Binding/Informational/Advisory)”
- Wichtig wegen append‑only + latest pointers.

---

### D) Right Column: **Latest Artefacts Cards**

**Widget-Struktur:**

- `st.subheader("Latest outputs")`
- grid mit `st.columns(2)` und pro Card:
  - Title (Season Plan, Phase Guardrails, …)
  - Badge: Binding / Informational / Advisory
  - Key metrics (z. B. total kJ corridor / key sessions / build:deload pattern)
  - Buttons: “Open” (deep link) + “Diff” + “Versions”

Authority‑Labels kommen direkt aus dem Artefaktmodell.

---

### E) Bottom: **Run History / Activity Feed**

**Widget-Struktur:**

- `st.subheader("Run History")`
- `st.dataframe(run_table)` oder Feed-Ansicht
- pro Row: timestamp, run_id, scope, result, artefacts_written_count + Links (“Logs”, “Outputs”, “Diff”)

---

## 2) Readiness-Regeln (missing / stale / blocked / ready)

### Grundidee

Pipeline mit harten Dependencies (Binding) → deterministische UI‑Prüfung:

**Macro → Meso → Micro → Builder → Analysis**

- Macro outputs: `season_plan`
- Meso outputs: `phase_guardrails`, `phase_structure` (+ optional preview)
- Micro outputs: `week_plan`
- Builder outputs: `workouts_yyyy-ww.json`
- Analysis outputs: `des_analysis_report`

---

### A) Dependency Graph (für den Hub)

**Required (hard)**

- Week Plan requires: Phase Guardrails + Phase Structure (+ availability, zones as info)
- Phase artefacts require: Season Plan
- Season Plan requires: scenario selection (oder latest selection) + inputs
- Scenario selection requires KPI guidance segment selection from the KPI Profile.
- Export requires: Week Plan
 

**Optional (soft)**

- Season Scenarios optional, aber wenn Macro neu: empfohlen
- Phase Preview optional/informational
- `macro_meso_feed_forward` / `block_feed_forward` optional scoped override

---

### B) Status-Definitionen (präzise)

For each artefact `A` and context (athlete_id, ISO year/week, selected phase):

#### 1) **missing (❌)**

- Kein passendes Artefakt vorhanden:
  - week artefacts: `meta.iso_week == target`
  - range artefacts: `meta.iso_week_range` deckt target week ab
  - “latest/” pointer existiert nicht

#### 2) **blocked (🔒)**

- Artefakt fehlt **und** mindestens ein *required upstream* ist missing/blocked
  - z. B. `workouts_plan` blocked, wenn `block_governance` oder `block_execution_arch` fehlt

#### 3) **stale (⚠️)**

Mindestens eines:

- Upstream ist **neuer** als Artefakt (by `meta.created_at` / index timestamp / version ordering)
- Artefakt passt nicht zum Kontext:
  - week mismatch: `workouts_plan` existiert, aber anderes `iso_week`
  - range mismatch: `block_execution_arch` deckt target week nicht ab
- Schema‑Validierung schlägt fehl (`validate_outputs.py`)

#### 4) **ready (✅)**

- vorhanden, validiert, passt zum Kontext, und kein required upstream ist newer

---

### C) Step-spezifische Regeln (Pipeline Checkliste)

#### Step 1: Inputs (Ready wenn Mindestset da)

**Required inputs (pragmatisch):**

- `season_brief_yyyy.md`
- `events.md`
- `latest/kpi_profile.json`
- `availability_yyyy-ww.json` (für target year)
- `zone_model` (latest)
- `wellness_yyyy-ww.json` (latest)

**Stale** wenn:

- availability nicht zum Jahr passt
- wellness/zone_model sehr alt vs target week (Policy definieren, z. B. >4 Wochen)

#### Step 2: Season Scenarios

- **missing**: kein `season_scenarios_yyyy-ww--yyyy-ww`
- **stale**: season_brief/events/kpi_profile newer als scenarios

#### Step 3: Scenario Selection

- **blocked**: scenarios missing
- **stale**: selection älter als scenarios (oder bezieht sich auf anderes scenario set)

#### Step 4: Season Plan (`season_plan`)

- **blocked**: selection missing (wenn zwingend)
- **stale**: selection newer als macro_overview, oder inputs newer (season_brief / wellness)

#### Step 5/6: Phase Guardrails + Phase Structure

- **blocked**: macro_overview missing oder deckt target week nicht ab
- **stale**: macro_overview newer oder zone_model newer (wenn relevant)

#### Step 7: Phase Preview (optional)

- **never blocks** downstream
- **stale** nur kosmetisch (wenn arch/governance newer)

#### Step 8: Week Plan

- **blocked**: guardrails oder structure missing
- **stale**: guardrails/structure newer, oder week mismatch

#### Step 9: Export (workouts_yyyy-ww.json)

- **blocked**: week plan missing
- **stale**: workouts_plan newer als export

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
    for step in readiness:
        with st.expander(f"{step.badge} {step.label}", expanded=step.expanded):
            st.write(step.summary)
            st.caption(step.reason)
            c1, c2 = st.columns(2)
            c1.button("Open", on_click=open_deeplink, args=[step.deeplink])
            if step.can_run:
                c2.button(step.run_label, on_click=run_scoped, args=[ctx, step.scope])

with right:
    st.subheader("Run Planning")
    mode = st.radio("Run mode", ["Orchestrated (recommended)", "Scoped"])
    scope = None
    override_text = None
    if mode == "Scoped":
        scope = st.selectbox("Scope", SCOPES)
        override_text = st.text_area("Override")

    run_id = st.text_input("Run ID", value=auto_run_id(ctx))
    validate_only = st.checkbox("Validate only (no write)", value=False)

    st.info(run_scope_summary(ctx, mode, scope))
    st.button("Run", on_click=run_planning, args=[ctx, mode, scope, override_text, run_id, validate_only])

    st.subheader("Latest outputs")
    cards = get_latest_cards(ctx)
    render_cards(cards)

st.subheader("Run History")
render_run_history(ctx)
```

---

## 4) UI Details that make “stale/blocked” usable

- **Every stale/blocked status needs “Reason + Fix”**
  - Reason: “Phase Guardrails missing for week 2026-W06”
  - Fix: Button “Run Phase (Guardrails + Structure)”
- **Authority badges should be consistent**
  - Binding (Season Plan / Phase Guardrails / Phase Structure / Week Plan)
  - Informational (Phase Preview, Zones, Wellness)
  - Advisory (DES report)

---

## 5) Decision Context

The decision is whether to:

1) Keep **separate Plan pages** (Season/Phase/Week/Workouts), or  
2) Build a **central Plan Hub** with readiness and model execution view.

This proposal assumes the Hub is a **summary + orchestration layer**, with deep links to existing pages.
