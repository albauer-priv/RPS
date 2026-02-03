# ADR-022: Vector Store Sync Policy

Status: Accepted  
Date: 2026-02-03

## Context

Vector stores are a remote knowledge dependency and must remain consistent with
the repo manifests. Manual syncing is error-prone and makes the UI’s knowledge
state drift from the files on disk.

## Decision

We run a background sync check from Streamlit startup that:

- Computes a deterministic manifest hash (manifest + source file hashes).
- Compares the hash to the last synced hash stored in
  `.cache/vectorstores_state.json`.
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

