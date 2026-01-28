# Project Context: RPS (Randonneur Performance System)

## 🎯 Core Goal & Status
- **Purpose:** End-to-end planning system for endurance athletes (Macro/Meso/Micro/Workouts) with UI, agents, and artifact pipeline.
- **Current focus:** Stabilize Streamlit UI (Coach/Plan-Week), logging presentation, knowledge injection, and preflight flows.
- **Last milestone:** Coach streaming via Responses events, UI log levels, unified knowledge injection, Macro/Meso/Micro flows in the UI.

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
- [ ] Coach: clean response bubble + reasoning, smooth UI state.
- [ ] Logging: finalize UI/console/file levels; complete "speaking" UI logs.
- [ ] Preflight: validate inputs, handle renderer errors robustly.
- [ ] Agents: consistent workspace load order; stable Season Brief & Events access.
- [ ] Artifact renderer: implement missing renderers (e.g., Wellness).

## 📌 Key Docs & Config
- `doc/system_architecture.md`: System overview + UI/agent flows.
- `doc/artefact_flow_overview_and_detail.md`: Artifact flows & dependencies.
- `doc/how_to_plan.md`: Plan-week / Macro / Meso / Micro process.
- `doc/planners.md`: Planner roles & responsibilities.
- `config/agent_knowledge_injection.yaml`: Knowledge injection per agent/mode.
- `prompts/agents/*.md`: Agent prompts (Macro/Meso/Micro/Coach/etc.).
- `knowledge/_shared/sources/specs/load_estimation_spec.md`: Load definitions + Meso intersection.
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
- Macro flow: Scenarios → Selection → Macro Overview.
- Plan week: Macro → Meso → Micro → Workouts (artifacts + renderer).
- UI: state machine drives actions; buttons only update state/params.
- Block artefacts: `block_*` ISO-week ranges must align to the covering Macro phase range. Mismatches are auto-normalized with a warning log.

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
  - Re-run a small end-to-end flow (e.g., preflight → macro → plan-week) to confirm.
  - Validate outputs with `python scripts/validate_outputs.py` (optionally `--year/--week/--athlete`).

## ⚠️ Known Constraints / "Don'ts"
- No new dependencies without approval.
- No schema changes without changelog/version bump.
- No web search/external calls without explicit approval (except Coach when web search is enabled).
