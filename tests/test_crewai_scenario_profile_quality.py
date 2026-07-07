from __future__ import annotations

from pathlib import Path

from rps.agents.crewai_task_execution import (
    _SEASON_PLANNING_TASKS,
)
from rps.crewai_runtime import load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_task_blueprints,
)
from rps.crewai_runtime.guardrails import (
    resolve_task_policy,
    season_scenarios_profile_quality,
    season_scenarios_selection_contract_complete,
)
from rps.crewai_runtime.guardrails_context import guardrail_runtime_context


def _season_scenario_item(
    *,
    scenario_id: str,
    load_philosophy: str,
    risk_profile: str,
    key_differences: str,
    cadence: str,
    allowed_domains: list[str],
    decision_notes: list[str],
    best_suited_if: str,
    risk_flags: list[str],
    constraint_summary: list[str] | None = None,
    event_alignment_notes: list[str] | None = None,
    kpi_guardrail_notes: list[str] | None = None,
    season_archetype: str = "none",
    season_archetype_rationale: list[str] | None = None,
    recovery_margin: str = "medium",
    fatigue_exposure: str = "moderate",
    specificity_density: str = "controlled",
) -> dict:
    return {
        "scenario_id": scenario_id,
        "name": f"Scenario {scenario_id}",
        "core_idea": key_differences,
        "load_philosophy": load_philosophy,
        "risk_profile": risk_profile,
        "key_differences": key_differences,
        "best_suited_if": best_suited_if,
        "scenario_guidance": {
            "recovery_margin": recovery_margin,
            "fatigue_exposure": fatigue_exposure,
            "specificity_density": specificity_density,
            "deload_cadence": cadence,
            "risk_flags": risk_flags,
            "event_alignment_notes": event_alignment_notes or [],
            "constraint_summary": constraint_summary or [],
            "kpi_guardrail_notes": kpi_guardrail_notes or [],
            "decision_notes": decision_notes,
            "season_archetype": season_archetype,
            "season_archetype_rationale": season_archetype_rationale or [],
            "intensity_guidance": {"allowed_domains": allowed_domains},
        },
    }


def _season_scenarios_payload(*scenarios: dict, notes: list[str] | None = None) -> dict:
    return {
        "meta": {"artifact_type": "SEASON_SCENARIOS", "schema_id": "SeasonScenariosInterface"},
        "data": {
            "notes": notes
            or [
                "allowed_domains define eligibility for later assignment only; they do not authorize every domain in every phase.",
                "objective mismatch remains unresolved upstream input context and is not resolved in the scenario layer.",
            ],
            "scenarios": list(scenarios),
        },
    }


def test_season_scenarios_profile_quality_accepts_same_domains_with_distinct_profiles() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Highest executability and lowest density.",
                key_differences="Completion-first with minimal fatigue exposure.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
                constraint_summary=["Low density."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work and long-ride progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
                constraint_summary=["Long-ride progression."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for a longer build with back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert ok is True
    assert payload["data"]["scenarios"][2]["scenario_id"] == "C"

def test_season_scenarios_selection_contract_complete_rejects_missing_operational_posture() -> None:
    failed, message = season_scenarios_selection_contract_complete(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Highest executability and lowest density.",
                key_differences="Completion-first with minimal fatigue exposure.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
                constraint_summary=["Low density."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work and long-ride progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
                constraint_summary=["Long-ride progression."],
                recovery_margin="",
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for a longer build with back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert "scenario_guidance.recovery_margin" in message

def test_season_scenarios_profile_quality_accepts_vo2_rationale_from_kpi_guardrail_notes() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Highest executability and lowest density.",
                key_differences="Completion-first with minimal fatigue exposure.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
                constraint_summary=["Low density."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
                constraint_summary=["Long-ride progression."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "VO2MAX"],
                decision_notes=["Use 3:1 cadence for back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
                kpi_guardrail_notes=[
                    "3:1 cadence supports the longer build, and VO2MAX is allowed only as sparse ceiling-support work when fresh-only, not primary identity, while ambition comes from specificity-under-fatigue and load posture."
                ],
            ),
        )
    )

    assert ok is True
    assert payload["data"]["scenarios"][2]["scenario_id"] == "C"

def test_season_scenarios_profile_quality_rejects_weak_scenario_c() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher weekly kJ only.",
                risk_profile="Higher risk.",
                key_differences="More kJ.",
                cadence="3:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 3:1 cadence for a bigger build."],
                best_suited_if="Choose only when stable recovery and high load tolerance support lower recovery margin.",
                risk_flags=["Too aggressive if fatigue risk appears."],
            ),
        )
    )

    assert failed is False
    assert "Scenario C must express ambitious specificity" in message

def test_season_scenarios_profile_quality_rejects_shared_cadence_without_explicit_justification() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1:1 cadence for high recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Higher specificity and fatigue exposure.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence for harder event-simulation weeks and back-to-back specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Fatigue exposure and event simulation."],
            ),
        )
    )

    assert failed is False
    assert message == "Season scenarios collapse cadence across A/B/C without explicit justification."

def test_season_scenarios_profile_quality_accepts_shared_cadence_with_explicit_justification() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=[
                    "Use 2:1:1 cadence and keep cadence constant across scenarios because differentiation comes from recovery margin and load philosophy."
                ],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=[
                    "Use 2:1:1 cadence and keep cadence constant while differentiation comes from specificity-under-fatigue and balanced risk posture."
                ],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Higher specificity and fatigue exposure.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=[
                    "Use 2:1:1 cadence and keep cadence constant while differentiation comes from event simulation, fatigue exposure, and risk profile."
                ],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Fatigue exposure and event simulation."],
            ),
        )
    )

    assert ok is True
    assert payload["data"]["scenarios"][0]["scenario_guidance"]["deload_cadence"] == "2:1:1"

def test_season_scenarios_profile_quality_accepts_recommendation_mirrored_cadence_with_explicit_justification() -> None:
    with guardrail_runtime_context(season_scenario_recommendation_context={"recommended_cadence": "2:1:1"}):
        ok, payload = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                    risk_profile="Lowest risk profile.",
                    key_differences="Completion-first with sparse tempo.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=[
                        "Use 2:1:1 cadence and keep cadence intentionally shared because differentiation comes from recovery margin and low-risk load philosophy."
                    ],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                    risk_profile="Balanced recovery risk.",
                    key_differences="Durability-forward target plan.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=[
                        "Use 2:1:1 cadence and keep cadence intentionally shared because differentiation comes from systematic progression, specificity-under-fatigue, and balanced risk posture."
                    ],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                    risk_profile="Higher specificity and fatigue exposure.",
                    key_differences="More back-to-back and hard-late specificity.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=[
                        "Use 2:1:1 cadence and keep cadence intentionally shared because differentiation comes from event simulation, fatigue exposure tolerance, and risk posture."
                    ],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Fatigue exposure and event simulation."],
                ),
            )
        )

    assert ok is True
    assert payload["data"]["scenarios"][0]["scenario_guidance"]["deload_cadence"] == "2:1:1"

def test_season_scenarios_profile_quality_rejects_recommendation_mirrored_cadence_without_rationale() -> None:
    with guardrail_runtime_context(season_scenario_recommendation_context={"recommended_cadence": "2:1:1"}):
        failed, message = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                    risk_profile="Lowest risk profile.",
                    key_differences="Completion-first with sparse tempo.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1:1 cadence for high recovery margin."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                    risk_profile="Balanced recovery risk.",
                    key_differences="Durability-forward target plan.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                    risk_profile="Higher specificity and fatigue exposure.",
                    key_differences="More back-to-back and hard-late specificity.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 2:1:1 cadence for harder event-simulation weeks and back-to-back specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Fatigue exposure and event simulation."],
                ),
            )
        )

    assert failed is False
    assert message == "Recommendation-default cadence was mirrored across all scenarios without scenario differentiation."

def test_season_scenarios_profile_quality_accepts_mixed_cadence_with_advisory_recommendation_context() -> None:
    with guardrail_runtime_context(season_scenario_recommendation_context={"recommended_cadence": "2:1:1"}):
        ok, payload = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                    risk_profile="Lowest risk profile.",
                    key_differences="Completion-first with sparse tempo.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence for the most recovery-protective option despite the advisory recommendation."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                    risk_profile="Balanced recovery risk.",
                    key_differences="Durability-forward target plan.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence because the advisory recommendation fits the balanced durability profile."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                    risk_profile="Higher specificity and fatigue exposure.",
                    key_differences="More back-to-back and hard-late specificity.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for a longer build with event simulation and back-to-back specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Fatigue exposure and event simulation."],
                ),
            )
        )

    assert ok is True
    assert payload["data"]["scenarios"][1]["scenario_guidance"]["deload_cadence"] == "2:1:1"

def test_season_scenarios_profile_quality_rejects_cluster_wording_without_multiple_future_events() -> None:
    with guardrail_runtime_context(
        season_scenario_event_context={
            "future_events": [{"type": "B", "date": "2026-08-02", "event_name": "Summer 200"}],
            "all_events": [{"type": "B", "date": "2026-08-02", "event_name": "Summer 200"}],
        }
    ):
        failed, message = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Low envelope.",
                    risk_profile="Low risk.",
                    key_differences="Conservative.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence to protect recovery margin."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                    event_alignment_notes=["Use the B-event cluster as a rehearsal platform."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Balanced envelope.",
                    risk_profile="Balanced risk.",
                    key_differences="Default.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Higher envelope with event simulation.",
                    risk_profile="Higher fatigue exposure.",
                    key_differences="Specificity under fatigue.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Event simulation and fatigue exposure."],
                ),
            )
        )

    assert failed is False
    assert message == "Cluster wording requires multiple relevant in-horizon events."

def test_season_scenarios_profile_quality_accepts_cluster_wording_with_multiple_future_events() -> None:
    with guardrail_runtime_context(
        season_scenario_event_context={
            "future_events": [
                {"type": "B", "date": "2026-08-02", "event_name": "Summer 200"},
                {"type": "B", "date": "2026-08-16", "event_name": "Late Summer 200"},
            ],
            "all_events": [
                {"type": "B", "date": "2026-08-02", "event_name": "Summer 200"},
                {"type": "B", "date": "2026-08-16", "event_name": "Late Summer 200"},
            ],
        }
    ):
        ok, payload = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Low envelope.",
                    risk_profile="Low risk.",
                    key_differences="Conservative.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence to protect recovery margin."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                    event_alignment_notes=["Use the B-event cluster as a low-risk rehearsal path."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Balanced envelope.",
                    risk_profile="Balanced risk.",
                    key_differences="Default.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Higher envelope with event simulation.",
                    risk_profile="Higher fatigue exposure.",
                    key_differences="Specificity under fatigue.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Event simulation and fatigue exposure."],
                ),
            )
        )

    assert ok is True
    assert payload["data"]["scenarios"][0]["scenario_id"] == "A"

def test_season_scenarios_profile_quality_rejects_pre_horizon_event_as_active_logic() -> None:
    with guardrail_runtime_context(
        season_scenario_event_context={
            "future_events": [{"type": "B", "date": "2026-08-02", "event_name": "Summer 200"}],
            "all_events": [
                {"type": "B", "date": "2026-04-11", "event_name": "Spring 200"},
                {"type": "B", "date": "2026-08-02", "event_name": "Summer 200"},
            ],
        }
    ):
        failed, message = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Low envelope.",
                    risk_profile="Low risk.",
                    key_differences="Conservative.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence and Spring 200 as an active rehearsal anchor."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Balanced envelope.",
                    risk_profile="Balanced risk.",
                    key_differences="Default.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Higher envelope with event simulation.",
                    risk_profile="Higher fatigue exposure.",
                    key_differences="Specificity under fatigue.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Event simulation and fatigue exposure."],
                ),
            )
        )

    assert failed is False
    assert message == "Season scenarios must not describe pre-horizon events as active rehearsal/anchor/peak logic."

def test_season_scenarios_profile_quality_rejects_resolved_objective_mismatch_claim() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
            notes=[
                "allowed_domains define eligibility for later assignment only; they do not authorize every domain in every phase.",
                "objective reconciled for the new event hierarchy here.",
            ],
        )
    )

    assert failed is False
    assert message == "Scenario layer must not claim that objective mismatch is already resolved."

def test_season_scenarios_profile_quality_rejects_ceiling_first_without_full_rationale() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for early ceiling support."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                season_archetype="ceiling_first_durability",
                season_archetype_rationale=["Early ceiling support is permitted."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario C may use ceiling_first_durability only with explicit rationale and preserved runway."

def test_season_scenarios_profile_quality_rejects_missing_selection_gate_semantics() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="A nice option for many athletes.",
                risk_flags=["General caution."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario A must include a meaningful best_suited_if selection gate."

def test_season_scenarios_profile_quality_rejects_missing_risk_flag_semantics() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["General caution if things get hard."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario A must include concrete caution markers in risk_flags."

def test_season_scenarios_profile_quality_rejects_vo2_rationale_missing_primary_identity_clause() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break or recovery slip appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "VO2MAX"],
                decision_notes=["Use 3:1 cadence for back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
                kpi_guardrail_notes=[
                    "3:1 cadence supports the longer build, and VO2MAX is allowed only as sparse ceiling-support work when fresh-only, while ambition comes from specificity-under-fatigue and load posture."
                ],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario C may allow VO2MAX only with explicit sparse ceiling-support rationale."

def test_season_scenarios_profile_quality_rejects_vo2_rationale_missing_specificity_source() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break or recovery slip appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with a larger workload envelope.",
                risk_profile="Ambitious performance-forward long build with lower recovery margin.",
                key_differences="More specificity and less recovery margin.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "VO2MAX"],
                decision_notes=["Use 3:1 cadence for a longer specificity build."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Longer overload build with reduced recovery margin."],
                kpi_guardrail_notes=[
                    "3:1 cadence supports the longer build, and VO2MAX is allowed only as sparse ceiling-support work when fresh-only, not primary identity, while ambition comes from durability ambition and general race readiness."
                ],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario C may allow VO2MAX only with explicit sparse ceiling-support rationale."

def test_season_scenarios_profile_quality_accepts_scenario_c_without_vo2max() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break or recovery slip appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
                kpi_guardrail_notes=[
                    "Ambition comes from specificity-under-fatigue, density, and event simulation rather than optional high-intensity escalation."
                ],
            ),
        )
    )

    assert ok is True
    assert "VO2MAX" not in payload["data"]["scenarios"][2]["scenario_guidance"]["intensity_guidance"]["allowed_domains"]

def test_season_scenarios_profile_quality_rejects_phase_wide_domain_authorization_wording() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
            notes=["allowed_domains are globally authorized for all phases."],
        )
    )

    assert failed is False
    assert message == "Season scenarios must state that allowed_domains are eligibility only, not phase-wide authorization."

def test_season_scenarios_task_policy_uses_profile_quality_guardrail() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)
    policy = resolve_task_policy(blueprints["season_scenarios"], bundle.task_policies)

    assert "season_scenarios_profile_quality" in policy.guardrails
    assert "season_scenarios_selection_contract_complete" in policy.guardrails

def test_season_scenarios_task_uses_narrow_workspace_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)
    task = blueprints["season_scenarios"]

    assert task.config["tools"] == ["workspace_get_input", "workspace_get_latest"]

def test_early_planning_tasks_consume_evidence_alignment_context_before_synthesis() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    expected_contexts = {
        "season_macrocycle_draft": "season_evidence_alignment",
        "season_load_corridor_draft": "season_evidence_alignment",
        "season_progression_review": "season_evidence_alignment",
        "season_phase_blueprint_draft": "season_evidence_alignment",
        "phase_guardrail_band_draft": "phase_evidence_alignment",
        "phase_structure_draft": "phase_evidence_alignment",
        "phase_cadence_recovery_draft": "phase_evidence_alignment",
        "week_load_target_draft": "week_evidence_alignment",
        "week_revision_draft": "week_evidence_alignment",
        "week_workout_text_draft": "week_evidence_alignment",
    }

    for task_name, context_name in expected_contexts.items():
        task = blueprints[task_name]
        assert context_name in task.context_names
        assert "exact deterministic authority first" in task.description
        assert "resolved previous-week evidence" in task.description
        assert "evidence-alignment implications" in task.description
        assert "must not rewrite authority" in task.description

def test_season_planning_task_order_places_evidence_alignment_before_its_consumers() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)
    seen: set[str] = set()
    for task_name in _SEASON_PLANNING_TASKS:
        blueprint = blueprints[task_name]
        missing = [item for item in blueprint.context_names if item not in seen]
        assert missing == [], f"{task_name} has unresolved early contexts: {missing}"
        seen.add(task_name)

    evidence_idx = _SEASON_PLANNING_TASKS.index("season_evidence_alignment")

    assert evidence_idx > _SEASON_PLANNING_TASKS.index("season_historical_context_review")
    assert evidence_idx < _SEASON_PLANNING_TASKS.index("season_macrocycle_draft")
    assert evidence_idx < _SEASON_PLANNING_TASKS.index("season_load_corridor_draft")
    assert evidence_idx < _SEASON_PLANNING_TASKS.index("season_progression_review")
    assert evidence_idx < _SEASON_PLANNING_TASKS.index("season_phase_blueprint_draft")
    assert evidence_idx < _SEASON_PLANNING_TASKS.index("season_plan_finalize")

    assert _SEASON_PLANNING_TASKS.index("season_phase_blueprint_draft") > _SEASON_PLANNING_TASKS.index("season_progression_review")
    assert _SEASON_PLANNING_TASKS.index("season_phase_blueprint_draft") < _SEASON_PLANNING_TASKS.index("season_plan_finalize")
    assert "season_phase_blueprint_draft" in blueprints["season_plan_finalize"].context_names
