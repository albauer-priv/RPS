from rps.agents import multi_output_runner


def test_normalize_phase_guardrails_flattens_recovery_rules_list():
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "execution_non_negotiables": {
                "recovery_protection_rules": [
                    "Keep Monday easy.",
                    "Protect long-ride recovery.",
                ]
            },
            "load_guardrails": {"weekly_kj_bands": []},
        },
    }

    normalized = multi_output_runner.normalize_phase_guardrails_document(document)

    assert (
        normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"]
        == "Keep Monday easy. | Protect long-ride recovery."
    )
