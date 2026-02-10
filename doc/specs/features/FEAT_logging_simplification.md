---
Version: 1.0
Status: Implemented
Last-Updated: 2026-02-10
Owner: Platform
---
# FEAT: Logging Simplification (Env + Runtime)

* **ID:** FEAT_logging_simplification
* **Status:** Implemented
* **Owner/Area:** Platform / Observability
* **Last-Updated:** 2026-02-10
* **Related:** N/A

---

## 1) Context / Problem

**Current behavior**

* Logging is controlled by many environment variables, including per-target levels
  (`RPS_LOG_LEVEL_FILE`, `RPS_LOG_LEVEL_CONSOLE`, `RPS_LOG_LEVEL_UI`) and multiple
  LLM debug toggles (`RPS_LLM_STREAM_DEBUG`, `RPS_LLM_DEBUG_FILE_SEARCH`,
  `RPS_LLM_DEBUG_TOOLS`, `RPS_LLM_STREAM_LOG_REASONING`, etc.).
* Users must reason about overlapping flags and interactions to get a clean console.

**Problem**

* Too many logging flags create confusion, conflicting outputs, and hard-to-reproduce
  behavior. Debug toggles leak into console output even when standard log levels are set.

**Constraints**

* No new dependencies.
* Preserve file rotation/retention behavior.
* Keep the ability to enable deep LLM debugging when explicitly requested.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Collapse logging control to a small, predictable set of env vars.
* [x] Provide a single LLM debug switch that enables all deep debug behavior.
* [x] Keep reasoning logs configurable with a single mode switch.
* [ ] Maintain backward compatibility for one release (optional, if feasible).

**Non-Goals**

* [ ] Redesigning the logging backend or format.
* [ ] Changing log retention policy or log storage locations.

---

## 3) Proposed Behavior

**User/System behavior**

* Users control logging via a minimal set of env vars:
  * `RPS_LOG_LEVEL` (global default)
  * `RPS_LOG_CONSOLE`, `RPS_LOG_FILE`, `RPS_LOG_UI` (explicit overrides)
  * `RPS_LLM_DEBUG` (single switch for all LLM debug signals)
  * `RPS_LLM_REASONING_LOG` (off|summary|full)
  * `RPS_LLM_REASONING_LOG_FILE` (path)
* When `RPS_LLM_DEBUG=0`, LLM debug output should be quiet even if streaming is enabled.

**UI impact**

* UI affected: No (config + logging behavior only).

**Non-UI behavior (if applicable)**

* Components involved:
  * `rps.logging` (logger configuration)
  * `rps.openai.*` (LLM streaming/debug hooks)
  * `.env.example` (defaults)
* Contracts touched: none

---

## 4) Implementation Analysis

**Components / Modules**

* `rps.logging`: map new env vars to file/console/UI handlers; keep rotation/retention.
* `rps.openai.*`: gate all LLM debug/streaming diagnostics behind `RPS_LLM_DEBUG`.
* `.env.example`: update to the simplified set and include comments.
* Optional compatibility shim: accept legacy flags but log a deprecation warning.

**Data flow**

* Inputs: env vars at process start.
* Processing: configure handlers + debug gates.
* Outputs: consistent log noise levels; optional reasoning log file.

**Schema / Artefacts**

* None.

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Partial (if legacy env shim is kept for one release).
* Breaking changes: multiple old env vars ignored/removed.
* Fallback behavior: defaults to quiet console + INFO UI + DEBUG file.

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified.
* Resolution: N/A.

**Impacted areas**

* UI: none
* Pipeline/data: none
* Renderer: none
* Workspace/run-store: none
* Validation/tooling: `.env.example` + logging guidance
* Deployment/config: operators must update envs

**Required refactoring**

* Consolidate LLM debug flags into a single gate.
* Remove or deprecate redundant env vars.

---

## 6) Options & Recommendation

### Option A (recommended) — Minimal logging surface

**Summary**

* Replace many env vars with the minimal set described above.

**Pros**

* Predictable behavior.
* Easier operations and troubleshooting.

**Cons**

* Requires env migration.

**Risk**

* Some automated setups might rely on removed flags.

### Option B — Keep old vars but add presets

**Summary**

* Introduce `RPS_LOG_PROFILE=quiet|default|debug` while keeping all old flags.

**Pros**

* Lower migration friction.

**Cons**

* Still complex; old flags remain confusing.

### Recommendation

* Choose: Option A
* Rationale: aligns with “radical simplification” and reduces support burden.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] New env vars implemented and documented.
* [x] Legacy logging flags removed or deprecated with warnings.
* [x] LLM debug output is silent unless `RPS_LLM_DEBUG=1`.
* [x] Reasoning log mode controls output as `off|summary|full`.
* [x] Validation passes: `python -m py_compile $(git ls-files '*.py')`.
* [ ] No regressions in UI logging panels and file rotation.

---

## 8) Migration / Rollout

**Migration strategy**

* Update `.env.example` + documentation.
* Provide a migration note and (optional) one-release compatibility shim.

**Rollout / gating**

* Feature flag/config: N/A
* Safe rollback: revert env changes and restore legacy flags.

---

## 9) Risks & Failure Modes

* Failure mode: Operators lose LLM debug visibility due to missing flags.
  * Detection: missing debug lines when expected.
  * Safe behavior: `RPS_LLM_DEBUG=1` restores all debug channels.
  * Recovery: add temporary compatibility mapping if needed.

---

## 10) Observability / Logging

**New/changed events**

* `logging.config`: log the resolved logging profile + handlers at startup.
* `llm.debug_gate`: log whether LLM debug is enabled.

**Diagnostics**

* `runtime/athletes/<id>/logs/rps.log`
* `runtime/athletes/<id>/logs/reasoning_chunks.log` (if enabled)

---

## 11) Documentation Updates

* [x] `.env.example` — replace logging section with simplified vars.
* [x] `doc/specs/contracts/logging_policy.md` — note new logging controls.
* [x] `CHANGELOG.md` — record logging simplification.

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Logging policy: `doc/specs/contracts/logging_policy.md`
* Validation / runbooks: `doc/runbooks/validation.md`
* ADRs: `doc/adr/README.md`
