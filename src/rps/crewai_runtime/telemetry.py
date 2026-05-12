"""Run-store telemetry helpers for CrewAI flows and crews."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rps.ui.run_store import append_event

logger = logging.getLogger(__name__)

JsonMap = dict[str, Any]


def emit_runtime_event(
    *,
    root: Path | None,
    athlete_id: str | None,
    run_id: str | None,
    event_type: str,
    **payload: object,
) -> None:
    """Append one runtime event when the run context is available."""

    if root is None or not athlete_id or not run_id:
        return
    try:
        append_event(
            root,
            athlete_id,
            run_id,
            {
                "type": event_type,
                **payload,
            },
        )
    except Exception as exc:  # pragma: no cover - telemetry must stay best-effort
        logger.warning("Failed to append runtime event %s for run %s: %s", event_type, run_id, exc)

