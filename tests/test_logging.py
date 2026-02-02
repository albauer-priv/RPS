from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

from rps.core.logging import prune_old_logs


def _touch(path: Path, days_ago: int) -> None:
    path.write_text("log", encoding="utf-8")
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    epoch = ts.timestamp()
    os.utime(path, (epoch, epoch))


def test_prune_old_logs_skips_current_and_keeps_recent(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    _touch(log_dir / "rps.log", days_ago=30)
    _touch(log_dir / "rps-20260201-000.log", days_ago=10)
    _touch(log_dir / "rps-20260201-001.log", days_ago=2)

    removed = prune_old_logs(log_dir, retention_days=7)
    assert removed == 1
    assert (log_dir / "rps.log").exists()
    assert (log_dir / "rps-20260201-000.log").exists() is False
    assert (log_dir / "rps-20260201-001.log").exists()
