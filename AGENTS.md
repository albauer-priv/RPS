# AGENTS.md — RPS Agent Entry Point

This file is the compatibility entry point for coding agents working in this repository.
It is intentionally short.

## Purpose

- `AGENTS.md` is the **agent entry/source map**.
- `.clinerules` contains the **operative Cline working rules**.
- `.clinerules.d/` contains **area-specific supporting checklists**.
- `.developer_handoff/` may exist as a **local, non-authoritative development handoff aid**.

## Required first reads

For any non-trivial task, read in this order:

1. `.clinerules`
2. `doc/overview/feature_backlog.md`
3. `doc/architecture/agents.md`
4. Relevant ADRs in `doc/adr/`
5. Relevant feature spec in `doc/specs/features/`

Also always check:

- `git status -sb`
- `git --no-pager log --oneline -5`

If uncommitted changes exist, summarize them and do not edit overlapping files until preserve/revert strategy is clear.

## Canonical source map

- **Cline working rules:** `.clinerules`
- **Additional area checklists:** `.clinerules.d/`
- **Agent/runtime authority map:** `doc/architecture/agents.md`
- **Architecture decisions:** `doc/adr/`
- **Feature behavior/specs:** `doc/specs/features/`
- **Documentation index:** `doc/README.md`
- **Backlog priority:** `doc/overview/feature_backlog.md`
- **Validation procedure:** `doc/runbooks/validation.md`
- **Release history:** `CHANGELOG.md`
- **Runtime/system truth:** validated workspace artefacts, code-owned deterministic context, and runtime-owned metadata

## Non-negotiables summary

- Do not overwrite user or branch-local work.
- No new dependencies without approval.
- No secrets in code or committed files.
- Behavior-affecting changes follow feature-first workflow.
- Respect top-level authority boundaries and planning/review/writer stage ownership.
- Keep runtime truth code-owned / workspace-owned where architecture requires it.
- Run the required validation before calling work complete unless the user explicitly narrows scope.
- Before non-WIP push commits, ensure affected canonical docs are updated to match the implementation, or explicitly record why no doc update was needed.
- Before non-WIP push commits, update `CHANGELOG.md`, make a SemVer decision, and if bumping the version also create/push the matching Git tag.

## Local developer handoff

If present, `.developer_handoff/` is:

- local
- optional
- non-authoritative
- development-time only

It must not define or override runtime behavior, architecture decisions, schemas, artefact contracts, planning rules, selected versions, pending operations, or workspace truth.

## Notes

- Do not duplicate large architecture tables or backlog snapshots here.
- Keep long-form rules in `.clinerules` and canonical system truth in `doc/`.
