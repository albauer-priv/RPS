"""Deprecated shim for data pipeline helpers."""

from __future__ import annotations

import sys

from rps.data_pipeline.common import *  # noqa: F403

print(
    "[DEPRECATED] scripts/data_pipeline/common.py is deprecated. "
    "Use rps.data_pipeline.common instead.",
    file=sys.stderr,
)
