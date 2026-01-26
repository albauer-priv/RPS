"""Agent specification structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSpec:
    """Static specification for a single agent."""
    name: str
    display_name: str
    vector_store_name: str
    prompt_file_stem: str
