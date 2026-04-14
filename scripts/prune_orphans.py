"""Delete managed files that are no longer attached to any vector store."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running this script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from rps.core.config import load_env_file  # noqa: E402
from rps.openai.client import get_client  # noqa: E402
from rps.openai.vectorstores import (  # noqa: E402
    MANAGED_BY,
    list_files,
    list_vector_store_files,
    list_vector_stores,
)
from scripts.script_logging import configure_logging  # noqa: E402


def main() -> None:
    """Delete managed files that are no longer attached to any vector store."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env_file(ROOT / ".env")
    logger = configure_logging(ROOT, Path(__file__).stem)
    client = get_client()

    attached_file_ids: set[str] = set()
    for store in list_vector_stores(client):
        for vs_file in list_vector_store_files(client, store.id):
            attached_file_ids.add(vs_file.file_id)

    removed = 0
    for file_obj in list_files(client):
        metadata = getattr(file_obj, "metadata", {}) or {}
        if metadata.get("managed_by") != MANAGED_BY:
            continue
        if file_obj.id in attached_file_ids:
            continue
        if args.dry_run:
            print(f"Would delete: {file_obj.id} {file_obj.filename}")
        else:
            client.files.delete(file_obj.id)
        removed += 1

    logger.info("Removed orphaned files count=%d dry_run=%s", removed, args.dry_run)
    print(f"Removed {removed} orphaned files.")


if __name__ == "__main__":
    main()
