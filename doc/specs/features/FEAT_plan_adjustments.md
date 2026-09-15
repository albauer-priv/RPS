---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: UI / Planning
---
# FEAT: Plan Adjustments (Input-Driven Staleness & Adjustment Suggestions)

* **ID:** FEAT_plan_adjustments
* **Status:** Draft
* **Owner/Area:** UI / Planning
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/ui/pages/plan/hub.py`, `src/rps/workspace/local_store.py`, `FEAT_user_inputs_modular`, `FEAT_user_data_editors`

---

## 1) Context / Problem

**Current behavior**

* The Plan Hub readiness system detects staleness *between plan artifacts* (e.g., Phase stale when Season Plan is newer) by comparing `created_at` timestamps from `index.json`.
* The inputs check (`_inputs_readiness_step`) verifies only that the four modular inputs exist — it does not compare input recency against the plan artifacts that depend on them.

**Problem**

* A user who updates their Availability after running a Phase plan will see "Phase: Ready" in the hub — no indication that the Phase was generated from stale inputs.
* There is no affordance to re-run just the affected downstream scope (Phase, Week Plan) when inputs change, without the user manually reasoning through the dependency chain.

**Constraints**

* Must not change the existing readiness pipeline contract (no breaking changes to `ReadinessStep` or `_compute_readiness`).
* Must reuse the existing scoped-run machinery (Scoped mode + scope selector in the hub).
* No new agent prompts, no new artifact types.
* Input timestamps must be read from `index.json` (same source as plan artifact timestamps) — no mtime/filesystem comparisons.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Detect when a modular input (ATHLETE_PROFILE, AVAILABILITY, PLANNING_EVENTS, LOGISTICS) has a `created_at` newer than the plan artifact it influences.
* [x] Surface adjustment suggestions in the Plan Hub as a dedicated UI section ("Plan Adjustment").
* [x] Each suggestion shows which input changed, which plan scope is affected, and when each was last updated.
* [x] Each suggestion has a one-click "Run Adjustment" button that pre-selects the appropriate scope and triggers the scoped run.
* [x] Tests for suggestion detection logic (unit, independent of Streamlit).

**Non-Goals**

* [ ] Changing planner agent prompts or output schemas.
* [ ] Automatic/scheduled adjustment runs.
* [ ] Adjusting Season Scenarios or Scenario Selection based on input changes (these are always user-driven).
* [ ] Per-field diff showing exactly what changed inside an input artifact.
* [ ] Blocking planning runs when inputs are stale (suggestions are advisory, not gating).

---

## 3) Proposed Behavior

### Input → Scope Dependency Map

| Input Artifact | Input Label | Affected Plan Artifact | Scope |
|---|---|---|---|
| ATHLETE_PROFILE | About You & Goals | SEASON_PLAN | Season Plan |
| PLANNING_EVENTS | Events | SEASON_PLAN | Season Plan |
| AVAILABILITY | Availability | PHASE_GUARDRAILS | Phase |
| LOGISTICS | Logistics | WEEK_PLAN | Week Plan |

### Suggestion logic

For each row in the table:
1. If the input artifact does not exist → skip (nothing to compare).
2. If the plan artifact does not exist → skip (readiness system handles "missing" state; no adjustment needed).
3. Compare `created_at` timestamps from `index.json`.
4. If `input.created_at > plan.created_at` → emit an `AdjustmentSuggestion`.

When multiple inputs map to the same scope (ATHLETE_PROFILE + PLANNING_EVENTS → Season Plan), they may each produce a suggestion for that scope, but the UI deduplicates by scope and shows the highest-priority (most-recently updated) input for each scope.

### UI section in Plan Hub

* Rendered just above the "Pipeline Readiness" section.
* Title: **"Plan Adjustment"**.
* When no suggestions exist: section is hidden (not rendered).
* When suggestions exist: section is always expanded (no collapsing).
* Each suggestion row shows:
  * Input label (e.g., "Availability")
  * Input updated timestamp
  * Affected scope label (e.g., "Phase")
  * Plan artifact last updated timestamp
  * A button: **"Run [Scope] Adjustment"** (e.g., "Run Phase Adjustment")
* Clicking the button sets `st.session_state["scope"]` to the scope label and triggers `st.rerun()`, which pre-selects that scope in the existing "Scoped" run panel below.

---

## 4) Implementation Analysis

### New module: `src/rps/orchestrator/plan_adjustments.py`

```python
@dataclass(frozen=True)
class AdjustmentSuggestion:
    input_label: str
    input_artifact_type: ArtifactType
    input_created_at: str          # ISO-8601
    plan_label: str
    plan_artifact_type: ArtifactType
    plan_created_at: str           # ISO-8601
    scope: str                     # "Season Plan" | "Phase" | "Week Plan"

INPUT_PLAN_DEPS: list[tuple[ArtifactType, str, ArtifactType, str, str]] = [...]

def get_adjustment_suggestions(
    index: JsonMap,
    store: LocalArtifactStore,
    athlete_id: str,
) -> list[AdjustmentSuggestion]:
    ...
```

* `index` is the `WorkspaceIndexManager.load()` map — same source the hub already uses.
* `store` is used to guard `latest_exists()` so only persisted `latest` artifacts are compared.
* Returns suggestions sorted by scope priority (Season Plan > Phase > Week Plan).
* Pure Python; no Streamlit; no I/O beyond what `index` already holds.

### Hub UI: `src/rps/ui/pages/plan/hub.py`

* Add import: `from rps.orchestrator.plan_adjustments import AdjustmentSuggestion, get_adjustment_suggestions`
* Add `_show_adjustment_section(athlete_id: str, index: JsonMap, store: LocalArtifactStore) -> None`:
  * Calls `get_adjustment_suggestions(index, store, athlete_id)`.
  * If empty: returns immediately (section hidden).
  * Otherwise renders an `st.subheader("Plan Adjustment")` block with one row per unique scope.
  * Button click: `st.session_state["run_mode"] = "Scoped"; st.session_state["run_scope"] = suggestion.scope; st.rerun()`
* Call `_show_adjustment_section` from the main render, before the readiness panel.

### Tests: `tests/test_plan_adjustments.py`

* Parametrize over all four input/scope pairs.
* Cases: no suggestions (input older), suggestion (input newer), no suggestion when plan missing, no suggestion when input missing.
* All tests are pure unit tests using a real (temp-dir) `LocalArtifactStore` and a hand-built `index` dict.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes. The existing readiness pipeline and scoped-run machinery are unchanged.
* No new artifact types, no new run-store event types.

**Impacted areas**

* Plan Hub: new section above readiness panel, no change to existing sections.
* New module `plan_adjustments.py`: pure logic, independently testable.
* Tests: new file.

---

## 6) Options & Recommendation

### Option A (recommended) — Separate `AdjustmentSuggestion` layer

* Keeps readiness pipeline unchanged.
* Logic is independently testable.
* UI is an additive section, no risk of breaking existing hub behavior.

### Option B — Integrate inputs into the readiness chain

* Add per-input `ReadinessStep` records; add them to `required` lists for plan artifacts.
* Would make stale badges appear in the existing readiness table.
* More invasive; changes the readiness chain contract; risks breaking existing hub tests.

### Recommendation

Option A — additive layer is the safe, focused path.

---

## 6a) Implementation Readiness Review

* [x] Scope completeness: new module + hub section + tests named.
* [x] Decision completeness: timestamp source (index.json), scope map, UI behavior all specified.
* [x] Architecture conformity: reuses existing scoped-run machinery, no new agent calls.
* [x] Execution readiness: can implement without inventing missing behavior.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `get_adjustment_suggestions` returns an `AdjustmentSuggestion` for each input that is newer than its downstream plan artifact (both must exist).
* [x] No suggestion emitted when input is older than the plan artifact.
* [x] No suggestion emitted when either artifact is missing.
* [x] Plan Hub shows "Plan Adjustment" section only when suggestions exist.
* [x] "Run [Scope] Adjustment" button pre-selects the scope in the Scoped run panel.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `./scripts/run_lint.sh`
* [x] Validation passes: `./scripts/run_typecheck.sh`
* [x] Validation passes: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_plan_adjustments.py -x`

---

## 8) Migration / Rollout

* No data migration required.
* Safe to deploy immediately.

---

## 9) Risks & Failure Modes

* **Risk**: `created_at` missing from index record.
  * Mitigation: treat as None → skip comparison → no suggestion emitted (safe fallback).
* **Risk**: Clock skew between machines producing index entries.
  * Mitigation: suggestions are advisory only; no planning is blocked.

---

## 10) Observability / Logging

* `get_adjustment_suggestions` logs at DEBUG level when it emits a suggestion.
* No new event types needed.

---

## 11) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.

---

## 12) Link Map

* `doc/overview/feature_backlog.md`
* `src/rps/orchestrator/plan_adjustments.py`
* `src/rps/ui/pages/plan/hub.py`
* `tests/test_plan_adjustments.py`
