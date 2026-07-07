"""JSON-safe scalar normalization and formatting for Intervals.icu compiled outputs."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from rps.data_pipeline.intervals_formatting import seconds_to_hms

# === Activities Actual helpers ===

def normalize_key(label: str) -> str:
    """Normalize a column label into a snake_case key."""
    key = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip()).strip("_").lower()
    return key or "col"


def unique_key(base: str, used: set[str]) -> str:
    """Return a unique key, suffixing with _N if needed."""
    if base not in used:
        return base
    idx = 2
    while f"{base}_{idx}" in used:
        idx += 1
    return f"{base}_{idx}"


def normalize_scalar(value):
    """Normalize pandas scalars into native Python values."""
    if pd.isna(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, pd.Timestamp):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def normalize_bool(value):
    """Normalize a scalar into a boolean when possible."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def format_date(value):
    """Format a scalar into a YYYY-MM-DD date string."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date().isoformat()
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[0]
    return text.split(" ", 1)[0]


def format_datetime(value):
    """Format a scalar into an ISO 8601 timestamp string."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return str(value)


def format_duration_hms(value):
    """Format a scalar into HH:MM:SS when possible."""
    value = normalize_scalar(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return seconds_to_hms(value)
    text = str(value)
    return text if text.strip() else None


def format_number(value):
    """Normalize numeric values into floats."""
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def format_int(value):
    """Normalize numeric values into integers."""
    value = normalize_scalar(value)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def format_string(value):
    """Normalize values into strings, returning None for empties."""
    value = normalize_scalar(value)
    if value is None:
        return None
    return str(value)


def ensure_keys(label: str, actual_keys: set[str], expected_keys: set[str], context: str) -> None:
    """Raise if actual keys differ from expected keys."""
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if not missing and not extra:
        return
    details = []
    if missing:
        details.append(f"missing: {sorted(missing)}")
    if extra:
        details.append(f"extra: {sorted(extra)}")
    detail_text = "; ".join(details)
    raise ValueError(f"{label} keys mismatch ({context}): {detail_text}")


def write_parquet_cache(df: pd.DataFrame, out_file: Path, logger: logging.Logger) -> None:
    """Best-effort Parquet cache write for analytics workloads."""
    try:
        df.to_parquet(out_file, index=False)
    except Exception as exc:
        try:
            fixed = df.copy()
            for col in fixed.columns:
                if fixed[col].dtype == object:
                    converted = pd.to_numeric(fixed[col], errors="coerce")
                    if converted.notna().any():
                        fixed[col] = converted
                    else:
                        fixed[col] = fixed[col].astype("string")
            fixed.to_parquet(out_file, index=False)
            logger.info("Parquet cache write succeeded after dtype cleanup path=%s", out_file)
        except Exception as retry_exc:
            logger.warning(
                "Parquet cache write failed path=%s error=%s retry_error=%s",
                out_file,
                exc,
                retry_exc,
            )
