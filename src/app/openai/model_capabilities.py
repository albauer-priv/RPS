"""Model capability helpers."""

from __future__ import annotations


def supports_temperature(model: str | None) -> bool:
    """Return True if the model accepts temperature."""
    if not model:
        return True
    normalized = model.strip().lower()
    if normalized.startswith("gpt-5"):
        return False
    return True
