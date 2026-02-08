"""Shared UI helpers for multipage Streamlit app."""

from __future__ import annotations

import io
import logging
import os
import re
from contextlib import redirect_stdout
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from jinja2 import BaseLoader, Environment
import streamlit as st

from rps.core.config import load_app_settings, load_env_file
from rps.core.logging import _normalize_level, setup_logging
from rps.openai.client import get_client
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.prompts.loader import PromptLoader
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange, parse_iso_week_range, range_contains
from rps.workspace.types import ArtifactType
from rps.workspace.paths import ARTIFACT_PATHS


ROOT = Path(__file__).resolve().parents[3]
load_env_file(ROOT / ".env")
SETTINGS = load_app_settings()

LOGGER = logging.getLogger("rps.streamlit")
UI_LOG_LEVEL = _normalize_level(os.getenv("RPS_LOG_LEVEL_UI", "INFO"))

CAPTURE_LOGGERS: list[logging.Logger] = [
    logging.getLogger("rps.workspace.guarded_store"),
]

PHASE_CARD_TEMPLATE = """#### Phase narrative
{{ phase.narrative or "N/A" }}

#### Phase Overview

| Area | Content |
|---|---|
| Core focus and characteristics | {{ phase.overview.core_focus_and_characteristics | join_lines }} |
| Phase goals |{% if phase.overview.phase_goals_primary %} - Primary: {{ phase.overview.phase_goals_primary }}{% endif %}{% if phase.overview.phase_goals_secondary %}<br>- Secondary: {{ phase.overview.phase_goals_secondary }}{% endif %} |
| Metabolic focus | {{ phase.overview.metabolic_focus or "N/A" }} |
| Expected adaptations (conceptual) | {{ phase.overview.expected_adaptations | join_lines }} |
| Evaluation focus (non-binding) | {{ phase.overview.evaluation_focus | join_lines }} |
| Phase exit assumptions | {{ phase.overview.phase_exit_assumptions | join_lines }} |
| Typical duration and intensity pattern (conceptual) | {{ phase.overview.typical_duration_intensity_pattern or "N/A" }} |
| Non-negotiables | {{ phase.overview.non_negotiables | join_lines }} |

#### Weekly Load Corridor (kJ-first)

| Metric | Min | Max | kJ/kg Min | kJ/kg Max | Notes |
|---|---:|---:|---:|---:|---|
| Weekly kJ | {{ phase.weekly_kj.min }} | {{ phase.weekly_kj.max }} | {{ phase.weekly_kj.kj_per_kg_min }} | {{ phase.weekly_kj.kj_per_kg_max }} | {{ phase.weekly_kj.notes }} |

#### Allowed / Forbidden Semantics

| Allowed INTENSITY_DOMAIN_ENUM | Allowed LOAD_MODALITY_ENUM | Forbidden INTENSITY_DOMAIN_ENUM |
|---|---|---|
| {{ phase.allowed_intensity_domains | join_or_na }} | {{ phase.allowed_load_modalities | join_or_na }} | {{ phase.forbidden_intensity_domains | join_or_na }} |
"""

_DURATION_PATTERN = re.compile(r"(?P<hours>\\d+)h(?P<minutes>\\d+)?m?|(?P<mins_only>\\d+)m")


def parse_duration_minutes(value: str) -> int:
    """Parse a duration string into minutes.

    Supports HH:MM:SS, HH:MM, or hours-only numeric strings.
    """
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, _seconds = parts
        return int(hours) * 60 + int(minutes)
    if len(parts) == 2:
        hours, minutes = parts
        return int(hours) * 60 + int(minutes)
    if len(parts) == 1 and parts[0].isdigit():
        return int(parts[0]) * 60
    return 0


def duration_minutes_from_workout_text(text: str) -> int:
    """Extract duration minutes from a workout text block."""
    if not text:
        return 0
    total = 0
    for match in _DURATION_PATTERN.finditer(text):
        if match.group("mins_only"):
            total += int(match.group("mins_only"))
            continue
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        total += hours * 60 + minutes
    return total


def format_duration_hhmm(total_minutes: int) -> str:
    """Format minutes into HH:MM."""
    if total_minutes <= 0:
        return ""
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def iso_week_date_range(year: int, week: int) -> tuple[date, date]:
    """Return start/end dates for an ISO week (Mon-Sun)."""
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return start, end


def iso_week_range_dates(range_spec: IsoWeekRange | None) -> tuple[date, date] | None:
    """Return start/end dates for an ISO week range."""
    if not range_spec:
        return None
    start, _ = iso_week_date_range(range_spec.start.year, range_spec.start.week)
    _, end = iso_week_date_range(range_spec.end.year, range_spec.end.week)
    return start, end


def init_ui_state() -> dict:
    """Initialize the shared UI state for the multipage app."""
    state = st.session_state.setdefault("rps_state", {})
    athlete_id = state.get("athlete_id") or os.getenv("ATHLETE_ID") or "i150546"
    state["athlete_id"] = athlete_id
    if "iso_year" not in state or "iso_week" not in state:
        iso = date.today().isocalendar()
        state.setdefault("iso_year", iso.year)
        state.setdefault("iso_week", iso.week)
    state.setdefault("system_logs", [])
    state.setdefault("coach_session", {"previous_response_id": None, "run_id": None})
    state.setdefault("ui_dev_mode", False)
    state.setdefault("selected_phase_label", None)
    state.setdefault("status_state", "idle")
    state.setdefault("status_title", "Status")
    state.setdefault("status_message", "Idle")
    state.setdefault("status_last_run_id", None)
    state.setdefault("status_last_action", None)
    st.session_state["athlete_id"] = athlete_id
    st.session_state["iso_year"] = state["iso_year"]
    st.session_state["iso_week"] = state["iso_week"]
    st.session_state["ui_dev_mode"] = state["ui_dev_mode"]
    st.session_state["selected_phase_label"] = state["selected_phase_label"]
    return state


def get_athlete_id() -> str:
    """Return the current athlete id, persisting it in session state."""
    state = init_ui_state()
    athlete_id = state.get("athlete_id") or os.getenv("ATHLETE_ID") or "i150546"
    state["athlete_id"] = athlete_id
    st.session_state["athlete_id"] = athlete_id
    return athlete_id


def get_iso_year_week() -> tuple[int, int]:
    """Return the current ISO year/week, persisting them in session state."""
    state = init_ui_state()
    year = int(state.get("iso_year") or date.today().isocalendar().year)
    week = int(state.get("iso_week") or date.today().isocalendar().week)
    state["iso_year"] = year
    state["iso_week"] = week
    st.session_state["iso_year"] = year
    st.session_state["iso_week"] = week
    return year, week


@st.cache_data(show_spinner=False)
def _cached_season_plan(athlete_id: str, workspace_root: Path) -> dict | None:
    """Return the latest season plan for sidebar selection (cached)."""
    store = LocalArtifactStore(root=workspace_root)
    if not store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN):
        return None
    payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    return payload if isinstance(payload, dict) else None


def build_phase_options(phases: list[dict]) -> tuple[list[str], dict[str, dict]]:
    """Build selectbox options and a label->phase map for the sidebar."""
    options: list[str] = []
    phase_map: dict[str, dict] = {}
    for phase in phases:
        phase_id = phase.get("phase_id") or ""
        name = phase.get("name") or "Phase"
        iso_range = phase.get("iso_week_range") or ""
        label = f"{phase_id} · {name} · {iso_range}".strip(" ·")
        options.append(label)
        phase_map[label] = phase
    return options, phase_map


def render_global_sidebar() -> dict:
    """Render the global sidebar controls and update session state."""
    state = init_ui_state()
    workspace_root = Path(os.getenv("ATHLETE_WORKSPACE_ROOT", str(SETTINGS.workspace_root)))
    with st.sidebar:
        st.subheader("Global")
        athlete_id = st.text_input("Athlete ID", value=state["athlete_id"])
        year = int(
            st.number_input(
                "ISO Year",
                min_value=2000,
                max_value=2100,
                value=state["iso_year"],
                step=1,
            )
        )
        week = int(
            st.number_input(
                "ISO Week",
                min_value=1,
                max_value=53,
                value=state["iso_week"],
                step=1,
            )
        )
        ui_dev_mode = st.toggle("Dev mode", value=bool(state.get("ui_dev_mode", False)))

        phases = []
        phase_label = state.get("selected_phase_label")
        season_plan = _cached_season_plan(athlete_id, workspace_root)
        if isinstance(season_plan, dict):
            phases = season_plan.get("data", {}).get("phases", []) or []
        if phases:
            options, _ = build_phase_options(phases)
            if phase_label not in options:
                phase_label = options[0]
            phase_label = st.selectbox("Phase", options=options, index=options.index(phase_label))

    state["athlete_id"] = athlete_id
    state["iso_year"] = year
    state["iso_week"] = week
    state["ui_dev_mode"] = ui_dev_mode
    state["selected_phase_label"] = phase_label
    st.session_state["athlete_id"] = athlete_id
    st.session_state["iso_year"] = year
    st.session_state["iso_week"] = week
    st.session_state["ui_dev_mode"] = ui_dev_mode
    st.session_state["selected_phase_label"] = phase_label
    return state


def set_status(
    *,
    status_state: str,
    title: str | None = None,
    message: str | None = None,
    last_action: str | None = None,
    last_run_id: str | None = None,
) -> None:
    """Set global status panel values."""
    state = init_ui_state()
    if title is not None:
        state["status_title"] = title
    if message is not None:
        state["status_message"] = message
    state["status_state"] = status_state
    if last_action is not None:
        state["status_last_action"] = last_action
    if last_run_id is not None:
        state["status_last_run_id"] = last_run_id


def render_status_panel() -> None:
    """Render the always-visible status panel."""
    state = init_ui_state()
    title = state.get("status_title") or "Status"
    message = state.get("status_message") or "Idle"
    status_state = state.get("status_state") or "idle"
    last_action = state.get("status_last_action")
    last_run_id = state.get("status_last_run_id")

    with st.container():
        body = f"**{title}** — {message}"
        if last_action:
            body = f"{body}\n\nLast action: {last_action}"
        if last_run_id:
            body = f"{body}\n\nRun id: {last_run_id}"

        if status_state == "error":
            st.error(body)
        elif status_state == "running":
            st.warning(body)
        elif status_state == "done":
            st.success(body)
        else:
            st.info(body)


def ensure_logging(athlete_id: str) -> str:
    """Ensure file logging is configured for the current athlete."""
    state = init_ui_state()
    current = state.get("_ui_log_file")
    if current and state.get("_ui_log_athlete") == athlete_id:
        return str(current)

    log_dir = SETTINGS.workspace_root / athlete_id / "logs"
    log_file = str(log_dir / "rps.log")
    setup_logging(log_file=log_file)
    state["_ui_log_file"] = log_file
    state["_ui_log_athlete"] = athlete_id
    state["_log_file_announced"] = False
    return log_file


def append_system_log(source: str, content: str, level: int = logging.INFO) -> None:
    """Append a UI system log line if it meets the UI log level."""
    if level < UI_LOG_LEVEL:
        return
    logs: list[dict] = st.session_state["rps_state"].setdefault("system_logs", [])
    logs.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "content": content,
        }
    )


def announce_log_file(athlete_id: str) -> None:
    """Ensure the log file path is recorded as the first UI log entry."""
    state = init_ui_state()
    log_file = ensure_logging(athlete_id)
    if not state.get("_log_file_announced"):
        append_system_log("log", f"Log file: {log_file}", level=logging.INFO)
        state["_log_file_announced"] = True


def ui_log(message: str, *, level: int = logging.INFO, source: str = "ui") -> None:
    """Log to file and UI system logs."""
    athlete_id = get_athlete_id()
    ensure_logging(athlete_id)
    announce_log_file(athlete_id)
    LOGGER.log(level, message)
    append_system_log(source, message, level=level)


def system_log_panel(expanded: bool = True) -> None:
    """Render the system log panel with the latest entry plus history."""
    logs: list[dict] = st.session_state["rps_state"].setdefault("system_logs", [])
    with st.expander("System output / logs", expanded=expanded):
        if not logs:
            st.caption("No system output yet.")
        else:
            last = logs[-1]
            st.caption(f"{last['ts']} · {last['source']}")
            st.code(last["content"])
            if len(logs) > 1:
                with st.expander("History", expanded=False):
                    for entry in reversed(logs[:-1]):
                        st.caption(f"{entry['ts']} · {entry['source']}")
                        st.code(entry["content"])

        log_file = st.session_state["rps_state"].get("_ui_log_file")
        if not log_file:
            athlete_id = get_athlete_id()
            log_file = ensure_logging(athlete_id)
        path = Path(log_file) if log_file else None
        if path and path.exists():
            tail = deque(maxlen=200)
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    tail.append(line.rstrip("\n"))
            if tail:
                st.caption("Log file tail")
                st.code("\n".join(tail))
            else:
                st.caption("Log file is empty.")


def base_runtime() -> dict:
    """Return a cached runtime bundle (client/prompt loader/vectorstore)."""
    cache_key = "_rps_runtime_cache"
    cached = st.session_state.get(cache_key)
    if cached:
        return cached
    client = get_client()
    runtime = {
        "client": client,
        "prompt_loader": PromptLoader(SETTINGS.prompts_dir),
        "vs_resolver": VectorStoreResolver(SETTINGS.vs_state_path),
    }
    st.session_state[cache_key] = runtime
    return runtime


def multi_runtime_for(agent_name: str):
    """Return an AgentRuntime for the requested agent."""
    from rps.agents.multi_output_runner import AgentRuntime as MultiRuntime

    base = base_runtime()
    return MultiRuntime(
        client=get_client(agent_name),
        model=SETTINGS.model_for_agent(agent_name),
        temperature=SETTINGS.temperature_for_agent(agent_name),
        reasoning_effort=SETTINGS.reasoning_effort_for_agent(agent_name),
        reasoning_summary=SETTINGS.reasoning_summary_for_agent(agent_name),
        max_completion_tokens=SETTINGS.max_completion_tokens_for_agent(agent_name),
        prompt_loader=base["prompt_loader"],
        vs_resolver=base["vs_resolver"],
        schema_dir=SETTINGS.schema_dir,
        workspace_root=SETTINGS.workspace_root,
    )


class _BufferHandler(logging.Handler):
    def __init__(self, sink: list[str], on_emit: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self.sink = sink
        self.on_emit = on_emit

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - simple glue
        msg = self.format(record)
        if msg:
            self.sink.append(msg)
            if self.on_emit:
                self.on_emit(msg)


def capture_output(
    fn: Callable[[], object],
    *,
    loggers: list[logging.Logger] | None = None,
    on_log_line: Callable[[str], None] | None = None,
) -> tuple[object | None, str]:
    """Capture stdout + selected logger output for UI display."""
    buf = io.StringIO()
    log_lines: list[str] = []
    handler = _BufferHandler(log_lines, on_emit=on_log_line)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    targets = list(dict.fromkeys(loggers or []))
    previous_levels: dict[logging.Logger, int] = {}
    for lg in targets:
        previous_levels[lg] = lg.level
        if lg.level > logging.INFO:
            lg.setLevel(logging.INFO)
        lg.addHandler(handler)
    result: object | None = None
    try:
        with redirect_stdout(buf):
            result = fn()
    finally:
        for lg in targets:
            lg.removeHandler(handler)
            prev = previous_levels.get(lg)
            if prev is not None:
                lg.setLevel(prev)
    stdout_text = buf.getvalue().strip()
    logs_text = "\n".join(log_lines).strip()
    combined = "\n\n".join(part for part in (stdout_text, logs_text) if part)
    return result, combined


def make_ui_run_id(name: str) -> str:
    """Return a timestamped UI run id for logging/traceability."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name)
    return f"ui_{safe}_{stamp}"


def season_plan_covers_week(athlete_id: str, year: int, week: int) -> tuple[bool, str | None]:
    """Return whether the latest season plan covers the given ISO week."""
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    try:
        season_plan = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    except FileNotFoundError:
        return False, "Plan Week requires a Season Plan."

    if not isinstance(season_plan, dict):
        return False, "Plan Week requires a Season Plan."

    meta = season_plan.get("meta", {}) or {}
    iso_range = meta.get("iso_week_range")
    target = IsoWeek(year=year, week=week)

    if isinstance(iso_range, str):
        try:
            if range_contains(parse_iso_week_range(iso_range), target):
                return True, None
        except Exception:
            pass

    data = season_plan.get("data", {}) or {}
    phases = data.get("phases") if isinstance(data, dict) else None
    if isinstance(phases, list):
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            phase_range = phase.get("iso_week_range")
            if isinstance(phase_range, str):
                try:
                    if range_contains(parse_iso_week_range(phase_range), target):
                        return True, None
                except Exception:
                    continue

    return False, f"Iso week {week:02d} {year} not part of Season Plan."


def render_phase_markdown(phase: dict) -> str:
    """Render phase details using the legacy phase card template."""
    overview = phase.get("overview", {}) if isinstance(phase, dict) else {}
    goals = overview.get("phase_goals", {}) if isinstance(overview, dict) else {}
    overview = dict(overview)
    overview["phase_goals_primary"] = goals.get("primary")
    overview["phase_goals_secondary"] = goals.get("secondary")
    weekly = (phase.get("weekly_load_corridor") or {}).get("weekly_kj") or {}
    semantics = phase.get("allowed_forbidden_semantics") or {}

    def join_lines(value: object) -> str:
        if not value:
            return "N/A"
        if isinstance(value, list):
            return "<br>".join(str(item) for item in value)
        return str(value)

    def join_or_na(value: object) -> str:
        if not value:
            return "N/A"
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)

    def norm(value: object) -> str:
        return "N/A" if value in (None, "") else str(value)

    env = Environment(loader=BaseLoader(), autoescape=False)
    env.filters["join_lines"] = join_lines
    env.filters["join_or_na"] = join_or_na
    template = env.from_string(PHASE_CARD_TEMPLATE)
    return template.render(
        phase={
            "narrative": phase.get("narrative"),
            "overview": overview,
            "weekly_kj": {
                "min": norm(weekly.get("min")),
                "max": norm(weekly.get("max")),
                "kj_per_kg_min": norm(weekly.get("kj_per_kg_min")),
                "kj_per_kg_max": norm(weekly.get("kj_per_kg_max")),
                "notes": weekly.get("notes") or "",
            },
            "allowed_intensity_domains": semantics.get("allowed_intensity_domains", []),
            "allowed_load_modalities": semantics.get("allowed_load_modalities", []),
            "forbidden_intensity_domains": semantics.get("forbidden_intensity_domains", []),
        }
    )


def athlete_phase_card(athlete_id: str, year: int, week: int) -> None:
    """Render the active phase card for the current athlete/week."""
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    try:
        season_plan = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    except FileNotFoundError:
        return
    phases = season_plan.get("data", {}).get("phases", []) if isinstance(season_plan, dict) else []
    target = IsoWeek(year=year, week=week)
    active = None
    for phase in phases:
        rng = phase.get("iso_week_range")
        if not rng:
            continue
        parsed = parse_iso_week_range(rng)
        if parsed and range_contains(parsed, target):
            active = phase
            break
    if not active:
        return

    phase_name = active.get("name", "Phase")
    iso_range = active.get("iso_week_range", "")
    headline = f"Phase: {phase_name} {iso_range}".strip()
    with st.expander(headline, expanded=False):
        st.markdown(render_phase_markdown(active), unsafe_allow_html=True)


def load_rendered_markdown(
    athlete_id: str,
    artifact_type: ArtifactType,
    *,
    version_key: str | None = None,
) -> str | None:
    """Return rendered markdown for an artifact if available."""
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    try:
        if not version_key:
            version_key = store.get_latest_version_key(athlete_id, artifact_type)
    except Exception:
        return None

    rendered_dir = SETTINGS.workspace_root / athlete_id / "rendered"
    prefix = ARTIFACT_PATHS[artifact_type].filename_prefix
    candidate = rendered_dir / f"{prefix}_{version_key}.md"
    if not candidate.exists():
        return None
    return candidate.read_text(encoding="utf-8")
