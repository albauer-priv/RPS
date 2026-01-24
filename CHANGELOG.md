# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Durability principles now include the permitted "Kinzlbauer macro template" archetype (macro-level sequencing and traceability anchors).
- Macro load corridor policy spec for deriving weekly kJ/TSS bands from availability, wellness, KPI guidance, and activity trends.
- KPI profiles now include moving-time pacing guidance (`kJ/kg/h` + `W/kg`) for brevet/ultra segments.
- Macro overview body metadata now records `body_mass_kg` alongside the reference mass window.
- Season brief template/spec now includes `Body-Mass-kg` for precise load scaling.
- Availability artefact (`AVAILABILITY`) + schema/interface spec, plus a Season Brief availability parser.
- Data pipeline now derives a ZONE_MODEL from Intervals.icu athlete sport settings and writes it to `latest/`.
- Season-Scenario-Agent with `SEASON_SCENARIOS` artefact + schema, plus strict store tool support.
- Season scenarios contract + interface spec for scenario → macro handoff.
- Season scenarios template and new `vs_season_scenario` vector store manifest.
- Season scenarios schema now includes advisory guidance (cadence, phase recommendations, risks, constraints, intensity guidance).
- Season scenario selection artefact + schema (`SEASON_SCENARIO_SELECTION`) with deterministic CLI write.
- New validation checklist for `SEASON_SCENARIOS`.
- Per-agent reasoning overrides via `OPENAI_REASONING_EFFORT_<AGENT>` and `OPENAI_REASONING_SUMMARY_<AGENT>`.
- CLI logging switches (`--log-level`, `--log-file`) with structured log output.
- Tool-call debug logging for agent runners.
- Responses API reasoning settings via `OPENAI_REASONING_EFFORT` / `OPENAI_REASONING_SUMMARY`.
- Reasoning summaries (when returned) are logged to CLI and log files.
- Meso-Architect prompt now specifies workspace_put_validated usage and block governance schema requirements.
- Added a BLOCK_GOVERNANCE template for Meso-Architect with fill markers.
- `--debug-file-search` now logs file_search results to CLI/logs.
- `run-task` CLI for strict schema-validated agent outputs (uses read tools + strict store tools).
- Meso-Architect prompt now enforces exact template structure when a template is found.
- Debug file_search logging now captures `file_search_call` results in strict runs.
- `run-task` now supports `--max-results` for file_search.
- Meso-Architect file_search guidance prioritizes the BLOCK_GOVERNANCE template filter.
- Meso-Architect prompt now requires strict store tool calls instead of raw JSON when available.
- `run-agent` now accepts `--task`, `--run-id`, `--max-results`, and strict mode toggles.
- Macro overview schema now supports structured recovery protection (`fixed_rest_days` + `notes`) and requires it under global constraints.
- Block execution architecture schema now includes structured weekly load ranges with a required `source` field.
- Added a BLOCK_EXECUTION_ARCH template for Meso-Architect with fill markers.
- Added a BLOCK_EXECUTION_PREVIEW template for Meso-Architect with fill markers.
- Added templates for Macro-Planner (MACRO_OVERVIEW, MACRO_MESO_FEED_FORWARD).
- Added templates for Micro-Planner (WORKOUTS_PLAN).
- Added templates for Workout-Builder (INTERVALS_WORKOUTS).
- Added templates for Performance-Analyst (DES_ANALYSIS_REPORT).
- Principles validation checks added to macro overview, block governance, and block execution arch validation docs.
- Macro overview justification section with structured citations and per-phase rationale.
- Wellness artefact (`WELLNESS`) + schema/interface spec for daily biometric/self-report data.
- Data pipeline now writes `wellness_yyyy-ww.json` and latest `wellness.json`.
- Availability validation checklist and `validate_outputs.py` support for availability artefacts.
- Standalone scripts now emit per-run logs with timestamped filenames under `var/athletes/<athlete_id>/logs`.
- Logging policy document for levels, format, and per-run log file locations.
- Artifact writes now emit INFO logs with type, version key, and path.
- Artifact saves now trigger automatic rendering to Markdown when a template exists.
- Missing render templates now log an error and are skipped without failing the run.
- Runner now forces tool calls for DES_ANALYSIS_REPORT to avoid fallback writes.
- Performance-Analyst prompt now pins DES report schema constants and recommendation scope.

### Fixed
- Workspace tool writes now tolerate missing `run_id` by falling back to meta/context defaults.
- Agent runner now auto-generates a run id for tool-based writes.
- Schema validation errors now return detailed failure lists in tool results.
- Agent runners now preserve the last non-empty text output after tool-call iterations.
- Agent runners now recover text from message output items when output_text is empty.
- Mode A scenarios now inline the season brief to avoid tool-call loops that suppressed scenario output.
- Strict multi-output runner now falls back to storing validated JSON when the model omits the store tool call.
- Strict runner now forces tool calls for `SEASON_SCENARIOS`, `SEASON_SCENARIO_SELECTION`, and `MACRO_OVERVIEW` when missing.
- Runner normalizes season-scenario payloads (required arrays, disallowed keys) before validation.
- Runner normalizes workouts plan meta fields to schema constants before validation.
- Performance-Analyst prompt no longer stops early when binding sources are not returned by file_search.
- Default CLI log filenames now include a UTC timestamp to avoid overwriting logs per run.
- Responses payloads now omit `temperature` for models that do not support it (e.g., gpt-5).
- Activities trend metadata now derives `iso_week_range` from the underlying temporal scope.
- `validate_outputs.py` now uses the updated logging helper signature.

### Changed
- KPI profile schema removed per-kg preload windows and now requires moving-time rate guidance instead.
- Macro overview schema/template replaces per-kg preload references with `moving_time_rate_guidance`.
- Macro-Planner now derives weekly kJ corridors from body mass, kJ/kg/h guidance, and weekly hours.
- Macro/Meso/Micro/Scenario prompts now require AVAILABILITY for weekday constraints + weekly hours.
- Availability artefacts now scope from generation date to season year end and are replaced by newer versions.
- Meso-Architect governance now targets upper-third load bands for build/peak weeks by default.
- ZONE_MODEL owner moved to Data-Pipeline; Meso-Architect now consumes the latest model instead of generating it.
- Macro overview schema now requires `body_mass_kg` and removes `reference_mass_window_kg`.
- KPI profile narrative guidance now references moving-time rate bands instead of legacy kJ/kg preloads.
- Macro Mode A scenarios now run Season-Scenario-Agent, store `season_scenarios`, and render the same cached scenario dialogue for selection.
- Macro-Planner prompt can optionally load `SEASON_SCENARIOS` as advisory input.
- System architecture, planner workflow, how-to-plan, and artefact flow docs updated to include Season-Scenario-Agent and `season_scenarios`.
- Season-Scenario prompt and template expanded to emit guidance fields; scenario cache output now includes guidance + phase outline.
- Macro-Planner prompt now consumes scenario guidance when present.
- Macro Mode A selection (`select`) is now deterministic (no LLM) and `overview` accepts optional `--scenario` if selection exists.
- `run-agent` now defaults to strict tool mode for JSON-producing agents; use `--non-strict` to opt out.
- Macro Mode A helper now passes reasoning settings into the strict runner.
- Meso-Architect and Micro-Planner now have access to the macro load corridor policy (informational, non-binding).
- Availability parser now derives the season year from the Season Brief when `--year` is omitted.
- Availability parser now correctly parses decimal hour values (e.g., 1.5 h).
- Multi-output runner now auto-widens degenerate block governance bands (min == max).
- Meso-Architect no longer uses markdown templates; outputs are schema-driven JSON only.
- Macro, Season-Scenario, Micro-Planner, Workout-Builder, and Performance-Analyst templates removed in favor of schema-driven JSON.
- Agent prompts now fully remove template lookup rules; all outputs are schema-driven JSON only.
- Macro Mode A overview now accepts a moving-time rate band override.
- Wellness artefact now includes `body_mass_kg` (from Intervals.icu athlete profile, with wellness fallback).
- Meso-Architect prompt now enforces non-zero weekly band widths and upper-third corridor placement.
- Macro-Planner now writes structured fixed rest days when provided.
- Meso-Architect now propagates macro-level availability/risk constraints into governance and execution architecture.
- Meso-Architect now mirrors block governance load ranges into execution architecture.
- Guarded store now rejects Meso outputs that fail macro-constraint propagation checks.
- Block governance template now embeds macro-constraint mapping placeholders.
- Agent prompts now include conditional template usage guidance.
- Guarded store now enforces execution preview traceability to execution architecture.
- Meso-Architect prompt now requires weekly kJ/TSS progression patterns (default 3:1) unless macro specifies steady-state.
- Durability-first principles updated to v1.1 with expanded progressive overload guidance, intensity distribution rules, and 3:1 alternatives.
- Principles paper translated to English and synced for macro/meso knowledge sources.
- Macro-Planner prompt now requires applying Principles sections 2-6.
- Meso-Architect prompt now requires applying Principles sections 3.3, 3.4, 4, 5, and 6.
- Macro-Planner prompt now requires populating `data.justification` with citations and per-phase rationale.
- Macro-Planner validation now enforces narrative/domain consistency and deload flag alignment.
- Macro overview template updated to v1.1 to include justification fields.
- Macro Mode A overview now injects selected scenario details into the prompt when available.
- Validation tooling and docs now include wellness outputs.
- Scenario, macro, and meso prompts now conditionally apply Principles 3.4 sequencing guidance only when the ultra/brevet archetype is explicitly requested, and only when availability supports the time-crunched weekend emphasis.
- Principles 3.2 backplanning guidance rewritten as an agent-executable planning cookbook and synced to agent knowledge copies.
- Principles 3.2 macrocycle wording now aligns with `MACRO_CYCLE_ENUM` (Base/Build/Peak/Transition).
- Macro-Planner prompt now mirrors the `MACRO_CYCLE_ENUM` wording in backplanning guidance.
- Agent artifact storage now nests plans/analysis/exports under `var/athletes/<id>/data/`, and the legacy `workouts/` folder is no longer created.

## [0.2.0] - 2026-01-22

### Added
- Per-agent model overrides via `OPENAI_MODEL_<AGENT>` and CLI plumbing to honor them.
- Per-agent temperature overrides via `OPENAI_TEMPERATURE_<AGENT>` (plus global `OPENAI_TEMPERATURE`).
- `workspace_get_input` tool for athlete-specific markdown inputs (season brief, events).
- Vector store sync progress output and `--reset` to reinitialize stores.
- Vector store sync now attaches header/schema-derived attributes for filtered file_search.
- Schema bundling workflow (`scripts/bundle_schemas.py`) and bundled outputs under `knowledge/_shared/sources/schemas/bundled/`.
- Vector store smoke test script: `scripts/smoke_vectorstores.py`.
- Build checklist and recommended model guidance docs.
- Mode A macro helper script for scenarios + macro overview (`scripts/macro_mode_a.py`).

### Changed
- Force `file_search` by default in agent runs; add `--no-file-search` to disable.
- Shared knowledge manifests now reference bundled schemas; rendered KPI sidecars removed.
- Schema bundler handles `jsonref` serialization for bundled outputs.
- Agent prompts now treat instructions as a single file with section-based guidance; removed bundle/BEGIN/END marker references.
- Agent prompts now point to schema files instead of deprecated templates and year-specific filenames.
- Agent prompts are simplified further by removing legacy template/YAML language and redundant checks.
- Planning docs now specify copying the selected KPI profile into `latest/kpi_profile.json`.
- Artefact flow docs now describe the two-step Macro Mode A scripts.
- KPI profile JSON sources moved to top-level `kpi_profiles/` and removed from vector store manifests.
- Data pipeline scripts now accept `--athlete` with `.env` fallback for multi-athlete runs.
- Data pipeline docs now include multi-athlete CLI examples.
- User input interface specs/templates for season briefs and events moved to shared knowledge sources.
- Workspace docs now mention `inputs/` and the user-input templates.
- Agent prompts now require user inputs to be loaded via `workspace_get_input` (not file_search).
- Agent prompts now include access hints for tool-based artifact loading.
- Agent prompts now include mode-specific access hints with optional-input guidance.
- Agent prompts now include file_search filter guidance for knowledge sources.
- Workspace read tools now expose `workspace_get_block_context` for block-scoped access.
- How-to-plan docs now include concrete macro/meso/micro/workout-builder/performance-analysis CLI commands.
- Planning docs now reference `workspace_get_block_context` and avoid embedding tool-usage hints in CLI examples.
- JSON schemas normalized for strict tool compatibility (explicit types/required, flattened `allOf`, removed unsupported constraints).
- Version key derivation now supports string-based `iso_week` and `iso_week_range` metadata.
- Docs and README now document the two-step Macro Mode A workflow.
- Model guidance notes include Macro Mode A scenario token-throughput tip.
- Agent runners now pass optional temperature settings; `.env.example` and model docs reflect temperature overrides.
- System architecture docs now describe vector store attributes, filtering, and agent access hints.
- Durability bibliography now carries a compliant YAML header.

### Removed
- Legacy schema copies under `knowledge/_shared/sources/schemas/` (replaced by bundled variants).
- Obsolete shared schemas `data_confidence` and `macro_cycle_enum` from knowledge sources.

## [0.1.0] - 2026-01-20

### Changed
- Complete rewrite targeting OpenAI Responses API.

### Added
- Local workspace docs and validation guide under `doc/`.
- Data pipeline validator script: `scripts/validate_outputs.py`.
- Artefact flow overview with updated Mermaid diagrams.
- Vector store operations and incident guidance in `doc/system_architecture.md`.

### Changed
- Data pipeline docs updated to reference `get_intervals_data.py`.
- System docs updated for workspace handling and validation flow.
