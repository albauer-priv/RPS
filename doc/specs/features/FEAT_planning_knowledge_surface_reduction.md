---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Runtime / Knowledge
---
# FEAT: Planning Knowledge Surface Reduction

* **ID:** FEAT_planning_knowledge_surface_reduction
* **Status:** Implemented
* **Owner/Area:** CrewAI runtime / planning knowledge integration
* **Last-Updated:** 2026-05-19

---

## 1) Context / Problem

**Current behavior**

* Many Season, Phase, and Week planning specialists still attach static CrewAI knowledge bundles.
* CrewAI knowledge search can embed very large task/query strings, which may exceed embedding input limits.

**Problem**

* Planning specialists now rely mainly on deterministic contracts, workspace tools, and bounded task context.
* Static knowledge for many planning specialists adds cost and failure surface without adding real authority.
* Oversized knowledge-search queries can fail with provider-side embedding length errors.

**Constraints**

* No schema changes.
* Coach/report/workout-editor knowledge behavior should remain intact unless explicitly targeted.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Disable static knowledge for planning specialists where deterministic context already owns the task.
* [x] Compact knowledge-search query text before it reaches embedding/search code.
* [x] Hard-cap remaining knowledge-search queries to stay under provider embedding limits.

**Non-Goals**

* [x] No removal of knowledge from Coach or report paths in this step.
* [x] No redesign of CrewAI upstream knowledge internals.

---

## 3) Proposed Behavior

**User/System behavior**

* Season/Phase/Week planning specialists that operate from contracts, snapshots, and workspace tools no longer attach static knowledge bundles.
* Remaining knowledge-enabled agents use compacted, hard-capped search queries.

**Non-UI behavior**

* Components involved: `knowledge_sources.yaml`, `knowledge.py`
* Contracts touched: none

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/knowledge_sources.yaml`: remove unnecessary knowledge bundles from planning specialists.
* `src/rps/crewai_runtime/knowledge.py`: add search-query compaction and hard truncation guard.

**Data flow**

* Inputs: static knowledge bundle config, CrewAI knowledge search queries
* Processing: disable knowledge for selected planning agents; compact and cap remaining query text
* Outputs: fewer knowledge lookups and safer embedding requests

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: some planning specialists no longer use static knowledge search
* Fallback behavior: deterministic contracts and workspace tools remain authoritative

**Impacted areas**

* Runtime knowledge search
* Planning-cost / planning-failure surface
* Telemetry/logs only indirectly through fewer provider errors

**Required refactoring**

* Centralize knowledge-search compaction in the runtime helper layer instead of relying on agent prompts.

---

## 6) Options & Recommendation

### Option A — Keep knowledge and only truncate queries

**Pros**

* Smaller config change

**Cons**

* Still pays for knowledge where no real value exists
* Still leaves broader failure surface

### Option B (recommended) — Remove unnecessary planning knowledge, then cap remaining queries

**Pros**

* Reduces both cost and failure surface
* Aligns planning authority with deterministic contracts

**Cons**

* Requires explicit judgment about which specialists still benefit from static knowledge

### Recommendation

* Choose: Option B
* Rationale: removing unnecessary knowledge is the bigger and cleaner fix; query capping is then the safety net

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Selected Season/Phase/Week planning specialists resolve to no static knowledge sources.
* [x] Remaining knowledge-enabled search queries are compacted and hard-capped before runtime search.
* [x] Validation passes: syntax, lint, typecheck, targeted CrewAI tests

---

## 8) Migration / Rollout

**Migration strategy**

* None; runtime/config only

**Rollout / gating**

* No feature flag
* Safe rollback: restore previous knowledge bundles and remove search guard

---

## 9) Risks & Failure Modes

* Failure mode: a planning specialist loses needed static reference knowledge
  * Detection: planning quality drop or review mismatches
  * Safe behavior: deterministic contracts still prevent structural drift
  * Recovery: re-enable knowledge on the specific specialist only

* Failure mode: query compaction trims too aggressively
  * Detection: relevant knowledge hits disappear
  * Safe behavior: planning still uses workspace/contract context
  * Recovery: increase cap or refine marker extraction

---

## 10) Observability / Logging

**New/changed events**

* No new runtime event types
* Knowledge query compaction may emit debug logs when truncation is applied

**Diagnostics**

* `rps.log`
* provider-side embedding errors should drop from planning runs

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — record planning knowledge reduction and query caps
