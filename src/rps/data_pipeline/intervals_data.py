#!/usr/bin/env python3
"""Fetch Intervals.icu data and compile activities_actual + activities_trend outputs.

This script is the single data-pipeline entrypoint for activities_* artefacts.
"""

from __future__ import annotations

import argparse
import logging
from datetime import timedelta
from pathlib import Path

from requests.auth import HTTPBasicAuth

from rps.data_pipeline.common import (
    athlete_latest_dir,
    configure_logging,
    load_env,
    require_env,
    resolve_athlete_id,
)
from rps.data_pipeline.intervals_activities_actual import compile_activities_actual
from rps.data_pipeline.intervals_activities_trend import compile_activities_trend
from rps.data_pipeline.intervals_api_client import (
    session,
)
from rps.data_pipeline.intervals_date_utils import (
    DEFAULT_WEEKS,
    iso_week_to_dates,
    parse_args,
    parse_ymd,
    resolve_default_range,
)
from rps.data_pipeline.intervals_export import export_range
from rps.data_pipeline.intervals_historical_baseline import compile_historical_baseline
from rps.data_pipeline.intervals_wellness import write_wellness
from rps.data_pipeline.intervals_zone_model import write_zone_model


def run_pipeline(args: argparse.Namespace, logger: logging.Logger | None = None) -> int:
    """Run the end-to-end Intervals.icu pipeline."""
    load_env()
    if logger is None:
        logger = configure_logging(Path(__file__).stem)
    athlete_id = args.athlete or resolve_athlete_id()
    api_key = require_env("API_KEY")
    base_url = require_env("BASE_URL")
    logger.info("Intervals pipeline athlete=%s base_url=%s", athlete_id, base_url)

    session.auth = HTTPBasicAuth("API_KEY", api_key)
    has_week = args.year is not None and args.week is not None
    has_range = args.from_date is not None and args.to_date is not None

    if has_week and has_range:
        raise SystemExit("Provide either --year/--week OR --from/--to, not both.")

    if has_week:
        _, end_date = iso_week_to_dates(args.year, args.week)
        from_date = end_date - timedelta(days=90)
        to_date = end_date
    elif has_range:
        try:
            from_date = parse_ymd(args.from_date)
            to_date = parse_ymd(args.to_date)
        except ValueError as err:
            raise SystemExit("Invalid date format. Expected YYYY-MM-DD, e.g. --from 2025-10-28") from err
        if from_date > to_date:
            raise SystemExit(f"--from {from_date} is after --to {to_date}.")
    else:
        from_date, to_date = resolve_default_range(weeks=DEFAULT_WEEKS)

    logger.info("Intervals pipeline range from=%s to=%s", from_date, to_date)
    latest_dir = athlete_latest_dir(athlete_id)

    print("[1/5] Fetching athlete settings + zone model...")
    logger.info("Stage 1: zone model")
    write_zone_model(
        athlete_id=athlete_id,
        base_url=base_url,
        latest_dir=latest_dir,
        skip_validate=args.skip_validate,
    )

    print("[2/5] Fetching wellness data...")
    logger.info("Stage 2: wellness data")
    write_wellness(
        athlete_id=athlete_id,
        base_url=base_url,
        from_date=from_date,
        to_date=to_date,
        skip_validate=args.skip_validate,
    )

    print("[3/5] Fetching activity data from Intervals.icu...")
    logger.info("Stage 3: activity data")
    export_csv = export_range(
        athlete_id=athlete_id,
        base_url=base_url,
        from_date=from_date,
        to_date=to_date,
    )

    print("[4/5] Compiling activities_actual (latest week)...")
    logger.info("Stage 4: activities_actual")
    compile_activities_actual(
        athlete_id=athlete_id,
        input_csv=export_csv,
        skip_validate=args.skip_validate,
    )

    print("[5/6] Compiling activities_trend...")
    logger.info("Stage 5: activities_trend")
    compile_activities_trend(
        athlete_id=athlete_id,
        input_csv=export_csv,
        skip_validate=args.skip_validate,
    )

    print("[6/6] Compiling historical baseline...")
    logger.info("Stage 6: historical_baseline years=%s", args.historical_years)
    compile_historical_baseline(
        athlete_id=athlete_id,
        base_url=base_url,
        historical_years=args.historical_years,
        skip_validate=args.skip_validate,
    )

    logger.info("Pipeline complete latest_dir=%s", latest_dir)
    return 0


def main() -> int:
    args = parse_args()
    return run_pipeline(args)


if __name__ == "__main__":
    raise SystemExit(main())
