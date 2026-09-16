---
Version: 2.0
Status: Updated
Last-Updated: 2026-09-16
Owner: Product
---
# Feature Backlog

This backlog tracks upcoming features and refactors. Each item should link to a
feature spec ([doc/specs/features/FEAT_<slug>.md](/doc/specs/features/FEAT_<slug>.md)) before implementation.

Completed items are removed from this file; CHANGELOG.md is the authoritative record of what shipped.

---

## In Progress / Partially Done

- [~] FEAT_posting_receipts_inspection — receipt inspection + status (implemented; UX polish ongoing).

---

## Open / Deferred

- [ ] Full-run observation follow-up — before fixing the remaining Phase artifact quality gaps, rerun one complete Season→Phase→Week chain in the real runtime and analyze the resulting artefacts for: (a) canonical Season lineage `run_id` quality in Phase `trace_upstream`, (b) empty inherited `selection_rationale`, and (c) duplicated / partially rephrased `PHASE_STRUCTURE.upstream_intent.constraints`. Treat this as a post-run analysis gate, not an immediate code patch.
- [ ] Manual smoke pass for `Workout Editor` — verify preview/apply flows for move, start-time change, and workout-text replacement against a real athlete week in the UI.
- [ ] Manual active `Coach` smoke pass — verify context read, bounded edit preview/apply, scoped replan preview/apply, report preview/apply, and feed-forward preview/apply against a real athlete week in the UI.
- [ ] Manual CrewAI-compatible end-to-end smoke pass — run Season, Phase, Week, Coach, and Workout Editor in a CrewAI-capable Python 3.13/container runtime and validate flow persistence, memory/knowledge wiring, and preview/apply paths.
- [ ] FEAT_mandatory_output_audit_and_structured_output_migration — audit remaining `mandatory_output_*` families and migrate safe artifact/task families to `output_json` / `output_pydantic` plus guardrails; retain prompt-level contracts only where structured outputs remain unsafe.
- [ ] FEAT_parquet_rollups — precomputed analytics rollups for long ranges.
- [ ] FEAT_archival_policy — archive/restore old athlete data.
- [ ] FEAT_planner_positive_frontloading_rollout — apply the documented positive-frontloading template from `FEAT_season_scenario_positive_frontloading` to Season/Phase/Week planner chains with a mandatory 3-pass model (Pass 1 structural draft, Pass 2 semantic finalization, Pass 3 planner self-audit), explicit Pass 1 vs Pass 2 loopback rules, formal review classification, and copy-only writer preconditions.
- [ ] FEAT_crewai_memory_policy_tuning — tune CrewAI memory scoring/retention, add athlete-scoped forget/cleanup helpers, and keep Coach-confirmed preferences separate from planning artifacts.
- [ ] FEAT_crewai_files_evaluation — evaluate CrewAI Files only for PDF evidence, charts, screenshots, or external feedback; keep plan artifacts Workspace/Schema-owned.
- [ ] FEAT_crewai_planning_profile_tuning — refine where CrewAI planning is enabled, keeping deterministic Load/S5/Cadence outside planning LLM authority.
- [ ] FEAT_crewai_mcp_apps_policy — define conservative MCP/App usage for evidence search and external integrations with RPS preview/confirm/apply boundaries.
- [ ] FEAT_prompt_caching_investigation — no explicit LLM prompt-caching support exists today. Default model is `openai/gpt-5-mini` (`src/rps/crewai_runtime/provider.py`), which OpenAI caches automatically server-side for prefixes over ~1024 tokens. Task-description building already places static content before dynamic content — a structure favorable to caching, though incidental. Needs runtime observation (telemetry/logs on real calls) to confirm actual cache-hit behavior before deciding whether prefix-structure changes are worth making.

---

## Continuation Protocol (for new sessions)

When resuming work, follow this order so context stays consistent:

1) Read `.clinerules` for operative Cline rules.
2) Read `AGENTS.md` as the agent entry/source map.
3) Review this file and `CHANGELOG.md` for current status and recent work.
4) Check repo for in-flight changes: `git status`, recently modified files.
5) Implement the next backlog item only after the related feature doc is **Reviewed/Approved**.
6) Keep docs in sync:
   - [doc/ui/ui_spec.md](/doc/ui/ui_spec.md), [doc/architecture/workspace.md](/doc/architecture/workspace.md), [doc/overview/artefact_flow.md](/doc/overview/artefact_flow.md)
   - update [doc/README.md](/doc/README.md) index if files move
7) Run required checks:
   - `python -m py_compile $(git ls-files '*.py')`
   - one relevant smoke run (UI/CLI)
8) Update `CHANGELOG.md`, then commit and push.
