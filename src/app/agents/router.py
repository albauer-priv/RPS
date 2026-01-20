"""Agent router placeholder."""

from __future__ import annotations

from app.agents.registry import AGENTS


def route_request(_text: str) -> str:
    """Return the chosen agent name.

    This is a placeholder that always picks the first agent.
    """
    return next(iter(AGENTS))
