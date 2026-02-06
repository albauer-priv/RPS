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
* **Recent status:** Plan Hub season plan reset/delete actions now live in a collapsed expander; run summary banner uses plain text (no "Was wird alles erstellt" prefix).
* **Recent status:** Performance report readiness is now surfaced on Performance pages (Feed Forward + Report), and removed from Plan Hub planning readiness.
* **Recent status:** Plan Hub reset/delete now deletes latest artefacts (reset keeps scenarios/selection; delete removes them too).
* **Recent status:** Plan Hub worker loop moved into orchestrator helpers; System → Status now shows planning worker status.
* **Recent status:** Automatic planning flow document includes Mermaid labels wrapped in triple quotes for rendering.
* **Recent status:** Logging now writes to a single rps.log with daily/size rotation and run/log retention housekeeping.
* **Recent status:** Plan Hub Run Planning panel stays visible when only Week Plan is missing; scope inputs remain left of Run Planning.
* **Recent status:** Phase/Week/Workouts headers include ISO-week date ranges and render above captions; Season now shows the plan date range in the header.
* **Recent status:** Report page now surfaces Narrative/KPI Summary/Trend Analysis sections and hides raw JSON.
* **Recent status:** Data & Metrics decoupling chart shows weekly trend plus per-activity values.
* **Recent status:** Events page can upgrade legacy planning events payloads to restore all columns.

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

* `doc/architecture/system_architecture.md`: System overview + UI/agent flows.
* `doc/overview/artefact_flow.md`: Artifact flows & dependencies.
* `doc/overview/how_to_plan.md`: Plan-week / Season / Phase / Week process.
* `doc/overview/how_to_plan.md`: Planner roles & responsibilities and end-to-end flow.
* `doc/architecture/subsystems/intervals_posting.md`: Intervals posting semantics, receipts, and external_id strategy.
* `doc/ui/pages/plan_hub.md`: Plan Hub proposal with readiness rules and layout.
* `config/agent_knowledge_injection.yaml`: Knowledge injection per agent/mode.
* `prompts/agents/*.md`: Agent prompts (Season/Phase/Week/Coach/etc.).
* `schemas/**`: JSON schemas (esp. artifact interfaces).

---

## 3) Coding standards

### Naming conventions

* Variables / functions: `snake_case`
* Classes: `PascalCase`
* Constants: `UPPER_SNAKE_CASE`

### Documentation Rule (Single Source of Truth + Placement)

When adding or changing documentation, follow this rule:

1) Classify the doc by intent (choose exactly one):
   - OVERVIEW: orientation/explanation for humans (why / what)
   - SPEC: normative requirements (must/shall), feature behavior, contracts
   - ARCH: how the system is built (components, boundaries, data model, runtime)
   - UI: user-facing flows + action semantics; Streamlit-specific details are "UI Contract"
   - RUNBOOK: operational procedures (how to run/validate/recover)
   - ADR: a decision record (context → decision → alternatives → consequences)

2) Place the file in exactly one canonical location:
   - doc/overview/…
   - doc/specs/… (features/ or contracts/)
   - doc/architecture/… (and architecture/subsystems/…)
   - doc/ui/… (ui_spec + streamlit_contract + page deep-dives)
   - doc/runbooks/…
   - doc/adr/…

3) Avoid duplication:
   - If content overlaps, pick ONE canonical doc and replace the other with a short link.
   - README.md must remain a navigation hub (index) and must not become the canonical source.

4) Promotion path for proposals:
   - New ideas start as doc/proposals/<name>.md (optional).
   - Once accepted, convert to either:
     a) an ADR (decision), and/or
     b) an Architecture doc (implementation), and/or
     c) a Spec (normative behavior).
   - Mark the original as Superseded and link to the canonical doc(s).

5) Every doc must have a header:
   Version, Status (Draft/Updated/Deprecated/Superseded), Last-Updated (YYYY-MM-DD), and a single "Owner" or "Area".

## Agent Rule: Feature-First Workflow (Docs → Decision → Implementation)

For any change that affects behavior (feature, refactor with user impact, schema/contract change):

### 1) Create a Feature Doc FIRST
Create `doc/specs/features/FEAT_<slug>.md` before coding. **Use the required template at `doc/specs/features/FEAT_TEMPLATE.md`.** It must contain:

1. **Context / Problem**
   - Why change is needed; current behavior; constraints.

2. **Goals & Non-Goals**
   - Goals (must be true after release)
   - Non-Goals (explicit exclusions)

3. **Proposed Behavior**
   - New behavior description from user/system perspective.
   - If UI is affected: include a UI flow diagram (Mermaid).
   - If no UI: describe impacted components and contracts.

4. **Implementation Analysis**
   - How it can be implemented: components/modules, data flow, artefacts, schemas.

5. **Impact Analysis (complete)**
   - Conflicts with ADRs/principles?
   - Breaking changes? Compatibility?
   - What must be adjusted (UI, pipeline, renderer, validators, workspace, run store).
   - Required refactoring (explicit list).

6. **Options & Recommendation**
   - At least one alternative (if reasonable).
   - Tradeoffs, risks, and a recommended option.

7. **Acceptance Criteria (DoD)**
   - Testable bullets (validation passes, UI states, artefact outputs, performance guardrails).

8. **Migration / Rollout**
   - Backward compatibility strategy (schema versions, defaults, fallbacks).
   - Rollout gating (feature flag/config) if needed.

9. **Risks & Failure Modes**
   - What can go wrong, how it is detected, and expected safe behavior.

10. **Observability / Logging**
   - New/changed log events and diagnostics needed.
   - Link to logging policy doc.

11. **Documentation Updates**
   - List docs to update and intended changes (links + bullets).

12. **Link Map (required, no copy/paste)**
   - Links to relevant canonical docs (UI spec, architecture, workspace, schema versioning, logging policy, etc.)
   - The feature doc must not duplicate canonical content; it references it.

### 2) Optional but recommended sections (keep lightweight)
- **Open Questions** (max 5 bullets): unresolved decisions or unknowns.
- **Out of Scope / Deferred**: explicit exclusions and future follow-ups.

### 3) ADR Trigger (mandatory when applicable)
Create/update an ADR (`doc/adr/`) when the feature:
- changes architecture boundaries,
- introduces a new subsystem/component,
- changes persistence or schema strategy,
- modifies cross-cutting contracts (artefacts, run-store, workspace),
- or deviates from existing ADRs/principles.

### 4) Implementation After Approval
Only implement after the feature doc is reviewed/approved.
During implementation:
- Keep the feature doc in sync if scope changes.
- Update referenced docs as specified.
- Ensure validators/runbooks are updated when contracts/schemas change.

## Continuation Protocol (handoff between chats)

When starting a new chat or agent session, do this in order:

1) **Read `doc/overview/feature_backlog.md` first.**
   - Use the ranked list as the default priority.
   - Check the unlock graph for dependencies.

2) **Check the last 5 commits** to understand recent changes and avoid duplicating work.

3) **Verify current status** before coding:
   - `git status -sb`
   - If there are local changes, summarize them and ask whether to keep or revert.

4) **Confirm which backlog item is active** (unless the user explicitly specifies one).

5) **Apply Feature-First workflow**:
   - Ensure `doc/specs/features/FEAT_<slug>.md` exists (using the template).
   - Ensure ADR is created/updated if the change touches architecture, persistence, or cross-cutting contracts.

6) **Implementation loop**:
   - Code changes → tests → docs → changelog → commit/push.

7) **Always record outcomes**:
   - Update `CHANGELOG.md`.
   - Update relevant docs + backlog status when a feature is completed or partially done.

### Documentation (Mermaid)

* Mermaid diagram labels should wrap text in quotes, e.g. `["Label"]` or `{"Decision?"}`, to ensure consistent rendering.
* Avoid `\\n` in Mermaid labels; use `<br>` or a single space instead.
* For UI flow diagrams, use layered styling with a legend:
  - **Page (UI)** nodes in yellow
  - **Orchestrator** nodes in blue
  - **Agent** nodes in green
  - **Flow Step** nodes in neutral gray

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

## 3.1) Planning principles (implementation rule)

These rules must be applied when implementing planning flows, pickers, and selectors.

* Planning a week targets **current or next ISO week only** (one-week horizon).
* Planning can run **only if the week is within the current Season Plan ISO range**.
* Planning can run **only if higher-level artefacts exist** (`season_plan`, `phase_*`).
* **Performance Report** is **past-only** (Intervals activity data); never future weeks.
* **Feed Forward** runs for a **completed week** once Intervals data is complete.
* When Intervals data is newer, **create a new Performance Report** before Feed Forward.
* "Sunday" in rules/labels maps to **Wochenanker** in docs and UI copy.
* **Scoped planning** means the athlete provides an override for a selected level (Season/Phase/Week/Workouts) **only when modifying existing artefacts**. When planning a new week with no existing artefacts, override input is optional. The orchestrator/agent must receive the scope and (if provided) the override, and re-planning must apply to the selected scope and all lower levels.
* **Plan Week (default):** Plan Hub should prefer a scoped Week Plan run. Preselect **Plan Next Week** when the current week is fully ready; otherwise **Plan Week** (current week).
* UI pages must not call agents directly; delegate to orchestrator/service helpers (Plan Hub is UI, not controller).

### ADR process (automated)

* ADRs are stored as separate files in `doc/adr/` and indexed in `doc/adr/README.md`.
* Always evaluate changes for ADR-worthiness (architecture, flow orchestration, data/state lifecycle).
* If a change conflicts with an existing ADR, **pause and warn**.
* If an exception is required, add it to the relevant ADR with rationale.
* Keep ADRs updated automatically as part of change delivery.

---

## 4) Streamlit UI standards (design + structure)

### Multipage structure

* Keep each page script focused: input → render → delegate logic.
* Shared UI patterns belong in `/src/rps/ui` helpers.

### Charts (UI)

* Charts must use `st.plotly_chart(...)` exclusively.
* Do not use `st.line_chart`, `st.bar_chart`, `st.area_chart`, `st.altair_chart`, etc.

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

### Workspace index maintenance

* Streamlit startup now prunes missing artifact index entries in the background.
* Startup cleanup also removes orphaned rendered sidecars in `rendered/`.
* Keep the cleanup thread fire-once per session and never call `st.*` from it.
* Use the workspace index manager to remove missing paths and fix `latest/` pointers.
* Artefact rendering is integrated in `rps.rendering.renderer`; templates live in `src/rps/rendering/templates/`.
* Background jobs (data pipeline, housekeeping, report generation) write run records with `process_type`/`process_subtype`.
* Use the background run tracker helper in `rps.ui.run_store` to standardize async job status updates.
* Scheduler guardrails: only one active run per `process_type` + `process_subtype`; lower-priority planning runs are blocked while higher-priority runs are active.
* Mode A scenario generation + selection are integrated in the Plan → Season UI (no separate script required).
* System → History hosts latest outputs + run history; Plan Hub focuses on readiness and execution.

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

## Architecture Decision Log

ADR log is maintained as external files under `doc/adr/` (see `doc/adr/README.md` for index). Keep this section short and point to the ADR folder.

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
* Posting supports bulk upsert/delete via external_id; delete-removed is opt-in.

---

## 15) Don’ts (non-negotiable)

* No new dependencies without approval.
* No schema changes without changelog/version bump.
* No secrets in code or committed files.
* No web search/external calls without explicit approval (except Coach when explicitly enabled).
