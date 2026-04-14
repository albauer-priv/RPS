# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Multi-output agent runs now treat explicit model blocker responses (`STOP_REASON`, missing binding artefacts, next actions) as terminal failures, so the runner no longer forces a fallback store after a compliant stop and reports the blocker back instead.
- Internal type cleanup now covers `src/rps/workspace/api.py`, `src/rps/workspace/local_store.py`, `src/rps/workspace/index_manager.py`, `src/rps/workspace/index_exact.py`, and `src/rps/workspace/index_query.py`, tightening workspace payload/index metadata access across the storage and lookup layer.
- Internal type cleanup now covers `src/rps/openai/reasoning.py`, `src/rps/openai/runtime.py`, and `src/rps/openai/vectorstore_state.py`, tightening small Responses/vectorstore helper payloads and state access without changing runtime behavior.
- Stabilized `scripts/run_typecheck.sh` by switching the curated mypy commit gate from fragile per-file runs to grouped module/directory runs, avoiding the local `mypy` segfault seen on `src/rps/agents/runner.py` in single-file mode while preserving the same checked scope.
- Local commits now run a repo-managed pre-commit gate with `py_compile` plus a curated `mypy` scope, and the shared planning modules now have a committed typecheck entrypoint via `scripts/run_typecheck.sh`.
- Internal type cleanup now covers `src/rps/agents/runner.py` and `src/rps/agents/runner_strict.py`, replacing loose LiteLLM response/client handling with typed runtime/result helpers across both standard and strict agent execution paths.
- Internal type cleanup now covers `src/rps/orchestrator/plan_hub_actions.py` and `src/rps/orchestrator/plan_hub_worker.py`, replacing loose planning action/step/run bookkeeping with typed records and explicit narrowing helpers.
- Internal type cleanup now covers `src/rps/tools/store_output_tools.py` and `src/rps/workspace/guarded_store.py`, replacing loose schema/store payload handling with explicit JSON-map/list narrowing along the strict validated-write path.
- Internal type cleanup now covers `src/rps/orchestrator/plan_week.py`, `src/rps/orchestrator/season_flow.py`, and `src/rps/orchestrator/week_revision.py`, tightening orchestrator result/step typing and KPI/profile JSON narrowing across season/week planning flows.
- Internal type cleanup now covers the Plan/Coach UI layer, with `src/rps/ui/pages/plan/hub.py` moved off `Any`-based run/index payload handling while `plan/season.py`, `coach.py`, and `shared.py` remain green under the stricter UI mypy pass.
- Internal type cleanup now ignores third-party stub noise in repo-level `mypy` config and extends the green commit-gate scope to core logging/runtime, rendering, Intervals refresh, Season page output handling, and the athlete-profile editor pages.
- Internal type cleanup now covers `src/rps/ui/pages/plan/hub.py`, with explicit typed execution-step structures, safer run-record coercion, and the file added to the mandatory curated `mypy` gate.
- Internal type cleanup now covers `src/rps/ui/rps_chatbot.py`, tightening chat state and block typing, narrowing Streamlit chat-input/upload handling, and adding the Coach chat runtime to the mandatory curated `mypy` gate.
- Internal type cleanup now covers `src/rps/ui/pages/coach.py` and `src/rps/ui/shared.py`, replacing loosely typed Coach chat kwargs with explicit construction, tightening sidebar/log helper state types, and extending the mandatory curated `mypy` gate to the remaining core Coach UI modules.
- Internal type cleanup now covers `src/rps/data_pipeline/intervals_data.py`, tightening numeric narrowing, zone-model defaults, activity-id validation, and index-write metadata casts, and adds the Intervals pipeline entrypoint to the mandatory curated `mypy` gate.
- Plan Hub direct phase actions now honor isolated scoped intent: `Phase Guardrails` reruns no longer cascade into Structure/Preview/Week planning, and isolated forced phase runs in `plan_week(...)` now stop successfully once the requested exact-range phase artefact exists.
- `plan_week(...)` no longer injects direct selected KPI guidance into `phase_architect` runs, so `PHASE_GUARDRAILS` creation is no longer blocked by scenario-selection KPI gating when no matching `SEASON_PHASE_FEED_FORWARD` exists for the target phase range.
- Local embedded Qdrant access now reuses a cached client per storage path, avoiding self-inflicted `.cache/qdrant` lock errors during planning knowledge lookups.
- Local `knowledge_search` now auto-rebuilds the missing `vs_rps_all_agents` Qdrant collection from the canonical manifest and retries once, so planning does not hard-stop on a recoverable vectorstore sync issue.
- Agent knowledge injection is now driven consistently from `config/agent_knowledge_injection.yaml` across orchestration and multi-output runs; `phase_architect` now receives its missing `file_naming_spec.md` and `zone_model.schema.json`, and `season_planner` now injects the Season-only `load_estimation_spec.md` section from config instead of a code-only special case.
- Plan Hub phase cards now use a phase selector, and week/workout cards now use phase plus week selectors defaulted from the current-week phase context; Plan Hub planning actions are no longer restricted to current/next week only.
- Plan Hub readiness cards for `Phase Guardrails`, `Phase Structure`, `Phase Preview`, `Week Plan`, and `Build Workouts` now expose direct current/next phase or week actions that queue regular scoped planning runs through the worker.
- Phase-Guardrails recovery protection propagation now has a canonical array-to-string mapping, so season recovery notes no longer deadlock Phase Guardrails creation when the season plan provides multiple notes.
- LiteLLM Responses handling now replays prior response output items when `previous_response_id` is used, so Coach follow-up tool outputs can be matched back to their original tool calls.
- Athlete Profile -> KPI Profile now initializes the dropdown from the saved latest KPI profile and shows the active profile explicitly on page load.
- Plan Hub scoped reruns now force `plan_week` and workout export regeneration for explicitly selected `Week Plan` and `Build Workouts` steps, so existing weeks can be re-planned with an override instead of short-circuiting on existing artifacts.
- Clarified and test-covered scoped rerun behavior across planning scopes: `Season Scenarios` and `Season Plan` already rerun directly, `Phase` reruns are forced through `plan_week`, and `Selected Scenario` remains a manual Season-page action.
- Added English translations alongside German titles in the durability bibliography and principles references, and clarified the week anchor wording in planning principles.
- Updated package metadata name/description in `pyproject.toml` to match RPS.
- Updated Docker references to the real GHCR package (`ghcr.io/albauer-priv/rps:latest`) in compose and README usage examples.
- Enabled automatic GHCR publishing on pushes to `main` in `.github/workflows/ghcr-image.yml` (manual dispatch remains available).
- Translated remaining German wording in README navigation/headings to English.

## [0.10.4] - 2026-02-11

### Changed
- Rewrote `README.md` as an athlete-first introduction with principles, a workflow quickstart, a detailed index, and Docker-focused deployment notes.

### Changed
- Consolidated repo layout into `runtime/` (workspace/runs/logs) and `specs/` (knowledge, schemas, KPI profiles), removing the unused `evals/` folder and updating scripts/docs to the new roots.
- Backup now always creates a full archive; restore keeps a scope selector for partial re-import.
- Updated UI spec and artefact flow docs to reflect full backup + selective restore.
- Split detailed UI action specs and flow diagrams into `doc/ui/flows.md`, keeping `ui_spec` focused on page responsibilities.
- Trimmed `doc/overview/how_to_plan.md` to high-level guidance and linked readiness/run details to UI and architecture docs.
- Archived the superseded queue scheduler proposal under `doc/proposals/_archive/`.
- Standardized Mermaid node labels in docs by quoting non-identifier labels for GitHub rendering.
- Normalized in-doc links to repo-root paths (e.g., `/doc/...`) for GitHub previews.
- Moved UI implementation notes from `ui_spec` into the Streamlit contract and queued future items in the feature backlog.
- Updated `.env.example` model defaults to GPT‑5 mini/nano and adjusted temperatures to GPT‑5‑safe defaults.
- Removed the obsolete coach experiment entrypoint and deprecated model guidance doc.
- System → History status banner now renders under the page header for consistent layout.
- Plan Hub now surfaces an `Auto-creates phase artifacts` readiness hint and clarifies that Plan Week will create missing phase artifacts when needed.
- Plan Hub override gating is now consistent: overrides are required only when modifying existing artifacts.
- Doc references in `doc/` now use clickable Markdown links instead of plain-text paths.
- Simplified logging configuration to `RPS_LOG_LEVEL` + `RPS_LOG_CONSOLE` + `RPS_LOG_FILE` + `RPS_LOG_UI`, with unified LLM debug (`RPS_LLM_DEBUG`) and reasoning log control (`RPS_LLM_REASONING_LOG`).
- Removed the legacy CLI entrypoint (`src/rps/main.py`) and deprecated data pipeline wrapper scripts; documentation now reflects UI-only workflows and the `intervals_data.py` entrypoint.
- Removed legacy Season Brief support, legacy run-store JSONL fallback, and workspace legacy path normalization; schemas and docs now reference only Athlete Profile + Availability inputs.
- Events UI no longer auto-upgrades legacy payloads; legacy references removed from UI wording.
- Feed Forward now uses the selected ISO week (current or previous only), with a single chained action to create the DES report, Season→Phase feed forward, then Phase→Week feed forward.
- Feed Forward now shows a week selector, summary line, and uses a single action button label; readiness/trigger controls moved under the selector.
- Report page status panel now renders under the title and no longer shows a model reasoning expander.
- Plan → Week no longer shows the System output/logs expander.
- Analyse → Data & Metrics removes weekly load, durability/decoupling, and weekly decoupling charts.
- UI pages now follow a consistent layout order: Title → Athlete → Status hints → Actions/content.
- Workouts and System Status pages now render a single status panel (no duplicate status blocks).
- Events page now offers an upgrade action for legacy planning events payloads to restore all columns.
- Planning Events no longer include an `objective` field; legacy values are mapped into `goal` on load with schema bumped to 1.2.
- Events page now auto-upgrades legacy planning events on load instead of prompting.
- About You page now includes guidance headings and examples for goals, constraints, and assessment fields.
- Coach page now logs the effective model and base URL on initialization.
- Coach page log now includes whether an API key is set.
- Renamed LLM environment variables from `OPENAI_*` to `RPS_LLM_*` (no backward compatibility) and grouped per-agent overrides in `.env.example`.
- Replaced OpenAI file_search vectorstores with embedded Qdrant and a `knowledge_search` tool for local retrieval.
- Routed Responses-style agent/runtime calls through a LiteLLM adapter with per-agent config overrides.
- Local artifact writes now emit log entries in `rps.log` for easier debugging from Athlete Profile pages.

### Fixed
- Plan Week no longer crashes Intervals export due to `IsoWeek` formatting (week variable shadowing removed).
- LiteLLM message builder now batches tool calls and always emits matching tool responses to satisfy OpenAI tool-call sequencing.
- Tool output events now carry tool names through the runner to stabilize tool-call matching.
- `smoke_vectorstores` now syncs missing local collections using an existing Qdrant client and tolerates older Qdrant delete signatures.
- LiteLLM runtime no longer sends unsupported `project` parameter; it is passed via `extra_body` when set.
- Coach summary now defaults to the active coach model when no summary override is set.
- LiteLLM runtime now skips tool definitions missing a name to avoid Groq tool rendering errors.
- LiteLLM runtime now accepts tool definitions with nested `function.name` and logs any unnamed tools.
- LiteLLM runtime now drops invalid tool_choice entries when tool names are missing or mismatched.
- Coach tool outputs now include tool names so Groq can render tool messages.
- LiteLLM runtime now falls back to tool_call_id as tool name when a tool output is missing a name.
- Coach chat now logs response text lengths to help debug missing replies.
- Coach chat now logs tool call and output lengths for debugging empty responses.
- LiteLLM runtime now pairs tool calls and outputs to avoid invalid tool-message sequences for OpenAI.

## [0.10.3] - 2026-02-06

### Added
- Added a feature backlog doc to track upcoming specs.
- Added a Parquet cache feature spec and ADR for Intervals pipeline outputs.
- Plan Season now shows a date-range header derived from the Season Plan iso_week_range.
- Report page now shows Narrative/KPI Summary/Trend Analysis expanders above the rendered report content.
- Plan Phase/Week/Workouts headers now include the ISO-week date range.
- Workouts page now reuses Week Plan agenda durations and headers for current week listings.
- Added a manual "Refresh Intervals Data" action on the Data & Metrics page with AppTest coverage.
- Daily Durability scatter now includes a week-range slider to filter recent activity points.
- Athlete Profile → Availability now includes a "Parse Availability from Season Brief" action.
- Streamlit startup now runs a background vector store sync check and resets the store when the manifest hash changes.
- Added planning principles documentation and referenced it from the docs and AGENTS rules.
- Plan Hub now preselects Plan Next Week vs Plan Week based on readiness and enforces current/next ISO-week scope.
- Season scenario selection now captures KPI moving_time_rate_guidance selections and schema version bumped to 1.1.
- Season page now provides Create/Reset/Delete controls, renders scenario overview tables, and reuses the Phase page’s rendering per phase (no JSON dump), aligning it with the Phase card template.
- Home page marketing copy is now externalized (`static/marketing/home.md`) and rendered with a system state table that summarizes artifact availability, owners, and timestamps.
- Added Streamlit AppTest coverage for Home and Plan pages.
- WoW page now renders Intervals workouts from the export JSON as per-day expanders with code blocks.
- Plan Hub now persists per-run `run.json`/`steps.json` plus events, with async worker execution, run summaries, and blocked step propagation.
- Added Intervals posting receipts with idempotency (commit step) plus Week/Plan Hub UI to post workouts and inspect receipt status.
- Plan Hub run history now includes run store rows (muted superseded runs) with event table filtering.
- Added `intervals_posting.md` and refactored Intervals posting script into the data pipeline module.
- Posting commit now supports Intervals bulk upsert (updates) and bulk delete via external_id.
- Athlete Profile now includes a KPI Profile page with selection and workspace sync.
- Added Feed Forward page under Analyse with DES recommendations and feed-forward triggers.
- Streamlit startup now prunes missing artifact index entries in the background.
- Streamlit startup now removes orphaned rendered sidecars when source JSON is missing.
- Background processes (data pipeline refresh, housekeeping, report generation) now log to the run store with process type/subtype filters in System → Status.
- Added a background run tracker helper to standardize status updates for async jobs.
- Scheduling guards prevent overlapping runs of the same process type/subtype and block lower-priority planning runs when higher-priority ones are active.
- System → History now includes an Overview section (latest outputs + run history) and separate Artifact History headers for clarity.
- Added ADR-021 to enforce Plotly-only chart rendering in Streamlit UI.
- Added modular Athlete Profile inputs and pages: About You & Goals, Events, Logistics, and Historic Data.
- Added new input schemas for athlete_profile, planning_events, logistics, and historical_baseline.

### Changed
- Planning Events editor now splits A/B/C type from priority rank, adds time limit, and enforces 12-week spacing between A events.
- Athlete Profile input guidance now lives in UI pages; input templates were removed.
- Logistics editor now aligns to event list columns (date/id/type/status/impact/description) with enums.
- Logistics now auto-generates event IDs and saves status/impact in uppercase enums.
- Data & Metrics now prefers the Parquet cache for activities_trend and activities_actual with JSON fallback.
- Parquet cache writes now log when a retry succeeds, and metrics parsing fixes a missing date import.
- Parquet cache dtype cleanup now avoids deprecated pandas to_numeric behavior.
- Moved "Parse Availability from Season Brief" action to Data Operations page.
- Intervals pipeline now writes Parquet cache mirrors for activities_actual and activities_trend (best-effort).
- Added pyarrow dependency to support Parquet cache writes.
- Plan Phase/Week/Workouts headers now render above captions and status panels.
- System → Log now shows the live log file tail when UI session logs are sparse.
- Daily Durability scatter now aggregates all activities_actual files under data/<year>/<week> for fuller coverage.
- Activity-based chart scans now limit to the most recent 52 weeks for faster rendering.
- Plan → Week no longer exposes a Plan Week action; planning is initiated from Plan Hub.
- Weekly load chart now merges phase guardrail corridors across versions to keep min/max lines populated.
- Report page no longer renders the raw report JSON.
- Documentation refreshed to reflect current Plan Hub orchestration, report rendering, log/run handling, and corridor overlays.
- System → History latest outputs no longer show Open/Diff/Versions action buttons.
- System → History now normalizes Validity to strings to avoid Arrow serialization errors.
- Streamlit chart rendering is standardized to `st.plotly_chart` only (no native chart helpers).
- Data & Metrics charts now render via Plotly, with a graceful fallback message when Plotly is unavailable.
- Added Plotly to dependencies for chart rendering.
- Home page no longer shows the System output/logs expander.
- Data & Metrics now includes a planning corridor overview chart for Season/Phase/Week corridors.
- Planning corridor overview now overlays actual weekly kJ and planned weekly kJ for past/current weeks.
- Planning corridor overview now limits the x-axis to the Season Plan horizon (phase weeks only).
- Data & Metrics now includes a decoupling-only chart (weekly trend + per-activity decoupling).
- Weekly decoupling now reads from intensity_load_metrics to ensure the weekly line is visible.
- Planning corridor chart now renders Actual Weekly kJ as bars.
- Data & Metrics now includes weekly dose→outcome and daily durability scatter charts with interpretive captions.
- Weekly dose→outcome chart now auto-ranges the right axis to keep DI and decoupling readable.
- Weekly dose→outcome chart now uses separate right-side axes for DI and decoupling.
- Plan Hub Run Planning panel stays visible when only Week Plan is missing; scope inputs render in the left column again.
- Shared duration parsing/formatting helpers now back both Week and Workouts pages for consistent display.
- Historical baseline now reports kJ per activity (not per day), and Historic Data UI reflects the new metric.
- Documentation/specs now reference Athlete Profile, Planning Events, and Logistics as primary inputs (Season Brief legacy noted).
- Availability schema no longer requires Season Brief source text fields; legacy parser no longer emits them.
- Athlete Profile now enforces integer inputs for training age/endurance anchor and 1-decimal body mass.
- Centralized UI flow spec (`doc/ui/ui_spec.md`) now includes updated and unified diagrams, scoped override rules, plan-week scoped flow, and replace-latest semantics.
- Plan Hub and UI docs now reflect that posting to Intervals happens from the Workouts page, not the Hub.
- Plan Hub scoped runs now support optional overrides (required only when modifying existing artifacts) and pass overrides into orchestrators.
- Week page now focuses on plan-week only; posting and report actions are moved to their dedicated pages.
- LoadEstimationSpec now anchors KPI selection to Scenario Selection, pulls progression guardrails from ProgressiveOverloadPolicy, and requires user-provided data injection when Season Brief fields are present.
- LoadEstimationSpec is now injected in full for Season/Phase/Week agents (no section filters).
- Season Planner prompts now inject user-provided Season Brief fields (endurance anchor + ambition IF range) and a KPI profile placeholder block.
- Phase-Architect and Week-Planner prompts now inject Season Brief fields and selected KPI guidance when available.
- KPI Profile is now explicitly called out as a readiness prerequisite for planning/feed-forward flows, and scenario selection requires a KPI segment choice.
- Plan Hub run IDs now include a timestamp suffix to support multiple runs per day.
- Plan Hub run actions now render as bottom-aligned buttons for both orchestrated and scoped runs.
- Plan Hub now groups run actions into a dedicated box with a short explanation of each run mode.
- Plan Hub run actions now include the Plan Week CTA inside the actions box.
- Plan Week CTA now includes the target ISO week in its label.
- Marked `scripts/sync_vectorstores.py` as deprecated in favor of the UI background sync.
- Marked `scripts/data_pipeline/post_workout.py` as deprecated in favor of UI/intervals_post helper.
- Athlete Profile → Data Operations now supports backup/restore with partial restore modes.
- Data Operations now supports backup validation (dry-run) and a cached “Download Last Backup”.
- Data Operations now lists files that would be restored before confirming.
- Data Operations now shows a per-folder restore summary for quick review.
- Documentation restructured into overview/architecture/ui/specs/runbooks/proposals with required headers.
- Data ops runbook updated to reflect implemented UI and planned CLI tooling.
- Added UI page deep-dive docs and linked them from the UI spec and doc index.
- Added canonical agent registry doc and linked it from architecture/overview docs.
- Added Coach to the agent registry.
- Replaced deprecated `use_container_width` with `width="stretch"` for dataframes.
- Plan Hub reset/delete confirmation now validates on submit instead of disabling the Proceed button.
- Plan Hub delete/reset now prunes the workspace index so readiness updates immediately.
- Plan Hub readiness now treats missing latest files as missing even if a versioned record exists.
- Optional readiness steps now show as missing when no artifact is present.
- Week-scoped version keys now append a `__YYYYMMDD_HHMMSS` timestamp and week-based reads resolve to the newest timestamped version.
- Season and Phase artifacts now also append `__YYYYMMDD_HHMMSS`, and range/week reads resolve to the newest timestamped version per scope.
- Plan Hub hides Scope/Run Planning when required readiness has missing or blocked steps, and only enables Create Scenarios in that state.
- Plan Hub removes the placeholder "View dependency" buttons from readiness cards.
- Plan Hub now lists blocking dependencies when run planning is unavailable.
- Plan Hub now includes the blocking list inside the blue readiness hint.
- Plan Hub labels the workout export step as "Build Workouts."
- Plan Hub "Create Scenarios" now enqueues a scoped season-scenarios run.
- Plan Hub readiness cards now link to the Season page only for scenario selection and season plan; other actions run via Plan Week/Workouts.
- Plan Hub restores the Create Scenarios action to enqueue the season scenarios run.
- Plan Hub replaces `st.autorefresh` with a safe rerun timer for active runs.
- System Status now starts the queue worker when pending runs are detected.
- Queue scheduler now ignores the queued run’s own QUEUED status so pending items can be claimed.
- System Status now loads `.env` before starting the worker so RPS_LLM_API_KEY is available.
- Plan hub worker now logs to the run log_ref and records exceptions in events.jsonl.
- Plan Hub now exposes a cancel button for active runs even when planning is blocked.
- System Status now lets you select running/queued runs and cancel them from the table.
- Plan Hub removes per-run control buttons; run control lives in System → Status only.
- System Status now marks runs as FAILED when their queue item lands in the failed folder.
- Plan Hub now actively reruns every ~2s while a run is active.
- Season page now reports scenario selection write failures explicitly.
- Added Mandatory Output chapter for SEASON_SCENARIO_SELECTION (schema_version 1.1) and inject it into prompts.
- Season Scenario Selection now writes locally from UI inputs (no LLM).
- Season page no longer creates Season Plans; it directs to Plan Hub for planning.
- System Status now loads runs before checking failed queue entries (fixes NameError).
- System Status now includes a reset control that clears queues, locks, runs, and logs for the athlete.
- Season Planner prompt now requires Zone Model (FTP from data.model_metadata.ftp_watts).
- Season Planner load order now includes Zone Model in the Step 1 artefact list.
- Phase Guardrails now explicitly requires all planned_event_windows from Season Plan in events_constraints.
- Plan Hub "Create Season Plan" now enqueues a scoped season-plan run instead of linking to Season page.
- Guarded store now preserves derived version keys for envelope artifacts instead of forcing raw.
- Season page no longer shows a Create Scenarios button; scenarios are initiated from Plan Hub.
- Range-scoped artifacts now prefer iso_week_range for version keys, ensuring timestamped range versions.
- Workout-Builder invocation now uses ISO week labels without the "W" prefix to match week_plan version keys.
- Plan Hub no longer blocks Run Planning when Build Workouts is missing; workouts export is optional for readiness.
- Plan Hub now labels Build Workouts as optional in readiness.
- Phase Architect prompt now specifies exact-range dependencies for Phase Structure/Preview and removes obsolete EXECUTION_ARCH reference.
- Phase Architect prompt now includes a per-output load checklist for required exact-range artefacts.
- Phase Architect few-shot examples now cover each output type and reinforce baseline inputs + Mandatory Output Chapter conformance.
- Plan Hub run execution now refreshes the artifact index after step execution and fills missing step durations.
- Plan Hub run execution table now shows an Outputs Written count per step.
- Logging now writes to a single per-athlete rps.log with daily/size rotation (rps-YYYYMMDD-NNN.log); added ADR-019.
- Added background log cleanup with `RPS_LOG_RETENTION_DAYS` (default 7).
- Added run housekeeping: prune run history older than `RPS_RUN_RETENTION_DAYS` (default 7) and clear done/failed queues (ADR-020).
- README now documents log rotation and retention env vars.
- Phase Preview mandatory output now requires derived_from to include the base phase_structure_<iso_week_range>.json filename (timestamps handled internally).
- Mandatory output guidance now requires Phase Guardrails/Structure/Preview to reference stored artifact filenames (no guessed names) and to fully propagate planned event windows from Season Plan.
- Mandatory output chapters now explicitly require tool-call arguments to be valid JSON only.
- TPM rate limit errors now wait twice the suggested retry time and automatically retry once per request.
- TPM retry behavior is now configurable via RPS_TPM_WAIT_MULTIPLIER and RPS_TPM_RETRY_COUNT.
- Coach chat refactor now uses the in-repo chat class (no streamlit-openai), with compaction + token budgeting and UI summary positioning; verified stable for 8–10 dialog turns without errors.
- Phase page preview layout refactored: preview table in its own expander and weekly previews rendered below.
- All non-Coach pages now share a centralized global sidebar and a single status banner; plan actions run through `st.form` in collapsed action panels.
- Week/ WoW pages now present workouts in expandable day-focused views with agenda summaries and extracted week totals.
- Intervals export files are now versioned as `workouts_yyyy-ww.json` and stored under `data/exports/` with ISO-week keys.
- Plan Hub now supports manual scenario selection handoff (Season page) with restart + superseded run tracking.
- Plan Hub season plan reset/delete actions now live in a collapsed expander, and the run summary banner no longer includes the "Was wird alles erstellt:" prefix.
- Performance report readiness moved to Performance pages (Feed Forward + Report) and removed from Plan Hub planning readiness.
- Plan Hub reset/delete actions now remove latest artefacts (reset keeps scenarios/selection; delete removes them too).
- Plan Hub worker loop now lives in the orchestrator (UI delegates), and System → Status shows planning worker status.
- Added file-based queue + scheduler for planning runs; UI enqueues runs and System → Status shows queue counts.
- Queue scheduler is now managed via `st.cache_resource` to keep it alive per process.
- Added ADRs 014–018 (Plan Hub vs subpages, readiness visualization, staleness policy, posting policy, schema versioning).
- Plan Hub cancel now uses `cancel_requested`; workers stop safely and mark runs as CANCELLED.
- Consolidated `doc/planners.md` into `doc/overview/how_to_plan.md` and updated planning/system docs to reflect Plan Hub and commit steps.
- Renamed Plan WoW page to Workouts and added posting, delete, coach revision, and history views.
- Integrated artefact renderer into `rps.rendering.renderer`, removed the standalone script, and moved templates under `src/rps/rendering/templates/`.
- Auto-render now calls the integrated renderer directly (no subprocess).
- Hard cut-over to modular inputs (athlete_profile, planning_events, logistics, availability); Season Brief/events.md are deprecated.
- Agent knowledge manifest and mandatory-output specs updated to reference modular inputs and legacy season_brief_ref behavior.
- Intervals pipeline now compiles Historical Baseline from full-year fetches and stores yearly summaries; Historic Data reads the artifact and refreshes via the pipeline.

## [0.10.1] - 2026-01-29

### Changed
- Reordered multipage navigation and grouped Performance/Plan/Athlete Profile subpages.
- Added new Season/Phase/Week/WoW and Performance subpages with rendered markdown support where available.
- Switched Coach page to the streamlit-openai chat pattern with prompt injection + workspace tools.

## [0.10.0] - 2026-01-29

### Changed
- Rebuilt Streamlit UI as a multi-page app with isolated page scripts and ordered navigation.
- Added shared UI helpers for session state + logging; Home now reuses the phase overview widget and system log panel.
- Coach page now uses the agent runner with prompt injection and session history (no external chat widget).
- Analysis page renders weekly kJ + durability charts and parsed activities trend/actual tables.
- Athlete Profile pages load newest Season Brief / Events from inputs and reuse availability editor.


## [0.9.0] - 2026-01-28

### Changed
- Streamlit season flow now auto-enters scenario selection when scenarios exist; scenario selection UI is state‑driven and the command input hides during selection.
- Season plan lifecycle controls added: recreate/drop commands with PROCEED confirmation and targeted artifact purge.
- Plan‑week gating now enforces “season plan exists + ISO week covered” before enabling.
- Phase card now renders via Jinja template (narrative, structured overview table, load corridor, semantics) with a cleaner header.
- Documented per‑channel log levels and `APP_LOG_STDOUT` in `.env.example`.

## [0.8.0] - 2026-01-28

### Changed
- Completed remaining Season/Phase/Week renames (env vars, contracts, router naming, and feed‑forward conclusion labels).
- Updated LoadEstimationSpec override terminology to season‑level naming.
- Normalized phase knowledge bundle IDs and references in injection config.

## [0.7.0] - 2026-01-28

### Changed
- Hard-renamed core artefacts to athlete-facing names: Season Plan, Phase Guardrails, Phase Structure, Phase Preview, and Week Plan.
- Updated schema files, templates, contracts, prompts, UI labels/synonyms, knowledge injection, and docs to the new artefact names.
- Renamed workspace services/helpers to align with season plan terminology.

## [0.6.29] - 2026-01-28

### Changed
- Phase artefacts now normalize `iso_week_range` to the covering Season phase and emit a warning when inputs disagree.
- Streamlit UI system log captures phase-range normalization warnings from the guarded store.

## [0.6.28] - 2026-01-28

### Changed
- Coach output now renders in a dedicated panel with stored response + reasoning summary and no streaming token spam.
- Coach execution runs synchronously to avoid Streamlit ScriptRunContext issues.
- Workspace lookup now falls back to input files for Season Brief and Events when no latest artefact exists.
- Streamlit UI tweaks: collapsible phase card, relocated coach output below input, and history/log layout adjustments.
- Removed legacy Season Mode A helper script and updated planning docs to reflect the new season flow.
- Coach output now streams into a chat bubble above the input, while the reasoning box shows summary only.
- System output/logs panel now expands by default.
- Streamlit UI no longer logs coach state transitions; coach reasoning clears on exit.
- Added per-target log levels (file/console/UI) and UI now shows log file path as the first entry.
- `.env` now documents all variables with inline comments.

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
- Added optional Responses `web_search` tool wiring, gated by `.env` (`RPS_LLM_ENABLE_WEB_SEARCH`, `RPS_LLM_WEB_SEARCH_AGENTS`).
- Coach prompt now enforces workspace-first loading order and references the DES analysis report.
- Coach knowledge injection now always includes durability bibliography, season plan/phase/week plan mandatory output specs.
- Coach now uses per-agent model/reasoning overrides via `.env` (RPS_LLM_MODEL_COACH / RPS_LLM_REASONING_EFFORT_COACH).
- Streamlit system log widget now defaults to collapsed.

## [0.6.24] - 2026-01-26

### Changed
- Added a minimal Streamlit UI at `src/rps/ui/streamlit_app.py` with a simple state machine and chat-style commands.
- Documented Streamlit usage in `doc/ui/streamlit_contract.md` and referenced it from `doc/architecture/system_architecture.md`.
- Added `streamlit` to `pyproject.toml` dependencies.
- Documented the base+mode knowledge injection model in `doc/architecture/system_architecture.md`.
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
- Agent knowledge injection now supports per-mode blocks; plan-week selects mode by task (e.g., phase_guardrails vs phase_structure).
- Phase-Architect knowledge injection now uses per-mode bundle IDs, similar to week_planner.
- Season-Planner and Season-Scenario now use per-mode bundles, and the injection config is de-aliased for readability.

## [0.6.3] - 2026-01-26

### Changed
- Renamed the Python package from `app` to `rps` and updated CLI/docs to use `python -m rps.main`.
- Added response-text logging when agents return no tool call, plus a no-tool-call summary for debugging.
- Inserted a blank line before streamed reasoning headings (`**`/`#`) for readability.
- Season Mode A now injects the shared knowledge bundle for season/season scenario runs.
- Expanded the agent knowledge injection bundles (contracts, interfaces, mandatory output guides, evidence).
- Added `data_confidence` schema and required it in activities_actual/trend outputs; pipeline now emits `meta.data_confidence`.

## [0.6.11] - 2026-01-26

### Changed
- LoadEstimationSpec now normalizes `planned_Load_kJ` to ENDURANCE_LOW (IF_ref_load = 0.65) and updates feasibility + KPI mapping accordingly.
- Season plausibility check now uses mechanical `planned_kJ_week`, and Phase STOPs defer to the S5 ladder; patch section removed.
- All agent prompts now explicitly label Fueling/Energy as `planned_kJ` and Governance as `planned_Load_kJ` in logs/notes.
- Store tool schemas no longer require `data_confidence` in the global meta; activities schemas still require it.
- Phase guardrails hard-stop now defers to LoadEstimationSpec S5 ladder before stopping on empty intersections.
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
- Added agent knowledge injection config and injected mandatory specs/policies/schemas for phase/week/builder/analysis runs.
- Season scenario pass‑2 now enforces cadence→phase length mapping + planning math consistency.
- Season planner pass‑1 now requires scenario‑based phase count math and fail‑fasts on mismatches.
- Mandatory output specs no longer mention file_search retrieval (runtime injects them).
- Added load-order rule across agent prompts: read user input + workspace artefacts before knowledge files.
- Phase plan-week now injects LoadEstimationSpec (General + Phase sections) into the user prompt.
- LoadEstimationSpec updated (values adjusted).

## [0.6.0] - 2026-01-26

### Changed
- plan-week now treats downstream artefacts as stale when upstream season/phase/workouts updates are newer, and re-runs as needed (cascade rebuilds).

## [Unreleased]

### Added
- Clarified that `compile_activities_actual` iterates every ISO week in the Intervals export and writes schema-compliant CSV/JSON per week (latest copy still lives under `runtime/athletes/<athlete>/latest`), so additional artefacts only require rerunning with a wider range if older weeks are needed.
### Changed
- The root Streamlit app now triggers the background-threaded Intervals pipeline refresh (tracked in `st.session_state`) so stale data starts refreshing before any page needs it, and the Data & Metrics page can simply surface the status without blocking.
- Local workspace reads now respect the actual recorded paths for archived artifacts (e.g., `ACTIVITIES_ACTUAL` per ISO week) when loading specific versions, instead of assuming a single `data/analysis` folder.
- Vector store sync now retries transient API errors with backoff instead of failing immediately.
- Streaming output supports optional italic rendering of reasoning via `RPS_LLM_STREAM_ITALICS`.
- Consolidated all agent knowledge into a single vector store (`vs_rps_all_agents`) with a unified `specs/knowledge/all_agents/manifest.yaml`.
- Consolidated season/phase load policies into `load_estimation_spec.md` (General/Season/Phase sections) and removed the standalone policy docs.
- LoadEstimationSpec tightened: deterministic Season utilization/body-mass fallback, KPI band selector, domain aliasing, and clarified Season/Phase responsibilities.
- Added ENDURANCE_LOW/ENDURANCE_HIGH intensity domains (with legacy aliasing), renamed `SST` → `SWEET_SPOT`, and reintroduced THRESHOLD in intensity-domain enums across schemas, specs, prompts, and workout policy.
- Split KPI workout-to-signal mapping into `kpi_signal_effects_policy.md` (informational) and referenced it from WorkoutPolicy.
- Principles 3.3 now explicitly scope cadence selection to Scenario/Season (Phase must not apply a default cadence).
- Scenario/Season prompts now reiterate cadence ownership (Phase must not apply defaults).
- Phase-Architect prompt now forbids manual temporal scope derivation, sets `meta.iso_week` to the first week of the provided range, and requires exact-range PHASE_STRUCTURE for previews (no latest fallback).
- Phase-Architect prompt now hard-stops if any month text conflicts with `meta.temporal_scope` or ISO-week range (no month inference from ISO weeks).
- Week-Planner prompt now restricts file_search to knowledge documents, requires exact-range governance lookup (no latest fallback), and blocks month inference from ISO-week labels.
- Season-Planner prompt now hard-stops on calendar-month inference from ISO-week labels and month/temporal_scope conflicts.
- Phase-Architect prompt now explicitly warns that ISO-week labels are not calendar months.
- Season/Week prompt headers now include an explicit ISO-week ≠ month reminder.
- Season/Phase/Week prompts now require reading `load_estimation_spec.md` before any kJ/load derivation.
- Season/Phase/Week prompts now explicitly require reading `load_estimation_spec.md` before load derivations (knowledge retrieval allowed if needed).
- Phase/Week prompts now include a binding Spec/Contract Load Map (Name / Content / How to load).
- Season prompt now includes binding load maps with tool methods for runtime artefacts.
- Phase-Architect now hard-stops if weekly_kj_bands are not narrowed to the LoadEstimationSpec (Phase) intersection.
- LoadDistributionPolicy upper‑third target is now explicitly advisory-only and only when requested.
- Phase/Week prompts now include informational policy load maps (KPI signal effects, workout policy).
- Load distribution policy now explicitly disallows Season/Phase usage.
- All agent prompts now include consolidated knowledge retrieval guidance (metadata filters + file_search scope).
- Added per-agent knowledge retrieval tables (required files + filters; tool instructions and fallback behavior).
- Workout-Builder retrieval table now lists all required specs/policies/schemas (including file naming + traceability).
- Knowledge retrieval tables now include informational evidence sources (evidence layer + bibliography) where applicable.
- Consolidated file_search instructions into a single Knowledge Retrieval section per agent and removed vector‑store wording.
- Season-Scenario prompt now ends planning horizon at the last A/B/C event in the Season Brief (no post‑event extension unless explicitly requested); events.md is logistics‑only.
- Season-Planner prompt now treats A/B/C events as Season Brief‑only and uses events.md for logistics constraints only; Phase prompt notes the same.
- Season-Planner prompt now allows non-URL publication links (internal references) for scientific foundation entries.
- Season-Planner prompt now forbids empty citation strings in `data.justification` and requires at least one non-empty citation per phase.
- Season-Planner prompt now treats scenario `phase_plan_summary` as binding for total weeks/phases and requires season `iso_week_range` to match it when provided.
- Season-Planner prompt now instructs loading `load_estimation_spec.md` as the first action before any other derivations.
- Season Mode A overview now injects the LoadEstimationSpec (Season section) into the agent prompt to ensure immediate availability.
- Season Mode A now injects LoadEstimationSpec from file start through the "## Phase" header (General + Season sections).
- Added `mandatory_output_season_plan.md` and load it for Season-Planner output guidance; Season Mode A injects it into the overview prompt.
- Season Mode A overview prompt now delegates all output/tool guidance to the mandatory output/spec blocks, keeping the inline prompt minimal.
- Added `mandatory_output_season_scenarios.md` and load it for Season-Scenario output guidance; Season Mode A injects it into the scenarios prompt.
- Season-Planner agent calls now inject LoadEstimationSpec (General+Season section) automatically in the runner to avoid missing-file issues.
- Season-Scenario agent calls now inject the mandatory SEASON_SCENARIOS output guide automatically in the runner.
- Simplified season_planner and season_scenario prompts to defer all field/validation guidance to mandatory output chapters.
- Season-Scenario prompt trimmed to scenario-only guidance; removed load-corridor/kJ rules and clarified KPI Profile is loaded from workspace (no selection logic).
- Added runtime artifact load maps (workspace tools) for all agents.
- Season-Scenario prompt and Season Mode A scenario run now explicitly require store tool calls with top-level `{meta, data}` envelopes (no JSON in chat).
- Season-Planner prompt and Season Mode A overview run now enforce store tool calls with top-level `{meta, data}` envelopes (no JSON in chat).
- Season overview phase corridors now explicitly require `weekly_load_corridor.weekly_kj` (min/max/kj_per_kg/notes) in prompts and Mode A overview guidance.
- Auto-render now handles KeyboardInterrupts gracefully (store succeeds even if sidecar rendering is interrupted).
- Store tool failures now return clearer schema error summaries (with top validation errors) and envelope hints.
- Runner strict path and workspace tools now emit the same concise schema error summaries and envelope hints.
- Agents now hard-stop with `STOP_TOOL_CALL_REQUIRED` if a required store tool isn’t called (after one forced retry).
- Added mandatory output guides for all agent-produced artefacts (phase guardrails/arch/preview/feed-forward, week plan, intervals export, DES report, season feed-forward).
- Prompt cleanup: removed format-only output rules, normalized example filenames to patterns, and corrected contract filenames (`week__builder`, `season__phase`, `phase__week`, `analyst__season`).
- Prompt redundancy cleanup: consolidated repeated required-input/stop text across agents and removed duplicate validation checklists.
- File search now attaches only **one vector store per agent** (shared store removed); runtime, docs, and smoke test updated accordingly.
- Shared vector store manifest removed; shared knowledge is now referenced via `../_shared/...` paths inside each agent manifest.

## [0.4.2] - 2026-01-25

### Added
- Streaming helper for Responses API with live reasoning/output/usage via `RPS_LLM_STREAM*`.
- Reasoning log toggle (`RPS_LLM_STREAM_LOG_REASONING`) for log capture on completion.
- Load distribution policy doc (`load_distribution_policy.md`) and manifest entry (advisory day-weighting).

### Changed
- Season/Phase/Week/Performance-Analyst prompts now require `events.md` (no optional/if-present paths).
- Season-Scenario prompt now requires `events.md` (no optional/if-present path).
- Season-Planner prompt now requires `events.md` to be reflected in `meta.trace_events` and phase event constraints.
- Season Mode A overview now explicitly requires loading `events.md` and reflecting it in trace/events constraints.
- Season scenarios now include advisory planning math (`phase_count_expected`, `max_shortened_phases`, `shortening_budget_weeks`) and Season-Planner cross-checks these against computed phase counts.
- Season scenarios no longer output detailed `phase_recommendations`; they now emit compact `phase_plan_summary` instead.
- Season-Scenario validation now requires `planning_horizon_weeks` to match `meta.iso_week_range`.
- Season-Planner validation now requires the A-event to be placed in a Peak phase and preserves event identity when mapping Season Brief events.
- plan-week orchestration now validates season coverage by iso_week_range, logs matching phases, and checks phase artefacts by range before running phase/week steps.
- plan-week now invokes Phase-Architect once per artefact (one task per run) to respect single-output contracts.
- Script logging now mirrors start/finish messages to stdout via `log_and_print`.
- plan-week now prints "Done." after successful artefact creation and skips the builder if the versioned week plan is missing.
- Phase-Architect guidance and validations now require weekly_kj_bands and week_roles to match the phase iso_week_range length (no fixed 4-week assumption).
- Phase-Architect prompt now explicitly derives phase length from the provided iso_week_range or season phase range.
- Phase-Architect prompt now enforces verbatim season constraint propagation and required self_check/preview fields.
- Phase-Architect now hard-stops if execution-arch self_check fields are missing or load_ranges.source is not the exact phase_guardrails filename.
- Phase-Architect now sources A/B/C event windows from season_plan phase constraints (events.md remains logistics only).
- Week-Planner now must store WEEK_PLAN via the store tool call (no raw JSON outputs).
- Week-Planner now validates AVAILABILITY/WELLNESS/ZONE_MODEL coverage using temporal_scope before declaring missing inputs.
- Wellness artefact now extends temporal_scope (and iso_week_range) to calendar year end so body_mass_kg remains valid for forward planning.
- LoadEstimationSpec updated to treat `weekly_kj_bands` as `planned_Load_kJ_week`, refine IF derivation, rounding order, fallback IF mapping, clamps, units, and parse edge cases.
- Season load corridor policy updated to use planned_Load_kJ conversions.
- Agent prompts updated to prefer strict store tool calls and avoid JSON-in-chat output rules that conflict with tooling.
- Artefact renderer now skips JSON list artefacts (e.g., intervals_workouts) with a clear log message instead of crashing.
- Agent runners now support streaming Responses output with optional reasoning summary and token usage reporting (configurable via `RPS_LLM_STREAM*` env vars).
- Reasoning payloads now treat `gpt-5*` models as reasoning-capable.
- plan-week now runs Performance-Analyst for the previous ISO week (week-1), and skips analysis if that report week is outside the season plan range.
- Week-Planner now explicitly limits WEEK_PLAN output to the requested ISO week even when the phase range spans multiple weeks.
- Week-Planner no longer biases weekly kJ placement to the upper-third of the governance corridor.
- LoadEstimationSpec now defines planned_kJ (mechanical) vs planned_Load_kJ (stress‑weighted) and treats weekly_kj_bands as planned_Load_kJ.
- Added optional LoadDistributionPolicy for day‑weighting and weekly load distribution (advisory only).
- Season load corridor policy now expresses corridors as planned_Load_kJ using a phase‑level default IF conversion.
- LoadEstimationSpec now adds rounding order, midpoint handling for range targets, safety clamps, explicit fallback mode (IF‑direct), and α source‑of‑truth rules.
- Index exact-range checks now verify artifact files exist (prevents stale index hits).
- Index manager now normalizes legacy analysis paths to data/analysis when the new file exists.
- Phase guardrails schema now allows variable-length `weekly_kj_bands` (no fixed 4-week constraint).
- Phase structure/preview and phase feed-forward schemas now allow variable-length arrays (no fixed 4-week constraint).
- Phase structure now supports variable-length phases via `week_roles[]` and removes 4-week-only schema fields.
- File naming, contracts, and specs now reference generic phase ranges (no `+3`).
- Season/Phase cadence guidance and constrained-time-window rules formalized in Principles 3.3 and referenced by prompts.
- Saved artifacts now apply schema-aware rounding (integers stay integers; kg/hours/IF/etc. rounded consistently).

### Fixed
- Season overview renderer no longer references deprecated mass/preload fields.
- Season scenarios tool schema now includes required planning math fields and runner fills defaults to satisfy strict validation.

### Removed
- Legacy data pipeline scripts removed (`intervals_export.py`, `compile_activities_actual.py`, `compile_activities_trend.py`).

## [0.4.1] - 2026-01-24

### Added
- Durability principles now include the permitted "Kinzlbauer season template" archetype (season-level sequencing and traceability anchors).
- Season load corridor policy spec for deriving weekly kJ bands from availability, wellness, KPI guidance, and activity trends.
- KPI profiles now include moving-time pacing guidance (`kJ/kg/h` + `W/kg`) for brevet/ultra segments.
- Season overview body metadata now records `body_mass_kg` alongside the reference mass window.
- Season brief template/spec now includes `Body-Mass-kg` for precise load scaling.
- Availability artefact (`AVAILABILITY`) + schema/interface spec, plus a Season Brief availability parser.
- Data pipeline now derives a ZONE_MODEL from Intervals.icu athlete sport settings and writes it to `latest/`.
- Season-Scenario-Agent with `SEASON_SCENARIOS` artefact + schema, plus strict store tool support.
- Season scenarios contract + interface spec for scenario → season handoff.
- Season scenarios template and new `vs_season_scenario` vector store manifest.
- Season scenarios schema now includes advisory guidance (cadence, phase recommendations, risks, constraints, intensity guidance).
- Season scenario selection artefact + schema (`SEASON_SCENARIO_SELECTION`) with deterministic CLI write.
- New validation checklist for `SEASON_SCENARIOS`.
- Per-agent reasoning overrides via `RPS_LLM_REASONING_EFFORT_<AGENT>` and `RPS_LLM_REASONING_SUMMARY_<AGENT>`.
- CLI logging switches (`--log-level`, `--log-file`) with structured log output.
- Tool-call debug logging for agent runners.
- Responses API reasoning settings via `RPS_LLM_REASONING_EFFORT` / `RPS_LLM_REASONING_SUMMARY`.
- Reasoning summaries (when returned) are logged to CLI and log files.
- Phase-Architect prompt now specifies workspace_put_validated usage and phase guardrails schema requirements.
- Added a PHASE_GUARDRAILS template for Phase-Architect with fill markers.
- `--debug-file-search` now logs file_search results to CLI/logs.
- `run-task` CLI for strict schema-validated agent outputs (uses read tools + strict store tools).
- Phase-Architect prompt now enforces exact template structure when a template is found.
- Debug file_search logging now captures `file_search_call` results in strict runs.
- `run-task` now supports `--max-results` for file_search.
- Phase-Architect file_search guidance prioritizes the PHASE_GUARDRAILS template filter.
- Phase-Architect prompt now requires strict store tool calls instead of raw JSON when available.
- `run-agent` now accepts `--task`, `--run-id`, `--max-results`, and strict mode toggles.
- Season overview schema now supports structured recovery protection (`fixed_rest_days` + `notes`) and requires it under global constraints.
- Phase structure schema now includes structured weekly load ranges with a required `source` field.
- Added a PHASE_STRUCTURE template for Phase-Architect with fill markers.
- Added a PHASE_PREVIEW template for Phase-Architect with fill markers.
- Added templates for Season-Planner (SEASON_PLAN, SEASON_PHASE_FEED_FORWARD).
- Added templates for Week-Planner (WEEK_PLAN).
- Added templates for Workout-Builder (INTERVALS_WORKOUTS).
- Added templates for Performance-Analyst (DES_ANALYSIS_REPORT).
- Principles validation checks added to season plan, phase guardrails, and phase structure validation docs.
- Season overview justification section with structured citations and per-phase rationale.
- Wellness artefact (`WELLNESS`) + schema/interface spec for daily biometric/self-report data.
- Data pipeline now writes `wellness_yyyy-ww.json` and latest `wellness.json`.
- Availability validation checklist and `validate_outputs.py` support for availability artefacts.
- Standalone scripts now emit per-run logs with timestamped filenames under `runtime/athletes/<athlete_id>/logs`.
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
- Strict runner now forces tool calls for `SEASON_SCENARIOS`, `SEASON_SCENARIO_SELECTION`, and `SEASON_PLAN` when missing.
- Runner normalizes season-scenario payloads (required arrays, disallowed keys) before validation.
- Runner normalizes week plan meta fields to schema constants before validation.
- Performance-Analyst prompt no longer stops early when binding sources are not returned by file_search.
- Default CLI log filenames now include a UTC timestamp to avoid overwriting logs per run.
- Responses payloads now omit `temperature` for models that do not support it (e.g., gpt-5).
- Activities trend metadata now derives `iso_week_range` from the underlying temporal scope.
- `validate_outputs.py` now uses the updated logging helper signature.
- Added binding `progressive_overload_policy.md` (kJ-based cadence/deload/re-entry) for Season/Phase/Week.
- Clarified cadence/deload ownership across principles/policies/mandatory outputs to defer numeric rules to ProgressiveOverloadPolicy.
- Updated KPI profiles to align progression limits with ProgressiveOverloadPolicy (weekly <=10%, warning 10–12%, stop >15%; long-ride <=12%, warning 12–15%, stop >15%).

### Changed
- KPI profile schema removed per-kg preload windows and now requires moving-time rate guidance instead.
- Season overview schema/template replaces per-kg preload references with `moving_time_rate_guidance`.
- Season-Planner now derives weekly kJ corridors from body mass, kJ/kg/h guidance, and weekly hours.
- Season/Phase/Week/Scenario prompts now require AVAILABILITY for weekday constraints + weekly hours.
- Availability artefacts now scope from generation date to season year end and are replaced by newer versions.
- Phase-Architect governance now targets upper-third load bands for build/peak weeks by default.
- ZONE_MODEL owner moved to Data-Pipeline; Phase-Architect now consumes the latest model instead of generating it.
- Season overview schema now requires `body_mass_kg` and removes `reference_mass_window_kg`.
- KPI profile narrative guidance now references moving-time rate bands instead of legacy kJ/kg preloads.
- Season Mode A scenarios now run Season-Scenario-Agent, store `season_scenarios`, and render the same cached scenario dialogue for selection.
- Season-Planner prompt can optionally load `SEASON_SCENARIOS` as advisory input.
- System architecture, planner workflow, how-to-plan, and artefact flow docs updated to include Season-Scenario-Agent and `season_scenarios`.
- Season-Scenario prompt and template expanded to emit guidance fields; scenario cache output now includes guidance + phase outline.
- Season-Planner prompt now consumes scenario guidance when present.
- Season Mode A selection (`select`) is now deterministic (no LLM) and `overview` accepts optional `--scenario` if selection exists.
- `run-agent` now defaults to strict tool mode for JSON-producing agents; use `--non-strict` to opt out.
- Season Mode A helper now passes reasoning settings into the strict runner.
- Phase-Architect and Week-Planner now have access to the season load corridor policy (informational, non-binding).
- Availability parser now derives the season year from the Season Brief when `--year` is omitted.
- Availability parser now correctly parses decimal hour values (e.g., 1.5 h).
- Multi-output runner now auto-widens degenerate phase guardrails bands (min == max).
- Phase-Architect no longer uses markdown templates; outputs are schema-driven JSON only.
- Season, Season-Scenario, Week-Planner, Workout-Builder, and Performance-Analyst templates removed in favor of schema-driven JSON.
- Agent prompts now fully remove template lookup rules; all outputs are schema-driven JSON only.
- Season Mode A overview now accepts a moving-time rate band override.
- Wellness artefact now includes `body_mass_kg` (from Intervals.icu athlete profile, with wellness fallback).
- Phase-Architect prompt now enforces non-zero weekly band widths and upper-third corridor placement.
- Season-Planner now writes structured fixed rest days when provided.
- Phase-Architect now propagates season-level availability/risk constraints into governance and phase structure.
- Phase-Architect now mirrors phase guardrails load ranges into phase structure.
- Guarded store now rejects Phase outputs that fail season-constraint propagation checks.
- Phase guardrails template now embeds season-constraint mapping placeholders.
- Agent prompts now include conditional template usage guidance.
- Guarded store now enforces execution preview traceability to phase structure.
- Phase-Architect prompt now requires weekly kJ progression patterns (default 3:1) unless season specifies steady-state.

- Planning artefacts are now kJ-first only: removed TSS fields from season plan, phase guardrails/execution, week plans, and zone model examples.
- Renderer templates now omit TSS columns/sections for non-activities artefacts.
- Activities trend adherence now computes against planned weekly kJ from week plans; TSS remains only in activities_* artefacts.
- Durability-first principles updated to v1.1 with expanded progressive overload guidance, intensity distribution rules, and 3:1 alternatives.
- Principles paper translated to English and synced for season/phase knowledge sources.
- Season-Planner prompt now requires applying Principles sections 2-6.
- Phase-Architect prompt now requires applying Principles sections 3.3, 3.4, 4, 5, and 6.
- Season-Planner prompt now requires populating `data.justification` with citations and per-phase rationale.
- Season-Planner validation now enforces narrative/domain consistency and deload flag alignment.
- Season overview template updated to v1.1 to include justification fields.
- Season Mode A overview now injects selected scenario details into the prompt when available.
- Validation tooling and docs now include wellness outputs.
- Scenario, season, and phase prompts now conditionally apply Principles 3.4 sequencing guidance only when the ultra/brevet archetype is explicitly requested, and only when availability supports the time-crunched weekend emphasis.
- Principles 3.2 backplanning guidance rewritten as an agent-executable planning cookbook and synced to agent knowledge copies.
- Principles 3.2 macrocycle wording now aligns with `SEASON_CYCLE_ENUM` (Base/Build/Peak/Transition).
- Season-Planner prompt now mirrors the `SEASON_CYCLE_ENUM` wording in backplanning guidance.
- Agent artifact storage now nests plans/analysis/exports under `runtime/athletes/<id>/data/`, and the legacy `workouts/` folder is no longer created.
- Season/Phase/Week prompts now require `events.md` from inputs and STOP if it is missing.

## [0.2.0] - 2026-01-22

### Added
- Per-agent model overrides via `RPS_LLM_MODEL_<AGENT>` and CLI plumbing to honor them.
- Per-agent temperature overrides via `RPS_LLM_TEMPERATURE_<AGENT>` (plus global `RPS_LLM_TEMPERATURE`).
- `workspace_get_input` tool for athlete-specific markdown inputs (season brief, events).
- Vector store sync progress output and `--reset` to reinitialize stores.
- Vector store sync now attaches header/schema-derived attributes for filtered file_search.
- Schema bundling workflow (`scripts/bundle_schemas.py`) and bundled outputs under `specs/knowledge/_shared/sources/schemas/bundled/`.
- Vector store smoke test script: `scripts/smoke_vectorstores.py`.
- Build checklist and recommended model guidance docs.
- Mode A season helper script for scenarios + season plan (deprecated; streamlit UI replaces it).

### Changed
- Force `file_search` by default in agent runs; add `--no-file-search` to disable.
- Shared knowledge manifests now reference bundled schemas; rendered KPI sidecars removed.
- Schema bundler handles `jsonref` serialization for bundled outputs.
- Agent prompts now treat instructions as a single file with section-based guidance; removed bundle/BEGIN/END marker references.
- Agent prompts now point to schema files instead of deprecated templates and year-specific filenames.
- Agent prompts are simplified further by removing legacy template/YAML language and redundant checks.
- Planning docs now specify copying the selected KPI profile into `latest/kpi_profile.json`.
- Artefact flow docs now describe the two-step Season Mode A scripts.
- KPI profile JSON sources moved to top-level `specs/kpi_profiles/` and removed from vector store manifests.
- Data pipeline scripts now accept `--athlete` with `.env` fallback for multi-athlete runs.
- Data pipeline docs now include multi-athlete CLI examples.
- User input interface specs/templates for season briefs and events moved to shared knowledge sources.
- Workspace docs now mention `inputs/` and the user-input templates.
- Agent prompts now require user inputs to be loaded via `workspace_get_input` (not file_search).
- Agent prompts now include access hints for tool-based artifact loading.
- Agent prompts now include mode-specific access hints with optional-input guidance.
- Agent prompts now include file_search filter guidance for knowledge sources.
- Workspace read tools now expose `workspace_get_phase_context` for phase-scoped access.
- How-to-plan docs now include concrete season/phase/week/workout-builder/performance-analysis CLI commands.
- Planning docs now reference `workspace_get_phase_context` and avoid embedding tool-usage hints in CLI examples.
- JSON schemas normalized for strict tool compatibility (explicit types/required, flattened `allOf`, removed unsupported constraints).
- Version key derivation now supports string-based `iso_week` and `iso_week_range` metadata.
- Docs and README now document the two-step Season Mode A workflow.
- Model guidance notes include Season Mode A scenario token-throughput tip.
- Agent runners now pass optional temperature settings; `.env.example` and model docs reflect temperature overrides.
- System architecture docs now describe vector store attributes, filtering, and agent access hints.
- Durability bibliography now carries a compliant YAML header.

### Removed
- Legacy schema copies under `specs/knowledge/_shared/sources/schemas/` (replaced by bundled variants).
- Obsolete shared schemas `data_confidence` and `season_cycle_enum` from knowledge sources.

## [Unreleased]

### Added
- Athlete Profile now exposes a `Zones` page that renders the latest `zone_model.json` as a tabular overview (FTP ranges, watts, IF, intent) and appears in the navigation menu next to Availability and Logistics.
- Added an agents TODO reminding us to reconcile the Phase page preview helpers before reapplying the custom UI/templating work.
- Intervals data pipeline now compiles `historical_baseline` yearly summaries from full-year activity fetches.
- `RPS_LLM_MAX_COMPLETION_TOKENS` with per-agent overrides via `RPS_LLM_MAX_COMPLETION_TOKENS_<AGENT>`.

### Changed
- Plan Hub now collapses `Phase Guardrails`, `Phase Structure`, and `Phase Preview` into a single user-facing `Phase` card and scope; `Run Phase` now creates all three phase artefacts for the selected phase.
- Full-project `mypy` now passes across `src/`; queue/worker payload handling, plan pages, Intervals posting, historical baseline rendering, and performance metric flag access were tightened with explicit type narrowing instead of permissive `Any` flows.
- Typing boundaries across the LiteLLM adapter, agent runners, coach tool wiring, workspace read/write tools, guarded store validation, and renderer sorting were tightened further; full-project `mypy --check-untyped-defs src` now also passes.
- OpenAI response/streaming/vectorstore helpers and the run-store/queue-scheduler path were tightened further: response extraction and streaming now use concrete LiteLLM response types, vectorstore sync metadata/chunk payloads are modeled more explicitly, and run/queue records now use narrower typed accessors instead of broad object assumptions.
- `src/rps/ui/rps_chatbot.py` now uses concrete protocol-based types for Responses/File/Container/Vector Store access, with stricter JSON/message/block handling instead of broad dynamic payload assumptions.
- `src/rps/openai/litellm_runtime.py` now narrows LiteLLM payload, tool, message, and stream parsing helpers to explicit JSON-style structures, reducing broad dynamic typing in the Responses adapter.
- Week page now treats a missing Season Plan as a warning-state readiness hint instead of a hard page error, so the page still renders cleanly before planning inputs are complete.
- Plan Hub scoped `Phase Structure` runs now always rerun `Phase Preview` immediately after `Phase Structure`, keeping both phase artefacts aligned without requiring a separate manual preview run.
- User-authored input artefacts now use valid metadata semantics: `owner_agent` allows `User`, manual UI inputs no longer write `data_confidence: "USER"`, and bundled schemas were rebuilt accordingly.
- Guarded store validation for `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` now matches planned event windows semantically instead of requiring the exact season-plan string form to appear verbatim in downstream payload blobs, and recovery-protection notes are normalized safely from string or list inputs.
- Plan Hub now uses a direct-actions-first layout: routine planning is driven by readiness-card actions and the primary Plan Week CTA, while the generic scoped/orchestrated run builder moved into an `Advanced manual run` expander.
- Historic Data now reads yearly summaries from the `historical_baseline` artifact and refreshes via the Intervals pipeline.
- Historical baseline schema now includes `yearly_summary` payloads.
- Availability inputs now enforce 0.5h increments with 1-decimal precision, and travel risk values are normalized to uppercase (`LOW|MED|HIGH`) across UI, schema, and parser.
- Historic Data removes the baseline metrics block and rounds yearly summary kJ/km values to integers.
- Data Operations no longer surfaces the deprecated availability import expander.
- Athlete Profile docs updated to reflect the current Historic Data behavior.
- Planning Events UI now uses explicit Priority (A/B/C) and Rank (1-3) fields while preserving the stored schema mapping.
- Logistics events now auto-generate Event IDs on save and document uppercase status/impact enums.
- Availability UI now includes guidance for 0.5h increments and uppercase travel risk.
- Planning Events validation now enforces date format, rank uniqueness, and A-event spacing with clearer errors.
- Logistics events now require date/description, prevent duplicate dates, and sort entries by date with a status summary.
- Historic Data now shows the last refresh timestamp from baseline metadata.
- Athlete Profile tables now sort newest-first (events, logistics, yearly summary).
- Activities Trend table now populates period and weekly aggregate fields from parquet cache.
- Data & Metrics tables now include a newest-first toggle for trend/actual rows.
- Schema bundler strips nested `$id` values to avoid duplicate canonical-uri errors for strict tool validation.
- Multi-output runner stages tools (read/search first, store-only on forced tool calls) to reduce token load.
- Groq LiteLLM requests use `tool_choice=auto` when tools are present and retry TPM limits via `RPS_TPM_*`.
- Groq default model now falls back to `groq/openai/gpt-oss-20b` when `RPS_LLM_BASE_URL` points to Groq.
- Workspace state/index call sites now consistently narrow `object` payloads from the local store before reading artefact/index metadata, fixing the follow-on typing breakage from stricter store APIs.
- Performance Feed Forward, Plan Workouts, System History, System Status, startup vectorstore sync, and workspace read/write helpers now use explicit JSON-map access patterns instead of unchecked `.get()` chains on dynamic objects.
- Intervals posting receipt helpers now use explicit receipt/payload row types instead of broad dynamic dict typing, including safer text normalization for generated external IDs.
- A repo-managed `ruff` lint gate is now mandatory in `.githooks/pre-commit` via `scripts/run_lint.sh`, with a conservative initial rule set (`F`, `I`) and dev dependency/config stored in `pyproject.toml`.
- The initial `ruff --fix` sweep normalized imports and removed low-risk unused-code issues across scripts, app modules, workspace helpers, and tests so the new hook starts green instead of landing as a broken gate.
- Developer-facing docs now include the lint command and local hook activation step in `README.md`.
- The mandatory `ruff` gate was expanded slightly with a small set of safe modernization checks (`UP017`, `UP031`, `UP035`, `UP037`) after verifying a green repo run.
- The mandatory `ruff` gate now also covers low-risk `flake8-bugbear` checks `B904` and `B905`, with explicit `zip(..., strict=...)` handling and explicit exception chaining in CLI argument parsing.
- LiteLLM tool-call normalization now avoids constant-name `getattr(...)` lookups in the runtime adapter, reducing another small `ruff` `B009` quality hotspot without changing behavior.
- Weekly KPI aggregation in `intervals_data.py` now binds the current week frame explicitly into helper calls instead of relying on an implicit loop-variable closure, removing another `ruff` `B023` hotspot and making the helper semantics clearer.
- `SchemaBundler` now uses an explicit per-instance schema cache instead of `@lru_cache` on a bound method, keeping bundling reuse local to the bundler object and resolving the remaining `ruff` `B019` lifecycle warning cleanly.
- The mandatory `ruff` gate now also includes the low-risk simplification rules `SIM103` and `SIM108`, with targeted cleanups in logging helpers, runner predicates, Groq/model detection helpers, and authority normalization.
- Several remaining safe simplifications were applied outside the dense guarded-store normalization paths: `coach.py` now uses `contextlib.suppress` for optional numeric env parsing, while small nested-condition cleanups landed in `intervals_data.py`, `streaming.py`, and `plan/hub.py`.
- `guarded_store.py` numeric rounding heuristics were refactored into an explicit `_rounding_decimals()` helper and small nested-condition checks were flattened, removing the remaining local `SIM102`/`SIM114` hotspots while making the validation/normalization path easier to read.
- The local `scripts/` tree now uses explicit package-style imports for `script_logging` and direct imports from `rps.data_pipeline.common`, which removes the last repoweight `mypy` import-resolution errors and restores a clean `python3 -m mypy --explicit-package-bases src tests scripts` run.
- `scripts/run_typecheck.sh` now supports both the curated commit-gate scope and a documented `--full` mode for full-repository validation, and the central developer docs now reference both commands explicitly.
- A first low-risk `PERF401` cleanup pass replaced manual append loops with comprehensions/extends in schema checks, OpenAI response helpers, renderer context builders, and several Plan/System run-history table helpers.
- Additional low-risk lint cleanup replaced a few remaining parser/helper magic-number comparisons with named constants in logging, streaming, shared UI, and ISO helper modules, simplified the non-negative phase week offset clamp, and removed a repeated `split()` pattern in `intervals_data.py` without changing planning behavior.
- Repo-wide `PLR2004` cleanup is now complete: remaining runner, orchestrator, UI, workspace, data-pipeline, and test comparisons use named constants instead of scattered literal thresholds, including the activity-trend KPI flag thresholds in `intervals_data.py`.
- The final full-repo `mypy` cleanup pass typed the remaining `tests/test_plan_pages.py` fixtures/functions that still triggered `annotation-unchecked` notes, leaving `./scripts/run_typecheck.sh --full` fully clean.
- A second low-risk `PERF401` cleanup pass converted remaining simple row/message/path collectors in the Plan Phase/Week pages, chatbot message filtering, and backup path collection to comprehensions or `extend(...)`.
- The final `PERF401` cleanup pass simplified remaining constraint-mismatch error collection in `guarded_store.py`, leaving the full repository green for `ruff --select PERF401`.

## [0.1.0] - 2026-01-20

### Changed
- Complete rewrite targeting OpenAI Responses API.

### Added
- Local workspace docs and validation guide under `doc/`.
- Data pipeline validator script: `scripts/validate_outputs.py`.
- Artefact flow overview with updated Mermaid diagrams.
- Vector store operations and incident guidance in `doc/architecture/system_architecture.md`.

### Changed
- Data pipeline docs updated to reference `get_intervals_data.py`.
- System docs updated for workspace handling and validation flow.
