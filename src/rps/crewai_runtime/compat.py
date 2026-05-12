"""Compatibility helpers for CrewAI integration planning."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class CrewAIRuntimeStatus:
    """Describe whether CrewAI can be activated in the current interpreter."""

    python_version: str
    python_supported: bool
    package_installed: bool
    ok: bool
    message: str


def crewai_runtime_status() -> CrewAIRuntimeStatus:
    """Return the current CrewAI runtime compatibility status."""

    python_supported = sys.version_info < (3, 14)
    package_installed = importlib.util.find_spec("crewai") is not None
    ok = python_supported and package_installed
    if ok:
        message = "CrewAI runtime can be activated."
    elif not python_supported:
        message = "CrewAI runtime is blocked in this repo because the app runs on Python 3.14."
    else:
        message = "CrewAI runtime package is not installed."
    return CrewAIRuntimeStatus(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        python_supported=python_supported,
        package_installed=package_installed,
        ok=ok,
        message=message,
    )
