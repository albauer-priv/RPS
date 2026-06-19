# 40 — Validation and Release

## Default validation before completion

Unless the user explicitly narrows scope, run:

- `python3 -m py_compile $(git ls-files '*.py')`
- `./scripts/run_lint.sh`
- `./scripts/run_typecheck.sh`
- one relevant smoke run (see `.clinerules.d/60-test-runtime-env.md` for invocation patterns)

## Iterative-fix discipline

Prevent trial-and-error fix loops:

- **Before fixing a bug, add a reproducing test first.**
- If you make more than 2 fix commits in the same file/area in one session, **STOP** and do explicit root-cause analysis before the next commit.
- Do not commit "fix: repair X" without at least one test that would have caught the original bug.
- Fix commits without a repro test need an explicit note in the commit message explaining why no test is possible.
- Prefer one deliberate fix with test over multiple iterative trial commits.

## Schema / contract changes

Also run as needed:

- `python3 scripts/check_schema_required.py`
- `python3 scripts/bundle_schemas.py`
- relevant artifact validation / output validation

## CHANGELOG discipline

Format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/):

- Use `## [version] - YYYY-MM-DD` format for version sections
- Never use raw date headers (`## 2026-05-19`) or unbracketed headers (`# Unreleased`)
- Only one `## [Unreleased]` section, always at the top
- `[Unreleased]` stays empty except for truly uncommitted changes
- When tagging a version:
  1. Rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD`
  2. Add a new empty `## [Unreleased]` section at the top
- Never embed version-bump decisions inside `### Changed` bullet text
- Entries must be under `### Added`, `### Changed`, `### Fixed`, or `### Removed` only
- No inline prose sections, no raw commit dumps

## Commit / push discipline

Before commit or push:

- check whether a SemVer version bump is required
- update `CHANGELOG.md` per the CHANGELOG discipline rules above
- record if no version bump was needed and why

Before creating a non-WIP commit intended for push:

- review all documentation affected by the implementation
- update canonical docs to match the implemented behavior
- if no documentation update is needed, record why

For non-WIP commits intended for push:

1. Decide whether the change requires a SemVer version bump.
2. If a version bump is required:
   - update the canonical version file(s)
   - update `CHANGELOG.md` with the released version entry
   - create a Git tag for the new version, e.g. `vX.Y.Z`
   - push both commit and tag
3. If no version bump is required:
   - record why no version bump/tag was needed

Do not tag without a version bump.
Do not force version bumps or tags for purely local WIP commits.

## Deployment rule

If validation is expected through Docker or GitHub Action builds, commit and push before asking for server-side verification; otherwise the deployed instance may still reflect old code.