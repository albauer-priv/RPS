"""AppTest coverage for the Workouts page receipt status panel."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

_ATHLETE = "test_athlete"
_PAGE = "src/rps/ui/pages/plan/workouts.py"


def _current_iso() -> tuple[int, int]:
    iso = date.today().isocalendar()
    return iso.year, iso.week


def _version_key(year: int, week: int) -> str:
    return f"{year:04d}-{week:02d}"


def _receipt_dir(tmp_path: Path, year: int, week: int) -> Path:
    return tmp_path / _ATHLETE / "receipts" / "post_to_intervals" / f"{year:04d}-W{week:02d}"


def _write_workouts(tmp_path: Path, workouts: list[dict]) -> None:
    year, week = _current_iso()
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace(_ATHLETE)
    vk = _version_key(year, week)
    path = store.versioned_path(_ATHLETE, ArtifactType.INTERVALS_WORKOUTS, vk)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(workouts, ensure_ascii=False), encoding="utf-8")


def _payload_hash(item: dict) -> str:
    payload = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_receipt(tmp_path: Path, year: int, week: int, uid: str, data: dict) -> None:
    d = _receipt_dir(tmp_path, year, week)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{uid}.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", _ATHLETE)
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")
    # SETTINGS is a module-level singleton; re-create it after env vars are patched
    # so the AppTest page uses the correct workspace root.
    import rps.ui.shared as _shared
    from rps.core.config import load_app_settings
    monkeypatch.setattr(_shared, "SETTINGS", load_app_settings())


def test_workouts_page_renders_without_artifact(tmp_path):
    """Receipt panel is hidden when INTERVALS_WORKOUTS is missing."""
    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    assert len(at.error) == 0
    subheaders = [s.value for s in at.subheader]
    assert not any("Receipt Status" in s for s in subheaders)


def test_workouts_page_receipt_panel_all_posted(tmp_path):
    """Panel shows success summary when all workouts have matching receipts."""
    year, week = _current_iso()
    workout = {"name": "Endurance", "start_date_local": "2026-09-15T09:00:00"}
    _write_workouts(tmp_path, [workout])

    uid = hashlib.sha256(
        f"{workout['start_date_local']}|{workout['name']}".encode()
    ).hexdigest()[:16]
    _write_receipt(tmp_path, year, week, uid, {
        "payload_hash": _payload_hash(workout),
        "status": "POSTED",
        "workout_uid": uid,
    })

    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    assert len(at.error) == 0
    subheaders = [s.value for s in at.subheader]
    assert any("Receipt Status" in s for s in subheaders)
    # success summary → green st.success (no st.error for receipt conflicts)
    success_texts = " ".join(s.value for s in at.success)
    assert "1 posted" in success_texts


def test_workouts_page_receipt_panel_shows_unposted(tmp_path):
    """Panel reports unposted count when no receipts exist."""
    workout = {"name": "Threshold", "start_date_local": "2026-09-16T06:00:00"}
    _write_workouts(tmp_path, [workout])

    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    assert len(at.error) == 0
    subheaders = [s.value for s in at.subheader]
    assert any("Receipt Status" in s for s in subheaders)
    info_texts = " ".join(i.value for i in at.info)
    assert "1 unposted" in info_texts
    # unposted expander auto-expands when no conflicts
    expander_labels = [e.label for e in at.expander]
    assert any("Unposted" in label for label in expander_labels)


def test_workouts_page_receipt_panel_shows_conflict(tmp_path):
    """Panel shows conflict row with resolve button when receipt JSON is invalid."""
    year, week = _current_iso()
    workout = {"name": "VO2 Intervals", "start_date_local": "2026-09-17T07:00:00"}
    _write_workouts(tmp_path, [workout])

    uid = hashlib.sha256(
        f"{workout['start_date_local']}|{workout['name']}".encode()
    ).hexdigest()[:16]
    # write an intentionally invalid JSON receipt
    receipt_dir = _receipt_dir(tmp_path, year, week)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / f"{uid}.json").write_text("not valid json", encoding="utf-8")

    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    subheaders = [s.value for s in at.subheader]
    assert any("Receipt Status" in s for s in subheaders)
    # conflict → st.error summary badge AND per-row error block
    error_texts = " ".join(e.value for e in at.error)
    assert "1 conflict" in error_texts
    assert "Conflict" in error_texts
    # resolve button present
    button_labels = [b.label for b in at.button]
    assert any("Resolve conflict" in label for label in button_labels)


def test_workouts_page_receipt_panel_shows_update(tmp_path):
    """Panel reports update count when receipt exists but payload hash changed."""
    year, week = _current_iso()
    workout = {"name": "Long Ride", "start_date_local": "2026-09-14T08:00:00"}
    _write_workouts(tmp_path, [workout])

    uid = hashlib.sha256(
        f"{workout['start_date_local']}|{workout['name']}".encode()
    ).hexdigest()[:16]
    # write receipt with a stale hash
    _write_receipt(tmp_path, year, week, uid, {
        "payload_hash": "stalehash000",
        "status": "POSTED",
        "workout_uid": uid,
    })

    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    assert len(at.error) == 0
    info_texts = " ".join(i.value for i in at.info)
    assert "1 update" in info_texts
    # summary must not mention zero-counts for unposted or conflicts
    assert "unposted" not in info_texts
    assert "conflict" not in info_texts


def test_workouts_page_receipt_panel_posted_expander(tmp_path):
    """Panel shows a collapsed 'Posted' expander when workouts are posted."""
    year, week = _current_iso()
    workout = {"name": "Recovery Ride", "start_date_local": "2026-09-13T07:00:00"}
    _write_workouts(tmp_path, [workout])

    uid = hashlib.sha256(
        f"{workout['start_date_local']}|{workout['name']}".encode()
    ).hexdigest()[:16]
    _write_receipt(tmp_path, year, week, uid, {
        "payload_hash": _payload_hash(workout),
        "status": "POSTED",
        "workout_uid": uid,
    })

    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    expander_labels = [e.label for e in at.expander]
    assert any("Posted" in label for label in expander_labels)
    # success summary must include posted count and omit zero-count groups
    success_texts = " ".join(s.value for s in at.success)
    assert "1 posted" in success_texts
    assert "unposted" not in success_texts
    assert "conflict" not in success_texts
    assert "update" not in success_texts


def test_workouts_page_receipt_summary_omits_zero_counts(tmp_path):
    """Summary line shows only non-zero categories."""
    year, week = _current_iso()
    workouts = [
        {"name": "Morning Run", "start_date_local": "2026-09-15T06:00:00"},
        {"name": "Evening Ride", "start_date_local": "2026-09-15T18:00:00"},
    ]
    _write_workouts(tmp_path, workouts)

    uid0 = hashlib.sha256(
        f"{workouts[0]['start_date_local']}|{workouts[0]['name']}".encode()
    ).hexdigest()[:16]
    # post one workout; leave the other unposted
    _write_receipt(tmp_path, year, week, uid0, {
        "payload_hash": _payload_hash(workouts[0]),
        "status": "POSTED",
        "workout_uid": uid0,
    })

    at = AppTest.from_file(_PAGE)
    at.run(timeout=10)
    all_text = " ".join(i.value for i in at.info) + " ".join(s.value for s in at.success)
    # zero groups must not appear
    assert "0 " not in all_text
    assert "↻" not in all_text  # no update line
    assert "⚠" not in all_text  # no conflict line
