from __future__ import annotations

import io
import zipfile
from pathlib import Path

from rps.workspace.backup_restore import create_backup_bundle, restore_backup_bundle


def _write_file(path: Path, content: str = "data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_backup_excludes_runs_and_logs(tmp_path):
    athlete_id = "ath_001"
    root = tmp_path / athlete_id
    _write_file(root / "inputs" / "season_brief_2026.md", "brief")
    _write_file(root / "latest" / "season_plan.json", "{}")
    _write_file(root / "data" / "plans" / "season" / "season_plan_2026-05.json", "{}")
    _write_file(root / "receipts" / "post_to_intervals" / "2026-W05" / "receipt.json", "{}")
    _write_file(root / "rendered" / "season_plan.md", "render")
    _write_file(root / "runs" / "run.json", "{}")
    _write_file(root / "logs" / "rps.log", "log")

    bundle = create_backup_bundle(athlete_id, tmp_path, mode="full")
    with zipfile.ZipFile(io.BytesIO(bundle.data)) as archive:
        names = archive.namelist()
        assert any("inputs/season_brief_2026.md" in name for name in names)
        assert any("latest/season_plan.json" in name for name in names)
        assert all("/runs/" not in name for name in names)
        assert all("/logs/" not in name for name in names)


def test_restore_inputs_only(tmp_path):
    athlete_id = "ath_002"
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"

    _write_file(source_root / athlete_id / "inputs" / "events_2026.md", "events")
    _write_file(source_root / athlete_id / "latest" / "season_plan.json", "{}")

    bundle = create_backup_bundle(athlete_id, source_root, mode="full")
    restore_backup_bundle(
        athlete_id=athlete_id,
        workspace_root=target_root,
        archive_bytes=bundle.data,
        mode="inputs",
        force=False,
    )

    assert (target_root / athlete_id / "inputs" / "events_2026.md").exists()
    assert not (target_root / athlete_id / "latest" / "season_plan.json").exists()
