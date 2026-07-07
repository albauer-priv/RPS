# 10 — Docs, Specs, ADRs

## Documentation placement

Choose one canonical home only:

- OVERVIEW → `doc/overview/`
- SPEC → `doc/specs/`
- ARCH → `doc/architecture/`
- UI → `doc/ui/`
- RUNBOOK → `doc/runbooks/`
- ADR → `doc/adr/`

Avoid duplicate canonical content. Prefer short links to the owning document.

## Feature-first workflow

Behavior-affecting changes require a feature spec first under:

- `doc/specs/features/FEAT_<slug>.md`

Use `doc/specs/features/FEAT_TEMPLATE.md`.

## ADR triggers

Create or update an ADR when changing:

- architecture boundaries
- persistence or schema strategy
- cross-cutting contracts
- orchestration or authority flow
- state / memory lifecycle rules

## Module and file size / responsibility

Standard SWE heuristics apply here and are binding: Single Responsibility Principle, Common Closure Principle, the God Object/God Class anti-pattern, and Fowler's Divergent Change / Large Class smells.

- Treat a module or test file that crosses roughly 1500 lines or ~30-40 top-level functions/tests, or that is the most-changed file in the repo for unrelated reasons (Divergent Change), as a signal to evaluate a split. The line/function count is only a trigger for review — the actual criterion is Common Closure Principle: group code that changes for the same reason, split code that changes for different reasons.
- A pure internal split/move (identical behavior, only import paths change) does not need an ADR. A split that touches architecture boundaries, orchestration/authority flow, or telemetry contracts falls under "ADR triggers" above and needs one first, staged incrementally (see ADR-059 for the precedent).
- Trivial helpers used on both sides of a split may be duplicated per module rather than re-imported across the boundary, to avoid circular imports.
- For test files specifically: duplicate small autouse fixtures per split file rather than introducing a shared `conftest.py`, which would silently make them autouse for the entire suite, not just the split files.

## Plan audit before implementation

Before coding, check:

1. Are affected modules/docs/tests/validators/prompts/skills all listed?
2. Is the plan executable without inventing product behavior mid-flight?
3. Does the plan conform to active ADRs and authority boundaries?

## Post-implementation audit

Before completion, summarize:

1. What was fully implemented?
2. Which acceptance criteria were verified?
3. What remains open or deferred?
4. Any architecture/contract deviation?
5. Recommended next step?

## Documentation currency before commit

Before creating a non-WIP commit intended for push:

1. Review all canonical docs affected by the implementation.
2. Update those docs so they match the implemented behavior.
3. If behavior, architecture, contracts, schemas, UI flows, runtime behavior, validation, or operational workflow changed, update the owning docs before commit.
4. If no documentation update is needed, explicitly record why.
5. Do not commit implementation changes that intentionally leave affected documentation stale.

Typical owning docs by change type:

- feature / behavior → `doc/specs/features/`, `doc/overview/feature_backlog.md`, `CHANGELOG.md`
- architecture / runtime / orchestration → `doc/architecture/`, `doc/adr/`, relevant runbooks
- UI / Streamlit → `doc/ui/`
- schema / contracts → `doc/specs/`, `doc/architecture/schema_versioning.md`, validation docs
- operational workflow / validation / deployment → `doc/runbooks/`, `CHANGELOG.md`

## Mermaid rules

- Quote labels that contain spaces or special characters.
- Avoid `\\n`; use `<br>` or a single line.
- For UI flow diagrams, keep layered styling consistent.