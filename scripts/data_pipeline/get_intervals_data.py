#!/usr/bin/env python3
"""Deprecated: use `python -m rps.main parse-intervals` instead."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    print(
        "[DEPRECATED] scripts/data_pipeline/get_intervals_data.py\n"
        "Use: python -m rps.main parse-intervals [--year ... --week ...] [--from ... --to ...]",
        file=sys.stderr,
    )
    cmd = [sys.executable, "-m", "rps.main", "parse-intervals", *sys.argv[1:]]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
