---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Review Contract Context Hardening

* **ID:** FEAT_review_contract_context_hardening
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_season_contract_context_hardening, FEAT_phase_week_contract_context_hardening

---

## 1) Context / Problem

**Current behavior**

* Season, Phase, and Week review managers integrate audit outputs into approve/replan/reject decisions.
* Deterministic contracts are already available in runtime context, but review managers could still freely delegate or re-derive structural checks through prose.

**Problem**

* This leaves the same failure class open on the review layer: contract mismatches can be interpreted indirectly instead of checked against direct deterministic authority.

**Constraints**

* No persisted schema changes.
* Existing review crews stay in place.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Give review final tasks direct read-only access to the deterministic contracts they judge against.
* [x] Inject structured contract JSON into review task descriptions.
* [x] Disable free delegation for season/phase/week review managers.

**Non-Goals**

* [ ] Rebuild the review crew architecture.
* [ ] Introduce new persisted review artifacts.

---

## 3) Proposed Behavior

**User/System behavior**

* `season_review` can consume deterministic season contracts directly.
* `phase_review` can consume deterministic phase contracts directly.
* `week_review` can consume deterministic week contracts directly.
* Review managers act as bounded integrators of:
  * review task outputs
  * planning bundle
  * deterministic contract context

**UI impact**

* UI affected: No

---

## 4) Implementation Analysis

**Components / Modules**

* `config/crewai/tasks.yaml`: review final tasks get deterministic contract tools.
* `config/crewai/agents.yaml`: review managers no longer freely delegate.
* `src/rps/agents/crewai_backend.py`: contract blocks injected for review crews.
* `skills/*/review-decision/SKILL.md`: explicit contract-consumption language.

**Data flow**

* Inputs: planning bundle, review specialist outputs, bound deterministic contracts
* Processing: review decision against direct contract authority
* Outputs: unchanged review decision models

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none at persistence/schema level

**Impacted areas**

* Validation/tooling: review task tool surface expands
* Runtime behavior: fewer exploratory coworker calls from review managers

---

## 6) Options & Recommendation

### Option A — Harden review managers like finalizers

**Summary**

* Make review decisions directly contract-aware and non-delegating.

**Pros**

* Closes the same failure class at the review layer.

### Option B — Leave reviews prompt-only

**Cons**

* Keeps indirect, prose-based contract interpretation possible.

### Recommendation

* Choose: Option A

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Season/Phase/Week review tasks declare deterministic contract tools.
* [x] Season/Phase/Week review managers have free delegation disabled.
* [x] Review crew task descriptions include structured deterministic contract blocks.
* [x] Regression tests cover review config and contract-context injection.

