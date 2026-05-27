---
Version: 1.1
Status: Implemented
Last-Updated: 2026-05-27
Owner: Coach Runtime
---
# FEAT: Coach Evidence Source Guidance

* **ID:** FEAT_coach_evidence_source_guidance
* **Status:** Implemented
* **Owner/Area:** Coach Runtime
* **Last-Updated:** 2026-05-27
* **Related:** `skills/conversation/guarded-operations`, `skills/week/recommendation-and-adjustment`, `skills/shared/durability-methodology`

---

## 1) Context / Problem

**Current behavior**

* The Coach and Week Recommendation Specialist can access `factual_evidence` via CrewAI knowledge configuration.
* The repository now uses a canonical local evidence library under `skills/shared/durability-methodology/references/library/`, with generated operative lookup tables under `skills/shared/durability-methodology/references/`.

**Problem**

* The active Coach and recommendation skills did not explicitly define how to use durability evidence, preferred authors/domains, or web-researched sources.
* Evidence could be treated too generically unless the active skill body constrained source precedence and citation behavior.

**Constraints**

* Evidence is justification-only and must not override active RPS governance, S5/load bands, availability, schemas, or guardrails.
* No artifact schema change in this pass.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Move active lookup to the canonical local evidence library plus generated tables.
* [x] Decommission legacy bibliography files as operative lookup sources.
* [x] Add active Coach and Week Recommendation instructions for evidence use.
* [x] Define preferred authors and domains for source-backed explanations and web verification.
* [x] Prevent invented citations, thresholds, study claims, DOIs, and URLs.

**Non-Goals**

* [x] No new web-search tool implementation.
* [x] No schema or artifact changes.
* [x] No change to deterministic planning authority.

---

## 3) Proposed Behavior

**User/System behavior**

* When a user asks why a durability-first decision is appropriate, Coach uses injected evidence knowledge and primary-source verification as explanatory support.
* Coach prefers peer-reviewed and verified primary-source-backed references before practitioner material.
* Practitioner media can frame implementation, but not establish new governance rules.

**UI impact**

* UI affected: No.

**Non-UI behavior**

* Components involved: Coach prompt, Week Recommendation prompt, active Coach/Recommendation skills, shared durability references.
* Contracts touched: none.

---

## 4) Implementation Analysis

**Components / Modules**

* `skills/shared/durability-methodology/references/library/core_studies.yaml`: canonical operative core library.
* `skills/shared/durability-methodology/references/library/applied_sources.yaml`: canonical operative applied library.
* `skills/shared/durability-methodology/references/durability_reference_table_core.md`: primary operative scientific lookup.
* `skills/shared/durability-methodology/references/durability_reference_table_applied.md`: secondary applied/practitioner lookup.
* `skills/conversation/guarded-operations/SKILL.md`: active Coach source policy.
* `skills/week/recommendation-and-adjustment/SKILL.md`: recommendation source policy.
* `prompts/agents/coach.md` and `prompts/agents/week_recommendation_specialist.md`: compact prompt-level reminder.
* `src/rps/crewai_runtime/coach_chat.py`: recommendation task instruction for source-backed rationale.

**Data flow**

* Inputs: user question, injected evidence knowledge, optional primary-source verification result if exposed by runtime.
* Processing: Coach forms a bounded answer and uses evidence only as justification.
* Outputs: Coach response or coaching recommendation with compact verified citations when available, or omitted locators when verification is uncertain.

**Schema / Artefacts**

* New artefacts: none.
* Changed artefacts: none.
* Validator implications: active skill prompt tests cover source-policy presence.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: legacy bibliography files are no longer operative evidence inputs.
* Fallback behavior: if verification is unavailable, Coach uses retrieved knowledge and omits uncertain locators.

**Conflicts with ADRs / Principles**

* Potential conflicts: none.
* Resolution: evidence remains justification-only and preserves deterministic planning authority.

**Impacted areas**

* UI: none.
* Pipeline/data: none.
* Renderer: none.
* Workspace/run-store: none.
* Validation/tooling: skill prompt regression test.
* Deployment/config: none.

**Required refactoring**

* None.

---

## 6) Options & Recommendation

### Option A (recommended) — Active Skill Source Policy

**Summary**

* Keep the canonical local evidence library in skill references and put the source rules into active Coach/Recommendation skill bodies.

**Pros**

* Works with the current `SKILL.md`-only prompt rendering path.
* Keeps evidence source precedence close to the methods that use it.

**Cons**

* Does not itself add a runtime web-search tool.

**Risk**

* If a future runtime exposes web search differently, tool routing may need separate implementation.

### Option B — Knowledge-Only

**Summary**

* Rely on `knowledge_sources.yaml` and the generated evidence-library surfaces as retrieval material.

**Pros**

* Minimal changes.

**Cons**

* Does not actively constrain source precedence or citation behavior.

### Recommendation

* Choose: Option A.
* Rationale: the active skill body is the reliable instruction path for Coach behavior today.

---

## 7) Acceptance Criteria

* [x] Canonical local evidence library is present under shared durability skill references.
* [x] Coach active skill names preferred domains and authors.
* [x] Week recommendation skill names preferred domains and authors.
* [x] Prompts and Coach recommendation task warn against invented citations.
* [x] Evidence-use boundary remains justification-only.
* [x] Validation passes: syntax, lint, typecheck, targeted tests, full tests, relevant smoke.

---

## 8) Migration / Rollout

**Migration strategy**

* No persisted data migration.

**Rollout / gating**

* No feature flag; behavior is prompt/skill hardening only.

---

## 9) Risks & Failure Modes

* Failure mode: Coach cites a source not actually retrieved or verified.
  * Detection: prompt regression and review of Coach responses.
  * Safe behavior: answer without locator or label evidence as unverified/applied.
  * Recovery: add a stricter citation validator if needed.

* Failure mode: Coach treats a practitioner source as binding training authority.
  * Detection: review output against active governance and skill rules.
  * Safe behavior: active guardrails and deterministic constraints remain binding.
  * Recovery: harden recommendation guardrail if observed.

---

## 10) Observability / Logging

**New/changed events**

* None.

**Diagnostics**

* Inspect Coach run prompt/response traces and active skill prompt block.

---

## 11) Documentation Updates

* [x] `CHANGELOG.md` — document Coach evidence source guidance.
* [x] `doc/specs/features/FEAT_coach_evidence_source_guidance.md` — canonical feature note.

---

## 12) Link Map

* `skills/shared/durability-methodology/references/evidence_library_manifest.md`
* `skills/shared/durability-methodology/references/library/core_studies.yaml`
* `skills/shared/durability-methodology/references/library/applied_sources.yaml`
* `specs/knowledge/_shared/sources/principles/evidence_layer_durability.md`
* `config/crewai/knowledge_sources.yaml`
* `skills/conversation/guarded-operations/SKILL.md`
* `skills/week/recommendation-and-adjustment/SKILL.md`
* `skills/shared/durability-methodology/SKILL.md`
