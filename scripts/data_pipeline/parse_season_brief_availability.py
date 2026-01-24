#!/usr/bin/env python3
"""Parse Season Brief availability table into AVAILABILITY artefact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    # Allow running the script directly without installing the package.
    sys.path.insert(0, str(ROOT))

from scripts.data_pipeline.common import (  # noqa: E402
    athlete_data_dir,
    athlete_latest_dir,
    configure_logging,
    load_env,
    record_index_write,
    resolve_athlete_id,
    resolve_schema_dir,
    resolve_workspace_root,
)
from app.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise  # noqa: E402


DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

DAY_ALIASES = {
    "mon": "Mon",
    "monday": "Mon",
    "mo": "Mon",
    "montag": "Mon",
    "tue": "Tue",
    "tues": "Tue",
    "tuesday": "Tue",
    "di": "Tue",
    "dienstag": "Tue",
    "wed": "Wed",
    "wednesday": "Wed",
    "mi": "Wed",
    "mittwoch": "Wed",
    "thu": "Thu",
    "thur": "Thu",
    "thurs": "Thu",
    "thursday": "Thu",
    "do": "Thu",
    "donnerstag": "Thu",
    "fri": "Fri",
    "friday": "Fri",
    "fr": "Fri",
    "freitag": "Fri",
    "sat": "Sat",
    "saturday": "Sat",
    "sa": "Sat",
    "samstag": "Sat",
    "sun": "Sun",
    "sunday": "Sun",
    "so": "Sun",
    "sonntag": "Sun",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse Season Brief weekly availability table into AVAILABILITY artefact."
    )
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")
    parser.add_argument(
        "--year",
        type=int,
        help="Season year (YYYY). Optional; derived from Season Brief if omitted.",
    )
    parser.add_argument("--season-brief-path", type=Path, help="Explicit season brief path.")
    parser.add_argument("--skip-validate", action="store_true", help="Skip JSON schema validation.")
    return parser.parse_args()


def _load_season_brief(athlete_root: Path, year: int | None, explicit: Path | None) -> tuple[Path, str]:
    if explicit:
        if not explicit.exists():
            raise FileNotFoundError(f"Season brief not found: {explicit}")
        return explicit, explicit.read_text(encoding="utf-8")

    patterns = ["season_brief_*.md"]
    if year is not None:
        patterns.insert(0, f"season_brief_{year}.md")
    candidates: list[Path] = []
    for folder in (athlete_root / "inputs", athlete_root / "latest"):
        if not folder.exists():
            continue
        for pattern in patterns:
            candidates.extend(folder.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            "No season brief found. Place season_brief_*.md in inputs/ or latest/."
        )

    def sort_key(path: Path) -> tuple[int, float]:
        match_year = 0
        if year is not None and path.name.startswith(f"season_brief_{year}."):
            match_year = 1
        return (match_year, path.stat().st_mtime)

    best = max(candidates, key=sort_key)
    return best, best.read_text(encoding="utf-8")


def _parse_date(label: str, text: str) -> date | None:
    pattern = rf"{re.escape(label)}\\s*:\\s*(\\d{{4}}-\\d{{2}}-\\d{{2}})"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _extract_year(season_text: str, season_path: Path) -> int | None:
    match = re.search(
        r"^\s*[-*]?\s*Year\s*:\s*(\d{4})\s*$",
        season_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if match:
        return int(match.group(1))
    filename_match = re.search(r"season_brief_(\d{4})\.md", season_path.name)
    if filename_match:
        return int(filename_match.group(1))
    return None


def _iso_week_str(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-{iso.week:02d}"


def _normalize_weekday(raw: str) -> str:
    key = raw.strip().lower()
    key = re.sub(r"[^a-zäöü]+", "", key)
    if key in DAY_ALIASES:
        return DAY_ALIASES[key]
    raise ValueError(f"Unrecognized weekday: '{raw}'")


def _parse_bool(raw: str) -> bool:
    val = raw.strip().lower()
    if val in {"y", "yes", "true", "1", "ja"}:
        return True
    if val in {"n", "no", "false", "0", "nein"}:
        return False
    raise ValueError(f"Unrecognized boolean value: '{raw}'")


def _parse_travel_risk(raw: str) -> str:
    val = raw.strip().lower()
    if val in {"low", "niedrig"}:
        return "low"
    if val in {"med", "medium", "mid", "mittel"}:
        return "med"
    if val in {"high", "hoch"}:
        return "high"
    raise ValueError(f"Unrecognized travel risk: '{raw}'")


def _parse_hours(raw: str) -> tuple[float, float, float, bool]:
    text = raw.strip().lower()
    locked = "locked" in text
    text = text.replace(",", ".")
    text = re.sub(r"(hours?|hrs?|h)", "", text)
    text = text.replace("/", " ")
    text = text.strip()

    range_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)", text)
    if range_match:
        hours_min = float(range_match.group(1))
        hours_max = float(range_match.group(2))
        hours_typical = round((hours_min + hours_max) / 2, 2)
        return hours_min, hours_typical, hours_max, locked

    num_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if num_match:
        value = float(num_match.group(1))
        return value, value, value, locked

    if locked:
        return 0.0, 0.0, 0.0, True

    raise ValueError(f"Unrecognized hours value: '{raw}'")


def _extract_availability_table(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        if "weekly availability table" in line.lower():
            start_idx = idx
            break
    if start_idx is None:
        raise ValueError("Season Brief missing 'Weekly availability table' section.")

    header_idx = None
    for idx in range(start_idx, len(lines)):
        if lines[idx].strip().startswith("|") and "day" in lines[idx].lower():
            header_idx = idx
            break
    if header_idx is None:
        raise ValueError("Availability table header not found.")

    rows: list[dict[str, str]] = []
    for idx in range(header_idx + 1, len(lines)):
        line = lines[idx].strip()
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if all(re.match(r"^[-:\\s]+$", cell) for cell in cells):
            continue
        rows.append(
            {
                "day": cells[0],
                "hours": cells[1],
                "indoor": cells[2],
                "travel": cells[3],
            }
        )
    if not rows:
        raise ValueError("Availability table contains no rows.")
    return rows


def build_availability_payload(
    *,
    season_brief_ref: str,
    season_text: str,
    season_year: int,
) -> dict:
    table_rows = _extract_availability_table(season_text)

    entries = []
    seen_days: set[str] = set()
    for row in table_rows:
        weekday = _normalize_weekday(row["day"])
        if weekday in seen_days:
            raise ValueError(f"Duplicate weekday in table: {weekday}")
        seen_days.add(weekday)

        hours_min, hours_typical, hours_max, locked = _parse_hours(row["hours"])
        entry = {
            "weekday": weekday,
            "hours_min": hours_min,
            "hours_typical": hours_typical,
            "hours_max": hours_max,
            "indoor_possible": _parse_bool(row["indoor"]),
            "travel_risk": _parse_travel_risk(row["travel"]),
            "locked": locked,
            "source_hours_text": row["hours"],
            "source_indoor_text": row["indoor"],
            "source_travel_text": row["travel"],
        }
        entries.append(entry)

    required_days = set(DAY_ORDER)
    if seen_days != required_days:
        missing = sorted(required_days - seen_days)
        extra = sorted(seen_days - required_days)
        raise ValueError(f"Availability table must include all weekdays. Missing={missing}, extra={extra}")

    entries.sort(key=lambda item: DAY_ORDER.index(item["weekday"]))
    weekly_hours = {
        "min": round(sum(item["hours_min"] for item in entries), 2),
        "typical": round(sum(item["hours_typical"] for item in entries), 2),
        "max": round(sum(item["hours_max"] for item in entries), 2),
    }
    fixed_rest_days = [item["weekday"] for item in entries if item["locked"]]

    today = datetime.now(timezone.utc).date()
    valid_from = _parse_date("Valid-From", season_text)
    valid_to = _parse_date("Valid-To", season_text)
    start_day = valid_from or today
    if start_day < today:
        start_day = today
    end_day = valid_to or date(season_year, 12, 31)
    if end_day.year != season_year:
        end_day = date(season_year, 12, 31)
    if start_day > end_day:
        raise ValueError("Availability temporal scope invalid: start date after end date.")

    iso_week = _iso_week_str(start_day)
    last_iso_week = date(season_year, 12, 28).isocalendar().week
    iso_week_range = f"{iso_week}--{season_year}-{last_iso_week:02d}"

    run_ts = datetime.now(timezone.utc)
    meta = {
        "artifact_type": "AVAILABILITY",
        "schema_id": "AvailabilityInterface",
        "schema_version": "1.0",
        "version": "1.0",
        "authority": "Binding",
        "owner_agent": "Data-Pipeline",
        "run_id": f"{run_ts.strftime('%Y%m%d-%H%M%S')}-data-pipeline-availability",
        "created_at": run_ts.isoformat(),
        "scope": "Shared",
        "iso_week": iso_week,
        "iso_week_range": iso_week_range,
        "temporal_scope": {
            "from": start_day.isoformat(),
            "to": end_day.isoformat(),
        },
        "trace_upstream": [
            {
                "artifact": "season_brief",
                "version": "1.0",
                "run_id": season_brief_ref,
            }
        ],
        "trace_data": [],
        "trace_events": [],
        "notes": "Derived from Season Brief availability table.",
    }

    return {
        "meta": meta,
        "data": {
            "season_brief_ref": season_brief_ref,
            "availability_table": entries,
            "weekly_hours": weekly_hours,
            "fixed_rest_days": fixed_rest_days,
            "notes": "Season Brief weekday availability normalized.",
        },
    }


def main() -> int:
    load_env()
    logger = configure_logging(Path(__file__).stem)
    args = parse_args()
    athlete_id = args.athlete or resolve_athlete_id()

    athlete_root = resolve_workspace_root() / athlete_id
    season_path, season_text = _load_season_brief(athlete_root, args.year, args.season_brief_path)
    season_ref = season_path.name
    logger.info("Parse availability athlete=%s season_brief=%s", athlete_id, season_ref)
    season_year = args.year or _extract_year(season_text, season_path)
    if season_year is None:
        raise ValueError("Season year not found. Provide --year or include 'Year: YYYY' in Season Brief.")

    payload = build_availability_payload(
        season_brief_ref=season_ref,
        season_text=season_text,
        season_year=season_year,
    )

    validator = SchemaRegistry(resolve_schema_dir()).validator_for("availability.schema.json")
    if not args.skip_validate:
        try:
            validate_or_raise(validator, payload)
        except SchemaValidationError as exc:
            print("Availability validation failed:")
            for err in exc.errors:
                print(f"  - {err}")
            return 1

    iso_week = payload["meta"]["iso_week"]
    year_str, week_str = iso_week.split("-", 1)
    data_dir = athlete_data_dir(athlete_id) / year_str / week_str
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / f"availability_{iso_week}.json"
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    latest_dir = athlete_latest_dir(athlete_id)
    latest_dir.mkdir(parents=True, exist_ok=True)
    latest_file = latest_dir / "availability.json"
    latest_file.write_bytes(out_file.read_bytes())
    logger.info("Wrote availability iso_week=%s path=%s", iso_week, out_file)

    record_index_write(
        athlete_id=athlete_id,
        artifact_type="AVAILABILITY",
        version_key=iso_week,
        path=out_file,
        run_id=payload["meta"]["run_id"],
        producer_agent=payload["meta"]["owner_agent"],
        created_at=payload["meta"]["created_at"],
        iso_week=payload["meta"]["iso_week"],
        iso_week_range=payload["meta"]["iso_week_range"],
    )

    print(f"Availability written: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
