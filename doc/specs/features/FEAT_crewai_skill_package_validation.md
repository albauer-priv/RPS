---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-18
Owner: CrewAI Runtime
---
# FEAT: CrewAI Skill Package Validation

* **ID:** FEAT_crewai_skill_package_validation
* **Status:** Implemented
* **Owner/Area:** CrewAI Runtime
* **Last-Updated:** 2026-05-18
* **Related:** `scripts/validate_crewai_skills.py`, `config/crewai/skills.yaml`, `skills/**/SKILL.md`

---

## 1) Context / Problem

**Current behavior**

* CrewAI skills are now the primary method layer for Season, Phase, Week, Report, Coach, and shared runtime behavior.
* The runtime uses native CrewAI skill package paths and no longer manually renders `SKILL.md` bodies into prompts.
* Existing tests verify some local reference rules, but there is no reusable validator script for configured skill packages.

**Problem**

* A configured skill can drift into non-native references, missing local files, or mostly negative prompt language.
* Coach output quality suffered previously when instructions described mostly what not to do instead of what the coach should do.
* Agents perform better when a skill states the desired output or answer format explicitly.

**Constraints**

* No new dependency.
* Validation must not require CrewAI runtime import.
* Path/package errors should be hard failures.
* Positive phrasing and output-format checks should start as warnings, with a strict mode available.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Validate every skill referenced by `config/crewai/skills.yaml`.
* [x] Fail on missing skill directories or missing `SKILL.md`.
* [x] Fail on cross-skill/repo references such as `../`, `skills/`, `specs/knowledge/`, `doc/`, `config/`, or `prompts/`.
* [x] Fail on missing local `references/`, `scripts/`, or `assets/` targets.
* [x] Warn when a skill lacks positive action guidance.
* [x] Warn when negative constraints outweigh positive operating guidance.
* [x] Warn when a skill lacks an explicit output/answer/result format.
* [x] Support `--fail-on-warnings` for strict CI hardening.
* [x] Clean configured skills so strict validation currently passes without warnings.

**Non-Goals**

* [x] No automatic rewriting of all skills.
* [x] No semantic LLM review.
* [x] No CrewAI package/runtime dependency.

---

## 3) Proposed Behavior

**System behavior**

* `python3 scripts/validate_crewai_skills.py` scans configured CrewAI skill packages.
* The script exits non-zero for hard package/reference errors.
* With `--fail-on-warnings`, style and output-format warnings also fail the run.
* Configured skills include positive operating guidance and output-format guidance.
* Coach/recommendation skills receive explicit positive answer structure in `SKILL.md`.

**UI impact**

* UI affected: No.

---

## 4) Implementation Analysis

**Components / Modules**

* `scripts/validate_crewai_skills.py`: standalone validator.
* `tests/test_crewai_skill_validation.py`: validator unit tests.
* `skills/week/recommendation-and-adjustment/SKILL.md`: positive output format.
* `doc/overview/feature_backlog.md`: mark item implemented.

**Data flow**

* Inputs: `config/crewai/skills.yaml`, referenced `skills/**/SKILL.md`.
* Processing: package existence, local reference validation, positive/negative phrasing heuristics, output-format heuristic.
* Outputs: CLI findings and exit status.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes.
* Breaking changes: None; warning checks are advisory by default.
* Fallback behavior: `--fail-on-warnings` can be used later after all skills are explicitly formatted.

**Impacted areas**

* Validation/tooling: new script and tests.
* Runtime: no direct runtime behavior change.
* Skills: one Coach recommendation skill gains explicit output-format guidance.

---

## 6) Options & Recommendation

### Option A — Script With Advisory Style Checks

**Summary**

* Hard-fail structural/package problems; warn on prompt-quality rules.

**Pros**

* Immediate protection against broken CrewAI skill packages.
* Allows gradual cleanup of output-format sections across all skills.

**Cons**

* Style warnings do not yet block CI by default.

### Recommendation

* Choose: Option A.
* Rationale: hard package correctness should be enforced immediately; style/output cleanup can be ratcheted using `--fail-on-warnings`.

---

## 7) Acceptance Criteria

* [x] Configured skills are scanned from `config/crewai/skills.yaml`.
* [x] Missing `SKILL.md` and escaped references are hard failures.
* [x] Missing output format and weak positive phrasing create warnings.
* [x] Validator has tests for invalid external reference, missing output warning, valid local reference, and strict warning mode.
* [x] Recommendation skill includes positive answer/output structure.
* [x] `python3 scripts/validate_crewai_skills.py --fail-on-warnings` passes on the configured skill set.

---

## 8) Migration / Rollout

**Migration strategy**

* Add script as validation tooling.
* The configured skill set currently passes strict mode.

**Rollout / gating**

* Use `python3 scripts/validate_crewai_skills.py` locally.
* Use `python3 scripts/validate_crewai_skills.py --fail-on-warnings` for strict CI gating.

---

## 9) Risks & Failure Modes

* Failure mode: heuristic warnings are noisy for guardrail/syntax skills.
  * Detection: validator output.
  * Safe behavior: warnings remain non-blocking by default.
  * Recovery: add explicit positive operating guidance and output sections.
* Failure mode: a valid external URL is mistaken for an escaped reference.
  * Detection: validator finding.
  * Safe behavior: HTTP(S) and mailto links are allowed.

---

## 10) Observability / Logging

* CLI prints one line per finding plus a final summary.
* No runtime telemetry changes.

---

## 11) Documentation Updates

* [x] `doc/specs/features/FEAT_crewai_skill_package_validation.md`
* [x] `doc/overview/feature_backlog.md`
* [x] `CHANGELOG.md`

---

## 12) Link Map

* Skill config: `config/crewai/skills.yaml`
* Skill runtime: `src/rps/crewai_runtime/skills.py`
* Backlog: `doc/overview/feature_backlog.md`
