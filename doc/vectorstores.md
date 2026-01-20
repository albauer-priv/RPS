# Vector Store Workflow

Version: 2.0  
Status: Updated  
Last-Updated: 2026-01-20

---

## 1. Overview

This system uses **OpenAI hosted vector stores** as remote knowledge state.
Only **sources + manifests** live in the repo; embeddings never do.

```
knowledge/
  _shared/
    sources/
    manifest.yaml
  macro_planner/
    sources/
    manifest.yaml
  ...
```

Each agent has its own vector store. Shared knowledge can be included via `_shared`.

---

## 2. Manifest Format

Each `knowledge/<agent>/manifest.yaml` declares the vector store name and sources.

```yaml
agent: micro_planner
vector_store_name: vs_micro_planner
description: Micro planning rules

sources:
  - path: sources/micro_rules.md
    tags: [micro, rules]
  - path: sources/workouts_plan_contract.md
    tags: [schema]
```

Paths are relative to the manifest directory.

---

## 3. Sync Script

Use the repo helper to keep OpenAI stores in sync:

```bash
python3 scripts/sync_vectorstores.py
```

Useful flags:

- `--agent <name>`: sync one agent only
- `--manifest <path>`: sync one manifest
- `--delete-removed` / `--prune`: remove remote files missing locally
- `--dry-run`: preview changes

The sync writes `.cache/vectorstores_state.json`, which maps store names to IDs.

---

## 4. Vector Store IDs

IDs are environment-specific. You can set them explicitly to override lookup:

```
OPENAI_VECTORSTORE_SHARED_ID=vs_xxx
OPENAI_VECTORSTORE_MACRO_ID=vs_xxx
OPENAI_VECTORSTORE_MESO_ID=vs_xxx
OPENAI_VECTORSTORE_MICRO_ID=vs_xxx
OPENAI_VECTORSTORE_WORKOUT_ID=vs_xxx
OPENAI_VECTORSTORE_PERFORMANCE_ID=vs_xxx
```

If no env ID is set, the sync script creates or finds a store by name and writes
its ID to `.cache/vectorstores_state.json`.

---

## 5. Runtime Attachment

At runtime, the Responses API attaches **shared + agent vector stores** via
`file_search`:

```python
from app.openai.runtime import build_file_search_tool

tool = build_file_search_tool("micro_planner")
```

Or directly via state resolver:

```python
from app.openai.vectorstore_state import VectorStoreResolver

resolver = VectorStoreResolver()
shared_id = resolver.id_for_store_name("vs_shared_training")
agent_id = resolver.id_for_store_name("vs_micro_planner")
```

---

## 6. Operational Tips

- Keep sources small and well scoped.
- Use `tags` to support metadata filtering later.
- Avoid committing private PDFs; store locally and update only manifests if needed.
- `.cache/` is gitignored by default.

For operational limits, data sensitivity, and incident response, see
`doc/system_architecture.md` (Vector Stores section).

---

## End
