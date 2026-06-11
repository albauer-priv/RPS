---
Version: 1.0
Status: Implemented
Last-Updated: 2026-06-11
Owner: Planning / Orchestration
---
# FEAT: Shift-Left Planning Evidence Alignment

* **ID:** FEAT_shift_left_planning_evidence_alignment
* **Status:** Implemented
* **Owner/Area:** Planning / Orchestration
* **Last-Updated:** 2026-06-11
* **Related:** `season_flow.py`, `plan_week.py`, `context_snapshots.py`, `week_engine.py`

---

## 1) Context / Problem

**Current behavior**

* Season, Phase, and Week planning can read some historical evidence, but the timing and scope are inconsistent.
* Historical activity context was previously resolved as the latest week before the target week, not the exact previous week.
* Phase and Week planning could start without first ensuring that the previous completed week had a current `DES_ANALYSIS_REPORT`.
* Evidence interpretation was not an explicit early planning stage.

**Problem**

* The planner can synthesize structure before it has a stable evidence view for the completed prior week.
* Previous-week evidence and report freshness were not enforced by one deterministic rule.
* Week planning has a deterministic runtime path, so prompt-only evidence work would not affect the real planner.

**Constraints**

* Planning target week `W` may only consume weekly evidence from completed week `W - 1`.
* `DES_ANALYSIS_REPORT`, `ACTIVITIES_ACTUAL`, and `ACTIVITIES_TREND` must use the same `W - 1`.
* No authority-model redesign, no public planning-artifact schema change, no feed-forward redesign.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Resolve planning evidence for Season, Phase, and Week from the exact previous ISO week only.
* [x] Ensure Phase and Week have a current previous-week `DES_ANALYSIS_REPORT` before planning starts.
* [x] Add explicit early evidence-alignment stages before synthesis/finalization.
* [x] Inject evidence and evidence-alignment outputs into the real planning runtime paths early enough to shape planning.

**Non-Goals**

* [x] No change to deterministic legality, load-band, or authority ownership.
* [x] No Season auto-report generation in this patch.
* [x] No public artifact schema bump for Season/Phase/Week outputs.
* [x] No late reviewer that rewrites an already-finished plan.

---

## 3) Proposed Behavior

**User/System behavior**

* For planning target week `W`, the active evidence week is always `W - 1`.
* Season planning receives:
  * `HISTORICAL_BASELINE`
  * previous-week `ACTIVITIES_ACTUAL`
  * previous-week `ACTIVITIES_TREND`
  * early season evidence-alignment output
* Phase planning receives:
  * previous-week `DES_ANALYSIS_REPORT`
  * previous-week `ACTIVITIES_ACTUAL`
  * previous-week `ACTIVITIES_TREND`
  * early phase evidence-alignment output
* Week planning receives:
  * previous-week `DES_ANALYSIS_REPORT`
  * previous-week `ACTIVITIES_ACTUAL`
  * previous-week `ACTIVITIES_TREND`
  * early week evidence-alignment output
* Phase and Week planning abort if the required previous-week report cannot be created.

**UI impact**

* UI affected: Indirectly
* Existing planning actions now enforce earlier evidence gating through orchestration.

**Non-UI behavior**

* Components involved:
  * `src/rps/orchestrator/season_flow.py`
  * `src/rps/orchestrator/plan_week.py`
  * `src/rps/orchestrator/context_snapshots.py`
  * `src/rps/planning/week_engine.py`
  * CrewAI task/agent/skill wiring under `config/crewai/` and `skills/`
* Contracts touched:
  * orchestrator evidence resolution
  * planning snapshot prompt blocks
  * active CrewAI planning tasks/skills

---

## 4) Implementation Analysis

**Components / Modules**

* `planning_evidence.py`: shared previous-week evidence resolution, report freshness, and compact evidence blocks.
* `season_flow.py`: exact previous-week evidence injection and early season evidence-alignment stage.
* `plan_week.py`: exact previous-week evidence gating, report ensure helper, and planning snapshot enrichment for Phase and Week.
* `context_snapshots.py`: accept and persist `des_report` and `evidence_alignment` prompt blocks plus source versions.
* `week_engine.py`: consume exact previous-week evidence and early evidence-alignment output in the deterministic week planner.
* `config/crewai/*`, `prompts/agents/*`, `skills/*`: active task/skill/prompt frontloading.

**Data flow**

* Inputs:
  * `HISTORICAL_BASELINE`
  * `ACTIVITIES_ACTUAL` for `W - 1`
  * `ACTIVITIES_TREND` for `W - 1`
  * `DES_ANALYSIS_REPORT` for `W - 1` (Phase/Week only)
* Processing:
  * resolve exact evidence week
  * ensure current report where required
  * build compact evidence block
  * build evidence-alignment result before synthesis
* Outputs:
  * evidence prompt blocks
  * evidence-alignment prompt blocks
  * early CrewAI planning task outputs
  * deterministic week-engine evidence shaping

**Schema / Artefacts**

* New public artefacts: none
* Changed artefacts: `PLANNING_CONTEXT_SNAPSHOT` prompt blocks/source versions only, within existing flexible schema
* Validator implications: no public schema bump expected

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: planning now fails closed when required previous-week evidence or required report freshness is missing
* Fallback behavior: no target-week or non-adjacent evidence fallback in this patch

**Conflicts with ADRs / Principles**

* Potential conflicts: none expected
* Resolution: authority stays deterministic and planner-facing evidence is advisory shaping input only

**Impacted areas**

* UI: planning actions can trigger earlier report creation for Phase/Week
* Pipeline/data: report freshness is checked against exact previous-week activity versions
* Renderer: unchanged
* Workspace/run-store: planning snapshots persist more prompt-block/source-version context
* Validation/tooling: targeted evidence-resolution and snapshot tests expand
* Deployment/config: CrewAI task/agent/skill config expands

**Required refactoring**

* Replace “latest historical before target” resolution with exact previous-week resolution in planning paths
* Factor report freshness/evidence-week logic into one shared helper

---

## 6) Options & Recommendation

### Option A — Early evidence alignment in orchestrator plus active task wiring

**Summary**

* Resolve evidence before planning, ensure current reports where needed, inject evidence early, and add explicit evidence-alignment tasks/skills.

**Pros**

* Matches the real runtime path
* Keeps review/writer out of evidence repair
* Works for both CrewAI planning and deterministic Week planning

**Cons**

* Touches several orchestration and config surfaces

**Risk**

* If evidence freshness logic is too strict, planning will fail more often until data is complete

### Option B — Late evidence advisory after synthesis

**Summary**

* Let planner synthesize first, then review or adjust against evidence later.

**Pros**

* Smaller code change

**Cons**

* Violates shift-left requirement
* Keeps the planner blind during first-pass synthesis

### Recommendation

* Choose: Option A
* Rationale: it changes the earliest meaningful boundary where the planner can still make better decisions.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Planning target week `W` resolves weekly evidence from `W - 1` only.
* [x] Phase and Week ensure a current previous-week report before planning starts.
* [x] Season, Phase, and Week each get an early evidence-alignment stage before synthesis.
* [x] Phase and Week snapshots contain `des_report` and `evidence_alignment` prompt blocks when applicable.
* [x] Validation passes: `py_compile`, lint, type check, targeted tests.
* [x] No regressions in legality, authority propagation, preview/week alignment, or feed-forward ownership.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration required.
* Historical snapshots without the new prompt blocks remain readable.

**Rollout / gating**

* No feature flag
* Safe rollback: revert shared evidence helper and task wiring

---

## 9) Risks & Failure Modes

* Failure mode: previous-week evidence missing
  * Detection: orchestrator returns explicit planning error
  * Safe behavior: abort planning before synthesis
  * Recovery: refresh Intervals data or create the missing report

* Failure mode: stale previous-week report linked to wrong activity versions
  * Detection: evidence freshness helper rejects it
  * Safe behavior: regenerate report for the evidence week
  * Recovery: rerun report creation

---

## 10) Observability / Logging

**New/changed events**

* reuse existing planning/report orchestration logs for:
  * resolved evidence week
  * missing evidence
  * report regeneration trigger

**Diagnostics**

* `rps.orchestrator.plan_week`
* `rps.orchestrator.season_flow`
* persisted `PLANNING_CONTEXT_SNAPSHOT` source versions

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/specs/features/FEAT_shift_left_planning_evidence_alignment.md` — canonical feature doc
* [ ] `doc/overview/how_to_plan.md` — note previous-week evidence gating for planning
* [ ] `CHANGELOG.md` — add runtime planning evidence alignment entry
