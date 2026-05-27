# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added a mandatory evidence-curation runtime stage: new `evidence_curation_specialist` agent/task/skill, native Pydantic `EvidenceCurationModel`, deterministic trusted-source matching, quality-gate/activation pipeline, and provenance-aware study briefs rendered from structured curation output.
- Added a canonical repo-wide evidence library under `skills/shared/durability-methodology/references/library/`, including structured core/applied source registries, generated markdown lookup tables, per-study detail pages, and decommission markers for legacy bibliography/manifest files.
- Added a weekly evidence refresh path with fail-closed primary-source discovery from PubMed plus background run-store integration and a manual System Status trigger for evidence refresh runs.
- Added higher-fidelity evidence detail summaries across the canonical library: core and applied sources now carry structured focus/scope, concepts, findings, and practical RPS implications instead of thin lookup-only study cards.
- Added curated durability reference tables for shared planning/coaching skills, split into a higher-authority core table and a separate applied/practitioner table.
- Added repo-wide prompt/skill evidence-priority alignment for durability-first explanations: active coach/week-facing prompts and skills now use `core -> applied -> archive`, and CrewAI `factual_evidence` injects the curated tables ahead of the legacy bibliography.
- Added final durability reference cleanup across runtime/test/spec surfaces: coach runtime guidance, evidence tests, and season-plan example citations now point to the curated reference hierarchy instead of treating the legacy bibliography as the operative default.
- Added deterministic season-plan closure for auditability and guardrails: final `SEASON_PLAN` normalization now enriches authoritative input traces, corrects canonical PubMed links for core season references, surfaces explicit Build-entry and taper label semantics, and hard-blocks `SWEET_SPOT_EXTENSIVE` in `taper_freshening`.
- Added an upstream-first planning pipeline contract for Season, Phase, and Week flows: finalize agents now own semantic bundle completion, review stages default to formal approval with bounded replan only for true residual defects, and writers are explicitly constrained to serialization plus deterministic final projection.
- Added full progressive-overload policy guidance to active Season and Phase planner/review layers: task descriptions, planner prompts, and load/structure/review skills now explicitly carry cadence-family selection, ramp classes, deload vs mini-reset, reload vs re-entry, fallback behavior, conservative next-baseline logic, Build-entry readiness gates, and warning-only handling for user-owned objective mismatches.
- Added a combined policy/principle/prompt migration hardening pass: the central migration audit now covers legacy prompt sources plus all active prompt roles, and active Season/Phase/Week prompt authority is being normalized toward self-contained role boundaries with explicit injected deterministic authority.
- Added a dedicated GitHub Actions evidence-refresh workflow that runs the canonical library refresh on Linux/Python 3.13, retries transient failures, and commits refreshed evidence outputs back to `main` only when files actually change.

### Changed
- Changed the canonical documentation set (`doc/`) to match the new evidence runtime: architecture, flow, workspace, UI, and run-store docs now describe the repo-scoped evidence library, weekly `literature_refresh`, mandatory evidence curation, deterministic gating/activation, and System Status/History visibility for evidence refresh runs.
- Changed older evidence feature docs to explicit historical-step positioning, while `FEAT_repo_wide_evidence_library_and_refresh` and `FEAT_evidence_curation_pipeline` now serve as the current canonical evidence-system feature specs.
- Changed evidence-curation instructions and validation so `metadata_only` outputs stay identification-level, while `abstract_curated` outputs remain explicitly abstract-bounded instead of reading like final deterministic coaching policy.

### Fixed
- Fixed literature/reference handling to fail closed: active skills/prompts/runtime guidance now treat the canonical local evidence library as the only operative source, require `omit instead of invent` behavior for uncertain locators, and drop unverifiable publication links from persisted outputs instead of preserving model-supplied guesses.
- Fixed evidence-curation semantic leakage for weak source bases: discovery tags and title paraphrases no longer count as findings for `metadata_only` sources, `background_only` can no longer be mixed with stronger allowed-use categories for `abstract_curated` sources, and the quality gate now rejects direct imperative coaching language derived too aggressively from abstract-only material.
- Fixed `season_scenarios` active-prompt drift against the already stricter task/skill/guardrail contract: `prompts/agents/season_scenario.md` now locally carries the Scenario C `VO2MAX` ceiling-support explanation rule, and a regression test protects the prompt/task/skill alignment that prevents repeated guardrail retry failures.
- Fixed Season writer guardrail ordering so final `SEASON_PLAN` contract validation repairs deterministic role-week guardrail notes, canonical load modalities, and real event constraints before evaluating the writer output, preventing false blocking failures on code-owned fields such as `weekly_load_corridor.weekly_kj.notes`.
- Fixed planning-stage contract enforcement so review-ready bundle checks now run in Season/Phase/Week finalize stages, approved review decisions must carry an explicit writer-ready summary, stale phantom event placeholders are rejected upstream, and Season writer validation no longer blocks on forbidden-domain narrative cleanup that should have been resolved before writing.
- Fixed deterministic Season slot semantics so generic `BUILD` slots in `src/rps/planning/load_bands.py` no longer fall blindly to `threshold_build`; build-intent default selection now respects season intensity-domain governance and keeps canonical `season_phase_role` aligned with the final normalized phase intent.

## [0.17.0] - 2026-05-22

### Added
- Added a dual bundled schema publication path for structured outputs: the bundler now emits canonical bundled schemas for persisted validation and `bundled_output` schemas for OpenAI/CrewAI structured output.
- Added a deterministic Season semantic-contract layer: internal Season bundles now carry code-owned phase semantic profiles, explicit forbidden domains, exact season load-envelope handoff, and writer-safe semantic notes instead of leaving methodology-critical Season framing in prose only.
- Added explicit draft output models and runtime normalization stages for Season and Phase planning, with stage-aware telemetry for normalization and normalized-contract failures before review/writer handoff.
- Added explicit multi-A-event reverse-planning guidance for Season planning: planners may form one or more target macrocycles, must distinguish separate A-event anchors from peak clusters, and must classify A-event priority/cluster relationships in season justification without changing the persisted schema.

### Changed
- Changed generated schema-backed artifact models to be dual-schema-aware, so `model_json_schema()` now exposes the LLM-safe bundled output schema while post-parse validation still runs against the canonical bundled schema.
- Changed Season planning/review/writer handoff to validate canonical phase semantics, intent-specific domain limits, bundle completeness, and exact writer copy-through of `season_load_envelope` and phase semantics before persistence.
- Changed `season_plan_finalize` and `phase_bundle_finalize` to emit draft bundles only; deterministic taxonomy/domain/envelope semantics are now injected by Python normalization and validated after normalization instead of on raw LLM output.
- Changed deterministic Season/Phase semantic normalization to fail closed on invalid type-intent pairs while canonicalizing recoverable mismatches, so illegal combinations such as `PREPARATION + general_base` no longer pass through load-band context or bundle normalization unchecked.
- Changed the Season writer guardrail to reapply approved deterministic fields before exact-match validation, so `season_load_envelope`, phase taxonomy fields, and allowed/forbidden domain semantics cannot drift during artifact writing.
- Changed Season bundle normalization to derive deterministic `season_load_envelope` week-count fields from canonical cadence roles when drafts omit them, so persisted `SEASON_PLAN` artefacts always satisfy the required integer envelope schema.
- Changed canonical season semantics so `RECOVERY` is a legal non-quality domain across the phase taxonomy unless explicitly overridden, and season authority no longer treats it as an out-of-contract domain drift.
- Changed season-plan normalization and writer repair to derive `allowed_load_modalities` from canonical phase semantics, preserve `NONE`, serialize only real event constraints, materialize deterministic role-week guardrails in existing season-plan text, and surface objective/A-event mismatches as visible warnings instead of blockers.
- Changed season contract validation to check canonical load modalities, real event-constraint projection, role-week guardrail rendering, taper/event-week semantics, and warning-only objective/A-event mismatches.

## [0.16.0] - 2026-05-21

### Added
- Added a canonical phase-taxonomy migration contract: `phase_type`, canonical `phase_intent`, explicit `build_subtype`, and persisted `phase_taxonomy_version` are now documented through a new feature spec and ADR, with the old repo-specific phase-intent backbone marked superseded.
- Added fail-closed phase-semantic normalization helpers and migration trace semantics so legacy phase-intent values normalize only through explicit mappings, unknown legacy values are rejected, and Build phases carry a first-class selector key.
- Added schema enforcement for canonical season/phase semantics across `SEASON_PLAN`, `PHASE_GUARDRAILS`, `PHASE_STRUCTURE`, and `PHASE_PREVIEW`, including Build-only `build_subtype` rules and new-write rejection of legacy taxonomy values.
- Added canonical phase-taxonomy skill/task alignment across Season, Phase, and Week planning: active skills and Crew task descriptions now instruct planners to reason with explicit `phase_type`, `phase_intent`, `build_subtype`, and `phase_taxonomy_version` instead of legacy repo-specific intent labels.
- Added an auditable deterministic week workout selector above the protocol solver: week planning now evaluates candidate protocol variants with flat selector-rule rows, anti-monotony penalties, preview-alignment bonuses, modality strictness, and stable tie-breaks before solving concrete workout structure.
- Added a new `WEEK_WORKOUT_SELECTION_AUDIT` artefact plus CSV sidecar so every generated `WEEK_PLAN` can be externally reconstructed from candidate rows, matched selector rules, legality filters, scores, penalties, bonuses, and final picks.
- Added a canonical flat selector-policy registry in `config/planning/week_workout_selection_rules.yaml` and matching documentation under `doc/` for externally reviewable week-shape logic.
- Added conservative shortened-re-entry week-shape defaults: re-entry weeks now default to one true quality day plus endurance support, and non-anchor endurance days no longer select long-anchor protocols.
- Added review-bucket operationalization to the week selector audit and scoring layer: selector rows can now encode `SOLL`, `KANN`, `NUR_WENN`, and `VERMEIDEN`, and specificity-build VO2 carry-over cases are explicitly down-ranked as `NUR_WENN`.

### Changed
- Changed active Season, Phase, Week, and workout-planning skills plus Crew task descriptions to use only the canonical phase taxonomy and planner-purpose semantics, so `BUILD` focus is expressed upstream through `phase_intent` and `build_subtype` instead of repo-specific legacy labels.
- Changed operative week workout protocol, family, selector-rule, review-matrix, and audit-guide configuration to the canonical taxonomy, replacing generic or legacy planning labels with explicit `general_base`, `vo2_build`, `threshold_build`, `sst_build`, `durability_build`, `specificity_build`, `peak_sharpening`, `taper_freshening`, and `race_execution` semantics.

## [0.15.0] - 2026-05-20

### Added
- Added explicit week-shape guidance and documentation for shortened re-entry weeks: the canonical workout-generation docs now describe week-level protocol diversification, softer second-quality handling in re-entry weeks, preview-alignment warnings, and stricter effective modality handling when phase artefacts disagree on `K3`.
- Added canonical workout-generation documentation under `doc/`: a normative feature spec now defines supported workout domains/protocol classes, TiZ semantics, progression order, caps, prior-week progression reuse, Z2 add-on rules, and week-density rules, and a matching athlete-/coach-readable overview explains the same logic in plain language.
- Added direct config-driven solver semantics for workout progression caps and quality cost: protocol definitions now encode TiZ counting mode, standard/hard caps, progression priorities, redistribution thresholds, practical VO2 rep ceilings, and late-finish caps for durability sessions.
- Added a protocol-driven deterministic week workout engine: week workout generation now selects configured workout protocols, solves TiZ/set/rep structure plus optional Z2 add-ons, and renders canonical Intervals subset text from protocol metadata instead of coarse family templates.
- Added full first-pass protocol coverage for the canonical workout types defined in the active workout policy and durability-first principle, including threshold intervals, tempo over-under, VO2 20/10 microbursts, and durability-specific endurance finish day types.
- Added prior-week protocol progression reuse for deterministic week workout solving: the Week engine now infers the last canonical interval structure from the previous `WEEK_PLAN` and feeds that signature into classic-interval, microburst, and over/under progression decisions.
- Added a deterministic Week planning engine with configurable workout-family registry and selection policy, replacing runtime Week CrewAI planning/review/writer execution with code-owned contract loading, day-role allocation, load reconciliation, family selection, and validator-backed workout rendering.
- Added a deterministic workout generation stack for week planning: structured workout blueprints can now render through code-owned workout AST/renderer models, canonical section ordering, standalone loop headers, and strict validator-backed subset output instead of relying on LLM-authored final `workout_text`.
- Added week domain failure hardening across internal week bundles, review preflight, and writer guardrails: internal workout blueprints now require canonical legality fields, illegal phase-forbidden domains are blocked before writer execution, and writer legality compares final workout content against the approved planning bundle instead of relying on text heuristics alone.
- Added explicit week-band authority alignment across rendered deterministic week context, week skills, and week review task descriptions so agents treat `active_weekly_kj_band` as binding and `active_s5_band` as fallback/background only.
- Added a completed runtime migration for week workout authoring/review method sources: the operative rules from the legacy workout export contract, Intervals grammar, project subset validation, and workout policy now live directly in the active week workout skills plus local references.
- Added a normalized season/phase semantic backbone with `scenario_guidance.season_archetype` (`none` / `ceiling_first_durability`) plus schema-backed `phase_intent` propagation across Season Plan, Phase Guardrails, Phase Structure, Phase Preview, deterministic contract context, renderer context, and guarded-store validation.
- Added deterministic `phase_intent` derivation for season phase slots, including explicit support for `specificity_build` between generic durability build and late peak/taper semantics.
- Added weighted season-envelope derivation/validation so `season_load_envelope.expected_average_weekly_kj_range` is checked against written phase corridors instead of free-authored arithmetic.
- Added intent-aware planning guidance across season, phase, week, and workout skills/tasks so week shape and workout-family selection are constrained by inherited `phase_intent`.
- Added deterministic season intensity-domain authority propagation from `SEASON_SCENARIOS` / `SEASON_SCENARIO_SELECTION` into season load-capacity and season phase-load context, plus season contract checks that block a full-season collapse to `ENDURANCE only` when selected-scenario authority is broader.
- Added active kJ-first season-scenario methodology plus runtime quality checks so Scenario A/B/C differ primarily by exposure, recovery margin, specificity, and risk contract instead of domain breadth alone.
- Added an explicit repo-aligned phase-intensity semantic table directly into the active Season and Phase skills, covering `Transition`/`Base`/`Build`/`Peak` phase-intent guidance, conditional bridge use in Transition, `K3` as modality-only, and downward domain authority from Scenario to Phase to Week.
- Added five schema-backed user-facing `SEASON_SCENARIOS` fields — `typical_week_feel`, `main_payoff`, `main_cost`, `what_gets_prioritized`, and `what_gets_de_emphasized` — with normalization defaults, active scenario-skill/task guidance, and Season-page rendering.
- Added deterministic Season Scenario recommendations from historical baseline, activity trends, availability, events, athlete profile, and KPI context; the Season page now surfaces the recommendation and warns when a saved selection references an older scenario set.
- Added read-only deterministic season contract tools for CrewAI (`workspace_get_phase_slot_contract`, `workspace_get_season_phase_load_context`) so season tasks can consume code-owned phase-slot and phase-load authority without searching for synthetic artifacts.
- Added read-only deterministic phase/week contract tools for CrewAI (`workspace_get_phase_execution_context`, `workspace_get_week_calendar_context`) so phase and week finalizers can consume active execution authority directly.
- Added review-layer deterministic contract wiring so season, phase, and week review tasks can consume bound contract authority directly.
- Added explicit narrow tool scopes for planning/report context-read tasks and deterministic contract-review tasks, reducing broad workspace rediscovery.
- Added compact task-execution telemetry fields for assigned agent and actual model, so `events.jsonl` and `rps.log` can explain provider usage without dumping prompt bodies.
- Added a central CrewAI knowledge-search guard that compacts and hard-caps remaining search queries before embedding/search calls.
- Added a compact internal planning specialist task wrapper that spells out `payload_json`, tool-first retrieval, and a one-shot blocked-answer format.
- Added authoritative-runtime block preservation for internal specialist prompts, so snapshot, resolved-context, and deterministic-contract markdown blocks survive compacted task injection intact.
- Added short tool-usage guidance on bounded season planning tasks and season skills, clarifying when to use `workspace_get_input`, `workspace_get_latest`, and `workspace_get_version`.
- Added matching tool-usage guidance plus direct task tool scopes for bounded phase and week planning specialists, so task instructions now match the workspace/contract tools actually available at execution time.

### Fixed
- Fixed contract-valid but overly monotonous shortened re-entry weeks: the week engine now avoids duplicate quality protocol variants when possible, dampens a repeated second `TEMPO_CLASSIC` quality day instead of repeating the same upper-tempo dose unchanged, and emits warnings when `PHASE_PREVIEW` or `PHASE_STRUCTURE` disagree with the generated week shape.
- Fixed week workout progression from being only loosely heuristic: classic intervals now progress by documented order (`4x10 -> 4x12 -> 4x15 -> 5x12`), VO2 microbursts progress by reps before sets using on-time semantics, K3 and durability finish sessions respect explicit caps, and prior planned week state is reused under a stricter documented contract.
- Fixed week protocol selection so true quality cost is enforced across the whole week: `K3`, tempo, Sweet Spot, threshold, VO2, and late-finish durability protocols now consume quality budget, preventing a third hidden quality stimulus from slipping into endurance days when the weekly cap is already full.
- Fixed Week runtime dependence on CrewAI synthesis for main planning and scoped week replan/preview paths: `CREATE_WEEK_PLAN` now runs through the deterministic Week engine, bounded recompute shares the same family policy and rendering path, and generated weeks no longer depend on late Week Crew review loops to reach a valid artifact.
- Fixed recurring `WEEK_PLAN` failures caused by free-text workout authoring drift: week artifact creation now deterministically renders canonical workout text for supported planning families, preview text edits are canonicalized before persistence, and semantic checks compare parsed/generated structure instead of title/notes keyword heuristics.
- Fixed recoverable `WEEK_PLAN` writer failures caused by inline loop-step shorthand like `- 3x 12m ...`; week-plan normalization now rewrites that form into the project-valid standalone `3x` loop header plus step line before writer guardrails run.
- Fixed the active week workout runtime source split by tightening the authoring/review/writer skills and prompt around the strict project Intervals subset, explicit `PHASE_GUARDRAILS` legality precedence, and the rule that recovery-like low-load work must be authored as legal low-end `ENDURANCE` when `RECOVERY` is forbidden upstream.
- Fixed bounded week replans so later planning rounds no longer receive the full prior review-decision payload with stale blockers and warnings; the runtime now forwards only sanitized active replan instructions, preventing contradictory week-bundle narratives from exhausting replan rounds after the actionable load fix was already applied.
- Fixed `PHASE_PREVIEW` persistence after the `PHASE_STRUCTURE` S5-context repair by adding deterministic preview normalization against stored structure authority: exact `phase_structure_<version>.json` traceability is now injected at store time, fixed rest days are pinned back to `NONE`/`NONE`, excess `QUALITY` labels are downgraded before validation, and `PHASE_STRUCTURE` operational intensity domains now include required `NONE` / `RECOVERY` semantics when the allowed day roles require them.
- Fixed silent `PHASE_STRUCTURE` S5-context loss in guarded-store validation by removing the invalid `planning_events_payload` load-capacity kwarg, tightening the deterministic load-capacity wrapper signature, and logging phase-scoped builder failures instead of swallowing them into an empty context.
- Fixed `PHASE_STRUCTURE` store-time S5 validation by rebuilding phase-scoped load-capacity context with the active phase range, week roles, phase role, season plan, and scenario cadence before guarded-store contract checks.
- Fixed `PHASE_STRUCTURE` persistence after successful phase guardrails writes by deterministically projecting required season constraints into `upstream_intent.constraints` and rewriting `load_ranges.source` / `weekly_kj_bands` from the stored exact-range `PHASE_GUARDRAILS`.
- Fixed `PHASE_GUARDRAILS` persistence after successful phase runs by deterministically projecting required `SEASON_PLAN.global_constraints` into the normalized guardrails payload before guarded-store validation; missing availability assumptions, risk constraints, recovery notes, and planned event windows are now repaired in code instead of failing at store time.
- Fixed deterministic S5 fallback behavior for recovery-sensitive phase/week semantics so shortened re-entry / reset weeks no longer drop their role-aware progression reduction when KPI lower bounds conflict; reset-like weeks now retain material load reduction through a code-owned `phase_intent` + `week_role` fallback policy.
- Fixed `season_scenarios` runtime alignment by making the Scenario-C `VO2MAX` guardrail read `kpi_guardrail_notes` in addition to `decision_notes` / `constraint_summary`, and narrowed the task tool scope to `workspace_get_input` plus `workspace_get_latest` instead of the full read-only workspace bundle.
- Fixed the `season_scenarios` task/skill guidance for Scenario C so `VO2MAX` is only allowed when `decision_notes` or `kpi_guardrail_notes` explicitly explain its sparse ceiling-support / fresh high-intensity role; otherwise the model is instructed to omit `VO2MAX`.
- Fixed `PHASE_PREVIEW` guarded-store validation so agenda previews must stay derived from the stored `PHASE_STRUCTURE`: preview weeks now match phase coverage, agenda roles/domains/modalities stay inside structure authority, fixed non-training days remain non-training, and preview quality-day counts cannot exceed the structure cap.
- Fixed deterministic season load-capacity inference so representative `typical` capacity no longer comes from the hardest allowed intensity-domain ceiling; inferred season baselines and downstream build corridors are now anchored to a more plausible endurance-led weekly load assumption.
- Fixed Season Plan rendering/guidance to label phase and envelope load corridors as governance load kJ rather than plain weekly kJ, reducing confusion with mechanical work estimates.
- Fixed Plan Hub per-run log files to record `INFO` and above only, so readiness polling debug lines and harmless CrewAI/LanceDB debug traces no longer flood user-facing planning logs.
- Fixed the Season page `Season Scenarios` list view so the new scenario UX differentiation fields render in the main scenario overview, not only in the selected-scenario detail block.
- Fixed the season-plan guarded-store selected-scenario contract path to use the correct `season_scenarios_payload` call shape and to keep phase-level domain narrowing from back-propagating into season-level authority.
- Fixed CrewAI outer-flow state handling by declaring `workspace_root` on typed Season/Phase/Week/Report/Feed-Forward/Coach flow states, so run-store telemetry and exception reporting no longer fail on Pydantic state assignment.
- Fixed CrewAI flow-state persistence by storing `workspace_root` as a JSON-serializable string in typed flow state and converting back to `Path` only at runtime-event/exception boundaries.
- Fixed planning-crew cost concentration by switching Season, Phase, and Week planning crews from manager-driven hierarchical execution to explicit sequential specialist execution, leaving manager agents only on final synthesis tasks.
- Fixed planning knowledge oversubscription by removing static knowledge bundles from deterministic Season/Phase/Week planning specialists that already rely on contracts, snapshots, and workspace tools.
- Fixed internal planning specialist prompt bloat by replacing the full shared system wrapper with a compact agent-specific prompt plus tailored binding rules and compacted task context.
- Fixed bounded season specialists so event-priority and peak-window tasks can read workspace context directly, and disabled reasoning/replan loops for bounded season specialists and auditors that should act as deterministic tool-bound workers.
- Fixed macrocycle specialist runtime semantics by treating `season_macrocycle_draft` as a response-only internal draft step, adding bounded read tools for event/snapshot/phase-slot context, and disabling reasoning-agent observer behavior on `macrocycle_architect`.
- Fixed season review authority handling by treating the injected Candidate Season Bundle as the review subject, running the season review crew in sequential specialist mode, and disabling reasoning-agent observer behavior on `season_review_manager` so review no longer blocks on synthetic `candidate_season_bundle` retrieval.
- Fixed phase and week review runtime semantics by disabling reasoning-agent observer behavior on `phase_review_manager` and `week_review_manager`, aligning them with the sequential specialist review path already used in the shared review runner.
- Fixed phase and week review authority handling by treating the injected Candidate Phase/Week Bundles as the review subjects, removing season-specific review-subject injection from the shared review runner, and disabling native reasoning-agent observer behavior on bounded phase/week specialists and auditors.
- Fixed season manager contract consumption so season planning tasks receive structured deterministic season phase-slot/load JSON context and the finalizer is scoped to contract tools instead of broad workspace rediscovery.
- Fixed season finalization re-dispatching deterministic contract lookup through coworker delegation by disabling free delegation for `season_plan_manager` and tightening the final-synthesis guidance.
- Fixed phase/week finalization rediscovery risk by binding deterministic execution contracts into finalizer task context, scoping finalizers to contract tools, and disabling free delegation for `phase_bundle_manager` and `week_plan_manager`.
- Fixed review-manager rediscovery risk by binding deterministic contract JSON into season/phase/week review task context, scoping review final tasks to contract tools, and disabling free delegation for `season_review_manager`, `phase_review_manager`, and `week_review_manager`.
- Fixed remaining broad-rediscovery risk in planning support paths by narrowing `*_context_read` / `*_contract_review` tool surfaces and disabling free delegation for feed-forward and report-review managers.
- Fixed CrewAI model routing so role-specific runtime profiles win over generic app-level model defaults; the non-Groq app fallback now uses `gpt-5.4-mini`, and CrewAI runtime profiles now allow only the GPT-5.4 family.
- Fixed planning run failure reporting so `events.jsonl` captures structured LLM/provider root causes and Plan Hub step/run failures prefer those root causes over secondary shutdown errors.
- Fixed Intervals historical baseline validation by making artifact metadata canonicalization respect closed `meta` schemas instead of adding planning-only ISO/trace fields to schema-strict data-pipeline artifacts.
- Fixed planning CrewAI runs repeatedly calling failing native memory tools by disabling native CrewAI memory for planning/review/writer crews; code-owned snapshot artefacts remain the authoritative planning memory path.

## [0.14.0] - 2026-05-19

### Added
- Added code-owned deterministic planning-contract validators for Season, Phase, Week, writer-blueprint, and snapshot-freshness checks, with guardrail/runtime/store integration for Scenario-inherited structure, phase load context, active weekly bands, and non-binding memory boundaries.
- Added shared CrewAI skills for contract-context consumption, blueprint validation, blueprint-bound writing, and snapshot-memory consumption.

### Changed
- Season Plan generation now carries selected-scenario cadence semantics through deterministic phase slots, internal phase blueprints, and stricter Season skill/review guidance so plans inherit Scenario structure instead of reselecting cadence.
- Persisted artifact metadata is now code-owned: the runtime/workspace layer canonicalizes schema-critical `meta` fields before validation and save, while writer tasks focus on artifact data and non-authoritative trace intent.
- Trace references now distinguish semantic `schema_version` from operational workspace `version_key`; bundled schemas and schema-backed CrewAI artifact models were regenerated.
- Removed the local vectorstore/Qdrant runtime path entirely: startup sync, Plan Hub knowledge-store readiness, `knowledge_search`, vectorstore scripts/tests/modules, vectorstore manifest/config, and Qdrant dependency are gone; static knowledge now routes through CrewAI knowledge sources only.
- Collapsed the split endurance intensity domains into a single `ENDURANCE` enum across schemas, skills, specs, prompts, and tests; deterministic load estimation now uses the former high-endurance default (`0.70`) for `ENDURANCE`.
- Persisted CrewAI artifact schemas now use the dedicated writer-owner identities (`Season-Artifact-Writer`, `Phase-Artifact-Writer`, `Week-Artifact-Writer`, `Report-Artifact-Writer`) and bundled schemas were regenerated.
- Season and Phase planning crews no longer enable CrewAI-native pre-planning by default, avoiding the extra `Task Execution Planner` pass when RPS already supplies an explicit YAML task chain.
- Application logs now suppress high-volume HTTP, OpenAI usage, OpenAI tool-validation, callback, and tool lifecycle noise by default while keeping flow, crew, task, and guardrail progress visible.
- Knowledge store sync now logs manifest, source path, tags, chunk counts, collection, and completion summaries instead of relying on embedding HTTP transport lines for observability.
- CrewAI runtime progress is now mirrored into the main application log with compact flow, crew, task, agent, tool, output-format, and run identifiers so long-running planning runs are easier to inspect live.
- Reworded configured CrewAI skills toward positive operating guidance and added validation that flags explicit don't/never/no-style rules.
- Added CrewAI skill package validation for configured skills, including local-reference hard checks plus strict-ready checks for positive action guidance and explicit output/answer format.
- CrewAI task execution now uses task-scoped tools from `tasks.yaml`, task-level callbacks, and richer Flow failure state handling for rejected, missing-upstream, or store-failed paths.
- CrewAI runtime now supports native agent and crew config passthrough, explicit task `context:` dependencies, task callbacks, guardrail-failure telemetry, richer typed Flow state, and read-only writer memory.
- Schema bundling now regenerates schema-backed CrewAI artifact output models so persisted artifact tasks can use concrete JSON-Schema-derived structured output contracts.
- Persisted CrewAI artifact tasks now run an explicit `artifact_schema_valid` function guardrail before persistence, giving full JSON-Schema failures CrewAI's documented guardrail retry path.
- CrewAI runtime now relies on native `skills=[...]` activation only and no longer manually appends rendered `SKILL.md` bodies into goals, backstories, or task descriptions.
- Coach recommendation answers now use compact answer discipline for simple why-questions and avoid unsupported load arithmetic, IF targets, thresholds, citations, or checklist expansion.
- Coach finalization now detects task-runner reply markers such as `DONE`, `READY`, and `OUTPUT` and repairs the answer once into a conversational Coach response.
- Coach recommendation and finalization prompts now define the desired positive cycling-coach voice directly instead of relying mainly on negative style constraints.

### Fixed
- Fixed contract-aware Plan Week phase reruns so deterministic scenario phase slots are anchored to the active phase range start, and updated Plan page smoke tests to use valid Scenario/Phase/Week contract fixtures.
- Fixed repeated artifact persistence failures caused by agent-invented `schema_id`, `owner_agent`, or operational trace version strings by canonicalizing envelopes in `GuardedValidatedStore` and legacy read normalization.
- Fixed Season Plan persistence after writer-crew execution by aligning schema owner constants with the new writer-agent ownership model.
- Fixed CrewAI progress visibility by emitting planned task/agent rows before each Crew kickoff, so long runs show the upcoming task chain immediately.
- Fixed CrewAI runtime labels so event logs prefer RPS task, crew, and agent names instead of generic CrewAI labels like `Task` or `crew`.
- Fixed explicit `artifact_schema_valid` guardrail validation so schema-sensitive metadata constants and trace-reference versions are normalized before canonical JSON-Schema validation.
- Fixed schema-backed CrewAI artifact validation so operational trace reference version keys are normalized before canonical JSON-Schema validation, preventing Season Plan failures on `meta.trace_*[].version`.
- Fixed CrewAI structured-output hardening across internal output models by closing Pydantic schemas, replacing open internal draft maps with typed statement lists, and adding a registry-wide strict-schema regression test.
- Fixed Season Plan CrewAI structured-output startup by making `PlanningDraftModel` OpenAI strict-schema compatible.
- Fixed CrewAI task guardrail wrapper compatibility by removing alias-based return annotations that CrewAI's Task validation rejects.
- Fixed workspace persistence so operational `version_key` stays in the index/log and loaded runtime metadata, without being written into schema-strict artifact envelopes.
- Fixed Season Scenario persistence after CrewAI runs by normalizing schema-sensitive agent output fields such as meta version/scope, trace references, scalar/list notes, and `key_differences` before guarded-store validation.
- Fixed non-self-contained skill reference paths by copying referenced material into local skill `references/` directories and adding validation for local references.

## [0.13.0] - 2026-05-17

### Added
- Added Coach evidence-source guidance for durability explanations, including a copied durability bibliography under shared durability skill references plus preferred authors/domains for source-backed and web-verified rationale.
- Added deterministic load-band helpers for availability capacity, IF reference resolution, progression overlays, and S5 phase-band derivation under `src/rps/planning/load_bands.py`.
- Added deterministic workout-load estimation under `src/rps/planning/workout_load.py`, including workout-text segment parsing, loop handling, IF-direct fallback, week-plan load auditing, and injectable per-domain hourly calibration.
- Added a context-aware Week daily availability validator and CrewAI guardrail so `week_plan` outputs cannot place workouts on fixed-rest days or exceed explicit `availability_table.hours_max`.
- Added deterministic load-capacity context injection for Season, Phase, and Week planning prompts, plus a migration audit document for the CrewAI hardening pass.
- Added a deterministic planning context registry under `src/rps/planning/deterministic_context.py`, including Season cadence options, Season phase-slot skeletons, Phase execution context, Week calendar/availability context, DES report evidence context, and Coach operation boundaries.
- Added selected-scenario structure context injection for Season planning, carrying cadence-derived phase length, expected full phases, shortened phases, and planning-horizon consistency.
- Added deterministic last-event horizon context injection for Season Scenario generation, carrying last event date/week, weeks until event, inclusive planning horizon, and season ISO-week range.
- Added `config/crewai/runtime_profiles.yaml` plus runtime wiring for explicit CrewAI planning, agent reasoning, and per-role model routing defaults across planning, review, writer, and conversational crews.
- Added a strict single-method skill attachment model for CrewAI agents, dedicated per-role skill packages for managers/reviewers/week syntax handling, and richer skill reference content derived from the planning specs and policies.
- Expanded `doc/architecture/agents.md` into a third-party readable system map with crew-stage, agent-task-goal-skill, and shared knowledge tables across Season, Phase, Week, Report, and Coach paths.

### Changed
- Scenario Selection now uses a dedicated CrewAI task blueprint and shape guardrail instead of reusing the scenario-generation task route.
- Season, Phase, and Week skills now treat load capacity/S5 values as code-owned inputs and preserve the schema-valid `Base | Build | Peak | Transition` cycle set.
- Progressive-overload migration was tightened: Season, Phase, and Week skills now include the concrete baseline, ramp, cadence-specific build/deload/re-entry, mini-reset, and baseline-update rules from `ProgressiveOverloadPolicy`.
- Durability-first principles migration was tightened: active shared/season/phase/week skills now carry the binding boundary, kJ-first steering hierarchy, event-state labels, specificity/taper cycle translation, Kinzlbauer-like season archetype, intensity-distribution decision rules, preload semantics, masters/recovery handling, and non-compensation guardrails.
- LoadEstimationSpec migration was tightened: active load skills and references now carry exact terminology for `planned_kj` versus `planned_weekly_load_kj`, IF-direct fallback limits, output rounding, required trace identifiers, KPI/body-mass gating, S5 fallback/STOP semantics, and Week corridor mirror rules.
- Season Scenario, Season Plan, Phase, Week, Report, and Coach prompts now receive more precomputed runtime facts so agents apply deterministic context instead of recomputing dates, ranges, phase counts, week matrices, or operation boundaries.
- Validated the prose-to-skill migration file-by-file, added `doc/architecture/skills_source_migration_audit.md`, and marked the migrated planning prose sources under `specs/knowledge/_shared/sources/` as `Superseded` so they no longer compete as canonical runtime planning sources.
- CrewAI backend and conversational Coach/Workout Editor builders now apply repo-owned planning/reasoning/model policy directly to `Crew(...)` and `Agent(...)`, while still allowing environment overrides for crew planning and per-agent provider settings.
- CrewAI skill resolution now enforces one method skill per agent plus operational crew-level skills only, while the runtime skill prompt block remains `SKILL.md`-only and the operative planning logic has been moved out of thin references into the skill bodies themselves.

### Fixed
- Fixed Scenario Selection task routing ambiguity and added guardrails for Phase S5 band matching, exact Phase week coverage, Week corridor/recovery/export checks, Season cadence/cycle checks, and diagnostic-only DES reports.
- Fixed deterministic load-capacity context so negative availability and missing allowed domains remain visible STOP/warning states instead of being silently clamped or defaulted, selected KPI moving-time-rate guidance is forwarded into Phase/Week S5 mapping when present, complete `availability_table` rows can drive week-specific S5 hours, and KPI profile bands are available for deterministic S5 escalation.

## [0.12.0] - 2026-05-14

### Added
- Added a skills-first multi-crew planning runtime foundation: Season, Phase, Week, and Report task graphs now have explicit planning/review/writer task families in `config/crewai/tasks.yaml`, plus typed bundle/review/replan models in `src/rps/crewai_runtime/models.py`.
- Added canonical skill reference material for durability, load estimation, progression, cadence/re-entry, workout authoring, and DES diagnostics under `skills/**/references/`, so planning methodology now lives with the activated skills instead of legacy prose-only specs.
- Added a skills-first unified CrewAI planning layer under `skills/` plus `config/crewai/skills.yaml`, so Coach, Workout Editor, and planning flows now share explicit week/phase/season methodology bundles instead of runtime markdown injection.
- Added shared week-domain specialist prompts (`week_context_specialist`, `week_recommendation_specialist`, `week_revision_specialist`) and dedicated writer prompts (`season_artifact_writer`, `phase_artifact_writer`, `week_artifact_writer`, `report_artifact_writer`) for persisted artifact ownership.
- Added decomposed load-estimation source docs (`load_estimation_core.md`, `load_estimation_season.md`, `load_estimation_phase.md`, `load_estimation_week.md`) and removed runtime chapter slicing as a knowledge-delivery mechanism.

### Changed
- CrewAI backend season/week/report execution now runs through explicit planning -> review -> writer cycles with bounded replan handling, and phase artifact execution now writes approved artifacts from the same multi-crew pattern instead of a single bundle-only manager path.
- CrewAI config now uses finer-grained week/season/phase/review specialist names and scoped memory/knowledge profiles that match those new task families.
- Recut CrewAI agent/task config to shared specialist names and writer-agent ownership, splitting `season_planner_manager` into `season_plan_manager` / `season_feed_forward_manager` and `phase_architect_manager` into `phase_bundle_manager` / `phase_feed_forward_manager`.
- Replaced the old prompt-injection runtime path with skill resolution helpers in `src/rps/crewai_runtime/skills.py`; `config/agent_knowledge_injection.yaml` and `src/rps/agents/knowledge_injection.py` are removed from runtime use.
- Persisted artifact tasks now default to `output_json` plus envelope guardrails instead of prompt-only mandatory-output guidance.

### Removed
- Removed the YAML-backed `agent_knowledge_injection` runtime path and its `load_estimation_spec.md` heading-slicing logic.

- Added separate CrewAI policy/config layers for flow persistence, memory scopes, static knowledge sources, and task guardrail/output-mode policy under `config/crewai/`, plus new runtime helpers in `src/rps/crewai_runtime/` for guardrail resolution, knowledge-source mapping, and memory-profile wiring.
- Added a contract-only injection path via `build_contract_injection_block(...)`, so CrewAI runtime construction can keep explicit operational/contracts in prompts while static reference material moves into separate knowledge-source config.
- Added CrewAI runbooks for flow persistence, memory policy, static knowledge, and prompt/guardrail debugging under `doc/runbooks/`.
- Added a canonical CrewAI flow catalog in `doc/architecture/crewai_flows.md`, documenting outer flow entrypoints, Season/Phase/Week planning flows, specialist crews, per-surface toolsets, inputs, outputs, and runtime diagrams for planning, advisory, Coach, and Workout Editor paths.
- Added a shared manager-plus-specialist conversational CrewAI runtime for `Coach` and `Workout Editor`, with agent-specific knowledge injection, strict per-specialist tool visibility, and page-level bridge heuristics removed from Coach.
- Added an active Coach operation layer on top of the existing runtime: Coach can now inspect selected-week plan context, preview/apply bounded `WEEK_PLAN` edits, preview/apply scoped week replans, and trigger DES report / feed-forward runs through explicit operation tools with mandatory preview + confirm semantics.
- Added initial CrewAI foundation files under `config/crewai/` and `src/rps/crewai_runtime/`, including YAML agent/task definitions, typed operation result models, and a runtime compatibility helper that reports the current Python `3.14` blocker for full CrewAI activation.
- Added a CrewAI-only agent runtime gateway under `src/rps/agents/runtime.py`, so planner/advisory flows now route through one cutover point without any legacy backend fallback.
- Added a direct CrewAI provider-config resolver plus a dedicated CrewAI one-turn chat runner for the Coach page, so conversational Coach turns no longer depend on `rps_chatbot` or the legacy LiteLLM client object.
- Added internal CrewAI foundation models and YAML task/agent roles for Season and Phase specialist execution, including season audit/macrocycle drafts and an internal `PhaseBundle` vocabulary for future hierarchical Crew execution.
- Added live hierarchical Season/Phase execution on top of that foundation: `SEASON_PLAN` now runs specialist subtasks before manager finalization, and phase artefacts now run specialist subtasks plus an internal `PhaseBundle` manager step before the requested public phase artefact is persisted.
- Added dedicated prompt slices for Season and Phase specialist roles, so internal CrewAI specialists no longer reuse the top-level `season_planner` / `phase_architect` prompts.
- Added CrewAI Flow wrappers for outer Season and Phase orchestration under `src/rps/crewai_runtime/flows.py`.
- Added CrewAI Flow wrappers for outer Week, Report, and Feed-Forward orchestration, bringing the remaining planning/advisory chains onto the same Flow wrapper pattern.
- Added a Coach Flow router on top of the CrewAI turn runner, so explicit confirm/discard/pending-status messages now run through dedicated Flow routes instead of only page-local branching.
- Added additive `FLOW_*`, `CREW_*`, and direct `ARTEFACT_WRITTEN` runtime telemetry for direct CrewAI runs, with shared UI rendering on Plan Hub, System Status, and System History.
- Added a central CrewAI `BaseEventListener` adapter with run-context propagation, so Flow/Crew/Task/Tool lifecycle telemetry now comes from CrewAI's native event bus instead of predominantly manual emission.
- Added compact CrewAI runtime label normalization for `CREW_*`, `CREW_TASK_*`, and `TOOL_*` telemetry, preventing prompt-sized task payloads and generic `crew` labels from polluting `events.jsonl` and UI history.
- Added richer Coach-preferred advisory memory with a concrete `Current Week Plan Snapshot`, plus a one-time deterministic startup summary in the Coach chat for each fresh athlete/week context.
- Added a dedicated `CURRENT_WEEK_STATUS_SNAPSHOT` artefact under `data/context/`, so Coach now consumes persisted current-week actuals and deterministic plan-vs-actual status from snapshot memory instead of reading current-week raw actuals directly.
- Added explicit Coach prompt/runtime guidance to suppress repeated athlete-context boilerplate on normal follow-up turns once a startup context summary was already shown.
- Added explicit Coach language alignment and a deterministic scoped-preview fallback, so broad week-adjustment requests and follow-up `preview erstellen` turns can create `preview_scoped_week_replan` without relying on low-level workout-edit parameters.

### Changed
- CrewAI outer flow state models now carry richer typed state and compat-safe persist-policy decoration for Season, Phase, Week, Report, and Feed-Forward flows.
- CrewAI backend and conversational coach runtime now resolve task execution policy (`output_pydantic` / `output_json` / prompt-only), function guardrails, shared memory, scoped agent memory, and static knowledge profiles from explicit config instead of assuming broad prompt injection everywhere.
- Coach and Workout Editor chats now route through the same small-sliced conversational runtime: a thin manager classifies the turn, narrow specialists own context/advice/preview/pending work, and the outer Coach flow is telemetry-only instead of phrase-routing preview/apply semantics.
- Coach prompt and UI semantics are no longer read-only; the page now acts as an active planning surface while keeping all persisted writes behind existing guarded store and deterministic orchestration helpers.
- Advisory report/feed-forward execution now has reusable orchestrator helpers instead of only page-local wiring, so the same actions can be invoked from the active Coach surface.
- Scoped Coach week replans now generate a true preview-only `WEEK_PLAN` candidate with before/after metadata and JSON diff, and applying that pending preview persists the previewed document directly instead of re-running the planner.
- All planner/advisory orchestrators and shared UI runtime helpers now import the unified runtime gateway, and Coach shows the effective CrewAI runtime state directly.
- Coach page now renders its own Streamlit chat transcript and executes conversational turns through CrewAI-native `Agent`/`Task`/`Crew` objects, while the CrewAI persisted-artefact backend resolves provider settings directly from `RPS_LLM_*` env vars instead of reading `LiteLLMClient.config`.
- Responsibility boundaries are now aligned across CrewAI config, runtime normalization, and architecture docs: `Season-Planner` is the binding owner of `SEASON_PLAN` and `SEASON_PHASE_FEED_FORWARD`, `Phase-Architect` owns phase artefacts and `PHASE_FEED_FORWARD`, `Performance-Analyst` is diagnostic-only, and phase cadence is explicitly an application of season authority rather than a phase-selected default.
- Season entrypoints now route through CrewAI Flow-backed outer orchestration, and scoped `Run Phase` execution now computes one internal `PhaseBundle` and persists the requested public phase artefacts from that single grouped run instead of re-running the internal specialist chain per artefact.
- Season and Phase specialist execution now runs as one real hierarchical CrewAI crew per run instead of serial one-task crews, while Week revision, DES report generation, and feed-forward chaining now route through CrewAI Flow wrappers.
- Coach turns now create foreground run-store records and reuse the same run id for nested apply operations, so Coach-triggered flow, crew, and persisted artefact events stay traceable in one run timeline.
- Direct runtime telemetry now relies on CrewAI listener events for lifecycle coverage, while `ARTEFACT_WRITTEN` remains an explicit RPS-owned persistence-boundary event.
- Coach-applied week-plan edits and scoped replans now refresh `ADVISORY_MEMORY`, so the central memory stays aligned with the latest selected-week artefacts.
- Coach startup summaries now include dedicated `Current Week Actuals` and `Plan vs Actual` sections derived from `CURRENT_WEEK_STATUS_SNAPSHOT`, while `PLANNING_CONTEXT_SNAPSHOT` keeps the stable historical reference-week activity context unchanged.
- Coach startup summaries now omit the dedicated `Pending Status` section when no pending operation exists, reducing repeated no-op boilerplate on page open.
- Coach turn instructions now explicitly reply in the language of the current user message, and the Coach page can create a scoped week-replan preview directly before any model turn when the user asks for a broad weekly adjustment.

### Removed
- Removed the remaining LiteLLM-era runtime stack: `rps.openai.litellm_runtime`, `rps.openai.client`, `rps.openai.streaming`, `rps.openai.response_utils`, `rps.openai.runtime`, `rps.agents.runner`, `rps.agents.runner_strict`, `rps.agents.multi_output_runner`, and `rps.ui.rps_chatbot`.

### Changed
- Workout Editor chat on Plan → Workouts now uses the same CrewAI-native turn runner pattern as Coach instead of the legacy `rps_chatbot` transport, while preserving preview-before-apply semantics.
- Shared planner normalization helpers now live in `rps.agents.output_normalization`, so persisted CrewAI tasks no longer import legacy runner code just to recover schema/artefact invariants.
- Embedded Qdrant embeddings now use direct OpenAI client calls instead of `litellm.embedding(...)`, and dependency manifests no longer include `litellm`.

## [0.11.1] - 2026-05-12

### Added
- Added the previously missing bundled schema snapshots for `advisory_memory`, `athlete_state_snapshot`, and `planning_context_snapshot` under `specs/knowledge/_shared/sources/schemas/bundled/`, aligning the committed bundle set with the source schemas and workspace schema map.

### Changed
- Bumped the application version from `0.11.0` to `0.11.1`.

### Fixed
- Z2 metric semantics are now aligned across the Intervals pipeline, activity artefacts, trend artefacts, and report/planner consumers: fields named `Z2 Share` now mean pure `Power TiZ Z2 / sum(Power TiZ Z1..Z7)`, while `Z1 + Z2` remains a separate low-intensity metric; the activity-level `Power TiZ Share Z2 (%)` bug and derived `Flag Z2 Share >= 60%/70%` logic were corrected accordingly.
- Analyse → Report no longer renders the active `Creating performance report...` message twice in the same rerun; the job message now comes from a single shared render block and is covered by an AppTest regression.

### Changed
- `workspace_get_input` now canonicalizes JSON input envelopes through the same legacy-meta normalization used for regular workspace artefacts, so old inputs such as `LOGISTICS` with `meta.data_confidence: "USER"` no longer reach agents as invalid raw payloads in performance/feed-forward runs.
- Plan → Workouts now includes a bounded `Workout Editor` chat for the selected ISO week: users can preview moving a workout to an empty day, changing a start time, or replacing workout text, then explicitly apply the pending edit through the guarded `WEEK_PLAN` store and deterministic `INTERVALS_WORKOUTS` rebuild; `Coach` remains read-only.
- Bumped the application version to `0.11.0` for the snapshot-memory architecture expansion: Feed Forward now uses snapshot-first injection, Coach prefers central memory over raw artefact preload when available, and a new derived `ADVISORY_MEMORY` artefact tracks non-binding narrative context from recent planning/advisory outputs.
- Planner orchestration now persists code-owned derived memory snapshots (`ATHLETE_STATE_SNAPSHOT`, `PLANNING_CONTEXT_SNAPSHOT`) under `data/context/` and injects these snapshot files as the primary runtime memory for season/phase/week planning, while authoritative source artefacts remain unchanged.
- Plan Hub now prunes redundant `WORKOUT_EXPORT` steps whenever the same run already queues `WEEK_PLAN`, preventing duplicate `INTERVALS_WORKOUTS` writes for scoped week/full-chain runs while preserving standalone workout-export runs when a week plan is already ready.
- `WEEK_PLAN` normalization now rewrites malformed percent ranges like `68-72%` to the project-required `68%-72%` inside workout step lines before guarded validation, and the `week_planner` prompt now states this range rule explicitly alongside valid hour-duration examples.
- Feed Forward runs now inject resolved selected-week DES evaluation context and selected-week Season→Phase feed-forward context directly from workspace artefacts, and the `season_planner` / `phase_architect` prompts now bind explicit Mode C `workspace_get_version(...)` reads for `DES_ANALYSIS_REPORT` and feed-forward context where required.
- `SEASON_SCENARIOS` now normalizes its planning horizon deterministically from the last A/B/C `PLANNING_EVENTS` date before store, rewriting `meta.iso_week_range`, `meta.temporal_scope`, and `data.planning_horizon_weeks` so season replanning no longer truncates at a stale pre-September horizon when newer events exist.
- Season-scenario planning math is now code-normalized from the authoritative horizon and each scenario's `phase_length_weeks`: `phase_count_expected`, `shortening_budget_weeks`, and `phase_plan_summary` no longer rely on model arithmetic, and the `season_scenario` prompt/injection set was simplified accordingly.
- Season-scenario `intensity_guidance` is now normalized to the canonical agenda intensity domains; invalid proxy labels are dropped, legacy split endurance labels are normalized to `ENDURANCE`, and the season-scenarios schema now uses the same intensity-domain enum contract as season/phase artefacts.
- Season-scenario phase-summary normalization now avoids degenerate 1-week shortened phases by distributing shortening across up to two shortened phases with a minimum shortened-phase length of 2 weeks.
- Season-scenario normalization now also rejects `NONE`/`RECOVERY` in `avoid_domains`, sets `max_shortened_phases = 0` when no shortening budget exists, and normalizes `trace_data` / `trace_events` into consistent data-vs-event buckets before store.
- Week-scoped artefacts such as `SEASON_SCENARIOS` now ignore stale timestamp suffixes in `meta.version_key` and derive fresh store keys from `meta.iso_week` plus canonicalized `created_at`, preventing new runs from overwriting older timestamped season-scenario files.
- Workspace version resolution for partitioned weekly pipeline artefacts now follows the actual `data/YYYY/WW/*.json` layout for `ACTIVITIES_ACTUAL`, `ACTIVITIES_TREND`, and `WELLNESS`, so phase planning can resolve explicit historical week versions from the Docker-mounted runtime tree instead of looking under the legacy `data/analysis/` path.
- Guarded-store phase validation now parses both compact `YYYY-MM-DD (A|B|C)` markers and free-text season-plan `planned_event_windows` such as `YYYY-MM-DD B event rehearsal window`, preventing semantically correct `PHASE_GUARDRAILS` / `PHASE_STRUCTURE` outputs from stopping on raw-string mismatch while leaving `PHASE_PREVIEW` on its existing traceability-only check.
- Guarded-store `PHASE_STRUCTURE` validation now also accepts season recovery notes when the phase output preserves them in a single combined constraint string rather than one list item per note, preventing another false stop after `PHASE_GUARDRAILS` succeeds.
- `WEEK_PLAN` writes are now guarded by the same deterministic workout exportability checks used by the local workout exporter, so invalid workout text like malformed step lines is rejected at `store_week_plan` time instead of producing a saved plan that only fails during `INTERVALS_WORKOUTS` generation.
- Week planning now injects the latest historical `ACTIVITIES_ACTUAL` / `ACTIVITIES_TREND` versions into the `week_planner` just like phase planning does, and `plan_week(...)` skips the local workout export whenever the current run failed to produce a fresh `WEEK_PLAN`, preventing stale-plan exports after a week-planner STOP.
- The `week_planner` prompt now states the EBNF loop-header rule explicitly: loop counts like `3x` are standalone loop headers and MUST NOT be emitted as step lines such as `- 3x`, reducing malformed workout text from the source.
- Week planning now resolves the latest `WELLNESS.data.body_mass_kg` and injects it explicitly into the `week_planner` when KPI gating is active, reinforcing the contract that `WELLNESS` is the authoritative body-mass source for kJ/kg/h gating and preventing false STOPs when body mass is already present.
- Planner orchestrators now resolve KPI context in code from `KPI_PROFILE` plus `SEASON_SCENARIO_SELECTION` and inject the selected `w_per_kg` / `kj_per_kg_per_hour` ranges and available profile bands directly, reducing needless agent search/reconstruction of deterministic KPI values.
- Planner orchestrators now also inject resolved availability summaries, target-week/phase-range planning-event facts, and explicit phase identity/range facts, further shifting deterministic workspace interpretation out of the agents and into code.
- Planner prompts now explicitly honor `Resolved ... Context` blocks as authoritative, and planner orchestration additionally injects resolved zone-model and logistics facts so agents do less raw artefact searching for already-known values.
- `ATHLETE_PROFILE` is now injected as a `Resolved Athlete Context` block, and `season_scenario` now follows the same resolved-context architecture as the planner agents instead of relying only on raw artefact/tool interpretation.
- Planner prompts now distinguish between already-resolved deterministic facts and still-required unresolved/exact-range reads, reducing redundant artefact fetch pressure while keeping strict predecessor/version requirements in place.
- `phase_architect` and `week_planner` now receive a compact `Resolved Activity Context` built from historical `ACTIVITIES_TREND` and `ACTIVITIES_ACTUAL` versions, including recent load/durability signals and key sessions instead of forcing raw activity artefact reconstruction in the agent.
- `phase_architect` and `week_planner` now also receive resolved recovery, load-governance, event-priority, and feed-forward-applicability blocks, further moving deterministic season/phase interpretation out of the prompts and into orchestrator code.
- `season_planner` now uses the latest historical `ACTIVITIES_ACTUAL` / `ACTIVITIES_TREND` versions strictly before the target week, and receives the same compact resolved activity context instead of trying to read the in-progress target week.
- Phase-scoped reruns now always regenerate `PHASE_PREVIEW` after forced `PHASE_GUARDRAILS` / `PHASE_STRUCTURE` updates, and Plan Hub no longer marks the whole Phase card as missing when only the optional preview artefact is absent.
- `week_planner` now explicitly treats `PHASE_GUARDRAILS` and `PHASE_STRUCTURE` as exact-range predecessors using the full phase `iso_week_range` key, eliminating spurious single-week read attempts like `phase_guardrails_YYYY-WW.json`.
- Plan Hub now keeps `Build Workouts` available when the knowledge store is unavailable, because the workout export path runs locally; knowledge-store gating remains in place for agent-backed scopes such as `Week Plan`, `Phase`, and orchestrated planning.
- `INTERVALS_WORKOUTS` export generation now runs as a deterministic local code path instead of the `workout_builder` LLM step: `WEEK_PLAN` input schema is validated locally, workout text is checked against the cycling subset, the Intervals export array is mapped in code, and the result is stored via the existing week-scoped artefact path.
- Removed the legacy `workout_builder` agent wiring and prompt files; the export path now records `producer_agent=workout_export` in run/index metadata.
- Renamed the remaining workout-export task and Plan Hub step identifiers to neutral `BUILD_WORKOUT_EXPORT` / `WORKOUT_EXPORT` names, deleted the old mandatory-output chapter, and renamed the shared contract to `week__workout_export_contract.md`.
- Harmonized the local workout-export naming: orchestrator/exporter helpers now use `run_workout_export(...)` and `build_workout_export_payload(...)`, and the validation runbook links were cleaned up.
- Performance corridor charts now derive phase bands from the latest relevant `PHASE_GUARDRAILS` version per week instead of intersecting every historical version, and the chart x-axis is now built from all plotted series rather than only the season corridor.
- Performance corridor charts now also derive `Week Plan Min/Max` and `Planned Weekly kJ` from the latest stored `WEEK_PLAN` payload per ISO week, preventing stale rerun data from leaking into the overview chart.
- Performance corridor charts now trim their past window to the most recent 12 ISO weeks while keeping the future season/phase horizon visible, reducing visual noise from older historical bars.

## [0.10.5] - 2026-04-21

### Changed
- Week-scoped artefact version-key derivation now ignores stale range-shaped `meta.version_key` values like `2026-17--2026-17` on `WEEK_PLAN` envelopes and falls back to `meta.iso_week`, preventing week plans from being re-saved under a bogus range key even when the model echoes legacy metadata.
- Version-key derivation now ignores `meta.iso_week_range` for non-range artefacts such as `WEEK_PLAN`, preventing week plans from being stored under bogus keys like `2026-17--2026-17` and avoiding redundant second `plan_week` runs.
- Envelope writes now canonicalize `created_at`, `run_id`, and `version_key` at store time, so freshly stored phase artefacts no longer keep stale model timestamps that make later artefacts appear older than their actual write order.
- Week-Planner guidance now treats `AVAILABILITY` as shared latest user state instead of falsely requiring target-week coverage, and the Availability/Data-Pipeline contracts now state that the latest valid availability artefact remains authoritative until replaced.
- Phase Guardrails storage now rejects weekly kJ bands that contradict an explicit `feasible max` stated in the band notes, and the runner no longer widens degenerate S5 fallback bands after the model has emitted them.
- Phase-Architect guidance now binds `PHASE_STRUCTURE.load_ranges.source` to the exact stored `PHASE_GUARDRAILS` filename including the timestamped `version_key`, and the shared file-naming / traceability specs now reflect timestamped filenames for versioned season/phase/week artefacts.
- Multi-output runner now logs missing optional `SEASON_PHASE_FEED_FORWARD` / `PHASE_FEED_FORWARD` version reads as informational context misses instead of warning-level read failures.
- Plan Hub worker now bundles scoped phase runs so a single `Run Phase` execution can produce the requested phase artefact set in one combined `plan_week` call instead of queueing three redundant isolated subruns.
- Range-scoped artefact writes now persist string `iso_week_range` metadata into the workspace index, so exact-range checks immediately recognize freshly stored `PHASE_GUARDRAILS` / `PHASE_STRUCTURE` / `PHASE_PREVIEW` artefacts during isolated phase runs.
- Phase Guardrails binding guidance now explicitly treats season-plan `planned_event_windows` entries like `"YYYY-MM-DD (B)"` as compact source strings that must be transformed into structured `events_constraints.events[]` items, avoiding false model stops that demanded an unnecessary Season Plan rewrite.
- Performance Report creation now resolves and enforces week-scoped `ACTIVITIES_ACTUAL` / `ACTIVITIES_TREND` coverage for the selected ISO week, auto-attempts a targeted Intervals backfill before running DES analysis, and the Report, Feed Forward, and Coach preload paths no longer fall back to stale `latest` artefacts from another week where week-scoped context is required.
- Agent task routing now treats week- and phase-scoped artefacts explicitly by target ISO week/range instead of relying on unrelated `latest` artefacts, and workspace read tools now warn when `workspace_get_latest` is used on week-sensitive artefact types.
- Multi-output agent runs now log week-sensitive workspace tool warnings from read handlers, and the Coach / Performance / Feed-Forward prompt guidance now explicitly prefers week-scoped `workspace_get_version(...)` reads for week-sensitive artefacts instead of ambiguous `latest` instructions.
- Season-level prompts and season orchestration now label `latest` reads explicitly as shared/season-level where intended, and System → History now presents newest artefacts as `Latest Snapshots` with validity so week-/phase-scoped entries are not mistaken for selected-week state.
- Multi-output agent runs now treat explicit model blocker responses (`STOP_REASON`, missing binding artefacts, next actions) as terminal failures, so the runner no longer forces a fallback store after a compliant stop and reports the blocker back instead.
- Workspace reads now backfill canonical artefact meta for legacy/shared input envelopes, normalizing stale `data_confidence` values like `USER` and deriving missing ISO-week, temporal-scope, and traceability fields so older `KPI_PROFILE`, `PLANNING_EVENTS`, and `LOGISTICS` inputs no longer hard-stop strict agent bindings on read.
- Athlete Profile -> KPI Profile now stores a canonical workspace envelope on selection, including ISO-week scope and full traceability metadata, instead of copying the bundled spec JSON header through unchanged.
- Performance analysis now derives explicit `phase_week` and `phase_focus` from Season Plan phase context, and DES report generation no longer hard-requires stored phase artefacts when the core required inputs plus Season Plan are present.
- Performance analysis now checks `planning_events` and `logistics` before starting the agent run, so missing shared context inputs fail fast with a clear orchestrator message instead of surfacing later as an agent-side STOP.
- Run-store loading no longer crashes Streamlit startup/background scheduling: `load_runs(...)` now sorts by record timestamps with a dedicated helper and no longer collides with the run-directory timestamp helper used by history pruning.
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
- LoadEstimationSpec now normalizes `planned_Load_kJ` to ENDURANCE (IF_ref_load = 0.70) and updates feasibility + KPI mapping accordingly.
- Season plausibility check now uses mechanical `planned_kJ_week`, and Phase STOPs defer to the S5 ladder; patch section removed.
- All agent prompts now explicitly label Fueling/Energy as `planned_kJ` and Governance as `planned_Load_kJ` in logs/notes.
- Store tool schemas no longer require `data_confidence` in the global meta; activities schemas still require it.
- Phase guardrails hard-stop now defers to LoadEstimationSpec S5 ladder before stopping on empty intersections.
- Season Brief availability parsing moved into `rps` module with `rps.main parse-availability`; old script removed and docs updated.
- DES analysis report schema now allows `inconclusive` status; prompts/specs updated accordingly.
- Preflight now validates Season Brief, Events, and KPI Profile with clearer error messages before runs.

## [0.6.10] - 2026-01-26

### Changed
- LoadEstimationSpec now normalizes `planned_Load_kJ` to ENDURANCE (IF_ref_load = 0.70) and updates feasibility + KPI mapping accordingly.

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
- Added split endurance intensity domains (with legacy aliasing), renamed `SST` → `SWEET_SPOT`, and reintroduced THRESHOLD in intensity-domain enums across schemas, specs, prompts, and workout policy.
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
## 2026-05-19

- fix: season constraint, historical-context, and KPI-guidance specialists now have explicit scope separation in tasks, prompts, and skills so KPI semantics no longer drift back into constraint/event/corridor authority and historical reviews stay evidence-led instead of restating downstream governance
- refactor: reduced the repo-supported LLM env surface to global provider defaults only; per-agent, coach-specific, and crew-planning env overrides are no longer active runtime inputs
- docs: deployment environment documentation now points role-specific model policy to `config/crewai/runtime_profiles.yaml` instead of per-agent env keys
- refactor: reduced `src/rps/core/config.py` to a minimal app-level settings surface with only global LLM defaults and local path settings
- fix: app-level `SETTINGS` no longer reconstruct agent- or crew-scoped environment override policy that already belongs to CrewAI provider config and runtime profiles

## 2026-05-19

- fix: active `SEASON_PHASE_FEED_FORWARD` and `PHASE_FEED_FORWARD` CrewAI tasks now use their dedicated feed-forward manager agents instead of artifact-writer prompts
- fix: review managers now use dedicated review prompts instead of reusing planning-manager prompts, reducing synthesis/review role leakage
- fix: `conversation_manager` is now a non-delegating bounded router/finalizer and its prompt/skill rules explicitly preserve preview/apply and pending-scope boundaries

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
## 2026-05-04

- fix: season KPI-guidance task/prompt/skill are now scoped to KPI and moving-time-rate semantics only, instead of drifting into constraint, event-handling, and phase-corridor authority already owned by other season specialists
- perf: `season_plan_manager` and `season_review_manager` now run on `gpt-5.4-mini` with reasoning disabled, while `macrocycle_architect` remains on `gpt-5.4`; season telemetry/tests were updated to reflect the cheaper manager path
- fix: Streamlit startup now ensures athlete file logging immediately, and Plan Hub run logs attach at the root logger so cross-module runtime/telemetry events are written into the active run log instead of only the worker module logger
- docs: clarified intentional feed-forward version-key asymmetry across `SEASON_PHASE_FEED_FORWARD` and `PHASE_FEED_FORWARD` in artefact flow, workspace, and Feed Forward UI docs
- fix: scoped phase-run completion logs now report the effective executed phase artefacts, including bundled `PHASE_PREVIEW` reruns
- fix: `WEEK_PLAN` store/export now normalizes and validates linked workout duration, agenda duration, agenda mechanical `planned_kj`, and summary mechanical totals before save/export
- fix: deterministic workout duration derived from `workout_text` now overrides drifting stored `duration` / `planned_duration` values instead of only repairing sentinel durations
# Unreleased

- Completed the missing runtime migration of `workout_policy.md` into the active week workout skills. `skills/week/workout-construction/SKILL.md` now carries QUALITY intent target-band lookup, canonical workout-family semantics, parameter ranges, and progression constraints; `skills/week/workout-syntax-review/SKILL.md` now reviews policy-semantic compliance in addition to syntax/export safety.
- Consolidated the week workout runtime rules into active `SKILL.md` files, removed redundant workout-text reference fragments, and tightened week review/decision skills so workout-policy semantic drift is treated as an approval blocker.
# 2026-05-27

- Hardened evidence curation semantics for `metadata_only` sources: active skill/prompt/task/runtime context now explicitly forbids discovery-tag leakage and title-paraphrase pseudo-findings, and the quality gate rejects unsupported RPS transfer concepts for metadata-only summaries.
- Tightened `abstract_curated` evidence semantics: active curation instructions now require abstract-bounded wording, disallow mixing `background_only` with stronger allowed uses, and the quality gate rejects imperative coaching language derived too directly from abstract-only material.
- Tightened evidence refresh runtime behavior: PubMed abstract fetches now use bounded 429 backoff, already-curated verified entries are skipped instead of being reprocessed every due run, each refresh enforces a hard per-run processing cap, and the library is only rewritten when entries actually change.
