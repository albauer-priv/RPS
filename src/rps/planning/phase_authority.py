"""Shared helpers for phase authority, legacy band parsing, and week skeleton derivation."""

from __future__ import annotations

import re
from typing import Any

from rps.workspace.iso_helpers import IsoWeek, parse_iso_week

JsonMap = dict[str, Any]

_ROLE_WEEK_BAND_PATTERN = re.compile(
    r"(?P<week>\d{4}-\d{2})\s*:?\s*(?P<role>[A-Z_]+)\s*(?:min\s*)?(?P<min>\d+(?:\.\d+)?)\s*(?:-|max\s*)(?P<max>\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)
_WEEKDAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_RESET_WEEK_ROLES = {"DELOAD", "MINI_RESET", "SHORTENED_MINI_RESET"}


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _normalized_week_key(value: object) -> str:
    if isinstance(value, str) and value.strip():
        parsed = parse_iso_week(value.strip())
        if parsed is not None:
            return f"{parsed.year:04d}-{parsed.week:02d}"
        return value.strip()
    if isinstance(value, IsoWeek):
        return f"{value.year:04d}-{value.week:02d}"
    return ""


def normalize_role_week_load_bands(entries: object) -> list[JsonMap]:
    """Return canonical structured role-week load bands from structured or legacy inputs."""

    normalized: list[JsonMap] = []
    seen: set[tuple[str, str, int, int]] = set()
    for entry in _as_list(entries):
        entry_map = _as_map(entry)
        if entry_map:
            week = _normalized_week_key(entry_map.get("week"))
            role = str(entry_map.get("role") or "").strip().upper()
            band = _as_map(entry_map.get("band"))
            band_min = _as_float(band.get("min"))
            band_max = _as_float(band.get("max"))
            if week and role and band_min is not None and band_max is not None:
                low = int(round(min(band_min, band_max)))
                high = int(round(max(band_min, band_max)))
                marker = (week, role, low, high)
                if marker not in seen:
                    seen.add(marker)
                    normalized.append({"week": week, "role": role, "band": {"min": low, "max": high}})
                continue
        text = str(entry or "").strip()
        if not text:
            continue
        for match in _ROLE_WEEK_BAND_PATTERN.finditer(text):
            week = _normalized_week_key(match.group("week"))
            role = str(match.group("role") or "").strip().upper()
            low = int(round(float(match.group("min"))))
            high = int(round(float(match.group("max"))))
            marker = (week, role, min(low, high), max(low, high))
            if week and role and marker not in seen:
                seen.add(marker)
                normalized.append(
                    {
                        "week": week,
                        "role": role,
                        "band": {"min": marker[2], "max": marker[3]},
                    }
                )
    return normalized


def normalize_role_week_load_bands_from_text(text: object) -> list[JsonMap]:
    """Parse structured role-week load bands from free-text notes."""

    raw = str(text or "").strip()
    if not raw:
        return []
    return normalize_role_week_load_bands([raw])


def format_role_week_load_bands(entries: object) -> list[str]:
    """Render structured role-week load bands as stable compact strings."""

    rendered: list[str] = []
    for entry in normalize_role_week_load_bands(entries):
        band = _as_map(entry.get("band"))
        rendered.append(
            f"{entry.get('week')}: {entry.get('role')} {int(band.get('min', 0))}-{int(band.get('max', 0))}"
        )
    return rendered


def persisted_phase_weekly_kj_bands(entries: object) -> list[JsonMap]:
    """Serialize internal role-week authority into persisted phase weekly-band rows."""

    serialized: list[JsonMap] = []
    for entry in normalize_role_week_load_bands(entries):
        week = str(entry.get("week") or "").strip()
        role = str(entry.get("role") or "").strip().upper()
        band = _as_map(entry.get("band"))
        low = _as_float(band.get("min"))
        high = _as_float(band.get("max"))
        if not week or not role or low is None or high is None:
            continue
        minimum = int(round(min(low, high)))
        maximum = int(round(max(low, high)))
        serialized.append(
            {
                "week": week,
                "band": {
                    "min": minimum,
                    "max": maximum,
                    "notes": (
                        f"role {role}; "
                        f"S5 deterministic band is {minimum}-{maximum}; "
                        f"feasible band max is {maximum}"
                    ),
                },
            }
        )
    return serialized


def role_week_band_by_week(entries: object) -> dict[str, JsonMap]:
    """Return canonical structured week-band mapping keyed by ISO week."""

    return {
        str(entry.get("week")): _as_map(entry.get("band"))
        for entry in normalize_role_week_load_bands(entries)
        if str(entry.get("week") or "").strip()
    }


def choose_quality_domain(*, phase_intent: str, allowed_domains: list[str]) -> str:
    """Return the preferred quality domain inside the exact allowed phase legality."""

    normalized = [str(item).strip().upper() for item in allowed_domains if str(item).strip()]
    normalized_set = set(normalized)
    if phase_intent in {"shortened_re_entry", "general_base", "aerobic_base", "strength_endurance_base"}:
        if "TEMPO" in normalized_set:
            return "TEMPO"
    for candidate in ("TEMPO", "SWEET_SPOT", "THRESHOLD", "VO2MAX", "ENDURANCE"):
        if candidate in normalized_set:
            return candidate
    for candidate in normalized:
        if candidate not in {"NONE", "RECOVERY"}:
            return candidate
    return "ENDURANCE"


def build_week_skeleton_for_phase(
    *,
    week_keys: list[str],
    week_role_by_iso_week: dict[str, str],
    fixed_rest_days: list[str],
    allowed_day_roles: list[str],
    allowed_intensity_domains: list[str],
    allowed_load_modalities: list[str],
    quality_cap: int | None,
    phase_intent: str,
) -> list[JsonMap]:
    """Build a deterministic Mon-Sun week skeleton for each phase week."""

    allowed_role_set = {str(item).strip().upper() for item in allowed_day_roles if str(item).strip()}
    allowed_domains = [str(item).strip().upper() for item in allowed_intensity_domains if str(item).strip()]
    allowed_domain_set = set(allowed_domains)
    allowed_modalities = [str(item).strip().upper() for item in allowed_load_modalities if str(item).strip()]
    rest_days = {str(item).strip().title()[:3] for item in fixed_rest_days if str(item).strip()}
    normalized_cap = quality_cap if isinstance(quality_cap, int) and quality_cap >= 0 else 0
    quality_domain = choose_quality_domain(phase_intent=phase_intent, allowed_domains=allowed_domains)
    skeleton: list[JsonMap] = []
    for week in week_keys:
        week_role = str(week_role_by_iso_week.get(week) or "").strip().upper()
        is_reset = week_role in _RESET_WEEK_ROLES
        reentry_is_conservative = phase_intent == "shortened_re_entry" or week_role == "SHORTENED_RE_ENTRY"
        day_roles: dict[str, str] = {
            "Tue": "QUALITY" if normalized_cap >= 1 and not is_reset else "ENDURANCE",
            "Wed": "RECOVERY" if "RECOVERY" in allowed_role_set else "ENDURANCE",
            "Thu": (
                "ENDURANCE"
                if reentry_is_conservative
                else ("QUALITY" if normalized_cap >= 2 and not is_reset else "ENDURANCE")
            ),
            "Sat": "ENDURANCE",
            "Sun": "ENDURANCE",
        }
        days: list[JsonMap] = []
        for day in _WEEKDAY_ORDER:
            if day in rest_days:
                days.append(
                    {
                        "day_of_week": day,
                        "day_role": "REST",
                        "intensity_domain": "NONE",
                        "load_modality": "NONE",
                    }
                )
                continue
            day_role = day_roles.get(day, "ENDURANCE")
            if day_role == "RECOVERY":
                intensity_domain = "RECOVERY" if "RECOVERY" in allowed_domain_set else "ENDURANCE"
            elif day_role == "QUALITY":
                intensity_domain = quality_domain
            else:
                intensity_domain = "ENDURANCE" if "ENDURANCE" in allowed_domain_set else quality_domain
            load_modality = "NONE"
            if load_modality not in allowed_modalities and allowed_modalities:
                load_modality = allowed_modalities[0]
            days.append(
                {
                    "day_of_week": day,
                    "day_role": day_role,
                    "intensity_domain": intensity_domain,
                    "load_modality": load_modality,
                }
            )
        skeleton.append({"week": week, "week_role": week_role_by_iso_week.get(week), "days": days})
    return skeleton


def target_week_skeleton(week_skeleton: object, target_week: str) -> JsonMap:
    """Return one target-week skeleton entry from a multi-week skeleton payload."""

    target = _normalized_week_key(target_week)
    for entry in _as_list(week_skeleton):
        entry_map = _as_map(entry)
        if _normalized_week_key(entry_map.get("week")) == target:
            return entry_map
    return {}
