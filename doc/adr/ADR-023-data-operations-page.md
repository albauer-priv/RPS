---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: ADR
---
# ADR-023 — Athlete Data Operations Page

- **Status:** Accepted
- **Date:** 2026-02-03
- **Owners:** RPS UI

## Context

Athletes need a clear entrypoint for backup and restore operations. These flows are not part of planning or performance, and must live under Athlete Profile to keep ownership and scope clear.

## Decision

Add a new **Athlete Profile → Data Operations** page that hosts Backup and Restore actions. The page provides UI affordances and explanatory text; actual backup/restore logic will be implemented behind these actions.

## Consequences

- Backup/restore is discoverable without mixing with planning or analysis pages.
- Future UI/CLI workflows can be linked to this entrypoint.
- Runs/logs remain excluded from backup scope by default.

## Alternatives Considered

- Place under System → History/Status (rejected: not athlete-owned).
- Place under Plan Hub (rejected: not planning flow).
