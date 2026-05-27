"""Evidence library helpers with lazy refresh imports to avoid runtime cycles."""

from __future__ import annotations

from typing import Any

from .library import (
    DISCOVERY_LOCK_PATH,
    EvidenceEntry,
    all_library_entries,
    canonical_reference_locator,
    canonicalize_library_files,
    get_discovery_state,
    load_applied_sources,
    load_core_studies,
    save_applied_sources,
    save_core_studies,
    sync_reference_library_outputs,
)


def evidence_refresh_due(*args: Any, **kwargs: Any) -> bool:
    """Lazily import and evaluate the evidence refresh due check."""

    from .refresh import evidence_refresh_due as _impl

    return _impl(*args, **kwargs)


def refresh_evidence_library(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Lazily import and run the evidence refresh pipeline."""

    from .refresh import refresh_evidence_library as _impl

    return _impl(*args, **kwargs)


__all__ = [
    "DISCOVERY_LOCK_PATH",
    "EvidenceEntry",
    "all_library_entries",
    "canonicalize_library_files",
    "canonical_reference_locator",
    "evidence_refresh_due",
    "get_discovery_state",
    "load_applied_sources",
    "load_core_studies",
    "refresh_evidence_library",
    "save_core_studies",
    "save_applied_sources",
    "sync_reference_library_outputs",
]
