---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Runbooks
---
# CrewAI Flow Persistence

## Purpose

Document how RPS marks long-running CrewAI flows as persistence-aware.

## Policy

Configured in `config/crewai/flow_persistence.yaml`.

Default RPS policy:
- `season`: persistent
- `phase`: persistent
- `week`: persistent
- `report`: persistent
- `feed_forward`: persistent
- `coach`: non-persistent

## Runtime notes

* RPS uses a compat-safe persistence decorator wrapper in `src/rps/crewai_runtime/flows.py`.
* When CrewAI persistence is unavailable, flow classes still construct and run without persistence.
* Persistence does not replace run-store telemetry or artifact history.

## Debugging

Check:
- flow policy YAML
- `src/rps/crewai_runtime/flows.py`
- run telemetry in `events.jsonl`
