"""CrewAI execution backend for planner and advisory artefact tasks."""

from __future__ import annotations

from typing import Any

from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]


def _phase_document_from_bundle(bundle_document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Select the correct nested phase artifact document from a PhaseBundle."""

    if artifact_type == ArtifactType.PHASE_GUARDRAILS:
        candidate = bundle_document.get("guardrails_document") or bundle_document.get("guardrails")
    elif artifact_type == ArtifactType.PHASE_STRUCTURE:
        candidate = bundle_document.get("structure_document") or bundle_document.get("structure")
    elif artifact_type == ArtifactType.PHASE_PREVIEW:
        candidate = bundle_document.get("preview_document") or bundle_document.get("preview")
    else:
        raise ValueError(f"Unsupported PhaseBundle split target: {artifact_type.value}")
    if not isinstance(candidate, dict):
        raise RuntimeError(f"PhaseBundle missing nested document for {artifact_type.value}.")
    return candidate
