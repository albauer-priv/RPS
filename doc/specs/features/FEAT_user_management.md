---
Version: 1.0
Status: Implemented
Last-Updated: 2026-09-15
Owner: UI / Config
---
# FEAT: User Management (Auth / Login + Per-User Athlete ID and API Key)

* **ID:** FEAT_user_management
* **Status:** Draft
* **Owner/Area:** UI / Config
* **Last-Updated:** 2026-09-15
* **Related:** `src/rps/ui/shared.py`, `src/rps/core/config.py`, `FEAT_docker_deploy`

---

## 1) Context / Problem

**Current behavior**

* The app has no authentication — any browser on the same network can access all athlete workspaces.
* `athlete_id` defaults to a hardcoded value (`"i150546"`) or `ATHLETE_ID` env var; users enter it manually in the sidebar on every session.
* `RPS_LLM_API_KEY` is a single process-global env var; all sessions share the same LLM account.

**Problem**

* A coach managing multiple athletes cannot safely run a shared instance — any user could access any athlete's data.
* Mistyping athlete ID in the sidebar creates a new empty workspace silently.
* For small-team deployments (coach + 1-3 athletes), a full OAuth/database solution is overengineered.

**Constraints**

* Must be opt-in: if `RPS_USERS_FILE` is not set, the app behaves exactly as today (no auth, athlete_id from env/sidebar).
* No new heavy dependencies (only standard library + already-present `pyyaml`).
* Must not break any existing page flow when auth is disabled.
* Per-user API key override has a documented multi-session caveat (shared process env).

---

## 2) Goals & Non-Goals

**Goals**

* [x] Opt-in login gate: when `RPS_USERS_FILE` is set, every page requires login before rendering.
* [x] YAML user registry binding username → password hash + athlete_id + optional API key override.
* [x] After login: `athlete_id` is read from the user record — sidebar shows it read-only; no manual input.
* [x] Logout button in sidebar clears session and returns to the login screen.
* [x] Per-user `llm_api_key` (optional): if present, overrides `RPS_LLM_API_KEY` in `os.environ` at login time.
* [x] Password stored as `sha256:<hex>` hash; CLI helper (`python -m rps.ui.auth hash <password>`) to generate hashes.
* [x] Tests: user registry loading, password hashing/verification — pure unit tests, no Streamlit.

**Non-Goals**

* [ ] Full OAuth / SSO / SAML.
* [ ] Admin UI for user management (manual YAML editing is acceptable at this scale).
* [ ] Per-user model configuration (single global `RPS_LLM_MODEL` is fine).
* [ ] True multi-session API key isolation (env-override approach is sufficient for small-team single-host deployments; documented limitation).
* [ ] Password reset flow.

---

## 3) Proposed Behavior

### User registry file (`RPS_USERS_FILE`)

```yaml
# config/users.yaml
# Hash passwords: python -m rps.ui.auth hash mypassword
users:
  - username: alex
    password_hash: "sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd..."
    athlete_id: "i150546"
    # llm_api_key: "sk-..."      # optional, overrides RPS_LLM_API_KEY
    # llm_org_id: ""             # optional
```

### Login flow

1. Page loads → `render_global_sidebar()` calls `require_auth(state)`.
2. If `RPS_USERS_FILE` is not set → returns immediately (auth disabled).
3. If `state["auth_user"]` is set → user is already logged in → returns.
4. Otherwise: renders a centered login form (username + password) in the main area and calls `st.stop()`.
5. On submit: looks up username in registry, verifies password hash. On success: sets `state["auth_user"]` + optional env override + `st.rerun()`. On failure: shows error, stays on login form.

### After login

* `get_athlete_id()` returns `state["auth_user"]["athlete_id"]`.
* Sidebar shows `"Logged in as: {username} · {athlete_id}"` and a **Logout** button; no text input for athlete_id.
* Logout: clears `state["auth_user"]` and calls `st.rerun()`.

### Auth disabled (no `RPS_USERS_FILE`)

* `require_auth()` is a no-op.
* `get_athlete_id()` falls back to `os.getenv("ATHLETE_ID") or "i150546"` (current behavior).
* Sidebar shows the athlete_id text input as today.

---

## 4) Implementation Analysis

### New module: `src/rps/ui/auth.py`

```python
@dataclass(frozen=True)
class UserRecord:
    username: str
    athlete_id: str
    llm_api_key: str | None
    llm_org_id: str | None

def hash_password(plain: str) -> str: ...           # → "sha256:<hex>"
def verify_password(plain: str, stored: str) -> bool: ...
def load_user_registry(path: Path) -> dict[str, UserRecord]: ...
def users_file_path() -> Path | None: ...           # reads RPS_USERS_FILE env var
def require_auth(state: dict) -> None: ...          # renders login form + st.stop() if needed
```

`require_auth` renders a full-page login form (centered, outside sidebar) when the user is not authenticated. On successful login, writes `state["auth_user"]` = `{"username": ..., "athlete_id": ..., "api_key": ...}` and applies any env override.

CLI helper (via `__main__`):
```
python -m rps.ui.auth hash mypassword
→ sha256:5e884898da28...
```

### `src/rps/ui/shared.py` changes

* `init_ui_state()`: reads athlete_id from `state["auth_user"]["athlete_id"]` when present.
* `get_athlete_id()`: same — auth_user takes priority over env/default.
* `render_global_sidebar()`:
  * First call: `require_auth(state)` (may call `st.stop()`).
  * If `state["auth_user"]` is set: show `st.caption(f"👤 {username} · {athlete_id}")` + Logout button; skip athlete_id text input.
  * If not (auth disabled): keep existing athlete_id text input unchanged.

### `src/rps/core/config.py` — no changes needed

* The per-user api_key override is applied via `os.environ["RPS_LLM_API_KEY"] = ...` in `require_auth()` at login time. All downstream code that reads `os.getenv("RPS_LLM_API_KEY")` picks it up automatically.
* Documented caveat: in a multi-session deployment, the last login's api_key wins. Acceptable for single-host small-team use; a proper per-session secret store is a future concern.

### Tests: `tests/test_auth.py`

* `test_hash_password_format`: output starts with `"sha256:"`.
* `test_verify_password_correct/incorrect`: standard cases.
* `test_hash_verify_roundtrip`: `verify_password(pw, hash_password(pw))` is True.
* `test_load_user_registry`: loads YAML, returns `UserRecord` for each user.
* `test_load_missing_file`: returns empty dict.
* `test_load_invalid_missing_fields`: entries missing required fields are skipped.
* `test_load_optional_api_key`: api_key field is None when absent.

All tests are pure Python — no Streamlit, no env-var side effects.

---

## 5) Impact Analysis

**Compatibility**

* Backward compatible when `RPS_USERS_FILE` is not set — existing behavior unchanged.
* When set: all pages now require login. No new artifacts, no schema changes.

**Impacted areas**

* `src/rps/ui/shared.py`: `render_global_sidebar`, `init_ui_state`, `get_athlete_id`.
* `src/rps/ui/auth.py`: new module.
* Tests: new file.

---

## 6) Options & Recommendation

### Option A (recommended) — YAML file + sha256 hashing, opt-in via env var

* No new dependencies.
* Backward-compatible: auth disabled when `RPS_USERS_FILE` is not set.
* SHA-256 is sufficient for a team tool; not production-grade but better than plaintext.

### Option B — `st.secrets` TOML file

* Streamlit Cloud-native, uses `secrets.toml`.
* Only works on Streamlit Cloud or local dev — not portable for self-hosted Docker.

### Recommendation

Option A — portable, no extra deps, works in Docker and local dev alike.

---

## 6a) Implementation Readiness Review

* [x] Scope completeness: `auth.py` + `shared.py` changes + tests named.
* [x] Decision completeness: hash format, env-var override, opt-in behavior all specified.
* [x] Architecture conformity: additive; no breaking changes when auth disabled.
* [x] Execution readiness: can implement without inventing missing behavior.

---

## 7) Acceptance Criteria (Definition of Done)

* [x] When `RPS_USERS_FILE` is not set: app behavior is identical to before (no auth check, sidebar unchanged).
* [x] When `RPS_USERS_FILE` is set and user is not logged in: login form is shown, `st.stop()` prevents page from rendering.
* [x] After successful login: `get_athlete_id()` returns the user's configured athlete_id.
* [x] Sidebar shows logged-in user info and Logout button when authenticated; no athlete_id text input.
* [x] `python -m rps.ui.auth hash <password>` prints a usable hash.
* [x] `verify_password(plain, hash_password(plain))` is True.
* [x] Validation passes: `python3 -m py_compile $(git ls-files '*.py')`
* [x] Validation passes: `./scripts/run_lint.sh`
* [x] Validation passes: `./scripts/run_typecheck.sh`
* [x] Validation passes: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_auth.py -x`

---

## 8) Migration / Rollout

* Deploy without `RPS_USERS_FILE` → no behavior change.
* To enable auth: create `config/users.yaml`, hash passwords with CLI helper, set `RPS_USERS_FILE=config/users.yaml`.
* Existing workspace data is untouched; athlete_id in the registry must match the existing workspace directory.

---

## 9) Risks & Failure Modes

* **Risk**: user registry file missing or unreadable.
  * Mitigation: `load_user_registry` logs an error and returns empty dict → login form shows but no credentials work → app is locked. Safe-fail: users can still access if auth is disabled (no `RPS_USERS_FILE`).
* **Risk**: multi-session api_key clobbering.
  * Mitigation: documented limitation; acceptable for single-host small-team deployments.
* **Risk**: SHA-256 without salt is vulnerable to rainbow tables.
  * Mitigation: acceptable for internal tool; PBKDF2 can be substituted later without changing the interface (just change hash format prefix to `pbkdf2:`).

---

## 10) Observability / Logging

* `require_auth` logs `INFO` on successful login (username, not password).
* `load_user_registry` logs `WARNING` on YAML load errors.

---

## 11) Documentation Updates

* [x] `doc/overview/feature_backlog.md` — mark implemented.
* [x] `CHANGELOG.md` — record the feature.
* [x] This spec — update Goals checklist.
* [x] `config/users.yaml.example` — sample registry file.

---

## 12) Link Map

* `doc/overview/feature_backlog.md`
* `src/rps/ui/auth.py`
* `src/rps/ui/shared.py`
* `config/users.yaml.example`
* `tests/test_auth.py`
