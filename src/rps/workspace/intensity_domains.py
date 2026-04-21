"""Canonical intensity-domain helpers shared across planning layers."""

from __future__ import annotations

from typing import Final

CANONICAL_INTENSITY_DOMAINS: Final[tuple[str, ...]] = (
    "NONE",
    "RECOVERY",
    "ENDURANCE_LOW",
    "ENDURANCE_HIGH",
    "TEMPO",
    "SWEET_SPOT",
    "THRESHOLD",
    "VO2MAX",
)

INTENSITY_DOMAIN_ALIASES: Final[dict[str, str]] = {
    "ENDURANCE": "ENDURANCE_LOW",
}

_CANONICAL_SET: Final[set[str]] = set(CANONICAL_INTENSITY_DOMAINS)


def normalize_intensity_domain(value: object) -> str | None:
    """Return a canonical intensity-domain label or None for invalid values."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip().upper()
    if not cleaned:
        return None
    cleaned = INTENSITY_DOMAIN_ALIASES.get(cleaned, cleaned)
    if cleaned in _CANONICAL_SET:
        return cleaned
    return None


def normalize_intensity_domain_list(values: object) -> list[str]:
    """Return a de-duplicated canonical intensity-domain list preserving order."""
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        domain = normalize_intensity_domain(item)
        if domain is None or domain in seen:
            continue
        seen.add(domain)
        normalized.append(domain)
    return normalized
