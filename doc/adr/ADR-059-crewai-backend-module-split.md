---
Version: 1.0
Status: Accepted
Last-Updated: 2026-07-07
Owner: Agent Runtime
---
# ADR-059: CrewAI Backend Module Split

## Context

`src/rps/agents/crewai_backend.py` is 4357 lines and 87 top-level functions, mixing five distinct concerns: season/phase bundle normalization and semantic sanitization, CrewAI agent/crew/LLM construction, task execution orchestration, structured-output extraction/parsing, and artifact persistence/validation. It is the single most-changed file in the repository over the last 90 days, which is itself a symptom of low cohesion — unrelated changes routinely land in the same file.

This module owns cross-cutting contracts: it is the execution surface for the Season/Phase/Week/Report planning/review/writer stages (ADR-035 authority boundaries), it is wrapped by the outer Flow orchestration (ADR-037), and it emits the Flow/Crew/Task telemetry events (ADR-040). Because of that, `.clinerules.d/10-docs-specs-adr.md`'s ADR trigger for "cross-cutting contracts" applies here, unlike a purely internal refactor of a single-purpose module (e.g. the `deterministic_context.py` typed-projection migration, which needed no ADR because it never touched orchestration, authority, or telemetry boundaries).

An audit of the file (structural map + full external-consumer trace) found:

- No module-level imports of `crewai_backend` anywhere in the repo, and no re-export of its contents at `rps.agents.__init__`.
- 28 names imported by name across 5 files: the bulk (24 names) by `tests/test_crewai_runtime.py`, one name each by `src/rps/evidence/curation.py` and `src/rps/crewai_runtime/flows.py`, and two by `src/rps/agents/runtime.py` (dynamic imports inside functions).
- `tests/test_crewai_runtime.py` also monkeypatches 10 string-based paths (e.g. `"rps.agents.crewai_backend._execute_crewai_multiagent_crew"`) and does one full-module mock via `monkeypatch.setitem(sys.modules, "rps.agents.crewai_backend", ...)`.
- The file splits into 7 functional groups by dependency analysis:
  - **Group A** — season/phase bundle normalization and semantic sanitization (~1341 lines, 25 functions). No circular dependencies; calls only external imports and its own helpers.
  - **Group B** — CrewAI agent/crew/LLM construction and tool resolution (~1856 lines, 11 functions). Unidirectional dependency on `rps.crewai_runtime.*` and telemetry; no circular calls.
  - **Group C** — structured-output extraction and parsing (~231 lines, 10 functions). Self-contained aside from two small pieces of module-level state (see Decision).
  - **Validation group** — bundle/artifact contract validation and meta normalization (~77 lines, 7 functions). Calls guardrail validators; no circular calls.
  - **Group D** — contract/context-block building for prompts (~368 lines, 11 functions). Tightly coupled to mutable guardrail runtime context (`current_guardrail_runtime_context`); moderate extraction risk.
  - **Group E** — task execution orchestration (~1644 lines, 15 functions, including the 4 public entry points). This is the core glue: it calls into every other group through closures and callback signatures. High extraction risk.
  - **Group F/G** — artifact persistence (~58 lines) and small tooling/prompt-description utilities (~97 lines). Low risk but small enough that extracting them alone has limited payoff; folded into later phases or left in place per phase scope.

## Decision

Adopt a staged module split, one low-risk group per phase, tracked in `doc/specs/features/FEAT_crewai_backend_module_split.md`:

1. **Phase 1 (this ADR's initial implementation):** extract **Group C** into `src/rps/agents/crewai_output_extraction.py`.
2. **Phase 2 (tracked, not scheduled):** extract the **Validation group** into `src/rps/agents/crewai_validation.py`.
3. **Phase 3 (tracked, not scheduled):** extract **Group B** into `src/rps/agents/crewai_builders.py`.
4. **Phase 4 (tracked, not scheduled):** extract **Group A** into `src/rps/agents/crewai_bundle_normalization.py`.
5. **Group D and Group E stay in `crewai_backend.py` indefinitely.** They form the tightly-coupled orchestration core and untangling the guardrail-context coupling (Group D) and the closure-based execution flow (Group E) is a separate design problem, not a mechanical file split. No phase in this ADR attempts it.

For each phase, function bodies move verbatim (no logic changes). Where a moved function is still called from code that stays in `crewai_backend.py`, `crewai_backend.py` imports it back by name from the new module — no re-export shim is added in the other direction, per this repo's existing convention against compatibility-hack layers. External callers (production code and tests) update their import statements to the new module path directly; there is no re-export at `rps.agents.__init__` to preserve, so this does not change any package-level public surface.

Each phase must:
- Preserve every existing external name and its behavior exactly (verified via the existing `tests/test_crewai_runtime.py` suite, which directly imports and monkeypatches most of the moved names).
- Not change orchestration boundaries, authority boundaries, task/crew wiring, or telemetry event shapes.
- Land as its own commit/PR with full validation (compile, lint, typecheck, targeted + full test suite), the same discipline already used for the `deterministic_context.py` and `_load_latest_payload` refactor series.

## Consequences

- Positive: `crewai_backend.py` shrinks by ~231 lines in Phase 1 (more in later phases), each extracted module has one clear responsibility, and future changes to output-extraction logic no longer risk touching unrelated execution/normalization code in the same file/diff.
- Positive: no behavior change — this is purely an internal reorganization. No SemVer bump is required for any phase.
- Trade-off: multiple small commits/PRs are required instead of one large one, matching this repo's established staged-refactor discipline.
- Trade-off: `crewai_backend.py` remains a large file (Groups D and E alone are ~2000 lines) even after all four scheduled phases land. This ADR does not solve the full god-module problem — it removes the safely-extractable ~3500 lines, not the ~2000-line orchestration core.
- Risk: string-based monkeypatch targets in `tests/test_crewai_runtime.py` must be updated in lockstep with each phase's function moves, or tests will silently patch a stale/nonexistent attribute path. Each phase's implementation must grep for every monkeypatch string touching moved names before considering the phase complete.

## Exceptions

- Group D (contract/context-block building) and Group E (task execution orchestration) are explicitly excluded from this ADR's scope. Splitting them requires first resolving the guardrail-runtime-context coupling (Group D) and the closure-based planning/review/writer callback structure (Group E) — a design decision, not a mechanical extraction. A future ADR should address this separately if and when that design work happens.
