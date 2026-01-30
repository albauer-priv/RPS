#!/usr/bin/env python3
"""Send planned workouts to Intervals.icu via the Events Bulk API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from rps.data_pipeline.intervals_post import load_events, post_events  # noqa: E402
from scripts.data_pipeline.common import (
    athlete_latest_dir,
    configure_logging,
    load_env,
    require_env,
    resolve_athlete_id,
)

TIMEOUT_S = 30

def parse_args(default_base_url: str) -> argparse.Namespace:
    """Parse CLI arguments for posting workouts."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")
    parser.add_argument(
        "--json",
        "-j",
        help=(
            "Path to JSON file with events array "
            "(default: var/athletes/<athlete_id>/latest/workouts.json)"
        ),
    )
    parser.add_argument("--base-url", default=default_base_url, help="Base API URL")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_S, help="HTTP timeout (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; don't send request")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def main() -> int:
    """CLI entry point for posting workout events."""
    load_env()
    logger = configure_logging(Path(__file__).stem)

    base_url = require_env("BASE_URL")
    args = parse_args(default_base_url=base_url)
    athlete_id = args.athlete or resolve_athlete_id()
    api_key = require_env("API_KEY")

    json_path = (
        Path(args.json)
        if args.json
        else athlete_latest_dir(athlete_id) / "workouts.json"
    )
    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        logger.error("JSON file not found path=%s", json_path)
        return 2

    try:
        events = load_events(json_path)
    except Exception as exc:
        print(f"ERROR: Failed to load/validate JSON: {exc}", file=sys.stderr)
        logger.error("Failed to load/validate JSON: %s", exc)
        return 2
    logger.info("Post workouts athlete=%s events=%d json=%s", athlete_id, len(events), json_path)

    result = post_events(
        events=events,
        athlete_id=athlete_id,
        base_url=args.base_url,
        api_key=api_key,
        timeout_s=args.timeout,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    if args.verbose or args.dry_run:
        print("== Request Preview ==")
        print("POST", result.get("url"))
        print("Auth: (API_KEY, '')")
        print("Content-Type: application/json")
    if args.dry_run:
        print("Dry-run complete. No request sent.")
        logger.info("Dry run; no request sent")
        return 0
    print(f"Status: {result.get('status')}")
    if isinstance(result.get("response"), (dict, list)):
        logger.info("Posted events status=%s", result.get("status"))
        print(result.get("response"))
    else:
        print(result.get("response"))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
