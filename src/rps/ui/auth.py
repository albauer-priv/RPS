"""Opt-in authentication for the RPS Streamlit app.

Enabled by setting the RPS_USERS_FILE environment variable to a YAML file path.
When not set, all functions are no-ops and the app behaves as before.

Hash a password for the registry:
    python -m rps.ui.auth hash <password>
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_AUTH_STATE_KEY = "auth_user"


@dataclass(frozen=True)
class UserRecord:
    username: str
    athlete_id: str
    llm_api_key: str | None
    llm_org_id: str | None


def hash_password(plain: str) -> str:
    """Return a sha256 hash string in the form ``sha256:<hex>``."""
    digest = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def verify_password(plain: str, stored: str) -> bool:
    """Return True when ``plain`` matches the stored hash."""
    if not stored.startswith("sha256:"):
        return False
    expected = stored[len("sha256:"):]
    actual = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, expected)


def users_file_path() -> Path | None:
    """Return the path to the users YAML file, or None if auth is disabled."""
    raw = os.getenv("RPS_USERS_FILE")
    return Path(raw) if raw else None


def load_user_registry(path: Path) -> dict[str, UserRecord]:
    """Load user records from a YAML file keyed by username.

    Returns an empty dict on any error (missing file, bad YAML, etc.) so the
    app stays in a locked-but-stable state.
    """
    if not path.exists():
        logger.warning("User registry not found: %s", path)
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.error("Failed to load user registry %s: %s", path, exc)
        return {}
    users_list = raw.get("users") if isinstance(raw, dict) else None
    if not isinstance(users_list, list):
        logger.warning("User registry has no 'users' list: %s", path)
        return {}
    registry: dict[str, UserRecord] = {}
    for entry in users_list:
        if not isinstance(entry, dict):
            continue
        username = entry.get("username")
        athlete_id = entry.get("athlete_id")
        password_hash = entry.get("password_hash")
        if not (username and athlete_id and password_hash):
            logger.warning("Skipping incomplete user entry in registry: %s", entry)
            continue
        registry[str(username)] = UserRecord(
            username=str(username),
            athlete_id=str(athlete_id),
            llm_api_key=str(entry["llm_api_key"]) if entry.get("llm_api_key") else None,
            llm_org_id=str(entry["llm_org_id"]) if entry.get("llm_org_id") else None,
        )
    return registry


def _apply_user_env(user: UserRecord) -> None:
    """Apply per-user env overrides for downstream LLM calls."""
    if user.llm_api_key:
        os.environ["RPS_LLM_API_KEY"] = user.llm_api_key
    if user.llm_org_id:
        os.environ["RPS_LLM_ORG_ID"] = user.llm_org_id


def require_auth(state: dict) -> None:
    """Show login form and stop page rendering if the user is not authenticated.

    No-op when RPS_USERS_FILE is not set (auth disabled).
    Writes ``state["auth_user"]`` on successful login.
    """
    import streamlit as st  # local import to keep module importable outside Streamlit

    path = users_file_path()
    if path is None:
        return

    if state.get(_AUTH_STATE_KEY):
        return

    registry = load_user_registry(path)

    st.title("RPS · Login")
    with st.form("rps_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = registry.get(username)
        stored_hash = None
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for entry in (raw.get("users") or []):
                if isinstance(entry, dict) and entry.get("username") == username:
                    stored_hash = entry.get("password_hash")
                    break
        if user and stored_hash and verify_password(password, stored_hash):
            state[_AUTH_STATE_KEY] = {
                "username": user.username,
                "athlete_id": user.athlete_id,
            }
            _apply_user_env(user)
            logger.info("Login successful: username=%s athlete_id=%s", user.username, user.athlete_id)
            st.rerun()
        else:
            st.error("Invalid username or password.")

    st.stop()


def get_auth_user(state: dict) -> dict | None:
    """Return the authenticated user dict, or None if not logged in."""
    return state.get(_AUTH_STATE_KEY)


def logout(state: dict) -> None:
    """Clear the authenticated user from session state."""
    state.pop(_AUTH_STATE_KEY, None)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "hash":
        print(hash_password(sys.argv[2]))
    else:
        print("Usage: python -m rps.ui.auth hash <password>")
        sys.exit(1)
