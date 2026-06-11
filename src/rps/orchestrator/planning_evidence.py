"""Shared previous-week evidence resolution and alignment helpers for planning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from rps.orchestrator.resolved_context import build_resolved_activity_context_block
from rps.workspace.iso_helpers import IsoWeek, envelope_week, previous_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class PlanningEvidenceResolution:
    """Exact resolved evidence versions for one planning target week."""

    target_week: IsoWeek
    evidence_week: IsoWeek
    activities_actual_version: str | None = None
    activities_trend_version: str | None = None
    des_analysis_report_version: str | None = None


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


def resolve_planning_evidence_week(target_week: IsoWeek) -> IsoWeek:
    """Return the only valid weekly evidence week for a planning target week."""

    return previous_iso_week(target_week)


def resolve_previous_week_activity_versions(
    store: LocalArtifactStore,
    athlete_id: str,
    target_week: IsoWeek,
) -> PlanningEvidenceResolution:
    """Resolve exact previous-week activity versions for planning evidence."""

    evidence_week = resolve_planning_evidence_week(target_week)
    evidence_week_key = _week_key(evidence_week)
    return PlanningEvidenceResolution(
        target_week=target_week,
        evidence_week=evidence_week,
        activities_actual_version=store.resolve_week_version_key(
            athlete_id, ArtifactType.ACTIVITIES_ACTUAL, evidence_week_key
        ),
        activities_trend_version=store.resolve_week_version_key(
            athlete_id, ArtifactType.ACTIVITIES_TREND, evidence_week_key
        ),
        des_analysis_report_version=store.resolve_week_version_key(
            athlete_id, ArtifactType.DES_ANALYSIS_REPORT, evidence_week_key
        ),
    )


def report_matches_resolved_evidence(
    report_payload: JsonMap | None,
    *,
    evidence_week: IsoWeek,
    activities_actual_version: str,
    activities_trend_version: str,
) -> bool:
    """Check whether a report matches the resolved previous-week evidence.

    Week identity is mandatory. Source-version matching is enforced when the
    report carries explicit source lineage. Historical reports without explicit
    activity source references remain acceptable if the week matches.
    """

    if not isinstance(report_payload, dict):
        return False
    report_week = envelope_week(report_payload)
    if report_week is None or report_week.year != evidence_week.year or report_week.week != evidence_week.week:
        return False

    meta = _as_map(report_payload.get("meta"))
    data = _as_map(report_payload.get("data"))
    source_versions = _as_map(data.get("source_versions"))
    trace_upstream = _as_list(meta.get("trace_upstream"))

    actual_ref = _as_str(source_versions.get("activities_actual"))
    trend_ref = _as_str(source_versions.get("activities_trend"))
    if not actual_ref or not trend_ref:
        for entry in trace_upstream:
            entry_map = _as_map(entry)
            artifact = _as_str(entry_map.get("artifact")).upper()
            version_key = _as_str(entry_map.get("version_key") or entry_map.get("version"))
            if artifact == ArtifactType.ACTIVITIES_ACTUAL.value and not actual_ref:
                actual_ref = version_key
            elif artifact == ArtifactType.ACTIVITIES_TREND.value and not trend_ref:
                trend_ref = version_key

    if not actual_ref and not trend_ref:
        return True
    return actual_ref == activities_actual_version and trend_ref == activities_trend_version


def load_evidence_payloads(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    resolution: PlanningEvidenceResolution,
    include_report: bool,
) -> JsonMap:
    """Load resolved evidence payloads for planning."""

    actual_payload: JsonMap | None = None
    trend_payload: JsonMap | None = None
    report_payload: JsonMap | None = None
    if resolution.activities_actual_version:
        loaded = store.load_version(athlete_id, ArtifactType.ACTIVITIES_ACTUAL, resolution.activities_actual_version)
        actual_payload = loaded if isinstance(loaded, dict) else None
    if resolution.activities_trend_version:
        loaded = store.load_version(athlete_id, ArtifactType.ACTIVITIES_TREND, resolution.activities_trend_version)
        trend_payload = loaded if isinstance(loaded, dict) else None
    if include_report and resolution.des_analysis_report_version:
        loaded = store.load_version(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, resolution.des_analysis_report_version)
        report_payload = loaded if isinstance(loaded, dict) else None
    return {
        "activities_actual": actual_payload or {},
        "activities_trend": trend_payload or {},
        "des_analysis_report": report_payload or {},
    }


def render_historical_baseline_block(historical_baseline_payload: JsonMap | None) -> str:
    """Render a compact deterministic historical-baseline block for planning."""

    data = _as_map(_as_map(historical_baseline_payload).get("data"))
    metrics = _as_map(data.get("metrics"))
    yearly = _as_list(data.get("yearly_summary"))
    source = _as_map(data.get("source"))
    if not metrics and not yearly and not source:
        return ""
    lines = [
        "**Historical Baseline Evidence**",
        "Use this long-horizon baseline as context only; it shapes posture and realism, but it never overrides deterministic legality or exact load authority.",
    ]
    if metrics:
        for key in ("kj_per_year", "kj_per_activity", "kj_per_hour", "long_ride_tolerance_kj"):
            value = metrics.get(key)
            if value is not None:
                lines.append(f"{key}: {value}")
    if source:
        source_type = _as_str(source.get("source_type"))
        source_range = _as_str(source.get("range"))
        if source_type:
            lines.append(f"source_type: {source_type}")
        if source_range:
            lines.append(f"source_range: {source_range}")
    if yearly:
        lines.append("recent_yearly_summary:")
        for entry in yearly[-3:]:
            entry_map = _as_map(entry)
            year = entry_map.get("year")
            work_kj = entry_map.get("work_kj")
            activities = entry_map.get("activities")
            if year is not None:
                lines.append(f"- year {year}: work_kj {work_kj}, activities {activities}")
    return "\n".join(lines) + "\n"


def render_previous_week_report_block(
    *,
    target_week: IsoWeek,
    evidence_week: IsoWeek,
    report_version: str | None,
    report_payload: JsonMap | None,
) -> str:
    """Render a compact deterministic report evidence block."""

    report = _as_map(report_payload)
    data = _as_map(report.get("data"))
    summary_meta = _as_map(data.get("summary_meta"))
    kpi_summary = _as_map(data.get("kpi_summary"))
    weekly_analysis = _as_map(data.get("weekly_analysis"))
    trend_analysis = _as_map(data.get("trend_analysis"))
    recommendation = _as_map(data.get("recommendation"))
    if not data:
        return ""

    lines = [
        "**Previous Week Report Evidence**",
        "This report is advisory evidence for the completed prior week. It shapes conservatism, continuity, recovery, and durability interpretation, but it does not override deterministic legality or exact load-band authority.",
        f"target_iso_week: {_week_key(target_week)}",
        f"evidence_week: {_week_key(evidence_week)}",
    ]
    if report_version:
        lines.append(f"des_analysis_report_version: {report_version}")
    if summary_meta:
        report_year = summary_meta.get("year")
        report_iso_week = summary_meta.get("iso_week")
        lines.append(
            f"report_summary_week: {report_year}-{report_iso_week:02d}"
            if isinstance(report_year, int) and isinstance(report_iso_week, int)
            else "report_summary_week: unknown"
        )
    if kpi_summary:
        for key in ("durability", "fatigue_resistance", "fueling_stability"):
            entry = _as_map(kpi_summary.get(key))
            status = _as_str(entry.get("status"))
            rationale_text = _as_str(entry.get("rationale"))
            if status:
                lines.append(f"{key}.status: {status}")
            if rationale_text:
                lines.append(f"{key}.rationale: {rationale_text}")
    interpretation_map = _as_map(weekly_analysis.get("interpretation"))
    summary = _as_str(interpretation_map.get("summary"))
    if summary:
        lines.append(f"weekly_interpretation: {summary}")
    urgency = _as_str(recommendation.get("urgency"))
    if urgency:
        lines.append(f"recommendation.urgency: {urgency}")
    rationale_items = _as_list(recommendation.get("rationale"))
    if rationale_items:
        lines.append("recommendation.rationale:")
        for item in rationale_items[:3]:
            text = _as_str(item)
            if text:
                lines.append(f"- {text}")
    observations = _as_list(trend_analysis.get("observations"))
    if observations:
        lines.append("trend_observations:")
        for item in observations[:4]:
            item_map = _as_map(item)
            metric = _as_str(item_map.get("metric"))
            trend = _as_str(item_map.get("trend"))
            interpretation_text = _as_str(item_map.get("interpretation"))
            if metric or trend or interpretation_text:
                lines.append(f"- {metric}: {trend} ({interpretation_text})")
    return "\n".join(lines) + "\n"


def build_evidence_alignment_payload(
    *,
    scope: str,
    target_week: IsoWeek,
    evidence_week: IsoWeek,
    historical_baseline_payload: JsonMap | None = None,
    des_analysis_payload: JsonMap | None = None,
    activities_actual_payload: JsonMap | None = None,
    activities_trend_payload: JsonMap | None = None,
) -> JsonMap:
    """Build a compact deterministic evidence-alignment assessment.

    This is a planner-shaping summary only. It never mutates legality or exact
    load authority and exists so the real planning path has a compact, early,
    code-owned evidence interpretation surface.
    """

    caution_flags: list[str] = []
    planning_implications: list[str] = []
    prohibited_overreach: list[str] = []
    continuity_status = "stable"
    load_tolerance_signal = "neutral"
    recovery_fatigue_signal = "neutral"
    durability_signal = "neutral"
    conservative_load_fraction_cap = 0.5
    reduce_quality_density = False

    trend_data = _as_map(_as_map(activities_trend_payload).get("data"))
    weekly_trends = _as_list(trend_data.get("weekly_trends"))
    trend_entry = _as_map(weekly_trends[-1]) if weekly_trends else {}
    weekly_aggregates = _as_map(trend_entry.get("weekly_aggregates"))
    activity_count = weekly_aggregates.get("activity_count")
    work_kj = weekly_aggregates.get("work_kj")
    if activity_count in (0, None) or work_kj in (0, None):
        continuity_status = "disrupted"
        caution_flags.append("previous_week_continuity_low")
        planning_implications.append("Treat the next plan as continuity repair first, not as an aggressive progression opportunity.")
        prohibited_overreach.append("No aggressive catch-up progression on the first week after weak continuity evidence.")
        conservative_load_fraction_cap = min(conservative_load_fraction_cap, 0.35)

    report_data = _as_map(_as_map(des_analysis_payload).get("data"))
    kpi_summary = _as_map(report_data.get("kpi_summary"))
    durability = _as_map(kpi_summary.get("durability"))
    fatigue_resistance = _as_map(kpi_summary.get("fatigue_resistance"))
    recommendation = _as_map(report_data.get("recommendation"))

    durability_status = _as_str(durability.get("status"))
    fatigue_status = _as_str(fatigue_resistance.get("status"))
    urgency = _as_str(recommendation.get("urgency"))
    if durability_status in {"yellow", "red", "inconclusive"}:
        durability_signal = "caution" if durability_status == "yellow" else "constrained"
        reduce_quality_density = True
        caution_flags.append(f"durability_{durability_status}")
        planning_implications.append("Durability evidence does not support aggressive density or hidden compression.")
        prohibited_overreach.append("Do not add extra quality density to compensate for perceived freshness.")
        conservative_load_fraction_cap = min(conservative_load_fraction_cap, 0.4 if durability_status == "yellow" else 0.3)
    if fatigue_status in {"yellow", "red", "inconclusive"}:
        recovery_fatigue_signal = "watch" if fatigue_status == "yellow" else "constrained"
        reduce_quality_density = True
        caution_flags.append(f"fatigue_{fatigue_status}")
        planning_implications.append("Recovery/fatigue evidence supports conservative week shaping and cleaner recovery spacing.")
        prohibited_overreach.append("No stacked quality or back-loaded catch-up after weak fatigue-resistance evidence.")
        conservative_load_fraction_cap = min(conservative_load_fraction_cap, 0.4 if fatigue_status == "yellow" else 0.25)
    if urgency in {"medium", "high"}:
        load_tolerance_signal = "caution" if urgency == "medium" else "constrained"
        caution_flags.append(f"report_urgency_{urgency}")
        planning_implications.append("Treat the report urgency as a conservative shaping signal for the next planning step.")
        conservative_load_fraction_cap = min(conservative_load_fraction_cap, 0.4 if urgency == "medium" else 0.3)

    if not caution_flags:
        planning_implications.append("Evidence does not force an extra-conservative posture beyond the active deterministic authority.")

    if scope == "season":
        if continuity_status == "disrupted" or load_tolerance_signal != "neutral":
            planning_implications.append("Prefer conservative season cadence and progression posture until continuity evidence restabilizes.")
        else:
            planning_implications.append("Season ambition may remain consistent with the selected scenario, but recent evidence still constrains realism.")
        prohibited_overreach.append("Do not let advisory evidence widen season legality or override selected-scenario authority.")
    elif scope == "phase":
        if reduce_quality_density or continuity_status == "disrupted":
            planning_implications.append("Phase shaping should stay stabilization-oriented unless deterministic phase authority already requires a stronger build pattern.")
        else:
            planning_implications.append("Phase can preserve its deterministic intent while staying evidence-aware about recovery and density.")
        prohibited_overreach.append("Do not let evidence rewrite exact phase legality or exact role-week load bands.")
    else:
        if reduce_quality_density or continuity_status == "disrupted":
            planning_implications.append("Week shaping should prefer conservative load placement and lower quality density inside the active band.")
        else:
            planning_implications.append("Week can stay inside the active band without extra evidence-driven damping.")
        prohibited_overreach.append("Do not let evidence override deterministic week legality, fixed rest days, or active weekly band authority.")

    baseline_block_present = bool(_as_map(_as_map(historical_baseline_payload).get("data")))
    return {
        "scope": scope,
        "target_week": _week_key(target_week),
        "evidence_week": _week_key(evidence_week),
        "historical_baseline_present": baseline_block_present,
        "continuity_status": continuity_status,
        "load_tolerance_signal": load_tolerance_signal,
        "recovery_fatigue_signal": recovery_fatigue_signal,
        "durability_signal": durability_signal,
        "caution_flags": caution_flags,
        "planning_implications": planning_implications,
        "prohibited_overreach": prohibited_overreach,
        "conservative_load_fraction_cap": conservative_load_fraction_cap,
        "reduce_quality_density": reduce_quality_density,
    }


def render_evidence_alignment_block(payload: JsonMap | None) -> str:
    """Render a compact evidence-alignment block for prompt injection."""

    alignment = _as_map(payload)
    if not alignment:
        return ""
    lines = [
        "**Evidence Alignment**",
        "This is an early planning interpretation of previous-week evidence. It shapes conservatism and continuity handling, but it never rewrites deterministic legality or exact load authority.",
        f"scope: {_as_str(alignment.get('scope'))}",
        f"target_week: {_as_str(alignment.get('target_week'))}",
        f"evidence_week: {_as_str(alignment.get('evidence_week'))}",
        f"continuity_status: {_as_str(alignment.get('continuity_status'))}",
        f"load_tolerance_signal: {_as_str(alignment.get('load_tolerance_signal'))}",
        f"recovery_fatigue_signal: {_as_str(alignment.get('recovery_fatigue_signal'))}",
        f"durability_signal: {_as_str(alignment.get('durability_signal'))}",
    ]
    caution_flags = [str(item) for item in _as_list(alignment.get("caution_flags")) if str(item).strip()]
    if caution_flags:
        lines.append("caution_flags: " + ", ".join(caution_flags))
    planning_implications = [str(item) for item in _as_list(alignment.get("planning_implications")) if str(item).strip()]
    if planning_implications:
        lines.append("planning_implications:")
        lines.extend(f"- {item}" for item in planning_implications)
    prohibited = [str(item) for item in _as_list(alignment.get("prohibited_overreach")) if str(item).strip()]
    if prohibited:
        lines.append("prohibited_overreach:")
        lines.extend(f"- {item}" for item in prohibited)
    return "\n".join(lines) + "\n"


def render_previous_week_activity_block(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    resolution: PlanningEvidenceResolution,
) -> str:
    """Render the compact previous-week activity block used across planning scopes."""

    if not resolution.activities_actual_version or not resolution.activities_trend_version:
        return ""
    return build_resolved_activity_context_block(
        store,
        athlete_id,
        target_week=target_week,
        activities_actual_version=resolution.activities_actual_version,
        activities_trend_version=resolution.activities_trend_version,
    )


def render_json_compact_block(label: str, payload: JsonMap | None) -> str:
    """Render one compact JSON block for deterministic internal prompt injection."""

    mapping = _as_map(payload)
    if not mapping:
        return ""
    return f"**{label}**\n```json\n{json.dumps(mapping, indent=2, sort_keys=True)}\n```\n"
