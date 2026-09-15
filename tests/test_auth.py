"""Tests for optional auth/login (FEAT_user_management)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from rps.ui.auth import (
    UserRecord,
    hash_password,
    load_user_registry,
    verify_password,
)

# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------


def test_hash_password_format() -> None:
    result = hash_password("mysecret")
    assert result.startswith("sha256:")
    assert len(result) == len("sha256:") + 64


def test_verify_password_correct() -> None:
    stored = hash_password("correct")
    assert verify_password("correct", stored) is True


def test_verify_password_incorrect() -> None:
    stored = hash_password("correct")
    assert verify_password("wrong", stored) is False


def test_hash_verify_roundtrip() -> None:
    pw = "hunter2!@#abc"
    assert verify_password(pw, hash_password(pw)) is True


def test_verify_password_known_vector() -> None:
    # sha256("password") is well-known
    known = "sha256:" + hashlib.sha256(b"password").hexdigest()
    assert verify_password("password", known) is True
    assert verify_password("Password", known) is False


def test_verify_password_unsupported_format() -> None:
    assert verify_password("anything", "md5:abc123") is False


# ---------------------------------------------------------------------------
# load_user_registry
# ---------------------------------------------------------------------------


def _write_registry(path: Path, content: dict) -> None:
    path.write_text(yaml.dump(content), encoding="utf-8")


def test_load_user_registry_basic(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    _write_registry(f, {
        "users": [
            {
                "username": "alex",
                "password_hash": hash_password("secret"),
                "athlete_id": "i150546",
            }
        ]
    })
    registry = load_user_registry(f)
    assert "alex" in registry
    user = registry["alex"]
    assert isinstance(user, UserRecord)
    assert user.username == "alex"
    assert user.athlete_id == "i150546"
    assert user.llm_api_key is None
    assert user.llm_org_id is None


def test_load_user_registry_with_optional_fields(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    _write_registry(f, {
        "users": [
            {
                "username": "coach",
                "password_hash": hash_password("pw"),
                "athlete_id": "coach_ws",
                "llm_api_key": "sk-abc",
                "llm_org_id": "org-xyz",
            }
        ]
    })
    registry = load_user_registry(f)
    user = registry["coach"]
    assert user.llm_api_key == "sk-abc"
    assert user.llm_org_id == "org-xyz"


def test_load_user_registry_multiple_users(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    _write_registry(f, {
        "users": [
            {"username": "alice", "password_hash": hash_password("a"), "athlete_id": "a1"},
            {"username": "bob", "password_hash": hash_password("b"), "athlete_id": "b1"},
        ]
    })
    registry = load_user_registry(f)
    assert set(registry.keys()) == {"alice", "bob"}


def test_load_user_registry_missing_file(tmp_path: Path) -> None:
    registry = load_user_registry(tmp_path / "nonexistent.yaml")
    assert registry == {}


def test_load_user_registry_empty_file(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    f.write_text("", encoding="utf-8")
    registry = load_user_registry(f)
    assert registry == {}


def test_load_user_registry_invalid_yaml(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    f.write_text(":::invalid:yaml:::", encoding="utf-8")
    registry = load_user_registry(f)
    assert registry == {}


def test_load_user_registry_no_users_key(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    _write_registry(f, {"settings": {}})
    registry = load_user_registry(f)
    assert registry == {}


def test_load_user_registry_skips_incomplete_entries(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    _write_registry(f, {
        "users": [
            {"username": "incomplete"},  # missing athlete_id and password_hash
            {"username": "valid", "password_hash": hash_password("x"), "athlete_id": "ws1"},
        ]
    })
    registry = load_user_registry(f)
    assert "incomplete" not in registry
    assert "valid" in registry


def test_load_user_registry_non_dict_entry_skipped(tmp_path: Path) -> None:
    f = tmp_path / "users.yaml"
    _write_registry(f, {"users": ["not-a-dict", None]})
    registry = load_user_registry(f)
    assert registry == {}
