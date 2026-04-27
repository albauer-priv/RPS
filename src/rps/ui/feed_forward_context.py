from __future__ import annotations

from rps.workspace.iso_helpers import IsoWeek

JsonMap = dict[str, object]


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) and value else default


def _as_str_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


def build_resolved_des_evaluation_context(
    *,
    selected_week: IsoWeek,
    report_payload: JsonMap | None,
    report_ref: str,
    season_plan_ref: str,
    affected_phase_id: str,
    phase_range_key: str,
) -> str:
    """Build an authoritative selected-week DES evaluation context block."""
    report_data = _as_map(_as_map(report_payload).get("data"))
    weekly_analysis = _as_map(report_data.get("weekly_analysis"))
    interpretation = _as_map(weekly_analysis.get("interpretation"))
    recommendation = _as_map(report_data.get("recommendation"))

    lines = [
        "Resolved DES Evaluation Context (Authoritative)",
        f"- target_iso_week: {_week_key(selected_week)}",
        f"- season_plan_ref: {season_plan_ref or 'unknown'}",
        f"- des_analysis_report_ref: {report_ref or _week_key(selected_week)}",
        f"- affected_phase_id: {affected_phase_id or 'unknown'}",
        f"- affected_phase_range: {phase_range_key or 'unknown'}",
        (
            "- conclusion_basis: "
            + _as_str(interpretation.get("summary"), "No interpretation summary available.")
        ),
    ]

    rationale = _as_str_list(recommendation.get("rationale"))
    if rationale:
        lines.append("- rationale: " + " | ".join(rationale))

    considerations = _as_str_list(recommendation.get("suggested_considerations"))
    if considerations:
        lines.append("- suggested_considerations: " + " | ".join(considerations))

    return "\n".join(lines)


def build_resolved_season_phase_feed_forward_context(
    *,
    selected_week: IsoWeek,
    feed_forward_payload: JsonMap | None,
    feed_forward_ref: str,
) -> str:
    """Build an authoritative selected-week Season->Phase feed-forward context block."""
    data = _as_map(_as_map(feed_forward_payload).get("data"))
    source_context = _as_map(data.get("source_context"))
    decision_summary = _as_map(data.get("decision_summary"))
    phase_adjustment = _as_map(data.get("phase_adjustment"))
    adjustments = _as_map(phase_adjustment.get("adjustments"))
    kj_corridor = _as_map(adjustments.get("kj_corridor"))
    quality_density = _as_map(adjustments.get("quality_density"))
    applies_to_weeks_raw = phase_adjustment.get("applies_to_weeks")
    applies_to_weeks = [str(entry) for entry in applies_to_weeks_raw] if isinstance(applies_to_weeks_raw, list) else []

    lines = [
        "Resolved Season->Phase Feed Forward Context (Authoritative)",
        f"- target_iso_week: {_week_key(selected_week)}",
        f"- season_phase_feed_forward_ref: {feed_forward_ref or _week_key(selected_week)}",
        f"- season_plan_ref: {_as_str(source_context.get('season_plan_ref'), 'unknown')}",
        f"- des_analysis_report_ref: {_as_str(source_context.get('des_analysis_report_ref'), 'unknown')}",
        f"- affected_phase_id: {_as_str(source_context.get('affected_phase_id'), 'unknown')}",
        f"- conclusion: {_as_str(decision_summary.get('conclusion'), 'unknown')}",
    ]

    rationale = _as_str_list(decision_summary.get("rationale"))
    if rationale:
        lines.append("- rationale: " + " | ".join(rationale))
    if applies_to_weeks:
        lines.append("- applies_to_weeks: " + ", ".join(applies_to_weeks))

    direction = _as_str(kj_corridor.get("direction"), "unknown")
    percent = kj_corridor.get("percent")
    lines.append(f"- kj_corridor_direction: {direction}")
    if percent is not None:
        lines.append(f"- kj_corridor_percent: {percent}")

    lines.append(f"- quality_density_action: {_as_str(quality_density.get('action'), 'unknown')}")
    lines.append(
        "- quality_density_details: "
        + _as_str(quality_density.get("details"), "No quality density details provided.")
    )

    return "\n".join(lines)
