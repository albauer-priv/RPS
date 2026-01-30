# AGENTS.md — RPS (Randonneur Performance System)

This file is the **README for coding agents** working in this repository. It consolidates project context, guardrails, and the practical workflows an agent must follow.

**Primary goals**

* Keep the multi-page Streamlit UI stable and predictable (navigation + Plan/Performance subpages).
* Keep the agent + artifact pipeline correct (season/phase/week/workouts) and testable.
* Avoid regressions: always verify flows with commands + tests before declaring work complete.

---

## 0) Quick commands (run early, run often)

> Prefer running commands from repo root.

* Syntax check (fast): `python -m py_compile $(git ls-files '*.py')`
* Run app: `PYTHONPATH=src streamlit run src/rps/ui/streamlit_app.py`
* Tests (if present): `pytest -q`
* UI smoke check (manual): `PYTHONPATH=src streamlit run src/rps/ui/streamlit_app.py`
* Targeted CLI smoke checks (common):
  * Intervals pipeline help (safe): `PYTHONPATH=src python3 src/rps/data_pipeline/intervals_data.py --help`
  * Plan-week: smoke via UI (Plan → Week page) until a non-deprecated CLI entrypoint exists.

**Rule:** Before marking a task “done”, run at least **syntax check + one relevant smoke run** (UI or CLI), and fix failures.

---

## 1) Project context

### Core goal & current status

* **Purpose:** End-to-end planning system for endurance athletes (Season/Phase/Week/Workouts) with UI, agents, and artifact pipeline.
* **Current focus:** Stabilize **multi-page Streamlit UI** (navigation + Plan/Performance subpages), verify season flow + plan-week gating, and ensure athlete data pages resolve inputs correctly.
* **Last milestone:** Multi-page UI restructure with isolated page scripts and Coach chat migration.
* **Recent status:** Coach chat refactor (in-repo chat + compaction + summary UI) is stable across 8–10 dialog turns without errors.
* **Recent status:** Phase preview layout moved to its own expander with weekly previews below.

### Tech stack & constraints

* **Languages/Frameworks:** Python 3.14, Streamlit, OpenAI **Responses API**.
* **Code style:** Pythonic, minimal side effects.
* **Dependencies:** **No new dependencies without approval.**

---

## 2) Repository structure & key paths

### Structure map

* `/src/rps/ui`: Streamlit UI entry (`streamlit_app.py`) + shared helpers.
* `/src/rps/ui/pages`: Multi-page UI screens (Home/Coach/Analyse/Plan/Athlete Profile).
* `/src/rps/agents`: Agent runner / multi-output / tasks.
* `/src/rps/orchestrator`: Plan-week orchestration.
* `/src/rps/tools`: Workspace tools (read/write).
* `/src/rps/openai`: Responses API streaming, vectorstore, client.
* `/src/rps/workspace`: Artifact store, schemas, ISO helpers.
* `/config`: Knowledge injection, runtime config.
* `/knowledge`: Specs, policies, principles, schemas.
* `/var/athletes`: Workspace artifacts/logs/inputs.
* `/doc`: System architecture, planner docs, artifact flows.
* `/schemas`: JSON schemas (bundled + interface).

### Key docs & config

* `doc/system_architecture.md`: System overview + UI/agent flows.
* `doc/artefact_flow_overview_and_detail.md`: Artifact flows & dependencies.
* `doc/how_to_plan.md`: Plan-week / Season / Phase / Week process.
* `doc/how_to_plan.md`: Planner roles & responsibilities and end-to-end flow.
* `doc/intervals_posting.md`: Intervals posting semantics, receipts, and external_id strategy.
* `doc/plan_hub_proposal.md`: Plan Hub proposal with readiness rules and layout.
* `config/agent_knowledge_injection.yaml`: Knowledge injection per agent/mode.
* `prompts/agents/*.md`: Agent prompts (Season/Phase/Week/Coach/etc.).
* `schemas/**`: JSON schemas (esp. artifact interfaces).

---

## 3) Coding standards

### Naming conventions

* Variables / functions: `snake_case`
* Classes: `PascalCase`
* Constants: `UPPER_SNAKE_CASE`

### Script/layout discipline (Streamlit-aware)

Streamlit reruns scripts top-to-bottom. To avoid duplicated side effects and flaky UI:

**Recommended file order**

1. Imports
2. Constants + types (no side effects)
3. Pure helpers (transformations)
4. Service functions (IO / OpenAI / workspace reads)
5. Session/state initialization
6. UI composition/rendering (layout, containers, widgets) — **at the end**

**Hard rules**

* No expensive operations at module import time.
* No `st.*` calls inside worker threads.
* Keep page scripts small; move logic into helpers/services.

---

## 4) Streamlit UI standards (design + structure)

### Multipage structure

* Keep each page script focused: input → render → delegate logic.
* Shared UI patterns belong in `/src/rps/ui` helpers.

### Layout conventions

* One clear page hierarchy: **Title → primary controls → main content → details/debug**.
* Prefer these building blocks:

  * `st.container()` for sections (Header / Body / Footer)
  * `st.columns()` for 2–3 column layouts (avoid >3)
  * `st.tabs()` only for peer views (not navigation)
  * `st.expander()` for advanced details (reasoning, raw JSON, debug)
* Forms: use `st.form()` when multiple inputs must be submitted together.

### Rerun hygiene

* Avoid repeated banners/toasts on reruns; gate them with state.
* Use `st.status()`/`st.spinner()` for long operations; update state at completion.

### Chat UI (Coach)

* Use `st.chat_message` + `st.chat_input`.
* Store chat history in `st.session_state`.
* Show tool traces/reasoning only in an expander or a Dev Mode panel.

---

## 5) State management

### Session state keys

* Initialize keys at the top of each page before rendering.
* Namespaced keys to avoid collisions across pages.

Suggested common keys

* `athlete_id`
* `scenario_id`
* `chat_messages`
* `ui_dev_mode`
* `last_response_meta`

---

## 6) Performance: caching & rerun cost

Streamlit reruns are the core performance constraint.

### Caching strategy

* `@st.cache_resource`: long-lived clients/resources (OpenAI client, DB connections)

  * **Must be thread-safe** if shared across sessions.
* `@st.cache_data`: data transforms, file parsing, deterministic computations

### Avoid redundant work

* Cache expensive file reads/parsing.
* Compute summaries once and store in session state when appropriate.

---

## 7) Concurrency / multithreading (important)

**Principle:** Prefer caching + streaming + batching over ad-hoc background threads.

If concurrency is needed (typically IO-bound):

* Use `concurrent.futures.ThreadPoolExecutor` for IO-bound work only.
* Threads may compute or fetch, but **must not call `st.*`**.
* Collect results and render in the normal Streamlit run.
* Be careful with shared state; avoid race conditions.

Long-running jobs:

* Don’t run uncontrolled background threads across session lifetime.
* Prefer a job runner/worker pattern + polling UI (or periodic refresh) if truly long.

---

## 8) OpenAI Responses API (architecture + streaming)

### Where OpenAI code lives

* All OpenAI calls and event parsing live in `/src/rps/openai` (or `/src/rps/services` if that’s the repo convention).
* Prompts belong in `prompts/` and are referenced from code.

### Streaming UI rules

* For streaming output in UI, prefer `st.write_stream(generator)`.
* Build a wrapper generator that yields only text chunks.
* Append only text delta events to the UI stream.
* Persist final metadata (usage/cost/ids) only when the response is completed.

### Context management (Compaction)

For long conversations and agents:

* Use Responses API **compaction** to shrink context when needed.
* Keep the full raw history for audit/debug.
* Use compacted context only for subsequent calls.
* Trigger compaction based on thresholds (token budget, turns, latency), not on every turn.

### Token budgeting (tiktoken)

* Use `tiktoken` only if it is already approved/available in the project.
* Use it for **preflight estimation** (chunking, truncation), not as billing truth.
* Treat API-reported usage as source of truth.

---

## 9) Testing (mandatory behavior)

### Baseline verification

* Always run `python -m py_compile ...` before finishing.
* Use targeted CLI smoke runs relevant to the change.

### Streamlit AppTest

For any UI change:

* Always add/extend UI tests under `tests/` using `streamlit.testing.v1.AppTest`.
* Mock OpenAI calls in tests to avoid cost/flakiness.
* **No temporary test scripts** outside `tests/`.

---

## 10) Logging & documentation

### Logging conventions

* All non-trivial functions must log key actions: start, decisions, completion, errors.
* Use appropriate log levels.
* UI logs should be human-readable (e.g., “Calling Artifact Renderer…”, “Renderer done.”).
* Avoid logging secrets and PII.

### Docstrings (required for non-trivial logic)

Functions with side effects, IO, or non-trivial logic must have docstrings including:

* Purpose
* Inputs (types + meaning)
* Outputs/returns (types + meaning)
* Side effects (files/network/state)
* Errors/exceptions
* Example (if helpful)

---

## 11) Runtime/env variables (do not hardcode)

* `OPENAI_API_KEY`
* `OPENAI_MODEL*`, `OPENAI_TEMPERATURE*`, `OPENAI_REASONING_EFFORT*`
* `OPENAI_ENABLE_WEB_SEARCH`, `OPENAI_WEB_SEARCH_AGENTS`
* `OPENAI_STREAM*`
* `RPS_LOG_LEVEL_FILE`, `RPS_LOG_LEVEL_CONSOLE`, `RPS_LOG_LEVEL_UI`
* `OPENAI_FILE_SEARCH_MAX_RESULTS`

Rule: Secrets belong in `.streamlit/secrets.toml` locally and must be gitignored.

---

## 12) Change impact checklist (use before/after changes)

### Schema changes (`/schemas`, `knowledge/_shared/sources/schemas`)

* For schemas used by the Responses API: ensure **all properties are listed in `required`** (strict tool schema requirement).
* Run `python3 scripts/check_schema_required.py`.
* Re-run bundler: `python3 scripts/bundle_schemas.py`.
* Validate affected artifacts.

### Specs/Policies/Principles in vector store

* Re-sync vector store after spec/contract/header changes.
* Ensure metadata headers (ID/Type/Authority) remain correct.

### File renames / path moves

* Update references in prompts, manifests, and knowledge injection config.
* Re-scan manifests / run sync to avoid stale paths.

### Prompt changes (`prompts/agents/*.md`)

* Verify mandatory output docs and tool load orders.
* Check for duplicate or conflicting rules.

### Agent/tool wiring changes

* Re-run a small end-to-end flow (preflight → season → plan-week).
* Optionally validate outputs: `python scripts/validate_outputs.py [--year/--week/--athlete]`.

---

## 13) Working order (short)

* Preflight: inputs (Season Brief, Events), KPI profile, Availability, Intervals pipeline.
* Season flow: Scenarios → Selection → Season Plan.
* Plan week: Season Plan → Phase → Week → Workouts (artifacts + renderer).
* UI: multi-page layout; shared state tracks athlete id + logs across pages.
* Phase artifacts: `phase_*` ISO-week ranges align to covering Season Plan phase range; mismatches auto-normalize with warning.

---

## 14) Backlog (active)

* Run schema validation + bundler after rename sweep (fix broken refs).
* Re-sync vector store after spec/contract/header changes.
* Verify multi-page flow end-to-end (scenario creation → selection → season plan → plan-week enabled).
* Confirm plan-week gating and ISO-week range checks in UI.
* Coach UX: bubble + reasoning summary + tool access + rate-limit handling.
* Validate input pages: Season Brief + Logistics load newest inputs; Availability editor behavior.
* Investigate duplicated “Creating performance report…” banner and improve real-time reasoning stream.
* Season page: render selected scenario summary; remove JSON dump; align tables with template output.
* Add Create/Reset/Delete controls with requested confirmation semantics.
* Revisit Phase page helpers to avoid missing-argument errors after partial revert.

### Possible extensions (post‑MVP)

* Introduce a file‑backed queue with `pending/active/done` markers (multi‑worker readiness).
* Add worker heartbeats + stuck‑run recovery (timeout → FAILED or requeue).
* Support `validate_only` runs (no writes, validation only).
* Add `cancel_requested` handling so the worker can safely stop between steps.
* Optional per‑step log files (`runs/<run_id>/logs/<step_id>.log`) for deep debugging.
* Add heartbeat + “stuck run” UI (timeout → mark failed / requeue).
* Add unposted count + receipts diff check on Week page.
* Add receipt conflict UX (manual confirm) and external idempotency headers when available.
* Define external_id semantics for Intervals posting (upsert/delete) and store both external_id + Intervals id/uid in receipts.

---

## 15) Don’ts (non-negotiable)

* No new dependencies without approval.
* No schema changes without changelog/version bump.
* No secrets in code or committed files.
* No web search/external calls without explicit approval (except Coach when explicitly enabled).
