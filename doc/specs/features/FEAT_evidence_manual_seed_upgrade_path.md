---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-27
Owner: Planning Runtime
---
# FEAT: Evidence Manual Seed Upgrade Path

* **ID:** FEAT_evidence_manual_seed_upgrade_path
* **Status:** Implemented
* **Owner/Area:** Planning Runtime
* **Last-Updated:** 2026-05-27
* **Related:** `src/rps/evidence/refresh.py`, `skills/shared/durability-methodology/references/library/core_studies.yaml`, `.github/workflows/evidence-refresh.yml`

---

## 1) Context / Problem

**Current behavior**

* The evidence refresh pipeline automatically curates newly discovered verified candidates.
* Legacy-visible entries remain visible as `legacy_active` and can be backfilled only through a small abstract-backed legacy path.
* Manually added verified studies can be stored in the canonical library immediately.

**Problem**

* Manually seeded verified studies are not guaranteed to enter the normal curation pipeline during the GitHub Action refresh run.
* DOI-only manual seeds are especially weak, because the refresh path can fetch abstracts only when it already has a PubMed locator.
* This leaves operator-added evidence stuck in `metadata_only_not_activatable` even when a verifiable PubMed abstract exists.

**Constraints**

* No new dependencies.
* Keep the canonical evidence library fail-closed.
* Do not trigger full-library legacy re-curation accidentally.
* Preserve visible legacy entries until curated replacements exist.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Let intentionally marked manual legacy seeds enter the normal verified curation path during evidence refresh.
* [x] Resolve DOI-based manual seeds to PubMed IDs when possible so abstract-backed curation can run in GitHub Actions.
* [x] Keep the upgrade path narrow and explicit so existing legacy entries are not mass-processed.
* [x] Ensure generated study briefs and tables reflect the refreshed result after the action runs.

**Non-Goals**

* [x] No unrestricted DOI fulltext scraping.
* [x] No automatic re-curation of all old `legacy_active` entries.
* [x] No schema expansion for a separate manual-seed state in this pass.

---

## 3) Proposed Behavior

**User/System behavior**

* A manually added verified evidence entry can stay visible as `legacy_active` while awaiting structured curation.
* If that entry is explicitly marked `brief_status: pending_curation`, the next evidence refresh run treats it as a processable verified seed.
* If the locator is already a PubMed URL, the refresh fetches the abstract directly.
* If the locator is DOI-only, the refresh first tries deterministic PubMed DOI resolution and then fetches the abstract from PubMed when resolution succeeds.
* The GitHub Action refresh therefore upgrades deliberately seeded studies from metadata-only placeholders into fully curated/activated or rejected entries when source text supports it.

**UI impact**

* UI affected: No

**Non-UI behavior (if applicable)**

* Components involved: evidence refresh, evidence pipeline, generated evidence outputs, GitHub Action refresh workflow
* Contracts touched: evidence refresh state semantics for manually seeded verified entries

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/evidence/refresh.py`: add a narrow processing rule for legacy manual seeds and DOI-to-PubMed resolution.
* `skills/shared/durability-methodology/references/library/core_studies.yaml`: mark manual seeds as `pending_curation`.
* `tests/test_evidence_library.py`: cover pending manual seeds and DOI resolution behavior.

**Data flow**

* Inputs: existing canonical library entries, verified DOI/PubMed locators, PubMed search/fetch APIs
* Processing: identify explicitly pending manual seeds -> resolve PMID if needed -> fetch abstract -> run curation pipeline -> regenerate evidence outputs
* Outputs: upgraded evidence entries, regenerated study briefs, refreshed tables

**Schema / Artefacts**

* New artefacts: none
* Changed artefacts: canonical evidence entries can use `brief_status: pending_curation` while still `legacy_active`
* Validator implications: generated outputs and evidence refresh tests must pass

---

## 5) Impact Analysis (complete)

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: if DOI resolution or abstract fetch fails, the entry remains visible legacy metadata and is not falsely activated

**Conflicts with ADRs / Principles**

* Potential conflicts: none identified
* Resolution: the path remains fail-closed and source-bounded

**Impacted areas**

* UI: none
* Pipeline/data: manual verified legacy seeds can enter refresh-driven curation
* Renderer: generated study pages may move from metadata-only placeholders to structured curated briefs
* Workspace/run-store: standard evidence refresh stages only
* Validation/tooling: evidence refresh tests, syntax check
* Deployment/config: GitHub Action now has a reliable path to upgrade manually seeded studies

**Required refactoring**

* Separate “legacy visible” from “not eligible for immediate curation” by using `brief_status: pending_curation` as the narrow upgrade marker.
* Add DOI-to-PubMed resolution inside refresh rather than requiring operators to rewrite every seed as a PubMed locator manually.

---

## 6) Options & Recommendation

### Option A — Explicit `pending_curation` seed upgrade path

**Summary**

* Treat only explicitly marked legacy seeds as processable, and resolve DOI locators to PubMed when possible.

**Pros**

* Narrow blast radius
* Preserves visible placeholders
* Works inside the existing GitHub Action runtime

**Cons**

* DOI-only entries still depend on PubMed indexing
* Operators must mark intended seeds correctly

**Risk**

* Mis-marked entries could stay pending longer than expected

### Option B — Process all uncurated legacy entries

**Summary**

* Let refresh reprocess any legacy entry with missing curation markers.

**Pros**

* Less operator bookkeeping

**Cons**

* Too broad
* Likely to burn refresh capacity on old entries the operator did not intend to revisit

### Recommendation

* Choose: Option A
* Rationale: it gives the GitHub Action a deterministic path for newly seeded evidence without destabilizing the rest of the library.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] A `legacy_active` verified entry with `brief_status: pending_curation` enters the refresh pipeline.
* [x] A DOI-only pending seed can resolve to PubMed and fetch abstract text when PubMed has the paper indexed.
* [x] Existing curated verified entries are still skipped.
* [x] Validation passes: targeted evidence refresh tests, syntax check.
* [x] No regressions in generated evidence tables/briefs.
* [x] Performance guardrail: refresh still honors `max_entries_per_refresh`.

---

## 8) Migration / Rollout

**Migration strategy**

* Keep existing legacy entries unchanged unless they are intentionally marked `pending_curation`.
* Mark newly added manual seeds that should be upgraded by the action with `brief_status: pending_curation`.

**Rollout / gating**

* No feature flag.
* Safe rollback: restore previous refresh logic and revert seed status changes.

---

## 9) Risks & Failure Modes

* Failure mode: DOI does not resolve to a PubMed ID

  * Detection: refresh logs show unresolved DOI or missing abstract
  * Safe behavior: entry remains legacy metadata-only
  * Recovery: add a PubMed locator manually or curate from another supported source path later

* Failure mode: pending manual seeds exceed run cap

  * Detection: refresh stats show `skipped_due_to_cap`
  * Safe behavior: unprocessed seeds remain visible and pending
  * Recovery: rerun refresh or adjust cap deliberately

---

## 10) Observability / Logging

**New/changed events**

* existing evidence refresh logs now include DOI-to-PubMed resolution failures as warnings
* pending manual seeds flow through normal `VERIFIED -> CURATION_STARTED -> ...` stage events

**Diagnostics**

* GitHub Actions evidence refresh logs
* run-store evidence refresh events
* regenerated study briefs under `library/studies/`

---

## 11) Documentation Updates

* [x] `doc/runbooks/evidence_refresh.md` — document pending manual seed upgrade behavior
* [x] `doc/specs/features/FEAT_evidence_refresh_github_action.md` — mention that action upgrades explicitly pending manual seeds
* [x] `CHANGELOG.md` — record the new manual-seed upgrade path

---

## 12) Link Map (no duplication; links only)

* Architecture: `doc/architecture/system_architecture.md`
* Workspace: `doc/architecture/workspace.md`
* Evidence refresh runbook: `doc/runbooks/evidence_refresh.md`
* Existing evidence library feature: `doc/specs/features/FEAT_repo_wide_evidence_library_and_refresh.md`
* Existing curation pipeline feature: `doc/specs/features/FEAT_evidence_curation_pipeline.md`
* Existing GitHub Action feature: `doc/specs/features/FEAT_evidence_refresh_github_action.md`
