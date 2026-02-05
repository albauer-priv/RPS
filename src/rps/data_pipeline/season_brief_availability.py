"""Parse Season Brief availability table into AVAILABILITY artefact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import re
from typing import Any
import json

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise


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


@dataclass(frozen=True)
class AvailabilityResult:
    """Result for a parsed availability artefact."""
    payload: dict[str, Any]
    output_path: Path


def _iso_week_str(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-{week:02d}"


def _extract_year(text: str, season_path: Path) -> int | None:
    # Use regex whitespace tokens (\s) rather than literal backslash-s.
    match = re.search(r"Year\s*:\s*(\d{4})", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d{4})", season_path.name)
    if match:
        return int(match.group(1))
    return None


def _load_season_brief(
    athlete_root: Path,
    year: int | None,
    explicit: Path | None,
) -> tuple[Path, str]:
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


def load_season_brief(
    athlete_root: Path,
    year: int | None = None,
    explicit: Path | None = None,
) -> tuple[Path, str]:
    """Public Season Brief loader (inputs/ or latest/)."""
    return _load_season_brief(athlete_root, year, explicit)


def _parse_date(label: str, text: str) -> date | None:
    pattern = rf"{re.escape(label)}\s*:\s*(\d{{4}}-\d{{2}}-\d{{2}})"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _normalize_weekday(text: str) -> str:
    key = text.strip().lower()
    if key in DAY_ALIASES:
        return DAY_ALIASES[key]
    raise ValueError(f"Unknown weekday label: {text}")


def _parse_bool(text: str) -> bool:
    value = text.strip().lower()
    if value in {"yes", "y", "true", "ja", "j"}:
        return True
    if value in {"no", "n", "false", "nein"}:
        return False
    raise ValueError(f"Invalid boolean value: {text}")


def _parse_travel_risk(text: str) -> str:
    value = text.strip().lower()
    if value in {"low", "medium", "high"}:
        return "med" if value == "medium" else value
    if value in {"med", "mid"}:
        return "med"
    if value in {"n/a", "none"}:
        return "low"
    raise ValueError(f"Invalid travel risk value: {text}")


def _parse_hours(text: str) -> tuple[float, float, float, bool]:
    trimmed = text.strip().lower()
    locked = "[locked]" in trimmed or "(locked)" in trimmed
    trimmed = trimmed.replace("[locked]", "").replace("(locked)", "").strip()
    if "/ locked" in trimmed:
        locked = True
        trimmed = trimmed.replace("/ locked", "")
    trimmed = trimmed.replace("locked", "").strip()
    if "/" in trimmed:
        trimmed = trimmed.split("/", 1)[0].strip()
    for unit in (" hours", " hour", " hrs", " hr", " h"):
        if trimmed.endswith(unit):
            trimmed = trimmed[: -len(unit)].strip()
    trimmed = trimmed.replace(",", ".").strip()
    if "-" not in trimmed:
        hours = float(trimmed)
        return hours, hours, hours, locked
    parts = [p.strip() for p in trimmed.split("-")]
    if len(parts) == 2:
        min_h = float(parts[0])
        max_h = float(parts[1])
        typical = (min_h + max_h) / 2
        return min_h, typical, max_h, locked
    if len(parts) != 3:
        raise ValueError(f"Invalid hours format: {text}")
    return float(parts[0]), float(parts[1]), float(parts[2]), locked


def _extract_availability_table(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    rows: list[dict[str, str]] = []
    in_table = False
    for line in lines:
        if "weekly availability table" in line.lower():
            in_table = True
            continue
        if in_table and line.strip().startswith("##"):
            break
        if not in_table:
            continue
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        header_cells = [c.strip().lower() for c in cells]
        if (
            header_cells[0] in {"day", "weekday"}
            and "hours" in header_cells[1]
            and "indoor" in header_cells[2]
            and "travel" in header_cells[3]
        ):
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
        raise ValueError("Season Brief missing 'Weekly availability table' section.")
    return rows


def validate_season_brief_text(season_text: str, *, source: str) -> list[str]:
    """Return a list of validation errors for Season Brief interface."""
    errors: list[str] = []
    required_labels = ["Season-ID", "Year", "Athlete-ID", "Valid-From", "Valid-To", "Primary-Objective"]
    for label in required_labels:
        # Primary objective is often written as a heading without a colon.
        if label == "Primary-Objective":
            heading_ok = re.search(r"Primary\s+Objective", season_text, flags=re.IGNORECASE)
            colon_ok = re.search(r"Primary-Objective\s*:", season_text, flags=re.IGNORECASE)
            if not (heading_ok or colon_ok):
                errors.append(f"{source}: missing required field '{label}'.")
            continue
        pattern = rf"{re.escape(label)}\s*:"
        if not re.search(pattern, season_text, flags=re.IGNORECASE):
            errors.append(f"{source}: missing required field '{label}'.")
    valid_from = _parse_date("Valid-From", season_text)
    valid_to = _parse_date("Valid-To", season_text)
    if valid_from and valid_to and valid_from >= valid_to:
        errors.append(
            f"{source}: Valid-From must be before Valid-To (got {valid_from} >= {valid_to})."
        )
    try:
        _extract_availability_table(season_text)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{source}: availability table invalid ({exc}).")
    return errors


def validate_events_text(events_text: str, *, source: str) -> list[str]:
    """Return a list of validation errors for events.md interface."""
    errors: list[str] = []
    header_idx = None
    lines = events_text.splitlines()
    for idx, line in enumerate(lines):
        if "|" in line and "date" in line.lower() and "event-id" in line.lower():
            header_idx = idx
            break
    if header_idx is None:
        return [f"{source}: missing Event List table header."]
    rows: list[list[str]] = []
    for line in lines[header_idx + 1 :]:
        if line.strip().startswith("##"):
            break
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.match(r"^[-:\s]+$", cell) for cell in cells):
            continue
        if len(cells) < 6:
            continue
        rows.append(cells)
    if not rows:
        errors.append(f"{source}: Event List table has no rows.")
        return errors

    allowed_event_types = {"TRAVEL", "WORK", "WEATHER", "HEALTH", "FAMILY", "EQUIPMENT", "OTHER"}
    allowed_status = {"planned", "occurred", "cancelled"}
    allowed_impact = {"availability", "missed_session", "modality", "recovery", "data_quality", "none", "other"}
    for row in rows:
        date_str, event_id, event_type, status, impact, _desc = row[:6]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            errors.append(f"{source}: invalid event date '{date_str}'.")
        if not event_id:
            errors.append(f"{source}: event id missing for date {date_str}.")
        if event_type.upper() not in allowed_event_types:
            errors.append(f"{source}: invalid event type '{event_type}'.")
        if status.lower() not in allowed_status:
            errors.append(f"{source}: invalid event status '{status}'.")
        if impact.lower() not in allowed_impact:
            errors.append(f"{source}: invalid event impact '{impact}'.")
    return errors


def build_availability_payload(
    *,
    season_brief_ref: str,
    season_text: str,
    season_year: int,
) -> dict[str, Any]:
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
        "data_confidence": "MEDIUM",
    }

    return {
        "meta": meta,
        "data": {
            "source_type": "season_brief",
            "source_ref": season_brief_ref,
            "availability_table": entries,
            "weekly_hours": weekly_hours,
            "fixed_rest_days": fixed_rest_days,
            "notes": "Season Brief weekday availability normalized.",
        },
    }


def parse_and_store_availability(
    *,
    athlete_id: str,
    workspace_root: Path,
    schema_dir: Path,
    year: int | None = None,
    season_brief_path: Path | None = None,
    skip_validate: bool = False,
) -> AvailabilityResult:
    store = LocalArtifactStore(root=workspace_root)
    store.ensure_workspace(athlete_id)
    athlete_root = store.athlete_root(athlete_id)

    season_path, season_text = _load_season_brief(athlete_root, year, season_brief_path)
    season_ref = season_path.name
    season_year = year or _extract_year(season_text, season_path)
    if season_year is None:
        raise ValueError("Season year not found. Provide --year or include 'Year: YYYY' in Season Brief.")

    payload = build_availability_payload(
        season_brief_ref=season_ref,
        season_text=season_text,
        season_year=season_year,
    )

    validator = SchemaRegistry(schema_dir).validator_for("availability.schema.json")
    if not skip_validate:
        try:
            validate_or_raise(validator, payload)
        except SchemaValidationError as exc:
            details = "\n".join(f"  - {err}" for err in exc.errors)
            raise ValueError(f"Availability validation failed:\n{details}") from exc

    iso_week = payload["meta"]["iso_week"]
    out_file = store.versioned_path(athlete_id, ArtifactType.AVAILABILITY, iso_week)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    latest_file = store.latest_path(athlete_id, ArtifactType.AVAILABILITY)
    latest_file.write_bytes(out_file.read_bytes())

    store._record_index_write(  # noqa: SLF001
        athlete_id=athlete_id,
        artifact_type=ArtifactType.AVAILABILITY,
        version_key=iso_week,
        version_path=out_file,
        run_id=payload["meta"]["run_id"],
        producer_agent=payload["meta"]["owner_agent"],
        meta=payload["meta"],
    )

    return AvailabilityResult(payload=payload, output_path=out_file)
