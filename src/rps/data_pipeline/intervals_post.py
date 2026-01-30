"""Post planned workouts to Intervals.icu via Events Bulk API."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("start_date_local", "category", "type", "name")


def load_events(json_path: Path) -> list[dict[str, Any]]:
    """Load and minimally validate Intervals events payload."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of event objects")
    for i, ev in enumerate(data):
        if not isinstance(ev, dict):
            raise ValueError(f"Event #{i} must be an object")
        for required in REQUIRED_FIELDS:
            if required not in ev:
                raise ValueError(f"Event #{i} missing required field: '{required}'")
    return data


def post_events(
    *,
    events: list[dict[str, Any]],
    athlete_id: str,
    base_url: str,
    api_key: str,
    timeout_s: int = 30,
    upsert: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Post events to Intervals.icu bulk endpoint."""
    if not events:
        raise ValueError("No events provided")
    url = f"{base_url.rstrip('/')}/athlete/{athlete_id}/events/bulk"
    if upsert:
        url = f"{url}?upsert=true"
    logger.info("Posting %s events athlete=%s", len(events), athlete_id)
    if verbose or dry_run:
        logger.info("POST %s", url)
        logger.info("Payload: %s", json.dumps(events, ensure_ascii=False))
    if dry_run:
        return {"ok": True, "status": "dry_run", "url": url, "count": len(events)}
    try:
        resp = requests.post(
            url,
            auth=HTTPBasicAuth("API_KEY", api_key),
            headers={"Content-Type": "application/json"},
            json=events,
            timeout=timeout_s,
        )
    except requests.RequestException as exc:
        logger.error("HTTP request failed: %s", exc)
        return {"ok": False, "status": "request_failed", "error": str(exc)}
    payload: dict[str, Any] | str
    if "application/json" in resp.headers.get("Content-Type", ""):
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text
    else:
        payload = resp.text
    return {
        "ok": resp.ok,
        "status": resp.status_code,
        "url": url,
        "count": len(events),
        "response": payload,
    }


def delete_events(
    *,
    external_ids: list[str],
    athlete_id: str,
    base_url: str,
    api_key: str,
    timeout_s: int = 30,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Delete events by external_id via bulk-delete endpoint."""
    if not external_ids:
        raise ValueError("No external_ids provided")
    url = f"{base_url.rstrip('/')}/athlete/{athlete_id}/events/bulk-delete"
    payload = [{"external_id": external_id} for external_id in external_ids]
    logger.info("Deleting %s events athlete=%s", len(external_ids), athlete_id)
    if verbose or dry_run:
        logger.info("PUT %s", url)
        logger.info("Payload: %s", json.dumps(payload, ensure_ascii=False))
    if dry_run:
        return {"ok": True, "status": "dry_run", "url": url, "count": len(payload)}
    try:
        resp = requests.put(
            url,
            auth=HTTPBasicAuth("API_KEY", api_key),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout_s,
        )
    except requests.RequestException as exc:
        logger.error("HTTP request failed: %s", exc)
        return {"ok": False, "status": "request_failed", "error": str(exc)}
    response_payload: dict[str, Any] | str
    if "application/json" in resp.headers.get("Content-Type", ""):
        try:
            response_payload = resp.json()
        except Exception:
            response_payload = resp.text
    else:
        response_payload = resp.text
    return {
        "ok": resp.ok,
        "status": resp.status_code,
        "url": url,
        "count": len(payload),
        "response": response_payload,
    }
