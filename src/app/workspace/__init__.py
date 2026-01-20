"""Workspace package exports and lazy imports."""

from typing import TYPE_CHECKING

from .api import Workspace
from .types import ArtifactType, Authority

if TYPE_CHECKING:
    from .validated_api import ValidatedWorkspace


def __getattr__(name: str):
    """Provide lazy import access to ValidatedWorkspace."""
    if name == "ValidatedWorkspace":
        from .validated_api import ValidatedWorkspace

        return ValidatedWorkspace
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Workspace", "ArtifactType", "Authority", "ValidatedWorkspace"]
