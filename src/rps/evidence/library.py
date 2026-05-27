"""Canonical evidence library models, persistence, and rendered markdown sync."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
REFERENCES_DIR = ROOT / "skills" / "shared" / "durability-methodology" / "references"
LIBRARY_DIR = REFERENCES_DIR / "library"
STUDIES_DIR = LIBRARY_DIR / "studies"
ASSETS_DIR = LIBRARY_DIR / "assets"
CORE_LIBRARY_PATH = LIBRARY_DIR / "core_studies.yaml"
APPLIED_LIBRARY_PATH = LIBRARY_DIR / "applied_sources.yaml"
DISCOVERY_STATE_PATH = LIBRARY_DIR / "discovery_state.json"
DISCOVERY_LOCK_PATH = LIBRARY_DIR / "discovery.lock"
CORE_TABLE_PATH = REFERENCES_DIR / "durability_reference_table_core.md"
APPLIED_TABLE_PATH = REFERENCES_DIR / "durability_reference_table_applied.md"
LIBRARY_MANIFEST_PATH = REFERENCES_DIR / "evidence_library_manifest.md"
DECOMMISSIONED_SHARED_BIBLIOGRAPHY = REFERENCES_DIR / "durability_bibliography.md"
DECOMMISSIONED_CONVERSATION_BIBLIOGRAPHY = (
    ROOT / "skills" / "conversation" / "guarded-operations" / "references" / "durability_bibliography.md"
)
DECOMMISSIONED_SPEC_BIBLIOGRAPHY = (
    ROOT / "specs" / "knowledge" / "_shared" / "sources" / "evidence" / "durability_bibliography.md"
)
DECOMMISSIONED_SPEC_MANIFEST = ROOT / "specs" / "knowledge" / "_shared" / "sources" / "evidence" / "evidence_manifest.md"

CURATION_SCHEMA_VERSION = "1"
VISIBLE_ACTIVATION_STATES = frozenset({"active", "legacy_active"})


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalize_optional_text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() == "omitted" else text


def _coerce_str_list(value: object) -> tuple[str, ...]:
    if isinstance(value, list | tuple):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def _coerce_str_map(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _default_summary_card(entry_id: str, title: str, key_takeaways: tuple[str, ...], limits: tuple[str, ...]) -> dict[str, str]:
    return {
        "focus": title or entry_id,
        "main_takeaway": key_takeaways[0] if key_takeaways else "",
        "main_limit": limits[0] if limits else "",
    }


def _default_relevance_for_entry(*, source_kind: str, topic_tags: tuple[str, ...]) -> dict[str, Any]:
    best_use = "applied_translation" if source_kind == "applied" else "core_scientific_support"
    return {
        "overall_relevance": "medium",
        "relevance_rationale": "Legacy entry imported before structured relevance curation.",
        "rps_domains_supported": list(topic_tags[:3]),
        "target_audiences_supported": ["background_knowledge"],
        "best_use_mode": best_use,
        "activation_recommendation": "hold",
    }


def _default_brief_sections(entry: EvidenceEntry) -> dict[str, Any]:
    return {
        "why_this_source_matters_for_rps": entry.notes or "Legacy evidence entry pending structured brief curation.",
        "research_question_or_purpose": entry.question_or_focus,
        "study_type": entry.study_type or entry.source_type or "other",
        "population_or_context": entry.population_or_scope,
        "what_was_actually_examined": "; ".join(entry.what_was_examined) or entry.question_or_focus or "Not yet curated.",
        "core_concepts": list(entry.core_concepts),
        "key_takeaways": list(entry.key_takeaways),
        "important_findings": list(entry.important_findings),
        "practical_implications_for_rps": list(entry.practical_implications),
        "what_this_source_does_not_justify": list(entry.what_this_does_not_justify),
        "limits_and_transfer_boundaries": list(entry.important_limits),
        "allowed_uses_in_rps": list(entry.allowed_uses),
        "evidence_posture": entry.evidence_posture,
        "source_material_basis": entry.source_material_basis,
    }


@dataclass(frozen=True)
class EvidenceEntry:
    """One canonical evidence-library entry."""

    id: str
    source_kind: str
    authors: str
    year: int
    title: str
    journal_or_outlet: str
    source_type: str
    study_type: str
    reference_locator: str
    verification_status: str
    locator_source: str
    topic_tags: tuple[str, ...]
    question_or_focus: str
    population_or_scope: str
    what_was_examined: tuple[str, ...]
    core_concepts: tuple[str, ...]
    important_findings: tuple[str, ...]
    practical_implications: tuple[str, ...]
    key_takeaways: tuple[str, ...]
    what_this_does_not_justify: tuple[str, ...]
    important_limits: tuple[str, ...]
    allowed_uses: tuple[str, ...]
    authority_limit: str
    evidence_posture: str
    fulltext_status: str
    fulltext_local_path: str
    source_material_level: str
    source_material_basis: str
    notes: str
    summary_card: dict[str, str]
    relevance_assessment: dict[str, Any]
    brief_sections: dict[str, Any]
    brief_path: str
    brief_status: str
    activation_status: str
    trusted_source_match: bool
    trusted_match_reason: str
    legacy_active: bool
    curation_schema_version: str
    record_fingerprint: str
    last_verified_at: str
    discovered_at: str
    curated_at: str
    activated_at: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, source_kind: str | None = None) -> EvidenceEntry:
        resolved_kind = str(data.get("source_kind") or source_kind or "core")
        title = str(data.get("title") or "")
        key_takeaways = _coerce_str_list(data.get("key_takeaways"))
        limits = _coerce_str_list(data.get("important_limits"))
        source_material_level = str(data.get("source_material_level") or "metadata_only")
        evidence_posture = str(data.get("evidence_posture") or (
            "metadata_only_not_activatable" if source_material_level == "metadata_only" else "abstract_curated"
        ))
        activation_status = str(data.get("activation_status") or "legacy_active")
        legacy_active = bool(data.get("legacy_active", activation_status == "legacy_active"))
        entry = cls(
            id=str(data["id"]),
            source_kind=resolved_kind,
            authors=str(data["authors"]),
            year=int(data["year"]),
            title=title,
            journal_or_outlet=str(data.get("journal_or_outlet") or ""),
            source_type=str(data.get("source_type") or ""),
            study_type=str(data.get("study_type") or data.get("source_type") or "other"),
            reference_locator=_normalize_optional_text(data.get("reference_locator")),
            verification_status=str(data.get("verification_status") or "omitted"),
            locator_source=str(data.get("locator_source") or ""),
            topic_tags=_coerce_str_list(data.get("topic_tags")),
            question_or_focus=str(data.get("question_or_focus") or ""),
            population_or_scope=str(data.get("population_or_scope") or ""),
            what_was_examined=_coerce_str_list(data.get("what_was_examined")),
            core_concepts=_coerce_str_list(data.get("core_concepts")),
            important_findings=_coerce_str_list(data.get("important_findings")),
            practical_implications=_coerce_str_list(data.get("practical_implications")),
            key_takeaways=key_takeaways,
            what_this_does_not_justify=_coerce_str_list(data.get("what_this_does_not_justify")),
            important_limits=limits,
            allowed_uses=_coerce_str_list(data.get("allowed_uses")),
            authority_limit=str(data.get("authority_limit") or ""),
            evidence_posture=evidence_posture,
            fulltext_status=str(data.get("fulltext_status") or ""),
            fulltext_local_path=str(data.get("fulltext_local_path") or ""),
            source_material_level=source_material_level,
            source_material_basis=str(data.get("source_material_basis") or source_material_level),
            notes=str(data.get("notes") or ""),
            summary_card=_coerce_str_map(data.get("summary_card")) or _default_summary_card(str(data["id"]), title, key_takeaways, limits),
            relevance_assessment=_coerce_str_map(data.get("relevance_assessment")) or _default_relevance_for_entry(
                source_kind=resolved_kind,
                topic_tags=_coerce_str_list(data.get("topic_tags")),
            ),
            brief_sections=_coerce_str_map(data.get("brief_sections")),
            brief_path=str(data.get("brief_path") or f"studies/{data['id']}.md"),
            brief_status=str(data.get("brief_status") or "legacy_generated"),
            activation_status=activation_status,
            trusted_source_match=bool(data.get("trusted_source_match", False)),
            trusted_match_reason=str(data.get("trusted_match_reason") or ""),
            legacy_active=legacy_active,
            curation_schema_version=str(data.get("curation_schema_version") or CURATION_SCHEMA_VERSION),
            record_fingerprint=str(data.get("record_fingerprint") or data["id"]),
            last_verified_at=str(data.get("last_verified_at") or ""),
            discovered_at=str(data.get("discovered_at") or ""),
            curated_at=str(data.get("curated_at") or ""),
            activated_at=str(data.get("activated_at") or ""),
        )
        if not entry.brief_sections:
            return replace(entry, brief_sections=_default_brief_sections(entry))
        return entry

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_kind": self.source_kind,
            "authors": self.authors,
            "year": self.year,
            "title": self.title,
            "journal_or_outlet": self.journal_or_outlet,
            "source_type": self.source_type,
            "study_type": self.study_type,
            "reference_locator": self.reference_locator or "omitted",
            "verification_status": self.verification_status,
            "locator_source": self.locator_source,
            "topic_tags": list(self.topic_tags),
            "question_or_focus": self.question_or_focus,
            "population_or_scope": self.population_or_scope,
            "what_was_examined": list(self.what_was_examined),
            "core_concepts": list(self.core_concepts),
            "important_findings": list(self.important_findings),
            "practical_implications": list(self.practical_implications),
            "key_takeaways": list(self.key_takeaways),
            "what_this_does_not_justify": list(self.what_this_does_not_justify),
            "important_limits": list(self.important_limits),
            "allowed_uses": list(self.allowed_uses),
            "authority_limit": self.authority_limit,
            "evidence_posture": self.evidence_posture,
            "fulltext_status": self.fulltext_status,
            "fulltext_local_path": self.fulltext_local_path,
            "source_material_level": self.source_material_level,
            "source_material_basis": self.source_material_basis,
            "notes": self.notes,
            "summary_card": self.summary_card,
            "relevance_assessment": self.relevance_assessment,
            "brief_sections": self.brief_sections,
            "brief_path": self.brief_path,
            "brief_status": self.brief_status,
            "activation_status": self.activation_status,
            "trusted_source_match": self.trusted_source_match,
            "trusted_match_reason": self.trusted_match_reason,
            "legacy_active": self.legacy_active,
            "curation_schema_version": self.curation_schema_version,
            "record_fingerprint": self.record_fingerprint,
            "last_verified_at": self.last_verified_at,
            "discovered_at": self.discovered_at,
            "curated_at": self.curated_at,
            "activated_at": self.activated_at,
        }


def _load_yaml_entries(path: Path, *, source_kind: str) -> list[EvidenceEntry]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = payload.get("entries") or []
    return [EvidenceEntry.from_mapping(item, source_kind=source_kind) for item in entries if isinstance(item, dict)]


def _write_yaml_entries(path: Path, *, library_type: str, source_kind: str, entries: list[EvidenceEntry]) -> None:
    payload = {
        "version": 2,
        "library_type": library_type,
        "curation_schema_version": CURATION_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "entries": [replace(entry, source_kind=source_kind).to_mapping() for entry in entries],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_core_studies() -> list[EvidenceEntry]:
    """Return core studies from the canonical evidence library."""

    return _load_yaml_entries(CORE_LIBRARY_PATH, source_kind="core")


def load_applied_sources() -> list[EvidenceEntry]:
    """Return applied sources from the canonical evidence library."""

    return _load_yaml_entries(APPLIED_LIBRARY_PATH, source_kind="applied")


def save_core_studies(entries: list[EvidenceEntry]) -> None:
    """Persist core studies back to the canonical YAML file."""

    _write_yaml_entries(CORE_LIBRARY_PATH, library_type="core_studies", source_kind="core", entries=entries)


def save_applied_sources(entries: list[EvidenceEntry]) -> None:
    """Persist applied sources back to the canonical YAML file."""

    _write_yaml_entries(APPLIED_LIBRARY_PATH, library_type="applied_sources", source_kind="applied", entries=entries)


def canonicalize_library_files() -> None:
    """Rewrite canonical YAML files with current schema defaults."""

    save_core_studies(load_core_studies())
    save_applied_sources(load_applied_sources())


def all_library_entries() -> list[EvidenceEntry]:
    """Return all library entries."""

    return [*load_core_studies(), *load_applied_sources()]


def operatively_visible_entries(entries: list[EvidenceEntry]) -> list[EvidenceEntry]:
    """Return entries that should appear in operative generated evidence surfaces."""

    return [entry for entry in entries if entry.activation_status in VISIBLE_ACTIVATION_STATES or entry.legacy_active]


def _normalized_title(value: str) -> str:
    return " ".join(value.lower().replace("’", "'").replace("“", '"').replace("”", '"').split())


def canonical_reference_locator(title: object) -> str | None:
    """Return a verified canonical locator for one title when available."""

    target = _normalized_title(str(title or ""))
    if not target:
        return None
    for entry in load_core_studies():
        if entry.verification_status != "verified" or not entry.reference_locator:
            continue
        if _normalized_title(entry.title) == target:
            return entry.reference_locator
    return None


def get_discovery_state() -> dict[str, Any]:
    """Return the discovery-state JSON payload."""

    if not DISCOVERY_STATE_PATH.exists():
        return {
            "version": 1,
            "last_attempt_at": None,
            "last_success_at": None,
            "last_search_date": None,
            "stats": {},
        }
    return json.loads(DISCOVERY_STATE_PATH.read_text(encoding="utf-8"))


def save_discovery_state(state: dict[str, Any]) -> None:
    """Persist discovery-state JSON."""

    DISCOVERY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _join_cells(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else "none"


def _render_table(entries: list[EvidenceEntry], *, title: str, applied: bool) -> str:
    header = [
        f"# {title}",
        "",
        "Generated from the canonical local evidence library. Do not edit this file manually.",
        "",
        "## Curation Contract",
        "",
        "- Operative entries must be `active`; legacy content may remain visible as `legacy_active` until backfill completes.",
        "- Reference locators are included only when verified.",
        "- If a locator is uncertain, it is omitted rather than guessed.",
        "- Core sources remain justification-oriented; applied sources remain practice/context support only.",
        "",
        "| id | title | study_type | verification_status | activation_status | evidence_posture | source_material_level | topic_tags | main_takeaway | allowed_uses |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    rows: list[str] = []
    for entry in operatively_visible_entries(entries):
        rows.append(
            "| `{id}` | {title} | `{study_type}` | `{verification_status}` | `{activation_status}` | `{evidence_posture}` | `{source_material_level}` | `{tags}` | {main_takeaway} | `{uses}` |".format(
                id=entry.id,
                title=entry.title,
                study_type=entry.study_type or entry.source_type or "other",
                verification_status=entry.verification_status,
                activation_status=entry.activation_status,
                evidence_posture=entry.evidence_posture,
                source_material_level=entry.source_material_level,
                tags=_join_cells(entry.topic_tags),
                main_takeaway=entry.summary_card.get("main_takeaway") or "none",
                uses=_join_cells(entry.allowed_uses),
            )
        )
    footer = [
        "",
        "## Coverage Notes",
        "",
        "- This table is derived from structured library data and may be regenerated.",
        "- Legacy bibliography files are decommissioned and are no longer operative lookup sources.",
        "- Non-active candidates remain out of these generated evidence surfaces.",
    ]
    if applied:
        footer.append("- Applied sources are for coaching/practice translation and execution detail, not binding scientific proof.")
    return "\n".join([*header, *rows, *footer]) + "\n"


def _render_study_detail(entry: EvidenceEntry) -> str:
    lines = [
        f"# {entry.id}: {entry.title}",
        "",
        "Generated from the canonical local evidence library.",
        "",
        f"- Authors: {entry.authors}",
        f"- Year: {entry.year}",
        f"- Outlet: {entry.journal_or_outlet or 'none'}",
        f"- Source kind: `{entry.source_kind}`",
        f"- Source type: `{entry.source_type}`",
        f"- Study type: `{entry.study_type}`",
        f"- Reference locator: {entry.reference_locator or 'none'}",
        f"- Verification status: `{entry.verification_status}`",
        f"- Locator source: `{entry.locator_source or 'none'}`",
        f"- Activation status: `{entry.activation_status}`",
        f"- Evidence posture: `{entry.evidence_posture}`",
        f"- Topic tags: `{_join_cells(entry.topic_tags)}`",
        f"- Allowed uses: `{_join_cells(entry.allowed_uses)}`",
        f"- Authority limit: `{entry.authority_limit or 'none'}`",
        f"- Fulltext status: `{entry.fulltext_status or 'none'}`",
        f"- Source material basis: `{entry.source_material_basis or entry.source_material_level}`",
        f"- Last verified at: `{entry.last_verified_at or 'unknown'}`",
        f"- Curation schema version: `{entry.curation_schema_version}`",
    ]
    if entry.fulltext_local_path:
        lines.append(f"- Fulltext local path: `{entry.fulltext_local_path}`")
    lines.extend([
        "",
        "## Summary Card",
        "",
        f"- Focus: {entry.summary_card.get('focus') or 'none'}",
        f"- Main takeaway: {entry.summary_card.get('main_takeaway') or 'none'}",
        f"- Main limit: {entry.summary_card.get('main_limit') or 'none'}",
        "",
        "## Relevance to RPS",
        "",
        f"- Overall relevance: `{entry.relevance_assessment.get('overall_relevance') or 'unknown'}`",
        f"- Best use mode: `{entry.relevance_assessment.get('best_use_mode') or 'unknown'}`",
        f"- Activation recommendation: `{entry.relevance_assessment.get('activation_recommendation') or 'unknown'}`",
        f"- Rationale: {entry.relevance_assessment.get('relevance_rationale') or 'none'}",
        f"- Supported RPS domains: `{', '.join(str(item) for item in (entry.relevance_assessment.get('rps_domains_supported') or [])) or 'none'}`",
        f"- Target audiences: `{', '.join(str(item) for item in (entry.relevance_assessment.get('target_audiences_supported') or [])) or 'none'}`",
        "",
        "## Why This Source Matters for RPS",
        "",
        entry.brief_sections.get("why_this_source_matters_for_rps") or "none",
        "",
        "## Research Question / Purpose",
        "",
        entry.brief_sections.get("research_question_or_purpose") or "none",
        "",
        "## Population / Context",
        "",
        entry.brief_sections.get("population_or_context") or "none",
        "",
        "## What Was Actually Examined",
        "",
        entry.brief_sections.get("what_was_actually_examined") or "none",
        "",
        "## Core Concepts",
        "",
    ])
    lines.extend(f"- {item}" for item in (_coerce_str_list(entry.brief_sections.get("core_concepts")) or ("none",)))
    lines.extend(["", "## Key Takeaways", ""])
    lines.extend(f"- {item}" for item in (_coerce_str_list(entry.brief_sections.get("key_takeaways")) or ("none",)))
    lines.extend(["", "## Important Findings", ""])
    lines.extend(f"- {item}" for item in (_coerce_str_list(entry.brief_sections.get("important_findings")) or ("none",)))
    lines.extend(["", "## Practical Implications for RPS", ""])
    lines.extend(
        f"- {item}" for item in (_coerce_str_list(entry.brief_sections.get("practical_implications_for_rps")) or ("none",))
    )
    lines.extend(["", "## What This Source Does Not Justify", ""])
    lines.extend(
        f"- {item}" for item in (_coerce_str_list(entry.brief_sections.get("what_this_source_does_not_justify")) or ("none",))
    )
    lines.extend(["", "## Limits and Transfer Boundaries", ""])
    lines.extend(
        f"- {item}" for item in (_coerce_str_list(entry.brief_sections.get("limits_and_transfer_boundaries")) or ("none",))
    )
    if entry.notes:
        lines.extend(["", "## Notes", "", f"- {entry.notes}"])
    return "\n".join(lines) + "\n"


def _render_manifest() -> str:
    return "\n".join(
        [
            "# Evidence Library Manifest",
            "",
            "This repository uses one canonical local evidence library for operative literature/reference lookup.",
            "",
            "## Operative Sources",
            "",
            "1. `library/core_studies.yaml`",
            "2. `library/applied_sources.yaml`",
            "3. Generated markdown tables and study briefs derived from the canonical library",
            "",
            "## Rules",
            "",
            "- Bibliographic verification is not enough for activation.",
            "- Active evidence must pass curation plus deterministic quality gate.",
            "- Long-form study briefs are generated from structured curation output.",
            "- Only verified locators belong in active prompts, skills, runtime, or persisted outputs.",
            "- Primary-source verification is limited to PubMed, DOI/Crossref, official journal/publisher landing pages, NIH/PMC, and official OA repositories.",
            "",
            "## Migration",
            "",
            "- Legacy entries may remain visible as `legacy_active` until structured curation backfill completes.",
            "- Non-active candidates are excluded from operative evidence surfaces.",
        ]
    ) + "\n"


def _render_decommission_notice(title: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "> Decommissioned as an operative evidence source.",
            "",
            "This file remains only as a compatibility/history marker.",
            "",
            "Use the canonical evidence library instead:",
            "",
            "- `skills/shared/durability-methodology/references/library/core_studies.yaml`",
            "- `skills/shared/durability-methodology/references/library/applied_sources.yaml`",
            "- generated tables and study briefs under `skills/shared/durability-methodology/references/`",
            "",
            "Rules:",
            "- do not use this file as active lookup input",
            "- do not add or edit citations here",
            "- omit uncertain locators instead of inventing them",
        ]
    ) + "\n"


def sync_reference_library_outputs(*, rewrite_yaml: bool = True) -> None:
    """Regenerate markdown views and decommission notices from the canonical library."""

    if rewrite_yaml:
        canonicalize_library_files()
    core_entries = load_core_studies()
    applied_entries = load_applied_sources()

    CORE_TABLE_PATH.write_text(
        _render_table(core_entries, title="Durability Reference Table — Core", applied=False),
        encoding="utf-8",
    )
    APPLIED_TABLE_PATH.write_text(
        _render_table(applied_entries, title="Durability Reference Table — Applied", applied=True),
        encoding="utf-8",
    )
    LIBRARY_MANIFEST_PATH.write_text(_render_manifest(), encoding="utf-8")

    STUDIES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for entry in [*core_entries, *applied_entries]:
        if entry.activation_status not in VISIBLE_ACTIVATION_STATES and not entry.legacy_active:
            continue
        (STUDIES_DIR / f"{entry.id}.md").write_text(_render_study_detail(entry), encoding="utf-8")

    DECOMMISSIONED_SHARED_BIBLIOGRAPHY.write_text(
        _render_decommission_notice("Durability Bibliography (Decommissioned)"),
        encoding="utf-8",
    )
    DECOMMISSIONED_CONVERSATION_BIBLIOGRAPHY.write_text(
        _render_decommission_notice("Guarded Operations Durability Bibliography (Decommissioned)"),
        encoding="utf-8",
    )
    DECOMMISSIONED_SPEC_BIBLIOGRAPHY.write_text(
        _render_decommission_notice("Specification Durability Bibliography (Decommissioned)"),
        encoding="utf-8",
    )
    DECOMMISSIONED_SPEC_MANIFEST.write_text(
        _render_decommission_notice("Evidence Manifest (Decommissioned)"),
        encoding="utf-8",
    )
