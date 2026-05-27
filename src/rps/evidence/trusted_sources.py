"""Trusted-source normalization and fast-lane matching for evidence refresh."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
TRUSTED_SOURCES_PATH = ROOT / "config" / "evidence" / "trusted_sources.yaml"


def normalize_trusted_text(value: str) -> str:
    """Normalize author and outlet strings for trusted-source matching."""

    lowered = value.strip().lower()
    lowered = re.sub(r"[^\w\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


@lru_cache(maxsize=1)
def load_trusted_sources_policy() -> dict[str, Any]:
    """Load the trusted-source YAML policy."""

    payload = yaml.safe_load(TRUSTED_SOURCES_PATH.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _alias_index(values: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for canonical, aliases in values.items():
        canonical_norm = normalize_trusted_text(str(canonical))
        index[canonical_norm] = canonical_norm
        if isinstance(aliases, list | tuple):
            for alias in aliases:
                alias_norm = normalize_trusted_text(str(alias))
                if alias_norm:
                    index[alias_norm] = canonical_norm
    return index


def canonical_author_name(value: str) -> str:
    """Return the canonical normalized author name according to policy aliases."""

    normalized = normalize_trusted_text(value)
    alias_index = _alias_index(load_trusted_sources_policy().get("author_aliases") or {})
    return alias_index.get(normalized, normalized)


def canonical_outlet_name(value: str) -> str:
    """Return the canonical normalized outlet name according to policy aliases."""

    normalized = normalize_trusted_text(value)
    alias_index = _alias_index(load_trusted_sources_policy().get("outlet_aliases") or {})
    return alias_index.get(normalized, normalized)


def match_trusted_source(*, authors: str, outlet: str) -> tuple[bool, str]:
    """Return whether one source matches the trusted fast-lane policy."""

    policy = load_trusted_sources_policy()
    trusted_authors = {canonical_author_name(str(item)) for item in (policy.get("trusted_authors") or [])}
    trusted_outlets = {canonical_outlet_name(str(item)) for item in (policy.get("trusted_outlets") or [])}
    denied_pairs = {
        (canonical_author_name(str(item.get("author") or "")), canonical_outlet_name(str(item.get("outlet") or "")))
        for item in (policy.get("denylist_pairs") or [])
        if isinstance(item, dict)
    }
    pair_overrides = {
        (canonical_author_name(str(item.get("author") or "")), canonical_outlet_name(str(item.get("outlet") or "")))
        for item in (policy.get("trusted_author_outlet_pairs") or [])
        if isinstance(item, dict)
    }

    normalized_outlet = canonical_outlet_name(outlet)
    normalized_authors_blob = normalize_trusted_text(authors)
    author_candidates = set()
    alias_index = _alias_index(policy.get("author_aliases") or {})
    for alias, canonical in alias_index.items():
        if alias and alias in normalized_authors_blob:
            author_candidates.add(canonical)
    for listed in trusted_authors:
        if listed and listed in normalized_authors_blob:
            author_candidates.add(listed)
    if not normalized_outlet or not author_candidates:
        return False, ""
    for author in author_candidates:
        if (author, normalized_outlet) in denied_pairs:
            return False, f"Denied trusted pair: {author} / {normalized_outlet}"
        if (author, normalized_outlet) in pair_overrides:
            return True, f"Trusted author+outlet pair: {author} / {normalized_outlet}"
        if author in trusted_authors and normalized_outlet in trusted_outlets:
            return True, f"Trusted author+outlet match: {author} / {normalized_outlet}"
    return False, ""
