---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Plan Hub / Logging
---
# FEAT: Plan Hub Run Log Noise Reduction

* **ID:** FEAT_plan_hub_run_log_noise_reduction
* **Status:** Implemented
* **Owner/Area:** Plan Hub / Logging
* **Last-Updated:** 2026-05-19
* **Related:** `src/rps/orchestrator/plan_hub_worker.py`

---

## 1) Context / Problem

**Current behavior**

* Plan Hub run-specific log files attach an extra root handler when a planning run starts.
* That handler inherits the root logger level and therefore captures `DEBUG` output when the process root is in debug mode.

**Problem**

* User-facing run logs become noisy and appear to "switch" between `INFO` and `DEBUG`.
* Harmless third-party debug traces, including CrewAI/LanceDB table-open fallbacks, look like runtime failures in the planning log.

**Constraints**

* Keep global application logging unchanged.
* Do not hide real `INFO`/`WARNING`/`ERROR` signals from the run log.
* Avoid schema or artifact contract changes.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Keep Plan Hub run logs operator-readable at `INFO` and above.
* [x] Prevent debug-only framework noise from being written into per-run log files.

**Non-Goals**

* [x] Do not change the global root logger policy.
* [x] Do not redesign CrewAI memory behavior in this change.

---

## 3) Proposed Behavior

**User/System behavior**

* Plan Hub run log files only capture `INFO` and above by default.
* Repeated readiness polling debug lines and harmless CrewAI/LanceDB debug traces no longer appear in the run log.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: `plan_hub_worker`, Python logging
* Contracts touched: none

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/orchestrator/plan_hub_worker.py`: set an explicit `INFO` level on the run-specific file handler.
* `tests/test_plan_hub_worker.py`: add regression coverage for handler filtering.

**Data flow**

* Inputs: `log_ref` path for a queued plan run
* Processing: attach dedicated file handler with explicit level
* Outputs: quieter per-run log file

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none
* Validator implications: none

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: global logs still retain existing verbosity rules

**Conflicts with ADRs / Principles**

* Potential conflicts: none
* Resolution: n/a

**Impacted areas**

* UI: Plan Hub log presentation becomes clearer
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: per-run log contents only
* Validation/tooling: test coverage added
* Deployment/config: none

**Required refactoring**

* None beyond explicit handler configuration

---

## 6) Options & Recommendation

### Option A — Explicit `INFO` level on run-log handler

**Summary**

* Keep root logging as-is but constrain the additional Plan Hub run-log handler.

**Pros**

* Minimal change
* Preserves global debug behavior for operators
* Removes misleading debug noise from run logs

**Cons**

* Debug-only details are no longer visible in the per-run file

**Risk**

* Low

### Option B — Lower global root verbosity

**Summary**

* Reduce root/file logging globally.

**Pros**

* Broad noise reduction

**Cons**

* Affects unrelated diagnostics
* Higher blast radius

### Recommendation

* Choose: Option A
* Rationale: fixes the user-visible problem at the narrowest point.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Plan Hub run-log handler writes `INFO` entries.
* [x] Debug messages do not appear in the per-run log file.
* [x] Validation passes: `py_compile`, lint, type check, targeted tests
* [x] No regressions in Plan Hub worker tests

---

## 8) Migration / Rollout

**Migration strategy**

* None

**Rollout / gating**

* Feature flag / config: none
* Safe rollback: revert handler-level change

---

## 9) Risks & Failure Modes

* Failure mode: needed debug context is absent from the run-specific log
  * Detection: operator compares per-run log with global `rps.log`
  * Safe behavior: run still records `INFO`/`WARNING`/`ERROR`
  * Recovery: inspect global logs if deep debug is needed

---

## 10) Observability / Logging

**New/changed events**

* No new events; per-run handler now filters below `INFO`

**Diagnostics**

* Per-run log file referenced by `log_ref`
* Global application log remains unchanged

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `CHANGELOG.md` — note quieter Plan Hub run logs

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
