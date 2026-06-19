# 00 — Preflight

Use this checklist for any non-trivial task.

## Required reading order

1. Read `.clinerules`.
2. Read `doc/overview/feature_backlog.md`.
3. Read `AGENTS.md` if you need the source map.
4. Read `doc/architecture/agents.md` for agent/runtime work.
5. Read relevant ADRs and feature specs.

## Required git checks

- Run `git status -sb`.
- Run `git --no-pager log --oneline -5`.
- Summarize existing local changes before editing overlapping files.
- If scope overlaps with local changes, clarify preserve/revert strategy first.

## Git command hygiene

Always use safe, non-interactive git patterns:

- **Always use `--no-pager`** for all git commands to prevent hanging pager sessions.
- Use `git --no-pager diff --stat HEAD` to understand the current change surface.
- Use `git --no-pager show <hash> --stat` to inspect recent commits before editing overlapping files.
- Use `git stash` before risky multi-file changes when uncommitted work exists.
- Never use interactive git commands (`git rebase -i`, `git add -p`) in automated flows.
- Pipe long outputs through `head`: `git --no-pager show <hash> | head -100`
- For multi-file diffs, use `--stat` first, then targeted `git show <hash> -- path/to/file` for details.

## Scope classification

Classify the task before editing:

- docs-only
- UI / Streamlit
- agent / runtime / orchestration
- prompts / skills / tasks
- schema / contract
- tests / validation

## First question set

Before implementation, confirm:

1. Which canonical doc owns the behavior?
2. Is the task behavior-affecting?
3. Does it need a feature spec or ADR update?
4. Are there overlapping local changes?

## Developer handoff update

If `.developer_handoff/` exists:

1. Read `README.md` first.
2. Update `current_state.md` at task start.
3. Update `next_steps.md` after each completed meaningful task_progress milestone.
4. Update `open_risks.md` when blockers, overlapping local changes, or validation risks appear.
5. Update handoff notes again before completion.