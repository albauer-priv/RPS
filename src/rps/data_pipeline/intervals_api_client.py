"""Intervals.icu HTTP API client (session, retry policy, and raw fetch helpers)."""

from __future__ import annotations

from datetime import date

import requests
from requests.adapters import HTTPAdapter, Retry

# HTTP session with retries and a fixed timeout
session = requests.Session()
session.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    ),
)
DEFAULT_TIMEOUT = 15


def _get(url: str) -> requests.Response:
    """Perform a GET request with retry/timeout settings."""
    resp = session.get(url, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp


def get_activities(athlete_id: str, base_url: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch activities for a date range."""
    url = f"{base_url}/athlete/{athlete_id}/activities?oldest={start_date}&newest={end_date}"
    return _get(url).json()


def get_activity_detail(base_url: str, activity_id: str | int) -> dict:
    """Fetch detailed activity data by activity id."""
    url = f"{base_url}/activity/{activity_id}"
    return _get(url).json()


def get_power_curves_csv(athlete_id: str, base_url: str, start_date: date, end_date: date) -> str:
    """Fetch the power curves CSV for a date range."""
    url = (
        f"{base_url}/athlete/{athlete_id}/activity-power-curves.csv"
        f"?oldest={start_date}&newest={end_date}"
    )
    return _get(url).text


def get_athlete(athlete_id: str, base_url: str) -> dict:
    """Fetch athlete profile including sport settings when available."""
    url = f"{base_url}/athlete/{athlete_id}"
    return _get(url).json()


def get_wellness(athlete_id: str, base_url: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch wellness entries for a date range."""
    url = f"{base_url}/athlete/{athlete_id}/wellness?oldest={start_date}&newest={end_date}"
    return _get(url).json()
