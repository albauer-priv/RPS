---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-17
Owner: Coach Runtime
---
# FEAT: Coach Recommendation Answer Discipline

* **ID:** FEAT_coach_recommendation_answer_discipline
* **Status:** Implemented
* **Owner/Area:** Coach Runtime
* **Last-Updated:** 2026-05-17
* **Related:** `skills/week/recommendation-and-adjustment`, `skills/conversation/routing-and-finalization`

---

## 1) Context / Problem

**Current behavior**

* Coach correctly routes simple advisory questions to the Week Recommendation Specialist.
* The final answer can become too long, checklist-heavy, or add calculation/IF phrasing that was not necessary for the user question.

**Problem**

* Simple "why" questions should produce compact explanations, not action-plan checklists.
* The finalizer must not add domain calculations, thresholds, IF targets, or source claims beyond the specialist result and injected context.

**Constraints**

* No schema changes.
* Preview/apply semantics remain unchanged.
* Deterministic load and phase guardrails remain authoritative.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Make simple Coach why-answers compact.
* [x] Define the desired Coach voice positively: experienced, clear, calm, practical, appreciative, and solution-oriented.
* [x] Prevent DONE-checklist expansion unless requested.
* [x] Block task-runner labels such as `DONE`, `READY`, `OUTPUT`, `Was:`, `Prüfen:`, and `Bedingung:` in normal Coach replies.
* [x] Require load arithmetic and IF/threshold claims to be grounded in injected context or specialist output.
* [x] Avoid broad open-ended follow-up offers.

**Non-Goals**

* [x] No new model fields.
* [x] No new web-search tool.
* [x] No change to planning persistence behavior.

---

## 3) Proposed Behavior

**User/System behavior**

* For simple advisory why-questions, Coach answers like an experienced cycling coach: one direct decision, 2-4 reasons, and one practical next action.
* The tone is positive, calm, practical, appreciative, and solution-oriented without pressure or empty slogans.
* Coach does not add calculations, IF targets, thresholds, citations, or source claims unless they are present in context or verified evidence.
* If a final reply comes back in task-runner style, the runtime asks the finalizer to rewrite it once as a conversational Coach response.

**UI impact**

* UI affected: Yes, Coach response quality only.

**Non-UI behavior**

* Components involved: Coach conversational task prompts and active recommendation/finalization skills.
* Contracts touched: none.

---

## 4) Implementation Analysis

**Components / Modules**

* `skills/week/recommendation-and-adjustment/SKILL.md`: answer discipline.
* `skills/conversation/routing-and-finalization/SKILL.md`: finalizer discipline.
* `src/rps/crewai_runtime/coach_chat.py`: task-level instructions.
* `src/rps/crewai_runtime/coach_chat.py`: style issue detection and one-pass repair for final replies.
* `prompts/agents/week_recommendation_specialist.md` and `prompts/agents/conversation_manager.md`: compact reminders.

**Data flow**

* Inputs: selected-week context and specialist result.
* Processing: recommendation specialist creates bounded advice; finalizer preserves it without expansion.
* Outputs: compact Coach reply.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: prompt/skill regression checks.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: none.
* Fallback behavior: none.

**Conflicts with ADRs / Principles**

* Potential conflicts: none.
* Resolution: keeps Coach bounded and preview-first.

**Impacted areas**

* UI: Coach response wording.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: tests updated.
* Deployment/config: none.

---

## 6) Options & Recommendation

### Option A (recommended) — Prompt and Skill Discipline

**Summary**

* Add compact-answer constraints to active skills and Coach task prompts.

**Pros**

* Low risk.
* Keeps structured models unchanged.

**Cons**

* Still relies on model compliance.

### Option B — Hard Text Guardrail

**Summary**

* Reject answers above a token/line threshold.

**Pros**

* Stronger enforcement.

**Cons**

* Can reject legitimate complex answers.

### Recommendation

* Choose: Option A.
* Rationale: this is answer-style governance, not artifact validation.

---

## 7) Acceptance Criteria

* [x] Recommendation skill contains simple why-answer discipline.
* [x] Recommendation and finalizer skills contain positive Coach voice guidance.
* [x] Conversation finalization skill blocks checklist expansion for simple why-answers.
* [x] Coach task instructions forbid unsupported arithmetic/IF/source claims.
* [x] Runtime detects task-runner labels and repairs the final reply once.
* [x] Validation passes: syntax, lint, typecheck, tests, smoke.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted migration.

**Rollout / gating**

* No feature flag.

---

## 9) Risks & Failure Modes

* Failure mode: Model still produces a long checklist.
  * Detection: Coach smoke test.
  * Safe behavior: no persistence is affected.
  * Recovery: add a hard text guardrail if repeated.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Inspect Coach run output and task prompts.

---

## 11) Documentation Updates

* [x] This feature doc.
* [x] `CHANGELOG.md`.

---

## 12) Link Map

* `src/rps/crewai_runtime/coach_chat.py`
* `skills/week/recommendation-and-adjustment/SKILL.md`
* `skills/conversation/routing-and-finalization/SKILL.md`
