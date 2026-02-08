---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-06
Owner: Architecture
---
# Vector Store Workflow

Version: 2.0  
Status: Updated  
Last-Updated: 2026-02-06

---

## 1. Overview

This system uses a **local embedded Qdrant** vector store for knowledge state.
Sources + manifests live in the repo; embeddings are built locally at sync time.

```
knowledge/
  _shared/
    sources/
  all_agents/
    manifest.yaml
```

All agents use a single vector store. Shared knowledge is listed once in
`knowledge/all_agents/manifest.yaml` (no per‑agent stores).

Schemas are source-of-truth in `schemas/`. Bundled copies are generated for
vector store retrieval and stored under:

```
knowledge/_shared/sources/schemas/bundled/
```

Run `python scripts/bundle_schemas.py` before syncing vector stores.

---

## 2. Manifest Format

The unified `knowledge/all_agents/manifest.yaml` declares the store name and sources.

```yaml
agent: all_agents
vector_store_name: vs_rps_all_agents
description: Unified knowledge store for all agents

sources:
  - path: ../_shared/sources/specs/load_estimation_spec.md
    tags: [week, rules]
  - path: sources/week_plan_contract.md
    tags: [schema]
```

Paths are relative to the manifest directory.

---

## 3. Sync Script

Vector stores are synced locally via the background job (Streamlit). The helper
script is retained for manual validation and troubleshooting:

```bash
python3 scripts/smoke_vectorstores.py
```

The sync writes `.cache/vectorstores_state.json`, which maps store names to
local collection IDs.

---

## 3.1 Background Sync (Streamlit)

Streamlit startup runs a background check to keep vector stores current:

- Computes a deterministic manifest hash (manifest + source file hashes).
- Compares to the last synced hash stored in `.cache/vectorstores_state.json`.
- If the hash differs, performs a **reset + full sync**.

The check runs on a configurable interval:

```
RPS_VECTORSTORE_SYNC_INTERVAL_MINUTES=60
```

Disable the background sync (for manual control):

```
RPS_DISABLE_VECTORSTORE_SYNC=1
```

Local storage settings:

```
RPS_LLM_VECTORSTORE_PATH=.cache/qdrant
RPS_LLM_EMBEDDING_MODEL=text-embedding-3-small
RPS_LLM_EMBEDDING_BATCH_SIZE=32
```

---

## 4. Vector Store IDs

IDs map to local Qdrant collection names. The sync writes them to
`.cache/vectorstores_state.json` for runtime lookup.

---

## 5. Runtime Attachment

At runtime, agents call the `knowledge_search` function tool, which queries the
local Qdrant collection:

```python
from rps.tools.knowledge_search import search_knowledge

results = search_knowledge("week_planner", "What is the Week Plan schema?")
```

Or directly via state resolver:

```python
from rps.openai.vectorstore_state import VectorStoreResolver

resolver = VectorStoreResolver()
agent_id = resolver.id_for_store_name("vs_rps_all_agents")
```

---

## 6. Operational Tips

- Keep sources small and well scoped.
- Use `tags` to support metadata filtering later.
- Avoid committing private PDFs; store locally and update only manifests if needed.
- Do not include rendered sidecars (`*.md` under `var/athletes/*/rendered`) in vector stores.
- `.cache/` is gitignored by default.

For operational limits, data sensitivity, and incident response, see
`doc/architecture/system_architecture.md` (Vector Stores section).

---

## End
