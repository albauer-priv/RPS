#!/usr/bin/env python3
"""Send planned workouts to Intervals.icu via the Events Bulk API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

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


def load_events(json_path: Path) -> list[dict[str, Any]]:
    """Load and validate the events payload from a JSON file."""
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of event objects")
    for i, ev in enumerate(data):
        if not isinstance(ev, dict):
            raise ValueError(f"Event #{i} must be an object")
        for required in ("start_date_local", "category", "type", "name"):
            if required not in ev:
                raise ValueError(f"Event #{i} missing required field: '{required}'")
    return data


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

    url = f"{args.base_url.rstrip('/')}/athlete/{athlete_id}/events/bulk"

    if args.verbose or args.dry_run:
        print("== Request Preview ==")
        print("POST", url)
        print("Auth: (API_KEY, '')")
        print("Content-Type: application/json")
        print("Payload:", json.dumps(events, ensure_ascii=False, indent=2))

    if args.dry_run:
        print("Dry-run complete. No request sent.")
        logger.info("Dry run; no request sent")
        return 0

    try:
        resp = requests.post(
            url,
            auth=HTTPBasicAuth("API_KEY", api_key),
            headers={"Content-Type": "application/json"},
            json=events,
            timeout=args.timeout,
        )
    except requests.RequestException as exc:
        print(f"ERROR: HTTP request failed: {exc}", file=sys.stderr)
        logger.error("HTTP request failed: %s", exc)
        return 1

    print(f"Status: {resp.status_code}")
    logger.info("Posted events status=%s", resp.status_code)
    ctype = resp.headers.get("Content-Type", "")
    if "application/json" in ctype:
        try:
            print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
        except Exception:
            print(resp.text)
    else:
        print(resp.text)

    return 0 if resp.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
