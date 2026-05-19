---
Version: 1.0
Status: Superseded
Last-Updated: 2026-05-18
Owner: ADR
---
# ADR-022: Vector Store Sync Policy

Status: Superseded by ADR-050
Date: 2026-02-03

This decision is no longer active. The vectorstore runtime was removed by
[ADR-050](ADR-050-remove-vectorstore-runtime.md).

## Context

Vector stores are a remote knowledge dependency and must remain consistent with
the repo manifests. Manual syncing is error-prone and makes the UI’s knowledge
state drift from the files on disk.

## Decision

We run a background sync check from Streamlit startup that:

- Computes a deterministic manifest hash (manifest + source file hashes).
- Compares the hash to the last synced hash stored in
  `runtime/vectorstores_state.json`.
- If hashes match, mark the store as up to date.
- If hashes differ or the store is unknown, **reset** the vector store and
  re-sync all sources.

The background job:

- Writes run status to the run store under `process_type=system_housekeeping`
  and `process_subtype=vectorstore_sync`.
- Observes a configurable check interval (default: 60 minutes).
- Skips if a sync is already running.

## Consequences

- The vector store is kept current without manual intervention.
- Syncs are observable in System → Status and in run history.
- A reset on mismatch is slightly more expensive but guarantees clean state.
