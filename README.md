# my-openai-platform

Scaffold for OpenAI hosted vector stores with a unified, versioned knowledge base.

## Layout

- `src/rps/`: app code and OpenAI helpers.
- `doc/`: system documentation.
- `prompts/`: shared + per-agent prompts.
- `knowledge/`: versioned sources and manifests (no embeddings in repo).
- `scripts/`: sync/list/prune helpers for vector stores.
- `scripts/data_pipeline/`: Intervals.icu data pipeline scripts.
- `legacy/`: artifacts to migrate from the predecessor project (gitignored).
- `var/athletes/`: runtime state for local athlete workspaces (gitignored).
- `.cache/`: local sync state for vector stores (gitignored).

## Documentation

- `doc/README.md`: entry point and index for system docs.
- `doc/adr/README.md`: Architecture Decision Records (ADR) index.
- `doc/system_architecture.md`: system overview and design principles.
- `doc/vectorstores.md`: vector store setup and sync workflow.
- `doc/how_to_plan.md`: planner roles, artifacts, and flow.
- `doc/how_to_plan.md`: step-by-step planning workflow and cadence.
- `doc/artefact_flow_overview_and_detail.md`: end-to-end artefact flow with detail diagrams.
- `doc/artefact_renderer.md`: JSON-to-Markdown sidecar rendering.
- `doc/validation.md`: validate pipeline outputs against schemas.
- `doc/data_pipeline.md`: pipeline entrypoints, outputs, and defaults.
- `doc/planning_principles.md`: planning guardrails for scope, timing, and reports.
- `doc/workspace.md`: local workspace layout and rules.
- `doc/schema_versioning.md`: schema change policy and compatibility.
- `doc/deployment.md`: environment setup and deployment notes.
- `doc/recommended_models.md`: model selection guidance for cost-optimized runs.

## Quick start

1. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` and `ATHLETE_ID` (Intervals.icu).
2. Add documents under `knowledge/_shared/sources/` and update `knowledge/all_agents/manifest.yaml`.
3. Run `python scripts/bundle_schemas.py` (build bundled schemas for retrieval).
4. (Deprecated) `python scripts/sync_vectorstores.py` — use the UI background sync (or run only for manual recovery).

Per-agent model overrides (optional):

```
OPENAI_MODEL=gpt-4.1
OPENAI_MODEL_WEEK_PLANNER=gpt-4.1-mini
OPENAI_MODEL_WORKOUT_BUILDER=gpt-4.1-mini
```

## Streamlit coach experiment

The optional coach-only streaming UI uses the in-repo chat implementation.

```bash
PYTHONPATH=src streamlit run src/rps/ui/coach_experiment.py
```

## Build checklist

Prerequisites:

- Python 3.11+ (3.14 works)
- `pip` / virtualenv recommended

1. Copy `.env.example` to `.env` and set required keys.
2. Install dependencies (`pip install -r requirements.txt` or `pip install -e .`).
3. Build bundled schemas: `python scripts/bundle_schemas.py`.
4. (Deprecated) Sync vector stores: `python scripts/sync_vectorstores.py` — UI now runs background sync; use CLI only for manual recovery.
5. Smoke test: `python scripts/smoke_vectorstores.py --store vs_rps_all_agents --force-tool`.
6. Run data pipeline: use the current CLI entrypoint for `parse-intervals` (do not use deprecated `rps.main`).
7. Validate outputs: `python scripts/validate_outputs.py`.

### Logging (env)

Log files are written to `var/athletes/<athlete_id>/logs/rps.log` with rotation.

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
- All-in-one: `python -m rps.main parse-intervals --year 2026 --week 6`
- (Deprecated) Post workouts: `python scripts/data_pipeline/post_workout.py --json var/athletes/<athlete_id>/latest/intervals_workouts.json` — prefer Plan → Workouts UI.
- Validate outputs (latest): `python scripts/validate_outputs.py`
- Validate outputs (week): `python scripts/validate_outputs.py --year 2026 --week 6`

Outputs land in `var/athletes/<athlete_id>/data/` and are mirrored to `var/athletes/<athlete_id>/latest/`.

### Formatting & rounding policy

`python -m rps.main parse-intervals` applies a single rounding policy to all steps:

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

- Place your JSON schemas in `schemas/` (including all `$ref` targets).
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
    schema_dir=Path("schemas"),
)
```

## Artefact renderer

Render human-readable sidecars for JSON artefacts:

```bash
PYTHONPATH=src python3 -c "from pathlib import Path; from rps.rendering.renderer import render_json_sidecar; render_json_sidecar(Path('kpi_profiles/kpi_profile_des_brevet_200_400_km_masters.json'))"
```

## Vector store runtime

- (Deprecated) `scripts/sync_vectorstores.py` writes `.cache/vectorstores_state.json` with store IDs (UI background sync maintains this state now).
- Use `rps.openai.runtime.resolve_vectorstore_ids(...)` to attach the agent store.
- Load prompts from disk with `rps.prompts.loader.agent_system_prompt(...)`.

## Agent runner

```bash
PYTHONPATH=src python -m rps.main \\
  --agent week_planner \\
  --text "Plane Woche 2026-06 basierend auf der aktuellen Phase und dem KPI Profil."
```

```bash
PYTHONPATH=src python -m rps.main plan-week \\
  --year 2026 \\
  --week 6 \\
  --run-id run_2026_06
```

If `ATHLETE_ID` is set in `.env`, the `--athlete` flag is optional.
Use `--no-file-search` to disable forced vector store retrieval.

## Season planning (two-step)

Generate scenarios first, then create the season plan using the selected scenario:

```bash
PYTHONPATH=src python -m rps.main run-agent \
  --agent season_scenario \
  --task CREATE_SEASON_SCENARIOS \
  --text "Create season scenarios for ISO week 2026-06." \
  --run-id season_scenarios_2026_w06
```

```bash
PYTHONPATH=src python -m rps.main run-agent \
  --agent season_planner \
  --task CREATE_SEASON_PLAN \
  --text "Create the season plan for ISO week 2026-06 using scenario A." \
  --run-id season_plan_2026_w06
```

Scenarios are written to `.cache/season_scenarios/<run-id>.md` by default.

## Notes

- Vector stores are remote state; this repo only keeps sources + manifests.
- Shared knowledge should be referenced from each agent manifest via `../_shared/...` paths (single store per agent).
- Local artifacts live under `var/athletes/<athlete_id>/` and are managed by `rps.workspace`.
