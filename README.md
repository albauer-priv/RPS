# my-openai-platform

Scaffold for OpenAI hosted vector stores with versioned, per-agent knowledge.

## Layout

- `src/app/`: app code and OpenAI helpers.
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
- `doc/system_architecture.md`: system overview and design principles.
- `doc/vectorstores.md`: vector store setup and sync workflow.
- `doc/planners.md`: planner roles, artifacts, and flow.
- `doc/how_to_plan.md`: step-by-step planning workflow and cadence.
- `doc/artefact_flow_overview_and_detail.md`: end-to-end artefact flow with detail diagrams.
- `doc/artefact_renderer.md`: JSON-to-Markdown sidecar rendering.
- `doc/validation.md`: validate pipeline outputs against schemas.
- `doc/data_pipeline.md`: pipeline entrypoints, outputs, and defaults.
- `doc/workspace.md`: local workspace layout and rules.
- `doc/schema_versioning.md`: schema change policy and compatibility.
- `doc/deployment.md`: environment setup and deployment notes.
- `doc/recommended_models.md`: model selection guidance for cost-optimized runs.

## Quick start

1. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` and `ATHLETE_ID` (Intervals.icu).
2. Add documents under `knowledge/<agent>/sources/` and update `manifest.yaml`.
3. Run `python scripts/bundle_schemas.py` (build bundled schemas for retrieval).
4. Run `python scripts/sync_vectorstores.py`.

Per-agent model overrides (optional):

```
OPENAI_MODEL=gpt-4.1
OPENAI_MODEL_MICRO_PLANNER=gpt-4.1-mini
OPENAI_MODEL_WORKOUT_BUILDER=gpt-4.1-mini
```

## Build checklist

Prerequisites:

- Python 3.11+ (3.14 works)
- `pip` / virtualenv recommended

1. Copy `.env.example` to `.env` and set required keys.
2. Install dependencies (`pip install -r requirements.txt` or `pip install -e .`).
3. Build bundled schemas: `python scripts/bundle_schemas.py`.
4. Sync vector stores: `python scripts/sync_vectorstores.py`.
5. Smoke test: `python scripts/smoke_vectorstores.py --agent micro_planner --force-tool`.
6. Run data pipeline: `python scripts/data_pipeline/get_intervals_data.py`.
7. Validate outputs: `python scripts/validate_outputs.py`.

## Data pipeline (Intervals.icu)

- Set `ATHLETE_ID`, `API_KEY`, and `BASE_URL` in `.env`.
- All-in-one: `python scripts/data_pipeline/get_intervals_data.py --year 2026 --week 6`
- Legacy (deprecated): `intervals_export.py`, `compile_activities_actual.py`, `compile_activities_trend.py`
- Post workouts: `python scripts/data_pipeline/post_workout.py --json var/athletes/<athlete_id>/latest/intervals_workouts.json`
- Validate outputs (latest): `python scripts/validate_outputs.py`
- Validate outputs (week): `python scripts/validate_outputs.py --year 2026 --week 6`

Outputs land in `var/athletes/<athlete_id>/data/` and are mirrored to `var/athletes/<athlete_id>/latest/`.

### Formatting & rounding policy

`scripts/data_pipeline/get_intervals_data.py` applies a single rounding policy to all steps:

- Integer outputs: columns ending with `(W)`, `(bpm)`, `(rpm)`, `(J)`, `(kJ)` plus `Load (TSS)`, `Strain Score`,
  `Power Load`, `HR Load (HRSS)`, `Calories (kcal)`, `CTL (Fitness)`, `ATL (Fatigue)`, `Power/HR Z2 Time (min)`.
- One decimal: distance/speed/elevation/temp plus `Pa:Hr (HR drift)` and `Decoupling (%)`.
- Two decimals: ratio/efficiency/intensity/variability/polarization plus derived FIR/VO2/FTP and durability fields.
- Percent-int: `Compliance (%)`, `Sweet Spot Min (%FTP)`, `Sweet Spot Max (%FTP)`.

## Workspace usage

```python
from datetime import date

from app.workspace import ArtifactType, Workspace

ws = Workspace.for_athlete("ath_001")
ws.ensure()

week_key = ws.current_week_key(date.today())
block = ws.current_block(week_key, block_length_weeks=4)
ws.put(
    ArtifactType.WORKOUTS_PLAN,
    version_key=week_key,
    payload={"week": week_key, "sessions": []},
    producer_agent="micro_planner",
    run_id="run_2026-06_micro_001",
)

print(ws.list_versions(ArtifactType.WORKOUTS_PLAN))
print(block.range_key)
print(block.start_week, block.end_week)
```

```python
from app.workspace import ArtifactType, Authority, Workspace
from app.workspace.helpers import upstream_ref

ws = Workspace.for_athlete("ath_001")

ws.guard_put(
    ArtifactType.WORKOUTS_PLAN,
    version_key="2026-06",
    payload={"week": "2026-06", "sessions": []},
    producer_agent="micro_planner",
    run_id="run_2026-06_micro_001",
    authority=Authority.STRUCTURAL,
    trace_upstream=[
        upstream_ref(
            ArtifactType.BLOCK_EXECUTION_ARCH.value,
            ws.latest_version_key(ArtifactType.BLOCK_EXECUTION_ARCH),
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

from app.workspace import ArtifactType, Authority, Workspace

ws = Workspace.for_athlete("ath_001")
ws.put_validated(
    ArtifactType.BLOCK_EXECUTION_ARCH,
    version_key="2026-06--2026-09",
    payload={"example": True},
    payload_meta={
        "schema_id": "BlockExecutionArchInterface",
        "schema_version": "1.0",
        "version": "1.0",
        "authority": "Binding",
        "owner_agent": "Meso-Architect",
        "iso_week_range": {"start": {"year": 2026, "week": 6}, "end": {"year": 2026, "week": 9}},
        "trace_upstream": [],
    },
    producer_agent="meso_architect",
    run_id="run_2026-06_meso_001",
    schema_dir=Path("schemas"),
)
```

## Artefact renderer

Render human-readable sidecars for JSON artefacts:

```bash
python3 scripts/artefact_renderer.py knowledge/_shared/sources/kpi_profiles/kpi_profile_des_brevet_200_400_km_masters.json
```

## Vector store runtime

- `scripts/sync_vectorstores.py` writes `.cache/vectorstores_state.json` with store IDs.
- Use `app.openai.runtime.resolve_vectorstore_ids(...)` to attach shared + agent stores.
- Load prompts from disk with `app.prompts.loader.agent_system_prompt(...)`.

## Agent runner

```bash
PYTHONPATH=src python -m app.main \\
  --agent micro_planner \\
  --text "Plane Woche 2026-06 basierend auf dem aktuellen Block und KPI Profil."
```

```bash
PYTHONPATH=src python -m app.main plan-week \\
  --year 2026 \\
  --week 6 \\
  --run-id run_2026_06
```

If `ATHLETE_ID` is set in `.env`, the `--athlete` flag is optional.
Use `--no-file-search` to disable forced vector store retrieval.

## Notes

- Vector stores are remote state; this repo only keeps sources + manifests.
- If you want a shared store, use `knowledge/_shared/`.
- Local artifacts live under `var/athletes/<athlete_id>/` and are managed by `app.workspace`.
