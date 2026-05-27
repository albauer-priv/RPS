---
Version: 1.1
Status: Implemented
Last-Updated: 2026-05-27
Owner: Planning Runtime
---
# FEAT: Evidence Library High-Fidelity Summaries

* **ID:** FEAT_evidence_library_high_fidelity_summaries
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-27
* **Related:** `skills/shared/durability-methodology/references/library`, `src/rps/evidence/library.py`

---

## Historical Position

This document describes the **summary-depth upgrade** inside the evidence
library, but the current canonical runtime for discovery, curation, gating, and
activation is described in:

- `doc/specs/features/FEAT_repo_wide_evidence_library_and_refresh.md`
- `doc/specs/features/FEAT_evidence_curation_pipeline.md`

This file should be read as the content-quality uplift for study briefs, not as
the full current evidence-system contract.

---

## 1) Context / Problem

**Current behavior**

* The canonical evidence library already exists and drives generated markdown study sheets.
* The generated study sheets are structurally correct but too thin for real operational use.

**Problem**

* Two short takeaway bullets are not enough for planner- and coach-facing evidence work.
* The library needs richer summaries of concepts, findings, scope, and practical implications.
* Applied sources are also useful and should not be reduced to low-information placeholders.

**Constraints**

* Keep locator verification fail-closed.
* Do not claim precise quantitative findings unless they are confidently supported.
* Keep planning authority below deterministic contracts and active governance.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Extend the evidence-library data model to support higher-fidelity summaries.
* [x] Regenerate per-study markdown with richer sections.
* [x] Bring both core and applied sources to a uniformly higher summary level.
* [x] Preserve concise tabular lookup while making detail pages genuinely useful.

**Non-Goals**

* [x] No change to locator verification policy.
* [x] No automatic claim extraction from full texts in this pass.
* [x] No promotion of evidence over deterministic planning authority.

---

## 3) Proposed Behavior

**User/System behavior**

* Each study/source detail page now includes:
  * question or focus
  * population or scope
  * core concepts
  * important findings
  * practical implications for RPS
  * important limits
* Applied sources keep the same structural richness as core sources, while remaining lower-authority.

**UI impact**

* UI affected: No direct UI change.

**Non-UI behavior**

* Components involved: evidence YAML schema, markdown sync generator, generated detail pages.

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/evidence/library.py`
* `skills/shared/durability-methodology/references/library/core_studies.yaml`
* `skills/shared/durability-methodology/references/library/applied_sources.yaml`
* generated study pages under `references/library/studies/`

**Data flow**

* Structured YAML entries now carry richer semantic summary fields.
* Markdown detail pages are regenerated from those richer fields.

**Schema / Artefacts**

* Added structured summary fields to canonical library entries:
  * `question_or_focus`
  * `population_or_scope`
  * `core_concepts`
  * `important_findings`
  * `practical_implications`

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes, with additive fields.
* Breaking changes: none for active evidence lookup.
* Fallback behavior: if a field is absent, generated markdown remains readable.

**Impacted areas**

* Generated markdown detail quality
* Evidence authoring expectations
* Tests around library sync

---

## 6) Options & Recommendation

### Option A — Add richer structured summary fields

**Pros**

* Keeps one source of truth
* Makes markdown useful without manual drift
* Scales to future refresh/curation passes

**Cons**

* Requires explicit curation work for every source

### Recommendation

* Choose: Option A

---

## 7) Acceptance Criteria

* [x] Canonical library entries support richer structured summary fields.
* [x] Generated study markdown includes concepts, findings, and practical implications.
* [x] Core and applied entries are both upgraded to a higher, more uniform summary level.
* [x] Validation passes.

---

## 8) Migration / Rollout

* Additive schema extension only.
* Regenerate markdown after library updates.

---

## 9) Risks & Failure Modes

* Failure mode: richer summaries become overconfident or too specific.
  * Detection: review of generated detail sheets
  * Safe behavior: summaries stay qualitative and avoid unsupported exact effect claims
  * Recovery: tighten wording in YAML entries

---

## 10) Observability / Logging

* No new logging path required.

---

## 11) Documentation Updates

* [x] This feature doc
* [x] Regenerated detail sheets
* [x] `CHANGELOG.md`
