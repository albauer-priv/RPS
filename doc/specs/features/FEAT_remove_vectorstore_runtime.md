---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-18
Owner: Runtime
---
# FEAT: Remove Vectorstore Runtime

* **ID:** FEAT_remove_vectorstore_runtime
* **Status:** Implemented
* **Owner/Area:** Runtime / Knowledge / UI
* **Last-Updated:** 2026-05-18

## 1) Context / Problem

RPS now uses CrewAI skills and CrewAI `knowledge_sources` for static methodology and
contracts. Workspace tools and snapshot/advisory memory provide athlete/runtime
context. The local Qdrant vectorstore remained in the Streamlit startup path, Plan
Hub readiness UI, and `knowledge_search` tool surface, causing unnecessary sync
work and log noise.

## 2) Goals & Non-Goals

**Goals**

* Remove vectorstore startup sync.
* Remove Plan Hub knowledge-store readiness and rebuild UI.
* Remove `knowledge_search` from agent tool surfaces.
* Remove local vectorstore modules, scripts, and tests.
* Remove Qdrant dependency from project metadata.

**Non-Goals**

* Change CrewAI memory policy.
* Change CrewAI `knowledge_sources` static reference loading.
* Change workspace artefact access.

## 3) Proposed Behavior

Planning and advisory runs use:

* configured CrewAI `knowledge_sources` for static references
* skills for methodology
* workspace tools for artefacts and inputs
* CrewAI/snapshot/advisory memory for non-binding memory

No local vectorstore is built, checked, queried, or exposed in the UI.

## 4) Implementation Analysis

Remove the vectorstore from active runtime boundaries:

* `streamlit_app.py`: no background vectorstore sync.
* Plan Hub: no knowledge-store status/rebuild panel.
* Workspace tools: no `knowledge_search` function.
* Runtime dataclasses/config: no vectorstore resolver/state path.
* Agent specs: no vectorstore name.
* Project dependencies: no Qdrant client.

## 5) Impact Analysis

Compatibility: intentionally removes `knowledge_search` and vectorstore helper scripts.

Risk: any prompt that still asks for `knowledge_search` will fail by tool absence. This
is expected and should be corrected by using CrewAI knowledge sources or workspace reads.

## 6) Options & Recommendation

Option A: disable startup sync only.

Option B: remove the vectorstore runtime completely.

Recommendation: Option B. The vectorstore is redundant with the current skills-first
CrewAI knowledge architecture and creates operational noise.

## 7) Acceptance Criteria

* No app startup vectorstore sync.
* No Plan Hub knowledge-store UI.
* `read_only_workspace` tools do not include `knowledge_search`.
* No runtime imports from `rps.openai.vectorstore*`, `rps.vectorstores`, or Qdrant.
* Tests, lint, typecheck, and smoke checks pass.

## 8) Migration / Rollout

No data migration. Existing local vectorstore files under runtime/cache become inert and
can be deleted manually.

## 9) Risks & Failure Modes

* Failure mode: stale prompt text refers to `knowledge_search`.
  * Detection: CrewAI reports unknown/missing tool or the agent asks for unavailable retrieval.
  * Recovery: move that reference to configured knowledge sources or workspace reads.

## 10) Observability / Logging

Vectorstore sync log events disappear. Knowledge-source loading remains handled by CrewAI
runtime construction.

## 11) Documentation Updates

* Changelog updated.
* Active architecture docs updated to describe CrewAI knowledge sources as the static
  reference path.

