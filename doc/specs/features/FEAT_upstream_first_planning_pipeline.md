---
Version: 1.0
Status: Approved
Last-Updated: 2026-05-22
Owner: Planning Runtime
---
# FEAT: Upstream-First Planning Pipeline

* **ID:** FEAT_upstream_first_planning_pipeline
* **Status:** Approved
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-22
* **Related:** ADR-056

---

## 1) Context / Problem

**Current behavior**

* Season, Phase, and Week flows use `finalize -> review -> writer`.
* Review and writer still catch semantically repairable defects late.
* Writer guardrails currently see raw LLM artifacts plus only partial deterministic repair.

**Problem**

* Writers fail on context-owned or semantically upstream-fixable issues.
* Review is heavier than necessary and often acts as a second planning step.
* Writers have the least context, so retry loops are the wrong place for semantic repair.

**Constraints**

* No schema-field change in this pass.
* Deterministic contract fields remain code-owned.
* Week exportability and workout syntax remain hard writer-stage protections.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move semantic repair as far upstream as possible into `..._finalize`.
* [x] Make `..._review` mostly an approval/escalation gate.
* [x] Keep writers focused on serialization plus deterministic final projection.
* [x] Apply the same ownership model to Season, Phase, and Week.

**Non-Goals**

* [x] No removal of review stages.
* [x] No weakening of schema/exportability checks.
* [x] No persisted artifact schema redesign in this pass.

---

## 3) Proposed Behavior

**User/System behavior**

* Finalize outputs are treated as near-final planning bundles.
* Review normally approves and documents warnings.
* Writer directly serializes approved bundles and should not be the first place where semantic contradictions surface.

**UI impact**

* UI affected: No

**Non-UI behavior**

* Components involved:
  * CrewAI task policies
  * finalize/review/writer prompts
  * planning contract validators
  * runtime writer guardrails
* Contracts touched:
  * internal Season/Phase/Week bundle contracts
  * review-decision runtime contract
  * writer-stage deterministic projection contract

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/planning/contracts.py`: new finalize-readiness validators, writer-stage semantic filtering rules.
* `src/rps/crewai_runtime/guardrails.py`: new finalize guardrails, stronger review-decision integrity, deterministic repair generalization.
* `src/rps/agents/crewai_backend.py`: normalized bundle validation before review, writer-stage deterministic projection boundaries.
* `config/crewai/task_policies.yaml`: finalize guardrail staging.
* `config/crewai/tasks.yaml`: task descriptions aligned to ownership.
* `prompts/agents/*.md` and relevant `skills/**/SKILL.md`: explicit checklists and ownership language.

**Data flow**

* Inputs: specialist drafts, deterministic contexts, approved bundles.
* Processing:
  * finalize synthesizes and self-checks
  * runtime validates normalized bundle readiness
  * review approves or bounded-replans
  * writer serializes and applies deterministic projection
* Outputs:
  * unchanged persisted artifact schemas
  * fewer writer retries
  * earlier bounded replans

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: none structurally
* Validator implications:
  * finalize bundles must be semantically review-ready
  * writer artifacts remain schema-valid and contract-consistent

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes at schema level
* Breaking changes:
  * finalize tasks may now fail earlier on semantic bundle defects
  * review approvals are stricter about approved vs replan-ready outputs
* Fallback behavior:
  * bounded replan remains the recovery path

**Conflicts with ADRs / Principles**

* Potential conflicts:
  * none; this clarifies existing authority boundaries
* Resolution:
  * formalized in ADR-056

**Impacted areas**

* UI: no direct change
* Pipeline/data: season/phase/week planning runtime behavior
* Renderer: none
* Workspace/run-store: no schema changes; telemetry may show earlier finalize failures and fewer writer retries
* Validation/tooling: new finalize readiness checks
* Deployment/config: task policy and prompt/skill updates

**Required refactoring**

* split semantic blockers from writer-stage contract checks
* generalize deterministic writer projection as a technical finalization layer only

---

## 6) Options & Recommendation

### Option A — Upstream-first ownership model

**Summary**

* Finalize repairs semantics, review confirms, writer serializes.

**Pros**

* Better use of context
* Fewer unstable writer retries
* Clearer ownership boundaries

**Cons**

* Requires prompt, guardrail, and runtime coordination

**Risk**

* Over-tight finalize checks could fail too early if not aligned with bounded replan behavior

### Option B — Keep current structure and harden writer prompts

**Summary**

* Leave ownership mostly unchanged and ask the writer to behave better.

**Pros**

* Smaller change set

**Cons**

* Keeps semantic repair in the lowest-context stage
* Does not solve structural retry instability

### Recommendation

* Choose: Option A
* Rationale: the writer has the least context and is the wrong stage for semantic repair.

---

## 7) Acceptance Criteria (Definition of Done)

* [ ] Season finalize catches semantic/event/domain drift before writer handoff.
* [ ] Phase finalize catches structure/load-role drift before writer handoff.
* [ ] Week finalize catches agenda/domain/export-intent drift before writer handoff.
* [ ] Review normally approves clean finalize bundles and only escalates real residual issues.
* [ ] Writer no longer blocks on forbidden-domain prose drift or phantom event semantics for Season.
* [ ] Deterministic writer projection remains in place for code-owned fields.
* [ ] Validation passes: `py_compile`, lint, typecheck, targeted CrewAI/planning tests.
* [ ] No regressions in Season / Phase / Week artifact persistence.

---

## 8) Migration / Rollout

**Migration strategy**

* No schema migration.
* Behavior-only rollout through runtime, task-policy, prompt, and skill changes.

**Rollout / gating**

* Feature flag / config: none
* Safe rollback:
  * revert task-policy + guardrail + prompt/skill changes

---

## 9) Risks & Failure Modes

* Failure mode: finalize guardrails become stricter than intended
  * Detection: early `*_BUNDLE_NORMALIZED_CONTRACT_FAILED` runtime events
  * Safe behavior: stop before writer, request bounded replan or fail clearly
  * Recovery: relax or relocate the specific finalize check

* Failure mode: writer still sees semantic blockers
  * Detection: writer guardrail telemetry still reports semantic blockers
  * Safe behavior: no invalid artifact persists
  * Recovery: move remaining semantic check upstream or downgrade writer-stage copy

---

## 10) Observability / Logging

**New/changed events**

* existing normalized contract failure events become more meaningful because finalize owns more readiness validation

**Diagnostics**

* inspect `events.jsonl`, `rps.log`, and run-store step telemetry for:
  * finalize normalized contract failures
  * review replan decisions
  * reduced writer guardrail retries

---

## 11) Documentation Updates

Update these docs as part of implementation:

* [x] `doc/adr/ADR-056-upstream-first-planning-pipeline.md` — architecture decision
* [x] `doc/adr/README.md` — ADR index
* [x] `CHANGELOG.md` — behavior change summary

## 12) Link Map

* [AGENTS.md](/Users/alexander/RPS/AGENTS.md)
* [doc/overview/artefact_flow.md](/Users/alexander/RPS/doc/overview/artefact_flow.md)
* [doc/overview/how_to_plan.md](/Users/alexander/RPS/doc/overview/how_to_plan.md)
* [doc/adr/README.md](/Users/alexander/RPS/doc/adr/README.md)
