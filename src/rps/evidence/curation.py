"""Evidence source-package construction and CrewAI-based structured curation."""

from __future__ import annotations

import json
from dataclasses import dataclass

from rps.agents.crewai_task_execution import execute_structured_internal_task_crewai
from rps.agents.runtime import AgentRuntime
from rps.core.config import load_app_settings, load_env_file
from rps.crewai_runtime.models import EvidenceCurationModel
from rps.prompts.loader import PromptLoader

from .library import ROOT, EvidenceEntry

RPS_CURATION_CONTEXT = """RPS evidence-curation context:
- RPS serves long-duration endurance athletes with cycling, brevet, and ultra relevance.
- Durability, repeatability, pacing stability, low metabolic strain under long work, and recovery coherence matter more than isolated fresh peak metrics.
- Evidence supports explanation and relevance classification, not binding governance.
- Core and applied sources both matter; applied sources remain lower-authority but still deserve high-quality summaries.
- Relevance should be judged specifically for durability, fatigue resistance, pacing, fueling, taper, progression, intensity-distribution framing, masters/recovery, brevet/ultra transfer, and coaching translation.
- You must explicitly state what the source does not justify.
- Discovery tags are not evidence and must not be echoed as findings.
- Title paraphrases are not empirical findings.
- For metadata-only packages, keep the output narrow: use background-only or reject posture, avoid sport-specific transfer labels unless grounded in the provided title/text, and state clearly when no extractable findings are available.
- For abstract-only packages, keep the language source-bounded: prefer "the abstract reports", "the abstract suggests", or "the review abstract describes" over direct coaching imperatives, and do not mix background_only with stronger allowed uses.
"""


def _truncate_text(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


@dataclass(frozen=True)
class EvidenceSourcePackage:
    """Deterministic input package for one evidence curation run."""

    source_id: str
    source_kind: str
    authors: str
    year: int
    title: str
    journal_or_outlet: str
    source_type: str
    verified_locator: str
    verification_status: str
    topic_tags: tuple[str, ...]
    trusted_source_match: bool
    trusted_match_reason: str
    source_material_level: str
    source_material_basis: str
    abstract_text: str
    oa_excerpt_text: str
    oa_fulltext_text: str
    existing_registry_summary: str
    rps_curation_context: str

    def to_prompt_payload(self) -> dict[str, object]:
        """Return a JSON-serializable source package for the curation task."""

        return {
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "authors": self.authors,
            "year": self.year,
            "title": self.title,
            "journal_or_outlet": self.journal_or_outlet,
            "source_type": self.source_type,
            "verified_locator": self.verified_locator or None,
            "verification_status": self.verification_status,
            "topic_tags": list(self.topic_tags),
            "trusted_source_match": self.trusted_source_match,
            "trusted_match_reason": self.trusted_match_reason,
            "source_material_level": self.source_material_level,
            "source_material_basis": self.source_material_basis,
            "abstract_text": self.abstract_text or None,
            "oa_excerpt_text": self.oa_excerpt_text or None,
            "oa_fulltext_text": self.oa_fulltext_text or None,
            "existing_registry_summary": self.existing_registry_summary or None,
            "rps_curation_context": self.rps_curation_context,
        }


def build_source_package(
    entry: EvidenceEntry,
    *,
    trusted_source_match: bool,
    trusted_match_reason: str,
    abstract_text: str = "",
    oa_excerpt_text: str = "",
    oa_fulltext_text: str = "",
) -> EvidenceSourcePackage:
    """Build one deterministic source package with bounded source text."""

    bounded_abstract = _truncate_text(abstract_text, 4000)
    bounded_excerpt = _truncate_text(oa_excerpt_text, 10000)
    bounded_fulltext = _truncate_text(oa_fulltext_text, 18000)
    if bounded_fulltext:
        material_level = "oa_fulltext"
        material_basis = "OA fulltext excerpt set: abstract, conclusion/key points, discussion, methods, results, optional introduction."
    elif bounded_excerpt:
        material_level = "oa_excerpt"
        material_basis = "OA excerpt only."
    elif bounded_abstract:
        material_level = "abstract_only"
        material_basis = "Curated from abstract-level material."
    else:
        material_level = "metadata_only"
        material_basis = "Metadata-only package; not activatable without stronger source text."
    existing_summary = " | ".join(
        [
            entry.question_or_focus,
            *entry.key_takeaways,
            *entry.important_findings,
        ]
    ).strip(" |")
    return EvidenceSourcePackage(
        source_id=entry.id,
        source_kind=entry.source_kind,
        authors=entry.authors,
        year=entry.year,
        title=entry.title,
        journal_or_outlet=entry.journal_or_outlet,
        source_type=entry.source_type,
        verified_locator=entry.reference_locator,
        verification_status=entry.verification_status,
        topic_tags=entry.topic_tags,
        trusted_source_match=trusted_source_match,
        trusted_match_reason=trusted_match_reason,
        source_material_level=material_level,
        source_material_basis=material_basis,
        abstract_text=bounded_abstract,
        oa_excerpt_text=bounded_excerpt,
        oa_fulltext_text=bounded_fulltext,
        existing_registry_summary=existing_summary,
        rps_curation_context=RPS_CURATION_CONTEXT,
    )


def build_evidence_runtime() -> AgentRuntime:
    """Construct a minimal AgentRuntime for evidence curation tasks."""

    load_env_file(ROOT / ".env")
    settings = load_app_settings()
    return AgentRuntime(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        reasoning_effort=settings.openai_reasoning_effort,
        reasoning_summary=settings.openai_reasoning_summary,
        max_completion_tokens=settings.openai_max_completion_tokens,
        prompt_loader=PromptLoader(settings.prompts_dir),
        schema_dir=settings.schema_dir,
        workspace_root=settings.workspace_root,
    )


def curate_source_package(
    package: EvidenceSourcePackage,
    *,
    athlete_id: str,
    run_id: str,
) -> EvidenceCurationModel:
    """Run the evidence curation CrewAI task for one source package."""

    runtime = build_evidence_runtime()
    description = "\n".join(
        [
            "Curate the verified evidence source package below for RPS.",
            "Summarize only from the provided material. Never invent locator data or unsupported findings.",
            "Discovery tags are routing metadata, not evidence. Do not mirror them as findings or relevance proof.",
            "For metadata-only packages, do not present title paraphrases as findings; use negative-capability statements about missing extractable findings instead.",
            "For abstract-only packages, keep findings and implications explicitly abstract-bounded and avoid direct imperative coaching language unless it is framed as abstract-supported guidance.",
            "Return only the structured evidence curation model.",
            "",
            "Source package JSON:",
            json.dumps(package.to_prompt_payload(), ensure_ascii=False, indent=2),
        ]
    )
    result = execute_structured_internal_task_crewai(
        runtime,
        crew_name="evidence_curation",
        task_name="evidence_curate_source",
        description=description,
        athlete_id=athlete_id,
        run_id=run_id,
    )
    if not isinstance(result, EvidenceCurationModel):
        raise RuntimeError("Evidence curation task did not return EvidenceCurationModel.")
    return result
