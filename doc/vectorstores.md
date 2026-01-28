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

Use the repo helper to keep OpenAI stores in sync:

```bash
python3 scripts/sync_vectorstores.py
```

Useful flags:

- `--manifest <path>`: sync one manifest
- `--delete-removed` / `--prune`: remove remote files missing locally
- `--reset`: delete all remote files before syncing (reinitialize)
- `--dry-run`: preview changes

The sync writes `.cache/vectorstores_state.json`, which maps store names to IDs.

---

## 4. Vector Store IDs

IDs are environment-specific. You can set them explicitly to override lookup:

```
OPENAI_VECTORSTORE_ALL_AGENTS_ID=vs_xxx
```

If no env ID is set, the sync script creates or finds a store by name and writes
its ID to `.cache/vectorstores_state.json`.

---

## 5. Runtime Attachment

At runtime, the Responses API attaches the shared store via `file_search`:

```python
from rps.openai.runtime import build_file_search_tool

tool = build_file_search_tool("week_planner")  # resolves vs_rps_all_agents
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
`doc/system_architecture.md` (Vector Stores section).

---

## End
