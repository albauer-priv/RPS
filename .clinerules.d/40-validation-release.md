# 40 — Validation and Release

## Default validation before completion

Unless the user explicitly narrows scope, run:

- `python3 -m py_compile $(git ls-files '*.py')`
- `./scripts/run_lint.sh`
- `./scripts/run_typecheck.sh`
- one relevant smoke run

## Schema / contract changes

Also run as needed:

- `python3 scripts/check_schema_required.py`
- `python3 scripts/bundle_schemas.py`
- relevant artifact validation / output validation

## Commit / push discipline

Before commit or push:

- check whether a SemVer version bump is required
- update `CHANGELOG.md`
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