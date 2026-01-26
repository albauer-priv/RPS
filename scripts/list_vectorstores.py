"""List OpenAI vector stores."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = str(ROOT / "src")
if SYS_PATH not in sys.path:
    # Allow running this script directly without installing the package.
    sys.path.insert(0, SYS_PATH)

from rps.core.config import load_env_file  # noqa: E402
from rps.openai.client import get_client  # noqa: E402
from rps.openai.vectorstores import list_vector_stores  # noqa: E402
from script_logging import configure_logging  # noqa: E402


def main() -> None:
    """List vector stores and their file counts."""
    load_env_file(ROOT / ".env")
    logger = configure_logging(ROOT, Path(__file__).stem)
    client = get_client()

    count = 0
    for store in list_vector_stores(client):
        count += 1
        file_counts = getattr(store, "file_counts", None) or {}
        total_files = file_counts.get("total", "?")
        print(f"{store.id}\t{store.name}\tfiles={total_files}")
    logger.info("Listed %d vector stores", count)


if __name__ == "__main__":
    main()
