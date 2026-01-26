#!/usr/bin/env python3
"""Deprecated: use `python -m rps.main parse-availability` instead."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    print(
        "[DEPRECATED] scripts/data_pipeline/parse_season_brief_availability.py\n"
        "Use: python -m rps.main parse-availability [--athlete ...] [--year ...]",
        file=sys.stderr,
    )
    cmd = [sys.executable, "-m", "rps.main", "parse-availability", *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
