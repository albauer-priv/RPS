#!/usr/bin/env python3
"""Validate data pipeline JSON outputs against the local schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from scripts.data_pipeline.common import (  # noqa: E402
    athlete_data_dir,
    athlete_latest_dir,
    configure_logging,
    load_env,
    resolve_athlete_id,
    resolve_schema_dir,
)
from app.workspace.schema_registry import (  # noqa: E402
    SchemaRegistry,
    SchemaValidationError,
    validate_or_raise,
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for schema validation."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate activities_actual / activities_trend / availability / wellness JSON outputs "
            "against local schemas. Defaults to the latest files for the configured athlete."
        )
    )
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")
    parser.add_argument("--year", type=int, help="ISO year for data directory lookup.")
    parser.add_argument("--week", type=int, help="ISO week for data directory lookup.")
    parser.add_argument("--actual-path", type=Path, help="Explicit activities_actual JSON path.")
    parser.add_argument("--trend-path", type=Path, help="Explicit activities_trend JSON path.")
    parser.add_argument("--availability-path", type=Path, help="Explicit availability JSON path.")
    parser.add_argument("--wellness-path", type=Path, help="Explicit wellness JSON path.")
    return parser.parse_args()


def resolve_paths(
    *,
    athlete_id: str,
    year: int | None,
    week: int | None,
    actual_path: Path | None,
    trend_path: Path | None,
    availability_path: Path | None,
    wellness_path: Path | None,
) -> list[tuple[str, Path]]:
    """Resolve schema files and JSON paths to validate."""
    if (year is None) != (week is None):
        raise ValueError("Provide both --year and --week, or neither.")

    targets: list[tuple[str, Path]] = []
    if actual_path or trend_path or availability_path or wellness_path:
        if actual_path:
            targets.append(("activities_actual.schema.json", actual_path))
        if trend_path:
            targets.append(("activities_trend.schema.json", trend_path))
        if availability_path:
            targets.append(("availability.schema.json", availability_path))
        if wellness_path:
            targets.append(("wellness.schema.json", wellness_path))
        return targets

    if year is not None and week is not None:
        week_str = f"{week:02d}"
        base = athlete_data_dir(athlete_id) / f"{year:04d}" / week_str
        targets.append(
            ("activities_actual.schema.json", base / f"activities_actual_{year}-{week_str}.json")
        )
        targets.append(
            ("activities_trend.schema.json", base / f"activities_trend_{year}-{week_str}.json")
        )
        targets.append(
            ("availability.schema.json", base / f"availability_{year}-{week_str}.json")
        )
        targets.append(
            ("wellness.schema.json", base / f"wellness_{year}-{week_str}.json")
        )
        return targets

    latest = athlete_latest_dir(athlete_id)
    targets.append(("activities_actual.schema.json", latest / "activities_actual.json"))
    targets.append(("activities_trend.schema.json", latest / "activities_trend.json"))
    targets.append(("availability.schema.json", latest / "availability.json"))
    targets.append(("wellness.schema.json", latest / "wellness.json"))
    return targets


def validate_file(registry: SchemaRegistry, schema_file: str, path: Path) -> bool:
    """Validate a JSON file against a schema file."""
    if not path.exists():
        print(f"FAIL: {path} (missing)")
        return False

    doc = json.loads(path.read_text(encoding="utf-8"))
    validator = registry.validator_for(schema_file)
    try:
        validate_or_raise(validator, doc)
    except SchemaValidationError as exc:
        print(f"FAIL: {path} ({schema_file})")
        for err in exc.errors:
            print(f"  - {err}")
        return False
    except Exception as exc:  # pragma: no cover - unexpected validator errors
        print(f"FAIL: {path} ({schema_file})")
        print(f"  - {exc}")
        return False

    print(f"OK: {path} ({schema_file})")
    return True


def main() -> int:
    """Validate outputs and return a process exit code."""
    load_env()
    logger = configure_logging(Path(__file__).stem)
    args = parse_args()
    athlete_id = args.athlete or resolve_athlete_id()

    targets = resolve_paths(
        athlete_id=athlete_id,
        year=args.year,
        week=args.week,
        actual_path=args.actual_path,
        trend_path=args.trend_path,
        availability_path=args.availability_path,
        wellness_path=args.wellness_path,
    )

    logger.info("Validating %d outputs for athlete=%s", len(targets), athlete_id)
    registry = SchemaRegistry(resolve_schema_dir())
    results = [validate_file(registry, schema_file, path) for schema_file, path in targets]
    if all(results):
        logger.info("Validation succeeded for all outputs")
        return 0
    logger.error("Validation failed for one or more outputs")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
