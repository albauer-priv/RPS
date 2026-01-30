"""Intervals posting helpers with receipt-based idempotency."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReceiptResult:
    """Result of a post-to-Intervals receipt run."""

    ok: bool
    posted: int
    skipped: int
    conflicts: list[str]
    outputs: list[dict[str, Any]]
    error: str | None = None


@dataclass(frozen=True)
class ReceiptStatus:
    """Status summary for Intervals receipts."""

    unposted: list[dict[str, Any]]
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
        return ReceiptStatus(unposted=[], conflicts=[], posted=[], error="Intervals workouts missing.")
    payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    if not isinstance(payload, list) or not payload:
        return ReceiptStatus(unposted=[], conflicts=[], posted=[], error="Intervals workouts payload invalid.")

    unposted: list[dict[str, Any]] = []
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
            conflicts.append(
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
    return ReceiptStatus(unposted=unposted, conflicts=conflicts, posted=posted)


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
        "idempotency_key": hashlib.sha256(
            f"{athlete_id}:{version_key}:{uid}:{_payload_hash(match)}".encode("utf-8")
        ).hexdigest(),
        "payload_hash": _payload_hash(match),
        "posted_at": _utc_iso_now(),
        "run_id": run_id,
        "workout_uid": uid,
        "conflict_resolved": True,
        "resolved_at": _utc_iso_now(),
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
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "posted_at": _utc_iso_now(),
            "run_id": run_id,
            "workout_uid": uid,
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
            conflicts=conflicts,
            outputs=outputs,
            error="Receipt conflicts detected.",
        )

    logger.info("Posting receipts completed posted=%s skipped=%s", posted, skipped)
    return ReceiptResult(
        ok=True,
        posted=posted,
        skipped=skipped,
        conflicts=[],
        outputs=outputs,
        error=None,
    )
