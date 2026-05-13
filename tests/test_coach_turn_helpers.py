from rps.ui.coach_turn_helpers import (
    build_scoped_preview_message,
    detect_reply_language,
    is_direct_week_adjust_request,
    is_preview_creation_request,
    localized_preview_created_reply,
)


def test_detect_reply_language_prefers_german_markers() -> None:
    assert detect_reply_language("Bitte den Wochenplan leicht anpassen") == "de"


def test_detect_reply_language_defaults_to_english() -> None:
    assert detect_reply_language("Please adjust the week plan slightly") == "en"


def test_direct_week_adjust_request_detects_broad_adjustment() -> None:
    assert is_direct_week_adjust_request("ok, bitte den Wochenplan entsprechend anpassen") is True
    assert is_direct_week_adjust_request("Was ist diese Woche geplant?") is False


def test_preview_creation_request_detects_explicit_preview_turn() -> None:
    assert is_preview_creation_request("ja, preview erstellen") is True
    assert is_preview_creation_request("ja") is False


def test_build_scoped_preview_message_includes_recent_context() -> None:
    message = build_scoped_preview_message(
        [
            {"role": "user", "content": "bitte den Wochenplan entsprechend anpassen"},
            {"role": "assistant", "content": "Ich kann daraus eine konkrete Preview machen."},
        ],
        "ja, preview erstellen",
    )
    assert "USER: bitte den Wochenplan entsprechend anpassen" in message
    assert "ASSISTANT: Ich kann daraus eine konkrete Preview machen." in message
    assert message.endswith("USER: ja, preview erstellen")


def test_localized_preview_created_reply_supports_german() -> None:
    reply = localized_preview_created_reply(
        language="de",
        iso_week="2026-20",
        summary="Scoped replan prepared for 2026-20.",
    )
    assert "Ich habe eine Preview" in reply
    assert "Bestaetigung erforderlich: ja" in reply
