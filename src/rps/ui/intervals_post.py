"""Intervals posting helpers with receipt-based idempotency."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from rps.data_pipeline.common import load_env
from rps.data_pipeline.intervals_post import delete_events, post_events


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReceiptResult:
    """Result of a post-to-Intervals receipt run."""

    ok: bool
    posted: int
    skipped: int
    conflicts: list[str]
    outputs: list[dict[str, Any]]
    deleted: int = 0
    error: str | None = None


@dataclass(frozen=True)
class ReceiptStatus:
    """Status summary for Intervals receipts."""

    unposted: list[dict[str, Any]]
    updates: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    posted: list[dict[str, Any]]
    error: str | None = None


def _utc_iso_now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _payload_hash(item: dict[str, Any]) -> str:
    """Compute a stable hash of a workout payload."""
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _workout_uid(item: dict[str, Any]) -> str:
    """Derive a stable workout UID from payload fields."""
    base = f"{item.get('start_date_local', '')}|{item.get('name', '')}"
    if base.strip("|"):
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return hashlib.sha256(_payload_hash(item).encode("utf-8")).hexdigest()[:16]


def _external_id(athlete_id: str, year: int, week: int, item: dict[str, Any]) -> str:
    """Derive a deterministic external_id for Intervals events."""
    start_date = item.get("start_date_local") or "unknown"
    name = (item.get("name") or "workout").strip().replace(" ", "_").lower()
    slot_key = name[:32]
    return f"rps:{athlete_id}:{year:04d}-W{week:02d}:{start_date}:{slot_key}"


def _receipt_dir(root: Path, athlete_id: str, year: int, week: int) -> Path:
    """Return the receipt directory for a given athlete/week."""
    return (root / athlete_id / "receipts" / "post_to_intervals" / f"{year:04d}-W{week:02d}").resolve()


def _receipt_path(root: Path, athlete_id: str, year: int, week: int, uid: str) -> Path:
    """Return receipt path for a single workout."""
    return _receipt_dir(root, athlete_id, year, week) / f"{uid}.json"


def inspect_intervals_receipts(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    year: int,
    week: int,
) -> ReceiptStatus:
    """Inspect receipts vs. workouts payload for unposted/conflict status."""
    version_key = f"{year:04d}-{week:02d}"
    if not store.exists(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key):
        return ReceiptStatus(unposted=[], updates=[], conflicts=[], posted=[], error="Intervals workouts missing.")
    payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    if not isinstance(payload, list) or not payload:
        return ReceiptStatus(unposted=[], updates=[], conflicts=[], posted=[], error="Intervals workouts payload invalid.")

    unposted: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    posted: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        uid = _workout_uid(item)
        payload_hash = _payload_hash(item)
        receipt_path = _receipt_path(store.root, athlete_id, year, week, uid)
        if not receipt_path.exists():
            unposted.append(
                {
                    "uid": uid,
                    "name": item.get("name") or "—",
                    "start_date_local": item.get("start_date_local") or "—",
                }
            )
            continue
        try:
            existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            conflicts.append(
                {
                    "uid": uid,
                    "name": item.get("name") or "—",
                    "start_date_local": item.get("start_date_local") or "—",
                    "reason": "Invalid receipt JSON",
                }
            )
            continue
        if existing.get("payload_hash") != payload_hash:
            updates.append(
                {
                    "uid": uid,
                    "name": item.get("name") or "—",
                    "start_date_local": item.get("start_date_local") or "—",
                    "reason": "Payload hash changed",
                }
            )
            continue
        posted.append(
            {
                "uid": uid,
                "name": item.get("name") or "—",
                "start_date_local": item.get("start_date_local") or "—",
            }
        )
    return ReceiptStatus(unposted=unposted, updates=updates, conflicts=conflicts, posted=posted)


def resolve_receipt_conflict(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    year: int,
    week: int,
    uid: str,
    run_id: str,
) -> bool:
    """Resolve a receipt conflict by overwriting with current payload hash."""
    version_key = f"{year:04d}-{week:02d}"
    if not store.exists(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key):
        return False
    payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    if not isinstance(payload, list) or not payload:
        return False
    match = next((item for item in payload if isinstance(item, dict) and _workout_uid(item) == uid), None)
    if not match:
        return False
    receipt_path = _receipt_path(store.root, athlete_id, year, week, uid)
    receipt = {
        "external_id": _external_id(athlete_id, year, week, match),
        "idempotency_key": hashlib.sha256(
            f"{athlete_id}:{version_key}:{uid}:{_payload_hash(match)}".encode("utf-8")
        ).hexdigest(),
        "payload_hash": _payload_hash(match),
        "posted_at": _utc_iso_now(),
        "run_id": run_id,
        "workout_uid": uid,
        "conflict_resolved": True,
        "resolved_at": _utc_iso_now(),
        "status": "POSTED",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def post_to_intervals_receipts(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    year: int,
    week: int,
    run_id: str,
) -> ReceiptResult:
    """Create receipts for Intervals workouts to enforce idempotency."""
    logger.info(
        "Posting receipts athlete=%s iso=%04d-W%02d run_id=%s",
        athlete_id,
        year,
        week,
        run_id,
    )
    version_key = f"{year:04d}-{week:02d}"
    if not store.exists(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key):
        logger.warning("Intervals workouts missing for iso=%s", version_key)
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            deleted=0,
            conflicts=[],
            outputs=[],
            error=f"Intervals workouts not found for ISO week {version_key}.",
        )
    payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    if not isinstance(payload, list) or not payload:
        logger.warning("Intervals workouts payload invalid for iso=%s", version_key)
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            deleted=0,
            conflicts=[],
            outputs=[],
            error="Intervals workouts payload is empty or invalid.",
        )

    outputs: list[dict[str, Any]] = []
    conflicts: list[str] = []
    posted = 0
    skipped = 0
    receipt_dir = _receipt_dir(store.root, athlete_id, year, week)
    receipt_dir.mkdir(parents=True, exist_ok=True)

    for item in payload:
        if not isinstance(item, dict):
            continue
        uid = _workout_uid(item)
        payload_hash = _payload_hash(item)
        external_id = _external_id(athlete_id, year, week, item)
        receipt_path = _receipt_path(store.root, athlete_id, year, week, uid)
        if receipt_path.exists():
            try:
                existing = json.loads(receipt_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                conflicts.append(uid)
                continue
            if existing.get("payload_hash") == payload_hash:
                skipped += 1
                outputs.append(
                    {
                        "receipt": str(receipt_path),
                        "status": "skipped",
                        "uid": uid,
                    }
                )
                continue
            conflicts.append(uid)
            continue

        idempotency_key = hashlib.sha256(
            f"{athlete_id}:{version_key}:{uid}:{payload_hash}".encode("utf-8")
        ).hexdigest()
        receipt = {
            "external_id": external_id,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "posted_at": _utc_iso_now(),
            "run_id": run_id,
            "workout_uid": uid,
            "status": "POSTED",
        }
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        posted += 1
        outputs.append(
            {
                "receipt": str(receipt_path),
                "status": "posted",
                "uid": uid,
            }
        )

    if conflicts:
        logger.error("Receipt conflicts detected for %s workouts", len(conflicts))
        return ReceiptResult(
            ok=False,
            posted=posted,
            skipped=skipped,
            deleted=0,
            conflicts=conflicts,
            outputs=outputs,
            error="Receipt conflicts detected.",
        )

    logger.info("Posting receipts completed posted=%s skipped=%s", posted, skipped)
    return ReceiptResult(
        ok=True,
        posted=posted,
        skipped=skipped,
        deleted=0,
        conflicts=[],
        outputs=outputs,
        error=None,
    )


def post_to_intervals_commit(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    year: int,
    week: int,
    run_id: str,
    base_url: str | None = None,
    api_key: str | None = None,
    allow_delete: bool = False,
) -> ReceiptResult:
    """Post Intervals workouts via API and write receipts with external IDs."""
    load_env()
    base_url = base_url or os.getenv("BASE_URL")
    api_key = api_key or os.getenv("API_KEY")
    if not base_url or not api_key:
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            deleted=0,
            conflicts=[],
            outputs=[],
            error="BASE_URL or API_KEY missing for Intervals posting.",
        )

    version_key = f"{year:04d}-{week:02d}"
    if not store.exists(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key):
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            deleted=0,
            conflicts=[],
            outputs=[],
            error=f"Intervals workouts not found for ISO week {version_key}.",
        )
    payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    if not isinstance(payload, list) or not payload:
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            deleted=0,
            conflicts=[],
            outputs=[],
            error="Intervals workouts payload is empty or invalid.",
        )

    to_post: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    conflicts: list[str] = []
    posted = 0
    skipped = 0
    deleted = 0

    receipt_map: dict[str, dict[str, Any]] = {}
    receipt_paths: dict[str, Path] = {}
    receipt_dir = _receipt_dir(store.root, athlete_id, year, week)
    if receipt_dir.exists():
        for path in receipt_dir.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            external_id = record.get("external_id")
            if external_id:
                receipt_map[external_id] = record
                receipt_paths[external_id] = path

    for item in payload:
        if not isinstance(item, dict):
            continue
        uid = _workout_uid(item)
        payload_hash = _payload_hash(item)
        external_id = _external_id(athlete_id, year, week, item)
        existing = receipt_map.get(external_id)
        if existing and existing.get("payload_hash") == payload_hash and existing.get("status") == "POSTED":
            skipped += 1
            outputs.append({"receipt": str(receipt_paths.get(external_id, "")), "status": "skipped", "uid": uid})
            continue
        item_with_id = dict(item)
        item_with_id["external_id"] = external_id
        to_post.append(item_with_id)

    if allow_delete:
        desired_ids = {_external_id(athlete_id, year, week, item) for item in payload if isinstance(item, dict)}
        to_delete = [
            external_id
            for external_id, receipt in receipt_map.items()
            if external_id not in desired_ids and receipt.get("status") == "POSTED"
        ]
        if to_delete:
            delete_result = delete_events(
                external_ids=to_delete,
                athlete_id=athlete_id,
                base_url=base_url,
                api_key=api_key,
            )
            if delete_result.get("ok"):
                for external_id in to_delete:
                    path = receipt_paths.get(external_id)
                    if not path:
                        continue
                    tombstone = {
                        "external_id": external_id,
                        "status": "DELETED",
                        "deleted_at": _utc_iso_now(),
                        "run_id": run_id,
                        "last_payload_hash": receipt_map.get(external_id, {}).get("payload_hash"),
                    }
                    path.write_text(json.dumps(tombstone, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    deleted += 1
                    outputs.append({"receipt": str(path), "status": "deleted"})
            else:
                return ReceiptResult(
                    ok=False,
                    posted=posted,
                    skipped=skipped,
                    deleted=deleted,
                    conflicts=[],
                    outputs=outputs,
                    error=f"Intervals delete error: {delete_result.get('status')}",
                )

    if not to_post:
        return ReceiptResult(
            ok=True,
            posted=0,
            skipped=skipped,
            deleted=deleted,
            conflicts=[],
            outputs=outputs,
            error=None,
        )

    result = post_events(
        events=to_post,
        athlete_id=athlete_id,
        base_url=base_url,
        api_key=api_key,
        upsert=True,
    )
    if not result.get("ok"):
        return ReceiptResult(
            ok=False,
            posted=posted,
            skipped=skipped,
            deleted=deleted,
            conflicts=[],
            outputs=outputs,
            error=f"Intervals API error: {result.get('status')}",
        )

    response = result.get("response")
    response_list = response if isinstance(response, list) else []
    response_by_external = {
        (item.get("external_id") if isinstance(item, dict) else None): item for item in response_list
    }

    for item in to_post:
        uid = _workout_uid(item)
        payload_hash = _payload_hash(item)
        external_id = item.get("external_id")
        receipt_path = _receipt_path(store.root, athlete_id, year, week, uid)
        response_item = response_by_external.get(external_id) if external_id else None
        receipt = {
            "external_id": external_id,
            "intervals_event_id": response_item.get("id") if isinstance(response_item, dict) else None,
            "intervals_uid": response_item.get("uid") if isinstance(response_item, dict) else None,
            "payload_hash": payload_hash,
            "posted_at": _utc_iso_now(),
            "run_id": run_id,
            "workout_uid": uid,
            "status": "POSTED",
        }
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        posted += 1
        outputs.append({"receipt": str(receipt_path), "status": "posted", "uid": uid})

    return ReceiptResult(
        ok=True,
        posted=posted,
        skipped=skipped,
        deleted=deleted,
        conflicts=[],
        outputs=outputs,
        error=None,
    )


def delete_posted_workouts(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    year: int,
    week: int,
    run_id: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> ReceiptResult:
    """Delete posted workouts for a given ISO week (by external_id)."""
    load_env()
    base_url = base_url or os.getenv("BASE_URL")
    api_key = api_key or os.getenv("API_KEY")
    if not base_url or not api_key:
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            conflicts=[],
            outputs=[],
            deleted=0,
            error="BASE_URL or API_KEY missing for Intervals delete.",
        )
    receipt_dir = _receipt_dir(store.root, athlete_id, year, week)
    if not receipt_dir.exists():
        return ReceiptResult(
            ok=True,
            posted=0,
            skipped=0,
            conflicts=[],
            outputs=[],
            deleted=0,
            error=None,
        )
    receipts = []
    for path in receipt_dir.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if record.get("status") == "POSTED" and record.get("external_id"):
            receipts.append((record["external_id"], path, record))
    if not receipts:
        return ReceiptResult(
            ok=True,
            posted=0,
            skipped=0,
            conflicts=[],
            outputs=[],
            deleted=0,
            error=None,
        )
    external_ids = [item[0] for item in receipts]
    result = delete_events(
        external_ids=external_ids,
        athlete_id=athlete_id,
        base_url=base_url,
        api_key=api_key,
    )
    if not result.get("ok"):
        return ReceiptResult(
            ok=False,
            posted=0,
            skipped=0,
            conflicts=[],
            outputs=[],
            deleted=0,
            error=f"Intervals delete error: {result.get('status')}",
        )
    deleted = 0
    outputs: list[dict[str, Any]] = []
    for external_id, path, record in receipts:
        tombstone = {
            "external_id": external_id,
            "status": "DELETED",
            "deleted_at": _utc_iso_now(),
            "run_id": run_id,
            "last_payload_hash": record.get("payload_hash"),
        }
        path.write_text(json.dumps(tombstone, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        deleted += 1
        outputs.append({"receipt": str(path), "status": "deleted"})
    return ReceiptResult(
        ok=True,
        posted=0,
        skipped=0,
        deleted=deleted,
        conflicts=[],
        outputs=outputs,
        error=None,
    )
