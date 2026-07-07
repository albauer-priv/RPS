---
Version: 1.0
Status: Accepted
Last-Updated: 2026-07-07
Owner: Agent Runtime
---
# ADR-060: CrewAI Backend Context-Block and Task-Execution Split

## Context

ADR-059 split `src/rps/agents/crewai_backend.py` from 4357 to 2474 lines across four phases, extracting structured-output extraction (Group C), bundle/artifact validation, CrewAI agent/crew/LLM construction (Group B), and season/phase bundle normalization (Group A). It explicitly excluded two remaining groups, stating: *"Splitting them requires first resolving the guardrail-runtime-context coupling (Group D) and the closure-based planning/review/writer callback structure (Group E) — a design decision, not a mechanical extraction."*

This ADR re-examines that exclusion with a full, line-by-line trace of every remaining name in the file (not the original 4357-line estimate, which predates Phases 1-4 and was itself corrected multiple times during those phases — Group B was originally estimated at ~11 functions, turned out to be 14; a similar correction applies here).

**Finding: the coupling does not block a same-behavior file split.**

- `current_guardrail_runtime_context()` (the function context-block-building code calls) already lives in a separate module, `src/rps/crewai_runtime/guardrails.py`, and is already imported into `crewai_backend.py` today. A `ContextVar` resolves identically regardless of which `.py` file the reading function is physically defined in — moving the reading code to yet another module changes nothing about this mechanism.
- The actual context values (`phase_execution_context`, `phase_slot_context`, `season_phase_load_context`, `week_calendar_context`) are set from *outside* `crewai_backend.py` entirely — in `src/rps/orchestrator/plan_week.py:1374,1701` and `src/rps/orchestrator/season_flow.py:336,671` — and merge (via `current.update(...)` inside `guardrail_runtime_context`, not replacement) with the narrower `root=`/`athlete_id=`/`run_id=`/`component=`/`task_name=` context set closer to `crew.kickoff()` inside `crewai_backend.py`. This confirms the mechanism was already designed to cross module boundaries; nothing about a same-behavior split changes that.
- The closures (`_planning_runner`, `_review_runner`, and the tool-loading closures in `_build_crewai_tooling`) are ordinary Python closures. Python does not require a closure to be co-located with its caller — they work identically regardless of which module contains the enclosing function.

**Corrected group composition** (verified directly against the current 2474-line file via `grep`/line-range cross-referencing, not the earlier automated estimate, which mis-scoped several functions):

- **Group D (context-block building)** — 5 functions: `_loaded_input_version_key`, `_phase_writer_authority_context_block`, `_contract_context_blocks_for_task`, `_phase_bundle_finalize_authority_freeze_block`, `_phase_bundle_finalize_has_bound_contracts` (lines 236-619). `_as_map` (line 133) turns out to be used *exclusively* inside this range (all 15 call sites verified) — it moves with the group entirely, not duplicated.
- **Group E (task execution orchestration)** — larger than either prior estimate: 23 functions, not 14. The earlier automated pass mis-scoped 9 functions as "other helpers" (`_sanitize_replan_decision_context`, `_compact_internal_user_input`, `_extract_authoritative_runtime_blocks`, `_augment_user_input`, `_build_internal_task_description`, `_persist_artifact_document`, `_normalize_document`, `_build_crewai_tooling`, `_build_task_description`) that turned out, on direct call-site verification, to be exclusively called by Group E functions. Also moves: 7 exclusive task-name constants (`_TASK_BLUEPRINT_BY_AGENT_TASK`, `_SEASON_PLANNING_TASKS`, `_SEASON_REVIEW_TASKS`, `_PHASE_PLANNING_TASKS`, `_PHASE_REVIEW_TASKS`, `_WEEK_PLANNING_TASKS`, `_WEEK_REVIEW_TASKS`), 6 prompt-compaction constants (`_INTERNAL_PROMPT_CHAR_LIMIT`, `_INTERNAL_PROMPT_WORD_LIMIT`, `_INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT`, `_INTERNAL_PROMPT_PRIORITY_MARKERS`, `_AUTHORITATIVE_RUNTIME_BLOCK_PREFIXES`, `_INTERNAL_TOOL_FIRST_RULES`), and `ROOT` (all uses verified exclusive to Group E). This group includes all 4 of `crewai_backend.py`'s remaining public entry points: `execute_structured_internal_task_crewai`, `run_phase_bundle_crewai`, `run_agent_multi_output_crewai`, `run_agent_multi_output_preview_crewai`.
- **`_render_json_block`** is genuinely shared between Group D and Group E (verified call sites in both ranges) — duplicated into both new modules rather than having one group import from the other, to keep them as independent peers.
- **Remainder**: after both groups move, `crewai_backend.py` retains essentially nothing — `logger`, the `JsonMap`/`ToolMap` type aliases, and `_phase_document_from_bundle`, a function with **zero call sites anywhere in the repository** (verified via repo-wide grep) — i.e. pre-existing dead code, unrelated to this split. This ADR does not remove it (no-behavior-change scope); a future, separate, trivial cleanup can retire it and `crewai_backend.py` itself once nothing references either.
- **External production consumers** (not just the test file): `src/rps/evidence/curation.py`, `src/rps/crewai_runtime/flows.py`, and `src/rps/agents/runtime.py` (two dynamic imports) import the 4 Group E public entry points directly — confirmed by grep, and consistent with ADR-059's original external-consumer audit. These need their import paths updated in Phase 6, in addition to `tests/test_crewai_runtime.py`.

## Decision

Complete the staged module split from ADR-059:

1. **Phase 5**: extract Group D into `src/rps/agents/crewai_context_blocks.py`.
2. **Phase 6**: extract Group E into `src/rps/agents/crewai_task_execution.py`, and update the 3 external production consumers plus `tests/test_crewai_runtime.py`'s import block and monkeypatch strings.

Both phases move function bodies verbatim — no logic changes, no redesign of the `ContextVar`-based guardrail context mechanism, and no redesign of the closure-based planning/review/writer loop. This ADR supersedes ADR-059's Exceptions section: Groups D and E are no longer permanently excluded, but the specific *redesign* ADR-059 anticipated (making context explicit, replacing closures with a state machine) remains out of scope here and is not attempted — only the file relocation.

Same constraints as ADR-059: preserve every external name and behavior exactly; no orchestration/authority/telemetry boundary changes; no re-export shim (external callers update import paths directly); each phase lands as its own commit with full validation.

## Consequences

- Positive: closes out the entire `crewai_backend.py` module-split effort started in ADR-059. After Phase 6, `crewai_backend.py` shrinks to a near-empty shell (a handful of lines plus one pre-existing dead function), effectively dissolving the original 4357-line god-module down to nothing of substance.
- Positive: no behavior change in either phase — purely internal reorganization. No SemVer bump required.
- Trade-off: Phase 6 is the largest single phase across both ADRs (23 functions, ~1900 lines including constants) and touches 3 production import sites outside the test file, in addition to `tests/test_crewai_runtime.py`'s 9 monkeypatch strings. It requires the same exhaustive dependency-audit discipline as every prior phase, at the largest scale yet.
- Risk: the corrected Group E scope (23 vs. the originally estimated 14-15 functions) means the exhaustive audit at Phase 6's start must re-verify every function independently rather than trusting this ADR's classification as final — the same discipline that caught this correction in the first place must continue through implementation.
- Follow-up (explicitly out of scope here): `_phase_document_from_bundle`'s dead code and `crewai_backend.py`'s eventual full retirement are a separate, trivial future cleanup, not part of this ADR's no-behavior-change scope.

## Exceptions

None remaining for the module-split effort — this ADR closes out ADR-059's Exceptions section. A genuine *redesign* of guardrail-context threading (replacing `ContextVar` with explicit parameters) or the closure-based execution loop (replacing it with a state machine) remains unaddressed and would need its own future ADR if ever pursued; this ADR does not argue such a redesign is necessary, only that it is not required for the file-relocation split completed here.
