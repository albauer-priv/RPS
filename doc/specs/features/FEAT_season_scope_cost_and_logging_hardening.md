---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Runtime / Planning
---
# FEAT: Season Scope, Cost, and Logging Hardening

* **ID:** FEAT_season_scope_cost_and_logging_hardening
* **Status:** Implemented
* **Owner/Area:** Runtime / Planning
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_specialist_task_prompt_hardening, FEAT_macrocycle_task_runtime_semantics

---

## 1) Context / Problem

**Current behavior**

* Season bounded specialists run successfully, but `season_kpi_guidance_specialist` overlaps too heavily with `season_constraint_specialist`.
* Season manager-heavy steps still show a disproportionate amount of `gpt-5.4` usage in runtime logs.
* UI/run logging can miss module logs because the UI session does not always initialize file logging early enough and the per-run handler is attached too narrowly.

**Problem**

* KPI guidance is drifting into availability, rest-day, phase-corridor, and event-taper authority that belongs to constraint, progression, or load-governance roles.
* `season_plan_manager` dominates completions with `gpt-5.4`, which is unnecessarily expensive for bounded season-plan synthesis.
* Run log files are incomplete because only the worker module logger gets the run handler instead of the root logger.

**Constraints**

* No new dependencies.
* Keep season contracts and current task outputs backward compatible.
* Preserve deterministic contract-tool behavior and current specialist sequencing.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Tighten season KPI guidance so it only covers KPI/rate-band/pacing semantics.
* [x] Reduce expensive `gpt-5.4` usage in the season manager/review path where `mini` is sufficient.
* [x] Ensure root/runtime logs are written reliably to the configured UI and per-run log files.

**Non-Goals**

* [ ] Re-design season artifact schemas.
* [ ] Re-tune every planning role model in the whole repo.

---

## 3) Proposed Behavior

**User/System behavior**

* Season KPI guidance stays narrowly focused on moving-time-rate semantics, KPI band interpretation, pacing guardrails, and limits of KPI authority.
* Binding constraints remain in the season constraint specialist and related governance roles.
* Season plan manager and season review manager use `gpt-5.4-mini` without reasoning-agent mode.
* UI startup always attaches the athlete-scoped file log early, and plan-hub worker run logs capture cross-module runtime logs through the root logger.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved:
  - `config/crewai/tasks.yaml`
  - `config/crewai/runtime_profiles.yaml`
  - `prompts/agents/kpi_guidance_specialist.md`
  - `skills/season/kpi-guidance/SKILL.md`
  - `src/rps/core/logging.py`
  - `src/rps/ui/streamlit_app.py`
  - `src/rps/orchestrator/plan_hub_worker.py`
* Contracts touched:
  - season internal reasoning task descriptions
  - runtime model profile selection
  - root/run logging behavior

---

## 4) Implementation Analysis

**Components / Modules**

* `tasks.yaml`: narrow KPI task scope and explicit exclusions.
* `runtime_profiles.yaml`: downgrade season manager/review manager to `gpt-5.4-mini`, disable season manager reasoning.
* KPI prompt/skill: reinforce role boundaries.
* `streamlit_app.py`: initialize logging on startup from active athlete context.
* `plan_hub_worker.py`: attach per-run file handler to root logger instead of a single module logger.
* `core/logging.py`: keep setup idempotent enough for repeated UI calls while preserving file handler intent.

**Data flow**

* Inputs: season task context, athlete id, run log path.
* Processing: narrower specialist instructions, cheaper runtime profile selection, root logger attachment.
* Outputs: lower-cost season completions and fuller `rps.log` / run log files.

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none in artifact contracts
* Fallback behavior: if UI athlete context is absent, logging still falls back to existing handlers

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: behavior remains inside existing planning/runtime boundaries

**Impacted areas**

* UI: startup logging attachment
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: run log coverage improves
* Validation/tooling: runtime tests updated
* Deployment/config: runtime profile changes only

**Required refactoring**

* tighten KPI task/prompt/skill contract
* root-level run handler wiring
* season manager profile adjustment

---

## 6) Options & Recommendation

### Option A — Tighten scope and lower manager cost

**Summary**

* Keep the current architecture, narrow KPI authority, reduce season manager cost, and fix logging.

**Pros**

* Small, targeted change
* Immediate cost reduction
* Better runtime observability

**Cons**

* Does not fully eliminate all `gpt-5.4` usage because `macrocycle_architect` remains strong

**Risk**

* Slight chance of weaker final synthesis quality if `season_plan_manager` on `mini` underperforms

### Option B — Keep models and only improve prompts/logging

**Summary**

* Leave `gpt-5.4` manager usage unchanged and only fix scope/logging.

**Pros**

* Minimal quality risk

**Cons**

* Misses the main cost complaint

### Recommendation

* Choose: Option A
* Rationale: it addresses the user-visible cost issue and the logging gap without introducing architectural churn.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season KPI guidance task explicitly excludes availability/rest-day, phase corridor/load band, and event/taper authority.
* [x] `season_plan_manager` runs on `gpt-5.4-mini` with reasoning disabled.
* [x] `season_review_manager` runs on `gpt-5.4-mini`.
* [x] UI startup initializes file logging for the active athlete context.
* [x] Plan-hub worker run log handler attaches to the root logger and captures cross-module logs.
* [x] Validation passes: syntax, lint, typecheck, targeted tests.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema or artifact migration required.

**Rollout / gating**

* No feature flag.
* Safe rollback: revert runtime profile and logging changes.

---

## 9) Risks & Failure Modes

* Failure mode: manager on `mini` produces weaker final synthesis
  * Detection: season smoke logs and review outputs regress
  * Safe behavior: retain macrocycle architect on `gpt-5.4`; revert manager profile if needed
  * Recovery: restore manager model to `gpt-5.4`

* Failure mode: duplicate log handlers
  * Detection: repeated duplicate log lines
  * Safe behavior: attach handler only when same path is not already active
  * Recovery: restart session / remove duplicate handler logic

---

## 10) Observability / Logging

**New/changed events**

* No new telemetry event types.
* Root and run log files now receive a broader set of existing runtime log messages.

**Diagnostics**

* Check athlete `logs/rps.log`
* Check run-specific `log_ref` file from plan hub
* Check OpenAI completions for `season_plan_manager` and `season_review_manager` model distribution

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `CHANGELOG.md` — note scope, model, and logging hardening
