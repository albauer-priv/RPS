---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-19
Owner: Planning Runtime
---
# FEAT: Context Scope and Feed-Forward Hardening

* **ID:** FEAT_context_scope_and_feedforward_hardening
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-19
* **Related:** FEAT_review_contract_context_hardening, FEAT_phase_week_contract_context_hardening

---

## 1) Context / Problem

**Current behavior**

* Several `*_context_read` tasks still use broad `read_only_workspace`.
* `*_contract_review` tasks rely on injected context but are not explicitly tool-scoped.
* `season_feed_forward_manager`, `phase_feed_forward_manager`, and `des_review_manager` were still delegation-capable.

**Problem**

* Broad read surfaces encourage unnecessary rediscovery.
* Contract-review tasks can still drift into generic workspace inspection rather than direct contract checks.
* Feed-forward/report managers still exposed the same delegation-based loss of bounded authority.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Replace broad read-only workspace access on planning/report context-read tasks with explicit tool lists.
* [x] Scope `season_contract_review`, `phase_contract_review`, and `week_contract_review` directly to the relevant deterministic contract tools.
* [x] Disable free delegation for season/phase feed-forward managers and report review manager.

**Non-Goals**

* [ ] Re-architect feed-forward or report flows.

---

## 3) Proposed Behavior

* Context-read tasks use only the concrete tools they need.
* Contract-review tasks can call the direct deterministic contract tools they audit against.
* Feed-forward/report managers remain bounded and do not open coworker rediscovery paths.

---

## 4) Acceptance Criteria (Definition of Done)

* [x] Context-read tasks no longer use `read_only_workspace` blindly.
* [x] Contract-review tasks declare explicit deterministic contract tools.
* [x] `season_feed_forward_manager`, `phase_feed_forward_manager`, and `des_review_manager` have `allow_delegation: false`.
* [x] Regression tests cover config changes.

