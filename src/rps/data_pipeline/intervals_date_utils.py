"""ISO week / date utilities and CLI argument parsing for the Intervals.icu pipeline."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

DEFAULT_WEEKS = 24
ISO_SUNDAY_WEEKDAY = 7


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the end-to-end pipeline."""
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Intervals.icu activity data, then compile activities_actual (latest week) "
            "and activities_trend in a single run."
        )
    )
    parser.add_argument("--year", type=int, help="ISO year for the week, e.g. 2025")
    parser.add_argument("--week", type=int, help="ISO calendar week, e.g. 43")
    parser.add_argument("--from", dest="from_date", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--athlete", help="Athlete ID (defaults to ATHLETE_ID from .env).")
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip JSON schema validation in compile steps",
    )
    parser.add_argument(
        "--historical-years",
        type=int,
        default=3,
        help="Number of years to include in historical baseline aggregation.",
    )
    return parser.parse_args()


def parse_ymd(value: str) -> date:
    """Parse a YYYY-MM-DD date string."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def iso_week_to_dates(iso_year: int, iso_week: int) -> tuple[date, date]:
    """Convert an ISO week to its date range (Monday through Sunday)."""
    first_day = datetime.fromisocalendar(iso_year, iso_week, 1)
    last_day = first_day + timedelta(days=6)
    return first_day.date(), last_day.date()


def date_to_iso_week(target_date: date | datetime) -> tuple[int, int]:
    """Return the ISO year/week for a given date or datetime."""
    iso_year, iso_week, _ = target_date.isocalendar()
    return int(iso_year), int(iso_week)


def last_iso_week(iso_year: int) -> int:
    """Return the last ISO week number for the given ISO year."""
    return date(iso_year, 12, 28).isocalendar()[1]


def last_complete_week_end(today: date) -> date:
    """Return the last completed ISO week end (Sunday) before the given date."""
    if today.isoweekday() == ISO_SUNDAY_WEEKDAY:
        return today
    return today - timedelta(days=today.isoweekday())


def resolve_default_range(weeks: int = DEFAULT_WEEKS) -> tuple[date, date]:
    """Return the default date range covering the last N complete ISO weeks."""
    end_date = last_complete_week_end(datetime.now().date())
    end_monday = end_date - timedelta(days=6)
    start_monday = end_monday - timedelta(weeks=weeks - 1)
    return start_monday, end_date
