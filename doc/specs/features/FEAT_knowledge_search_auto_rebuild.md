---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-13
Owner: OpenAI
---
# FEAT: Knowledge Search Auto Rebuild

* **ID:** FEAT_knowledge_search_auto_rebuild
* **Status:** Implemented
* **Owner/Area:** Knowledge Search / Local Vectorstore
* **Last-Updated:** 2026-04-13
* **Related:** `src/rps/tools/knowledge_search.py`

---

## 1) Context / Problem

**Current behavior**

* Agents use `knowledge_search` against a local Qdrant collection resolved from vectorstore state.
* If the collection is missing, the tool raises and the agent may STOP due to mandatory knowledge-access rules.

**Problem**

* Planning can fail even though the repo-local manifest and knowledge files are available to rebuild the collection.
* Missing `vs_rps_all_agents` should be treated as a recoverable local toolchain issue.

**Constraints**

* Rebuild must use the canonical knowledge manifest.
* State file must be updated after rebuild.
* Retry behavior should be bounded to one rebuild attempt per search call.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Rebuild the local collection automatically when `knowledge_search` detects a missing collection.
* [x] Retry the same search once after the rebuild.
* [x] Keep failure explicit if the manifest cannot be found or rebuild fails.

**Non-Goals**

* [x] Changing hosted/OpenAI vectorstore behavior.
* [x] Introducing background retries or infinite retry loops.

---

## 3) Proposed Behavior

**User/System behavior**

* `knowledge_search` resolves the agent store as before.
* If Qdrant reports the collection as missing, the tool finds the matching local manifest, syncs it, updates state, and retries the query once.
* If rebuild succeeds, planning continues without a manual vectorstore repair step.

**UI impact**

* UI affected: No

---

## 4) Implementation Analysis

**Components / Modules**

* `src/rps/tools/knowledge_search.py`: detect missing collection, rebuild from manifest, retry search.
* `tests/test_knowledge_search.py`: verify rebuild+retry behavior.

**Data flow**

* Inputs: agent name, query, local vectorstore state, manifest
* Processing: search -> detect missing collection -> sync manifest -> retry
* Outputs: knowledge search results or explicit error

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible: Yes
* Breaking changes: none
* Fallback behavior: original exception still surfaces if rebuild cannot recover

---

## 7) Acceptance Criteria (Definition of Done)

* [x] Missing local collection triggers one rebuild attempt from the manifest.
* [x] Search retries once after rebuild.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: targeted knowledge search test
