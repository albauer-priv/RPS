# my-openai-platform

Scaffold for local vector stores with a unified, versioned knowledge base.

## Layout

- [`src/rps/`](src/rps/): app code and OpenAI helpers.
- [`doc/`](doc/): system documentation.
- [`prompts/`](prompts/): shared + per-agent prompts.
- [`specs/knowledge/`](specs/knowledge/): versioned sources and manifests (no embeddings in repo).
- [`scripts/`](scripts/): maintenance helpers (schemas, validation, vector stores).
- [`legacy/`](legacy/): artifacts to migrate from the predecessor project (gitignored).
- [`runtime/athletes/`](runtime/athletes/): runtime state for local athlete workspaces (gitignored).
- [`.cache/`](.cache/): local Qdrant state for vector stores (gitignored).

## Documentation

- [doc/README.md](doc/README.md): entry point and index for system docs.
- [doc/adr/README.md](doc/adr/README.md): Architecture Decision Records (ADR) index.
- [doc/architecture/system_architecture.md](doc/architecture/system_architecture.md): system overview and design principles.
- [doc/architecture/vectorstores.md](doc/architecture/vectorstores.md): vector store setup and sync workflow.
- [doc/overview/how_to_plan.md](doc/overview/how_to_plan.md): planner roles, artifacts, and flow.
- [doc/overview/how_to_plan.md](doc/overview/how_to_plan.md): step-by-step planning workflow and cadence.
- [doc/overview/artefact_flow.md](doc/overview/artefact_flow.md): end-to-end artefact flow with detail diagrams.
- [doc/architecture/renderer.md](doc/architecture/renderer.md): JSON-to-Markdown sidecar rendering.
- [doc/runbooks/validation.md](doc/runbooks/validation.md): validate pipeline outputs against schemas.
- [doc/architecture/subsystems/data_pipeline.md](doc/architecture/subsystems/data_pipeline.md): pipeline entrypoints, outputs, and defaults.
- [doc/overview/planning_principles.md](doc/overview/planning_principles.md): planning guardrails for scope, timing, and reports.
- [doc/architecture/workspace.md](doc/architecture/workspace.md): local workspace layout and rules.
- [doc/architecture/schema_versioning.md](doc/architecture/schema_versioning.md): schema change policy and compatibility.
- [doc/architecture/deployment.md](doc/architecture/deployment.md): environment setup and deployment notes.

## Quick start

1. Copy `.env.example` to `.env` and fill in `RPS_LLM_API_KEY` and `ATHLETE_ID` (Intervals.icu).
2. Add documents under `specs/knowledge/_shared/sources/` and update `specs/knowledge/all_agents/manifest.yaml`.
3. Run `python scripts/bundle_schemas.py` (build bundled schemas for retrieval).
4. Vector store sync runs in the UI background; use `python scripts/smoke_vectorstores.py` for manual verification.

Per-agent model overrides (optional):

```
RPS_LLM_MODEL=openai/gpt-5-mini
RPS_LLM_MODEL_WEEK_PLANNER=openai/gpt-5-mini
RPS_LLM_MODEL_WORKOUT_BUILDER=openai/gpt-5-nano
```

## Build checklist

Prerequisites:

- Python 3.11+ (3.14 works)
- `pip` / virtualenv recommended

1. Copy `.env.example` to `.env` and set required keys.
2. Install dependencies (`pip install -r requirements.txt` or `pip install -e .`).
3. Build bundled schemas: `python scripts/bundle_schemas.py`.
4. Vector store sync runs in the UI background; use `python scripts/smoke_vectorstores.py` for manual verification.
5. Smoke test: `python scripts/smoke_vectorstores.py --store vs_rps_all_agents`.
6. Run data pipeline via the UI (Refresh Intervals Data) or manually with the module entrypoint (see Data pipeline below).
7. Validate outputs: `python scripts/validate_outputs.py`.

### Logging (env)

Log files are written to `runtime/athletes/<athlete_id>/logs/rps.log` with rotation.

Optional env vars:
- `RPS_LOG_ROTATE_MB=50` (rotate when size exceeds MB)
- `RPS_LOG_RETENTION_DAYS=7` (delete rotated logs older than N days)
- `RPS_RUN_RETENTION_DAYS=7` (delete run history older than N days; clears done/failed queues)

## Testing

- UI changes must include Streamlit AppTest coverage in `tests/` (`streamlit.testing.v1.AppTest`).
- UI smoke test (manual): `PYTHONPATH=src streamlit run src/rps/ui/streamlit_app.py`
- Intervals pipeline help (safe CLI smoke): `PYTHONPATH=src python3 src/rps/data_pipeline/intervals_data.py --help`
- Run tests with `pytest -q`.

## Data pipeline (Intervals.icu)

- Set `ATHLETE_ID`, `API_KEY`, and `BASE_URL` in `.env`.
- Manual run: `PYTHONPATH=src python3 src/rps/data_pipeline/intervals_data.py --year 2026 --week 6`
- Validate outputs (latest): `python scripts/validate_outputs.py`
- Validate outputs (week): `python scripts/validate_outputs.py --year 2026 --week 6`

Outputs land in `runtime/athletes/<athlete_id>/data/` and are mirrored to `runtime/athletes/<athlete_id>/latest/`.

### Formatting & rounding policy

`src/rps/data_pipeline/intervals_data.py` applies a single rounding policy to all steps:

- Integer outputs: columns ending with `(W)`, `(bpm)`, `(rpm)`, `(J)`, `(kJ)` plus `Load (TSS)`, `Strain Score`,
  `Power Load`, `HR Load (HRSS)`, `Calories (kcal)`, `CTL (Fitness)`, `ATL (Fatigue)`, `Power/HR Z2 Time (min)`.
- One decimal: distance/speed/elevation/temp plus `Pa:Hr (HR drift)` and `Decoupling (%)`.
- Two decimals: ratio/efficiency/intensity/variability/polarization plus derived FIR/VO2/FTP and durability fields.
- Percent-int: `Compliance (%)`, `Sweet Spot Min (%FTP)`, `Sweet Spot Max (%FTP)`.

## Workspace usage

```python
from datetime import date

from rps.workspace import ArtifactType, Workspace

ws = Workspace.for_athlete("ath_001")
ws.ensure()

week_key = ws.current_week_key(date.today())
phase = ws.current_phase(week_key, phase_length_weeks=4)
ws.put(
    ArtifactType.WEEK_PLAN,
    version_key=week_key,
    payload={"week": week_key, "sessions": []},
    producer_agent="week_planner",
    run_id="run_2026-06_week_001",
)

print(ws.list_versions(ArtifactType.WEEK_PLAN))
print(phase.range_key)
print(phase.start_week, phase.end_week)
```

```python
from rps.workspace import ArtifactType, Authority, Workspace
from rps.workspace.helpers import upstream_ref

ws = Workspace.for_athlete("ath_001")

ws.guard_put(
    ArtifactType.WEEK_PLAN,
    version_key="2026-06",
    payload={"week": "2026-06", "sessions": []},
    producer_agent="week_planner",
    run_id="run_2026-06_week_001",
    authority=Authority.STRUCTURAL,
    trace_upstream=[
        upstream_ref(
            ArtifactType.PHASE_STRUCTURE.value,
            ws.latest_version_key(ArtifactType.PHASE_STRUCTURE),
        )
    ],
)
```

## Schema validation

- Place your JSON schemas in `specs/schemas/` (including all `$ref` targets).
- Use `Workspace.put_validated(...)` or `ValidatedWorkspace` to validate before saving.
- Envelope vs raw documents are detected automatically (e.g. `workouts.schema.json` is raw).
- Optional: run `python scripts/check_schema_refs.py` to verify all `$ref` files exist.

```python
from pathlib import Path

from rps.workspace import ArtifactType, Authority, Workspace

ws = Workspace.for_athlete("ath_001")
ws.put_validated(
    ArtifactType.PHASE_STRUCTURE,
    version_key="2026-06--2026-09",
    payload={"example": True},
    payload_meta={
        "schema_id": "PhaseStructureInterface",
        "schema_version": "1.0",
        "version": "1.0",
        "authority": "Binding",
        "owner_agent": "Phase-Architect",
        "iso_week_range": {"start": {"year": 2026, "week": 6}, "end": {"year": 2026, "week": 9}},
        "trace_upstream": [],
    },
    producer_agent="phase_architect",
    run_id="run_2026-06_phase_001",
    schema_dir=Path("specs/schemas"),
)
```

## Artefact renderer

Render human-readable sidecars for JSON artefacts:

```bash
PYTHONPATH=src python3 -c "from pathlib import Path; from rps.rendering.renderer import render_json_sidecar; render_json_sidecar(Path('specs/kpi_profiles/kpi_profile_des_brevet_200_400_km_masters.json'))"
```

## Vector store runtime

- The UI background sync writes `runtime/vectorstores_state.json` with collection IDs (use `scripts/smoke_vectorstores.py` to verify).
- Use `rps.openai.runtime.resolve_vectorstore_ids(...)` to attach the agent store.
- Load prompts from disk with `rps.prompts.loader.agent_system_prompt(...)`.

## Planning workflows

All planning flows are UI-driven now. Use:

- Plan Hub for season/phase/week/workouts planning runs.
- Performance pages for Report and Feed Forward runs.

For CI/smoke checks, use the CLI helpers listed above (e.g., `intervals_data.py --help`) and the Streamlit UI.

## Notes

- Vector stores are remote state; this repo only keeps sources + manifests.
- Shared knowledge should be referenced from each agent manifest via `../_shared/...` paths (single store per agent).
- Local artifacts live under `runtime/athletes/<athlete_id>/` and are managed by `rps.workspace`.
