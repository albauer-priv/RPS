---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-13
Owner: OpenAI
---
# FEAT: Qdrant Client Singleton

* **ID:** FEAT_qdrant_client_singleton
* **Status:** Implemented
* **Owner/Area:** Local Vectorstore Runtime
* **Last-Updated:** 2026-04-13
* **Related:** `src/rps/vectorstores/qdrant_local.py`

---

## 1) Context / Problem

**Current behavior**

* Each `get_qdrant_client()` call creates a new embedded local Qdrant client for the same path.

**Problem**

* Embedded local Qdrant does not allow concurrent access from multiple client instances to the same storage path.
* Planning fails with `Storage folder .cache/qdrant is already accessed by another instance of Qdrant client`.

**Constraints**

* The fix must preserve local-path and in-memory modes.
* Callers should not need to coordinate client reuse manually.

---

## 2) Goals & Non-Goals

**Goals**

* [x] Reuse one local Qdrant client per configured path.
* [x] Avoid path-lock failures caused by repeated client construction in the same process.
* [x] Cover the behavior with a focused test.

**Non-Goals**

* [x] Changing to a remote Qdrant server deployment.
* [x] Coordinating client reuse across separate OS processes.

---

## 3) Proposed Behavior

**User/System behavior**

* Repeated calls to `get_qdrant_client()` with the same configured path return the same client instance.
* Knowledge search and manifest sync use the shared client instead of racing on embedded storage initialization.

**UI impact**

* UI affected: No

---

## 7) Acceptance Criteria (Definition of Done)

* [x] `get_qdrant_client()` reuses the same client for the same path.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: targeted Qdrant helper test
