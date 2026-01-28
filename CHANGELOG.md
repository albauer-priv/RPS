# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.28] - 2026-01-28

### Changed
- Coach output now renders in a dedicated panel with stored response + reasoning summary and no streaming token spam.
- Coach execution runs synchronously to avoid Streamlit ScriptRunContext issues.
- Workspace lookup now falls back to input files for Season Brief and Events when no latest artefact exists.
- Streamlit UI tweaks: collapsible phase card, relocated coach output below input, and history/log layout adjustments.
- Removed legacy macro_mode_a script and updated planning docs to reflect the new macro flow.
- Coach output now streams into a chat bubble above the input, while the reasoning box shows summary only.
- System output/logs panel now expands by default.

## [0.6.26] - 2026-01-27

### Changed
- Streamlit show flow is state-machine backed, with an active coach window above the input and history collapsed below.
- Sidebar now shows the active state, uses ISO-week defaults, and updated action labels.
- Added robust Season Brief availability parsing (weekday header skip, hour formats, travel risk aliases, data_confidence).
- Availability and wellness artefacts now render via new Markdown templates and renderer support.
- Coach prompt now includes a strict G1 workspace load order (season brief/events + latest artefacts).
- Coach runs without workspace_get (prevents invalid input lookups).

## [0.6.25] - 2026-01-27

### Changed
- Streamlit UI now runs preflight automatically on startup, transitions to `core/plan` on success, and stops with a clear error on failure.
- Added a Coach agent (`prompts/agents/coach.md`) and wired coach mode into Streamlit with persistent Responses context via `previous_response_id`.
- Coach status is shown in the sidebar and a Coach action button is available.
- Knowledge injection now truly applies `base + bundle (+ mode)` with de-duplication.
- Added optional Responses `web_search` tool wiring, gated by `.env` (`OPENAI_ENABLE_WEB_SEARCH`, `OPENAI_WEB_SEARCH_AGENTS`).
- Coach prompt now enforces workspace-first loading order and references the DES analysis report.
- Coach knowledge injection now always includes durability bibliography, macro/block/workouts mandatory output specs.
- Coach now uses per-agent model/reasoning overrides via `.env` (OPENAI_MODEL_COACH / OPENAI_REASONING_EFFORT_COACH).
- Streamlit system log widget now defaults to collapsed.

## [0.6.24] - 2026-01-26

### Changed
- Added a minimal Streamlit UI at `src/rps/ui/streamlit_app.py` with a simple state machine and chat-style commands.
- Documented Streamlit usage in `doc/streamlit_ui.md` and referenced it from `doc/system_architecture.md`.
- Added `streamlit` to `pyproject.toml` dependencies.
- Documented the base+mode knowledge injection model in `doc/system_architecture.md`.
- Added a header comment to `config/agent_knowledge_injection.yaml` clarifying base vs mode bundles.
- Integrated the Intervals.icu pipeline into `rps` with `python -m rps.main parse-intervals`.
- Deprecated `scripts/data_pipeline/get_intervals_data.py` in favor of the new CLI entrypoint.
- Updated documentation/diagrams to reference `parse-intervals`.
- Preflight now runs the Intervals pipeline when zone model, wellness, or activities artefacts are missing (can be skipped via `--skip-intervals`).
- Preflight uses the default Intervals export range (latest completed weeks) rather than a week-anchored range to ensure current data.
- Artefact meta schema now allows optional `data_confidence` to validate activities outputs.
- `data_confidence` is now required in artefact meta; stores inject `"UNKNOWN"` when missing to satisfy strict schema tooling.
- Zone model outputs now include `meta.data_confidence` to satisfy strict validation.
- Normalized data_confidence values to uppercase (`HIGH|MEDIUM|LOW|UNKNOWN`).
- Wellness outputs now include `meta.data_confidence` to satisfy strict validation.
- Preflight skips Intervals fetches if activities_trend is younger than 2 hours, unless `--force-intervals` is set.
- Agent knowledge injection now supports per-mode blocks; plan-week selects mode by task (e.g., block_governance vs block_execution_arch).
- Meso-Architect knowledge injection now uses per-mode bundle IDs, similar to micro_planner.
- Macro-Planner and Season-Scenario now use per-mode bundles, and the injection config is de-aliased for readability.

## [0.6.3] - 2026-01-26

### Changed
- Renamed the Python package from `app` to `rps` and updated CLI/docs to use `python -m rps.main`.
- Added response-text logging when agents return no tool call, plus a no-tool-call summary for debugging.
- Inserted a blank line before streamed reasoning headings (`**`/`#`) for readability.
- Macro Mode A now injects the shared knowledge bundle for macro/season scenario runs.
- Expanded the agent knowledge injection bundles (contracts, interfaces, mandatory output guides, evidence).
- Added `data_confidence` schema and required it in activities_actual/trend outputs; pipeline now emits `meta.data_confidence`.

## [0.6.11] - 2026-01-26

### Changed
- LoadEstimationSpec now normalizes `planned_Load_kJ` to ENDURANCE_LOW (IF_ref_load = 0.65) and updates feasibility + KPI mapping accordingly.
- Macro plausibility check now uses mechanical `planned_kJ_week`, and Meso STOPs defer to the S5 ladder; patch block removed.
- All agent prompts now explicitly label Fueling/Energy as `planned_kJ` and Governance as `planned_Load_kJ` in logs/notes.
- Store tool schemas no longer require `data_confidence` in the global meta; activities schemas still require it.
- Block governance hard-stop now defers to LoadEstimationSpec S5 ladder before stopping on empty intersections.
- Season Brief availability parsing moved into `rps` module with `rps.main parse-availability`; old script removed and docs updated.
- DES analysis report schema now allows `inconclusive` status; prompts/specs updated accordingly.
- Preflight now validates Season Brief, Events, and KPI Profile with clearer error messages before runs.

## [0.6.10] - 2026-01-26

### Changed
- LoadEstimationSpec now normalizes `planned_Load_kJ` to ENDURANCE_LOW (IF_ref_load = 0.65) and updates feasibility + KPI mapping accordingly.

## [0.6.4] - 2026-01-26

### Changed
- Data pipeline now sets `meta.data_confidence` to MEDIUM by default and HIGH when core columns are complete for activities_actual/trend.

## [0.6.2] - 2026-01-26

### Changed
- Added agent knowledge injection config and injected mandatory specs/policies/schemas for meso/micro/builder/analysis runs.
- Season scenario pass‑2 now enforces cadence→phase length mapping + planning math consistency.
- Macro planner pass‑1 now requires scenario‑based phase count math and fail‑fasts on mismatches.
- Mandatory output specs no longer mention file_search retrieval (runtime injects them).
- Added load-order rule across agent prompts: read user input + workspace artefacts before knowledge files.
- Meso plan-week now injects LoadEstimationSpec (General + Meso sections) into the user prompt.
- LoadEstimationSpec updated (values adjusted).

## [0.6.0] - 2026-01-26

### Changed
- plan-week now treats downstream artefacts as stale when upstream macro/meso/workouts updates are newer, and re-runs as needed (cascade rebuilds).
- Vector store sync now retries transient API errors with backoff instead of failing immediately.
- Streaming output supports optional italic rendering of reasoning via `OPENAI_STREAM_ITALICS`.
- Consolidated all agent knowledge into a single vector store (`vs_rps_all_agents`) with a unified `knowledge/all_agents/manifest.yaml`.
- Consolidated macro/meso load policies into `load_estimation_spec.md` (General/Macro/Meso sections) and removed the standalone policy docs.
- LoadEstimationSpec tightened: deterministic Macro utilization/body-mass fallback, KPI band selector, domain aliasing, and clarified Macro/Meso responsibilities.
- Added ENDURANCE_LOW/ENDURANCE_HIGH intensity domains (with legacy aliasing), renamed `SST` → `SWEET_SPOT`, and reintroduced THRESHOLD in intensity-domain enums across schemas, specs, prompts, and workout policy.
- Split KPI workout-to-signal mapping into `kpi_signal_effects_policy.md` (informational) and referenced it from WorkoutPolicy.
- Principles 3.3 now explicitly scope cadence selection to Scenario/Macro (Meso must not apply a default cadence).
- Scenario/Macro prompts now reiterate cadence ownership (Meso must not apply defaults).
- Meso-Architect prompt now forbids manual temporal scope derivation, sets `meta.iso_week` to the first week of the provided range, and requires exact-range BLOCK_EXECUTION_ARCH for previews (no latest fallback).
- Meso-Architect prompt now hard-stops if any month text conflicts with `meta.temporal_scope` or ISO-week range (no month inference from ISO weeks).
- Micro-Planner prompt now restricts file_search to knowledge documents, requires exact-range governance lookup (no latest fallback), and blocks month inference from ISO-week labels.
- Macro-Planner prompt now hard-stops on calendar-month inference from ISO-week labels and month/temporal_scope conflicts.
- Meso-Architect prompt now explicitly warns that ISO-week labels are not calendar months.
- Macro/Micro prompt headers now include an explicit ISO-week ≠ month reminder.
- Macro/Meso/Micro prompts now require reading `load_estimation_spec.md` before any kJ/load derivation.
- Macro/Meso/Micro prompts now explicitly require reading `load_estimation_spec.md` before load derivations (knowledge retrieval allowed if needed).
- Meso/Micro prompts now include a binding Spec/Contract Load Map (Name / Content / How to load).
- Macro prompt now includes binding load maps with tool methods for runtime artefacts.
- Meso-Architect now hard-stops if weekly_kj_bands are not narrowed to the LoadEstimationSpec (Meso) intersection.
- LoadDistributionPolicy upper‑third target is now explicitly advisory-only and only when requested.
- Meso/Micro prompts now include informational policy load maps (KPI signal effects, workout policy).
- Load distribution policy now explicitly disallows Macro/Meso usage.
- All agent prompts now include consolidated knowledge retrieval guidance (metadata filters + file_search scope).
- Added per-agent knowledge retrieval tables (required files + filters; tool instructions and fallback behavior).
- Workout-Builder retrieval table now lists all required specs/policies/schemas (including file naming + traceability).
- Knowledge retrieval tables now include informational evidence sources (evidence layer + bibliography) where applicable.
- Consolidated file_search instructions into a single Knowledge Retrieval section per agent and removed vector‑store wording.
- Season-Scenario prompt now ends planning horizon at the last A/B/C event in the Season Brief (no post‑event extension unless explicitly requested); events.md is logistics‑only.
- Macro-Planner prompt now treats A/B/C events as Season Brief‑only and uses events.md for logistics constraints only; Meso prompt notes the same.
- Macro-Planner prompt now allows non-URL publication links (internal references) for scientific foundation entries.
- Macro-Planner prompt now forbids empty citation strings in `data.justification` and requires at least one non-empty citation per phase.
- Macro-Planner prompt now treats scenario `phase_plan_summary` as binding for total weeks/phases and requires macro `iso_week_range` to match it when provided.
- Macro-Planner prompt now instructs loading `load_estimation_spec.md` as the first action before any other derivations.
- macro_mode_a overview now injects the LoadEstimationSpec (Macro section) into the agent prompt to ensure immediate availability.
- macro_mode_a now injects LoadEstimationSpec from file start through the "## Meso" header (General + Macro sections).
- Added `mandatory_output_macro_overview.md` and load it for Macro-Planner output guidance; macro_mode_a injects it into the overview prompt.
- macro_mode_a overview prompt now delegates all output/tool guidance to the mandatory output/spec blocks, keeping the inline prompt minimal.
- Added `mandatory_output_season_scenarios.md` and load it for Season-Scenario output guidance; macro_mode_a injects it into the scenarios prompt.
- Macro-Planner agent calls now inject LoadEstimationSpec (General+Macro section) automatically in the runner to avoid missing-file issues.
- Season-Scenario agent calls now inject the mandatory SEASON_SCENARIOS output guide automatically in the runner.
- Simplified macro_planner and season_scenario prompts to defer all field/validation guidance to mandatory output chapters.
- Season-Scenario prompt trimmed to scenario-only guidance; removed load-corridor/kJ rules and clarified KPI Profile is loaded from workspace (no selection logic).
- Added runtime artifact load maps (workspace tools) for all agents.
- Season-Scenario prompt and macro_mode_a scenario run now explicitly require store tool calls with top-level `{meta, data}` envelopes (no JSON in chat).
- Macro-Planner prompt and macro_mode_a overview run now enforce store tool calls with top-level `{meta, data}` envelopes (no JSON in chat).
- Macro overview phase corridors now explicitly require `weekly_load_corridor.weekly_kj` (min/max/kj_per_kg/notes) in prompts and Mode A overview guidance.
- Auto-render now handles KeyboardInterrupts gracefully (store succeeds even if sidecar rendering is interrupted).
- Store tool failures now return clearer schema error summaries (with top validation errors) and envelope hints.
- Runner strict path and workspace tools now emit the same concise schema error summaries and envelope hints.
- Agents now hard-stop with `STOP_TOOL_CALL_REQUIRED` if a required store tool isn’t called (after one forced retry).
- Added mandatory output guides for all agent-produced artefacts (block governance/arch/preview/feed-forward, workouts plan, intervals export, DES report, macro feed-forward).
- Prompt cleanup: removed format-only output rules, normalized example filenames to patterns, and corrected contract filenames (`micro__builder`, `macro__meso`, `meso__micro`, `analyst__macro`).
- Prompt redundancy cleanup: consolidated repeated required-input/stop text across agents and removed duplicate validation checklists.
- File search now attaches only **one vector store per agent** (shared store removed); runtime, docs, and smoke test updated accordingly.
- Shared vector store manifest removed; shared knowledge is now referenced via `../_shared/...` paths inside each agent manifest.

## [0.4.2] - 2026-01-25

### Added
- Streaming helper for Responses API with live reasoning/output/usage via `OPENAI_STREAM*`.
- Reasoning log toggle (`OPENAI_STREAM_LOG_REASONING`) for log capture on completion.
- Load distribution policy doc (`load_distribution_policy.md`) and manifest entry (advisory day-weighting).

### Changed
- Macro/Meso/Micro/Performance-Analyst prompts now require `events.md` (no optional/if-present paths).
- Season-Scenario prompt now requires `events.md` (no optional/if-present path).
- Macro-Planner prompt now requires `events.md` to be reflected in `meta.trace_events` and phase event constraints.
- Macro Mode A overview now explicitly requires loading `events.md` and reflecting it in trace/events constraints.
- Season scenarios now include advisory planning math (`phase_count_expected`, `max_shortened_phases`, `shortening_budget_weeks`) and Macro-Planner cross-checks these against computed phase counts.
- Season scenarios no longer output detailed `phase_recommendations`; they now emit compact `phase_plan_summary` instead.
- Season-Scenario validation now requires `planning_horizon_weeks` to match `meta.iso_week_range`.
- Macro-Planner validation now requires the A-event to be placed in a Peak phase and preserves event identity when mapping Season Brief events.
- plan-week orchestration now validates macro coverage by iso_week_range, logs matching phases, and checks block artefacts by range before running meso/micro steps.
- plan-week now invokes Meso-Architect once per artefact (one task per run) to respect single-output contracts.
- Script logging now mirrors start/finish messages to stdout via `log_and_print`.
- plan-week now prints "Done." after successful artefact creation and skips the builder if the versioned workouts plan is missing.
- Meso-Architect guidance and validations now require weekly_kj_bands and week_roles to match the block iso_week_range length (no fixed 4-week assumption).
- Meso-Architect prompt now explicitly derives block length from the provided iso_week_range or macro phase range.
- Meso-Architect prompt now enforces verbatim macro constraint propagation and required self_check/preview fields.
- Meso-Architect now hard-stops if execution-arch self_check fields are missing or load_ranges.source is not the exact block_governance filename.
- Meso-Architect now sources A/B/C event windows from macro_overview phase constraints (events.md remains logistics only).
- Micro-Planner now must store WORKOUTS_PLAN via the store tool call (no raw JSON outputs).
- Micro-Planner now validates AVAILABILITY/WELLNESS/ZONE_MODEL coverage using temporal_scope before declaring missing inputs.
- Wellness artefact now extends temporal_scope (and iso_week_range) to calendar year end so body_mass_kg remains valid for forward planning.
- LoadEstimationSpec updated to treat `weekly_kj_bands` as `planned_Load_kJ_week`, refine IF derivation, rounding order, fallback IF mapping, clamps, units, and parse edge cases.
- Macro load corridor policy updated to use planned_Load_kJ conversions.
- Agent prompts updated to prefer strict store tool calls and avoid JSON-in-chat output rules that conflict with tooling.
- Artefact renderer now skips JSON list artefacts (e.g., intervals_workouts) with a clear log message instead of crashing.
- Agent runners now support streaming Responses output with optional reasoning summary and token usage reporting (configurable via `OPENAI_STREAM*` env vars).
- Reasoning payloads now treat `gpt-5*` models as reasoning-capable.
- plan-week now runs Performance-Analyst for the previous ISO week (week-1), and skips analysis if that report week is outside the macro planning range.
- Micro-Planner now explicitly limits WORKOUTS_PLAN output to the requested ISO week even when the block range spans multiple weeks.
- Micro-Planner no longer biases weekly kJ placement to the upper-third of the governance corridor.
- LoadEstimationSpec now defines planned_kJ (mechanical) vs planned_Load_kJ (stress‑weighted) and treats weekly_kj_bands as planned_Load_kJ.
- Added optional LoadDistributionPolicy for day‑weighting and weekly load distribution (advisory only).
- Macro load corridor policy now expresses corridors as planned_Load_kJ using a phase‑level default IF conversion.
- LoadEstimationSpec now adds rounding order, midpoint handling for range targets, safety clamps, explicit fallback mode (IF‑direct), and α source‑of‑truth rules.
- Index exact-range checks now verify artifact files exist (prevents stale index hits).
- Index manager now normalizes legacy analysis paths to data/analysis when the new file exists.
- Block governance schema now allows variable-length `weekly_kj_bands` (no fixed 4-week constraint).
- Block execution arch/preview and block feed-forward schemas now allow variable-length arrays (no fixed 4-week constraint).
- Block execution architecture now supports variable-length blocks via `week_roles[]` and removes 4-week-only schema fields.
- File naming, contracts, and specs now reference generic block ranges (no `+3`).
- Macro/Meso cadence guidance and constrained-time-window rules formalized in Principles 3.3 and referenced by prompts.
- Saved artifacts now apply schema-aware rounding (integers stay integers; kg/hours/IF/etc. rounded consistently).

### Fixed
- Macro overview renderer no longer references deprecated mass/preload fields.
- Season scenarios tool schema now includes required planning math fields and runner fills defaults to satisfy strict validation.

### Removed
- Legacy data pipeline scripts removed (`intervals_export.py`, `compile_activities_actual.py`, `compile_activities_trend.py`).

## [0.4.1] - 2026-01-24

### Added
- Durability principles now include the permitted "Kinzlbauer macro template" archetype (macro-level sequencing and traceability anchors).
- Macro load corridor policy spec for deriving weekly kJ bands from availability, wellness, KPI guidance, and activity trends.
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
- Added binding `progressive_overload_policy.md` (kJ-based cadence/deload/re-entry) for Macro/Meso/Micro.
- Clarified cadence/deload ownership across principles/policies/mandatory outputs to defer numeric rules to ProgressiveOverloadPolicy.
- Updated KPI profiles to align progression limits with ProgressiveOverloadPolicy (weekly <=10%, warning 10–12%, stop >15%; long-ride <=12%, warning 12–15%, stop >15%).

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
- Meso-Architect prompt now requires weekly kJ progression patterns (default 3:1) unless macro specifies steady-state.

- Planning artefacts are now kJ-first only: removed TSS fields from macro overview, block governance/execution, workouts plans, and zone model examples.
- Renderer templates now omit TSS columns/sections for non-activities artefacts.
- Activities trend adherence now computes against planned weekly kJ from workouts plans; TSS remains only in activities_* artefacts.
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
- Macro/Meso/Micro prompts now require `events.md` from inputs and STOP if it is missing.

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
