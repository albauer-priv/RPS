"""Pure helpers for Coach turn language and scoped-preview heuristics."""

from __future__ import annotations

from collections.abc import Sequence

JsonMap = dict[str, object]

_GERMAN_MARKERS = (
    "bitte",
    "woche",
    "wochenplan",
    "anpassen",
    "ändern",
    "verschieben",
    "erstellen",
    "vorschau",
    "ja",
    "nein",
    "und",
    "der",
    "die",
    "das",
    "leicht",
    "entsprechend",
)

_DIRECT_ADJUST_MARKERS = (
    "wochenplan anpassen",
    "woche anpassen",
    "restliche woche anpassen",
    "week plan adjust",
    "adjust the week plan",
    "adjust the week",
    "change the week plan",
    "update the week plan",
)

_PREVIEW_MARKERS = (
    "preview",
    "vorschau",
)

_AFFIRMATION_MARKERS = (
    "ja",
    "yes",
    "ok",
    "okay",
    "mach",
    "do it",
    "go ahead",
    "create",
    "erstellen",
)


def detect_reply_language(user_message: str, history: Sequence[JsonMap] | None = None) -> str:
    """Return a lightweight `de`/`en` guess based on the current user message first."""

    text = (user_message or "").strip().lower()
    if not text and history:
        for message in reversed(history):
            if str(message.get("role") or "") == "user":
                text = str(message.get("content") or "").strip().lower()
                if text:
                    break
    if any(ch in text for ch in ("ä", "ö", "ü", "ß")):
        return "de"
    if sum(1 for marker in _GERMAN_MARKERS if marker in text) >= 2:
        return "de"
    return "en"


def is_direct_week_adjust_request(user_message: str) -> bool:
    """Return true for broad week-adjustment requests that should map to a scoped replan preview."""

    text = (user_message or "").strip().lower()
    if any(marker in text for marker in _DIRECT_ADJUST_MARKERS):
        return True
    if "wochenplan" in text and any(marker in text for marker in ("anpassen", "ändern")):
        return True
    return "week plan" in text and any(marker in text for marker in ("adjust", "change", "update"))


def is_preview_creation_request(user_message: str) -> bool:
    """Return true when the user explicitly asks to create a preview."""

    text = (user_message or "").strip().lower()
    return any(marker in text for marker in _PREVIEW_MARKERS) and any(
        marker in text for marker in _AFFIRMATION_MARKERS
    )


def build_scoped_preview_message(history: Sequence[JsonMap], user_message: str) -> str:
    """Build a compact replan message from the latest conversation context."""

    relevant: list[str] = []
    for message in history[-4:]:
        role = str(message.get("role") or "").strip().upper()
        content = str(message.get("content") or "").strip()
        if role and content:
            relevant.append(f"{role}: {content}")
    relevant.append(f"USER: {user_message.strip()}")
    return (
        "Create a lightly adjusted scoped week replan from this conversation context. "
        "Preserve the week structure where possible and translate broad guidance into concrete selected-week plan changes.\n\n"
        + "\n\n".join(relevant)
    ).strip()


def localized_preview_created_reply(*, language: str, iso_week: str, summary: str) -> str:
    """Return a deterministic user-facing reply after creating a scoped replan preview."""

    if language == "de":
        return (
            f"Ich habe eine Preview fuer eine angepasste Wochenplan-Aenderung fuer {iso_week} erstellt.\n\n"
            f"Preview vorhanden: ja\n"
            f"Bestaetigung erforderlich: ja\n"
            f"Nur previewed: ja, es wurde noch nichts angewendet\n"
            f"Zusammenfassung: {summary}\n\n"
            "Wenn die Richtung passt, antworte mit `ja`, `anwenden` oder `confirm`."
        )
    return (
        f"I created a preview for an adjusted week-plan change for {iso_week}.\n\n"
        f"Preview exists: yes\n"
        f"Confirmation required: yes\n"
        f"Only previewed: yes, nothing has been applied yet\n"
        f"Summary: {summary}\n\n"
        "If this direction looks right, reply with `yes`, `apply`, or `confirm`."
    )
