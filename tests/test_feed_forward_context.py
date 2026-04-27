from rps.ui.feed_forward_context import (
    build_resolved_des_evaluation_context,
    build_resolved_season_phase_feed_forward_context,
)
from rps.workspace.iso_helpers import IsoWeek


def test_build_resolved_des_evaluation_context_includes_authoritative_fields():
    block = build_resolved_des_evaluation_context(
        selected_week=IsoWeek(2026, 17),
        report_payload={
            "data": {
                "weekly_analysis": {
                    "interpretation": {"summary": "Durability trend weakened after long rides."}
                },
                "recommendation": {
                    "rationale": ["Decoupling drift increased.", "Fueling stability was mixed."],
                    "suggested_considerations": ["Reduce corridor slightly", "Restrict density for one phase"],
                },
            }
        },
        report_ref="des_analysis_report_2026-17__20260427_055845.json",
        season_plan_ref="season_plan_2026-17__20260427_050000.json",
        affected_phase_id="P01",
        phase_range_key="2026-17--2026-19",
    )

    assert "Resolved DES Evaluation Context (Authoritative)" in block
    assert "- target_iso_week: 2026-17" in block
    assert "- season_plan_ref: season_plan_2026-17__20260427_050000.json" in block
    assert "- des_analysis_report_ref: des_analysis_report_2026-17__20260427_055845.json" in block
    assert "- affected_phase_id: P01" in block
    assert "- affected_phase_range: 2026-17--2026-19" in block
    assert "Durability trend weakened after long rides." in block
    assert "Decoupling drift increased." in block
    assert "Reduce corridor slightly" in block


def test_build_resolved_season_phase_feed_forward_context_includes_adjustment_fields():
    block = build_resolved_season_phase_feed_forward_context(
        selected_week=IsoWeek(2026, 17),
        feed_forward_payload={
            "data": {
                "source_context": {
                    "season_plan_ref": "season_plan_2026-17__20260427_050000.json",
                    "des_analysis_report_ref": "des_analysis_report_2026-17__20260427_055845.json",
                    "affected_phase_id": "P01",
                },
                "decision_summary": {
                    "conclusion": "adjust_phase",
                    "rationale": ["Durability signal dipped in the selected week."],
                },
                "phase_adjustment": {
                    "applies_to_weeks": ["2026-17", "2026-18"],
                    "adjustments": {
                        "kj_corridor": {"direction": "decrease", "percent": 8},
                        "quality_density": {
                            "action": "restrict",
                            "details": "Cap quality days at one for the first affected week.",
                        },
                    },
                },
            }
        },
        feed_forward_ref="season_phase_feed_forward_2026-17__20260427_060000.json",
    )

    assert "Resolved Season->Phase Feed Forward Context (Authoritative)" in block
    assert "- season_phase_feed_forward_ref: season_phase_feed_forward_2026-17__20260427_060000.json" in block
    assert "- season_plan_ref: season_plan_2026-17__20260427_050000.json" in block
    assert "- des_analysis_report_ref: des_analysis_report_2026-17__20260427_055845.json" in block
    assert "- affected_phase_id: P01" in block
    assert "- conclusion: adjust_phase" in block
    assert "- applies_to_weeks: 2026-17, 2026-18" in block
    assert "- kj_corridor_direction: decrease" in block
    assert "- kj_corridor_percent: 8" in block
    assert "- quality_density_action: restrict" in block
    assert "Cap quality days at one for the first affected week." in block
