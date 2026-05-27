"""Sync and optionally refresh the canonical evidence library."""

from __future__ import annotations

import argparse
import json

from rps.core.config import load_app_settings, load_env_file
from rps.evidence import refresh_evidence_library, sync_reference_library_outputs
from rps.evidence.library import ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync or refresh the canonical evidence library.")
    parser.add_argument("--discover", action="store_true", help="Run primary-source discovery before syncing outputs.")
    args = parser.parse_args(argv)

    load_env_file(ROOT / ".env")
    settings = load_app_settings()
    result = (
        refresh_evidence_library(
            athlete_id="system",
            workspace_root=settings.workspace_root,
        )
        if args.discover
        else {"status": "synced_only"}
    )
    sync_reference_library_outputs()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
