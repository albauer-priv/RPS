import pytest

from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.schema_registry import SchemaValidationError


def _store(tmp_path):
    return GuardedValidatedStore(
        athlete_id="test_athlete",
        schema_dir=tmp_path,
        workspace_root=tmp_path,
    )


def test_phase_guardrails_event_window_matches_structured_events(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-11 (B)", "2026-05-16 (A)"],
                "recovery_protection": {"fixed_rest_days": ["Mon"], "notes": "Protect Mon rest day."},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {
                "non_negotiables": ["Protect Mon rest day."],
                "key_risks_warnings": [],
            },
            "events_constraints": {
                "events": [
                    {"date": "2026-04-11", "week": "2026-15", "type": "B", "constraint": "B event"},
                    {"date": "2026-05-16", "week": "2026-20", "type": "A", "constraint": "A event"},
                ]
            },
            "execution_non_negotiables": {
                "recovery_protection_rules": "Protect Mon rest day.",
            },
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_accepts_free_text_event_window_markers(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [
                    "2026-04-25 B event rehearsal window",
                    "2026-05-16 A event peak window",
                ],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {"non_negotiables": [], "key_risks_warnings": []},
            "events_constraints": {
                "events": [
                    {"date": "2026-04-25", "week": "2026-17", "type": "B", "constraint": "B event"},
                    {"date": "2026-05-16", "week": "2026-20", "type": "A", "constraint": "A event"},
                ]
            },
            "execution_non_negotiables": {"recovery_protection_rules": ""},
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_matches_structured_assumptions_and_risks(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": ["Fixed rest days Mon and Fri."],
                "risk_constraints": ["Travel disruption may reduce execution quality."],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": ["Mon", "Fri"], "notes": "Protect recovery anchors."},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {
                "non_negotiables": ["Fixed rest days Mon and Fri."],
                "key_risks_warnings": ["Travel disruption may reduce execution quality."],
            },
            "events_constraints": {"events": []},
            "execution_non_negotiables": {
                "recovery_protection_rules": "Protect recovery anchors.",
            },
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_accepts_recovery_notes_string(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": [], "notes": "Single recovery note."},
            }
        }
    }
    document = {
        "data": {
            "execution_non_negotiables": {
                "recovery_protection_rules": "Single recovery note.",
            },
            "events_constraints": {"events": []},
        }
    }

    store._enforce_phase_guardrails_constraints(document, season_plan)


def test_phase_guardrails_rejects_band_above_explicit_feasible_max(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "data": {
            "phase_summary": {"non_negotiables": [], "key_risks_warnings": []},
            "events_constraints": {"events": []},
            "execution_non_negotiables": {"recovery_protection_rules": ""},
            "load_guardrails": {
                "weekly_kj_bands": [
                    {
                        "week": "2026-17",
                        "band": {
                            "min": 9000,
                            "max": 10600,
                            "notes": "Execution impossible because feasible max is 8470 planned_Load_kJ/week.",
                        },
                    }
                ]
            },
        }
    }

    with pytest.raises(SchemaValidationError) as exc:
        store._enforce_phase_guardrails_constraints(document, season_plan)

    assert any("explicit feasible max 8470" in err for err in exc.value.errors)


def test_phase_structure_event_window_matches_semantically(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-11 (B)"],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-14--2026-16"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Planned event 2026-04-11 with type B must be preserved.",
                ]
            },
            "execution_principles": {"recovery_protection": {"fixed_non_training_days": []}},
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-14--2026-16.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-14--2026-16",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_structure_accepts_free_text_event_window_markers(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-25 B event rehearsal window"],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-17--2026-19"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Preserve the planned event on 2026-04-25 with type B as a controlled rehearsal.",
                ]
            },
            "execution_principles": {"recovery_protection": {"fixed_non_training_days": []}},
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-17--2026-19.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-17--2026-19",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_structure_matches_constraints_as_list_items(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": ["Fixed rest days Mon and Fri."],
                "risk_constraints": ["Travel disruption may reduce execution quality."],
                "planned_event_windows": [],
                "recovery_protection": {"fixed_rest_days": ["Mon", "Fri"], "notes": ["Protect recovery anchors."]},
            }
        }
    }
    document = {
        "meta": {"iso_week_range": "2026-14--2026-16"},
        "data": {
            "upstream_intent": {
                "constraints": [
                    "Fixed rest days Mon and Fri.",
                    "Travel disruption may reduce execution quality.",
                    "Protect recovery anchors.",
                ]
            },
            "execution_principles": {
                "recovery_protection": {"fixed_non_training_days": ["Fri", "Mon"]},
            },
            "load_ranges": {
                "weekly_kj_bands": [],
                "source": "phase_guardrails_2026-14--2026-16.json",
            },
        },
    }

    store._load_phase_guardrails_for_range = lambda _expected: (
        {
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [],
                }
            }
        },
        "2026-14--2026-16",
    )

    store._enforce_phase_structure_constraints(document, season_plan)


def test_phase_guardrails_missing_structured_event_still_fails(tmp_path):
    store = _store(tmp_path)
    season_plan = {
        "data": {
            "global_constraints": {
                "availability_assumptions": [],
                "risk_constraints": [],
                "planned_event_windows": ["2026-04-11 (B)"],
                "recovery_protection": {"fixed_rest_days": [], "notes": []},
            }
        }
    }
    document = {"data": {"events_constraints": {"events": []}}}

    with pytest.raises(SchemaValidationError) as exc:
        store._enforce_phase_guardrails_constraints(document, season_plan)

    assert any("planned_event_windows" in err for err in exc.value.errors)
