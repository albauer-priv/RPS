# Project Context: RPS (Randonneur Performance System)

## 🎯 Core Goal & Status
- **Purpose:** End-to-end planning system for endurance athletes (Season/Phase/Week/Workouts) with UI, agents, and artifact pipeline.
- **Current focus:** Finish repo-wide Season/Phase/Week renames and keep Streamlit UI stable (Coach/Plan‑Week + logging).
- **Last milestone:** Hard rename of core artefacts/agents + schemas, contracts, prompts, docs, and UI to Season/Phase/Week.

## 🛠 Tech Stack & Conventions
- **Languages/Frameworks:** Python 3.14, Streamlit, OpenAI Responses API.
- **Code style:** Pythonic, minimal side effects; no new dependencies without approval.
- **Testing:** `python -m py_compile` for syntax checks; targeted CLI runs (e.g., `plan-week`, `parse-intervals`).

## 🧾 Documentation & Logging Conventions
- **Logging required:** All non-trivial functions should log key actions (start, important decisions, completion, errors). Use appropriate log levels; UI logs should be human-readable ("Calling Artefact Renderer…", "Renderer done.").
- **Docstrings required:** Functions with side effects, IO, or non-trivial logic must have docstrings.
- **Documentation style:** Prefer **detailed** documentation over short notes. For each function or module, include:
  - **Purpose/What it does**
  - **Inputs (types + meaning)**
  - **Outputs/returns (types + meaning)**
  - **Side effects** (files written, network calls, state changes)
  - **Errors/exceptions** (when and why they can occur)
  - **Examples** (short usage snippet if relevant)

## 📂 Key Paths (Structure Map)
- `/src/rps/ui`: Streamlit UI (`streamlit_app.py`).
- `/src/rps/agents`: Agent runner / multi-output / tasks.
- `/src/rps/orchestrator`: Plan-week orchestration.
- `/src/rps/tools`: Workspace tools (read/write).
- `/src/rps/openai`: Responses API streaming, vectorstore, client.
- `/src/rps/workspace`: Artifact store, schemas, ISO helpers.
- `/config`: Knowledge injection, runtime config.
- `/knowledge`: Specs, policies, principles, schemas.
- `/var/athletes`: Workspace artifacts/logs/inputs.
- `/doc`: System architecture, planner docs, artifact flows.
- `/schemas`: JSON schemas (bundled + interface).

## 📝 Active Todo List (Backlog)
- [ ] Run schema validation + bundler after rename sweep (and fix any broken refs).
- [ ] Re-sync vector store after spec/contract/header changes.
- [ ] Confirm UI flows (preflight → season → plan‑week) after renames.
- [ ] Logging: finalize UI/console/file levels; keep “speaking” UI logs clean.
- [ ] Coach UX: ensure response bubble + reasoning summary are consistent.

## 📌 Key Docs & Config
- `doc/system_architecture.md`: System overview + UI/agent flows.
- `doc/artefact_flow_overview_and_detail.md`: Artifact flows & dependencies.
- `doc/how_to_plan.md`: Plan-week / Season / Phase / Week process.
- `doc/planners.md`: Planner roles & responsibilities.
- `config/agent_knowledge_injection.yaml`: Knowledge injection per agent/mode.
- `prompts/agents/*.md`: Agent prompts (Season/Phase/Week/Coach/etc.).
- `knowledge/_shared/sources/specs/load_estimation_spec.md`: Load definitions + Phase intersection.
- `knowledge/_shared/sources/policies/progressive_overload_policy.md`: Progression/Deload rules.
- `knowledge/_shared/sources/principles/principles_durability_first_cycling.md`: Durability-first principles.
- `schemas/**`: JSON schemas (esp. artifact interfaces).

## 🔧 Key Runtime/Env Variables
- `OPENAI_API_KEY`: API access.
- `OPENAI_MODEL*`, `OPENAI_TEMPERATURE*`, `OPENAI_REASONING_EFFORT*`: agent overrides.
- `OPENAI_ENABLE_WEB_SEARCH`, `OPENAI_WEB_SEARCH_AGENTS`: web search (Coach).
- `OPENAI_STREAM*`: Responses streaming behavior.
- `RPS_LOG_LEVEL_FILE`, `RPS_LOG_LEVEL_CONSOLE`, `RPS_LOG_LEVEL_UI`: logging per channel.
- `OPENAI_FILE_SEARCH_MAX_RESULTS`: file_search limit.

## 🧭 Working Order (Short)
- Preflight: inputs (Season Brief, Events), KPI profile, Availability, Intervals pipeline.
- Season flow: Scenarios → Selection → Season Plan.
- Plan week: Season Plan → Phase → Week → Workouts (artifacts + renderer).
- UI: state machine drives actions; buttons only update state/params.
- Phase artefacts: `phase_*` ISO-week ranges must align to the covering Season Plan phase range. Mismatches are auto-normalized with a warning log.

## 🏷 Versioning Flow (Git Release Flow)
- Determine next SemVer (usually patch for UI/logging tweaks, minor for new flows).
- Update `CHANGELOG.md` with the new version header and bullet list.
- Commit changes.
- Create/update git tag (e.g., `v0.6.29`) pointing to the changelog commit.
- Push commit and tag.

## ✅ Change Impact Checklist
- **Schema changes (`/schemas`, `knowledge/_shared/sources/schemas`):**
  - For schemas used by the Responses API: ensure **all properties are listed in `required`** (strict tool schema requirement).
  - Run `python scripts/check_schema_required.py` to verify required coverage.
  - Re-run the schema bundler (if used in your workflow).
  - Validate affected artifacts locally.
- **Specs/Policies/Principles in vector store:**
  - Re-sync vector store (often `sync_vectorstores.py --reset` when IDs/headers change).
  - Ensure metadata headers (ID/Type/Authority) remain correct.
- **File renames / path moves:**
  - Update references in prompts, manifests, and knowledge injection config.
  - Re-scan manifests / run sync to avoid stale paths.
- **Prompt changes (`prompts/agents/*.md`):**
  - Verify mandatory output docs and tool load orders still match.
  - Check for duplicate or conflicting rules.
- **Agent/tool wiring changes:**
- Re-run a small end-to-end flow (e.g., preflight → season → plan-week) to confirm.
  - Validate outputs with `python scripts/validate_outputs.py` (optionally `--year/--week/--athlete`).

## ⚠️ Known Constraints / "Don'ts"
- No new dependencies without approval.
- No schema changes without changelog/version bump.
- No web search/external calls without explicit approval (except Coach when web search is enabled).
