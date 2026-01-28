from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
import json
import logging
import os
from pathlib import Path
import queue
import re
import shutil
import sys
import threading
from typing import Callable

import streamlit as st

from rps.agents.registry import AGENTS
from rps.agents.runner import run_agent_session
from rps.agents.multi_output_runner import AgentRuntime as MultiRuntime, run_agent_multi_output
from rps.agents.tasks import AgentTask
from rps.core.config import load_app_settings, load_env_file
from rps.core.logging import _normalize_level
from rps.data_pipeline.intervals_data import run_pipeline as run_intervals_pipeline
from rps.data_pipeline.season_brief_availability import parse_and_store_availability
from rps.main import _preflight
from rps.openai.client import get_client
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.openai.response_utils import extract_reasoning_summaries
from rps.orchestrator.plan_week import _build_injection_block, plan_week
from rps.prompts.loader import PromptLoader
from rps.rendering.auto_render import render_sidecar
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week_range, range_contains
from rps.workspace.types import ArtifactType



ROOT = Path(__file__).resolve().parents[3]
load_env_file(ROOT / ".env")
SETTINGS = load_app_settings()
LOGGER = logging.getLogger("rps.streamlit")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.WARNING)
UI_LOG_LEVEL = _normalize_level(os.getenv("RPS_LOG_LEVEL_UI", "INFO"))

# Keep system output focused on stdout from the pipeline/agents.
CAPTURE_LOGGERS: list[logging.Logger] = []


STOP_WORDS = {":q", ":quit", "exit", "quit"}

# Canonical command names -> synonyms (lowercase substrings)
COMMAND_SYNONYMS: dict[str, list[str]] = {
    "parse_intervals": ["parse intervals", "intervals", "fetch data", "update data"],
    "parse_availability": ["parse availability", "availability"],
    "scenarios": ["scenarios", "create scenarios", "season scenarios"],
    "select_scenario": ["select scenario", "choose scenario", "scenario selection"],
    "macro_overview": ["macro overview", "create macro", "overview"],
    "plan_week": ["plan week", "plan-week", "plan"],
    "show": ["show"],
    "coach": ["coach"],
    "stop": list(STOP_WORDS),
}

# Artefact aliases: canonical artifact key -> list of alias names
ARTIFACT_ALIASES: dict[str, list[str]] = {
    "macro_overview": ["macro_overview", "macro overview", "macro", "overview", "atp"],
    "block_governance": ["block_governance", "block governance", "governance"],
    "block_execution_arch": [
        "block_execution_arch",
        "block execution arch",
        "block execution architecture",
        "block_execution_architecture",
        "execution arch",
        "arch",
        "architecture",
        "bea",
    ],
    "block_execution_preview": [
        "block_execution_preview",
        "block execution preview",
        "execution preview",
        "preview",
        "week preview",
    ],
    "workouts_plan": ["workouts_plan", "workouts plan", "micro plan", "week plan"],
    "intervals_workouts": ["intervals_workouts", "intervals workouts", "intervals export"],
    "des_analysis_report": [
        "des_analysis_report",
        "des report",
        "analysis",
        "performance report",
        "report",
    ],
    "availability": ["availability"],
    "events": ["events"],
    "zone_model": ["zone model", "zones", "zone"],
    "kpi_profile": ["kpi profile", "profile"],
    "season_brief": ["season brief", "brief"],
    "wellness": ["wellness"],
}

ARTIFACT_TYPE_BY_KEY: dict[str, ArtifactType] = {
    "macro_overview": ArtifactType.MACRO_OVERVIEW,
    "block_governance": ArtifactType.BLOCK_GOVERNANCE,
    "block_execution_arch": ArtifactType.BLOCK_EXECUTION_ARCH,
    "block_execution_preview": ArtifactType.BLOCK_EXECUTION_PREVIEW,
    "workouts_plan": ArtifactType.WORKOUTS_PLAN,
    "intervals_workouts": ArtifactType.INTERVALS_WORKOUTS,
    "des_analysis_report": ArtifactType.DES_ANALYSIS_REPORT,
    "availability": ArtifactType.AVAILABILITY,
    "events": ArtifactType.EVENTS,
    "zone_model": ArtifactType.ZONE_MODEL,
    "kpi_profile": ArtifactType.KPI_PROFILE,
    "season_brief": ArtifactType.SEASON_BRIEF,
    "wellness": ArtifactType.WELLNESS,
}

RENDERABLE_ARTIFACT_KEYS: set[str] = {
    "macro_overview",
    "block_governance",
    "block_execution_arch",
    "block_execution_preview",
    "block_feed_forward",
    "macro_meso_feed_forward",
    "des_analysis_report",
    "activities_actual",
    "activities_trend",
    "zone_model",
    "workouts_plan",
    "kpi_profile",
    "availability",
    "wellness",
}

STATE_LABELS: dict[str, str] = {
    "init": "Init",
    "core": "Core",
    "coach": "Coach",
    "macro_overview": "Macro Flow",
    "exit": "Exit",
}

SUBSTATE_LABELS: dict[str, str] = {
    "plan_week": "Plan Week",
    "parse_intervals": "Fetch Intervals Data",
    "parse_availability": "Fetch Availability",
    "create_scenarios": "Create Scenarios",
    "select_scenario": "Select Scenario",
    "create_macro_overview": "Create Macro Overview",
    "macro_overview": "Create Macro Overview",
    "message": "Coach Message",
    "show": "Show",
}

ACTION_LABELS: dict[str, str] = {
    "plan_week": "Plan Week",
    "parse_intervals": "Fetch Intervals Data",
    "parse_availability": "Fetch Availability",
    "scenarios": "Create Scenarios",
    "select_scenario": "Select Scenario",
    "macro_overview": "Create Macro Overview",
    "coach_message": "Coach",
    "coach_start": "Coach Start",
    "coach_stop": "Coach Stop",
    "stopword": "Stop",
    "macro_overview_done": "Macro Overview Done",
    "scenarios_done": "Scenarios Done",
}


@dataclass
class StateMachine:
    state: str = "init"
    substate: str | None = None
    parameters: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def transition(
        self,
        next_state: str,
        next_substate: str | None = None,
        params: dict | None = None,
        action: str | None = None,
    ) -> None:
        self.history.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "from": self.state,
                "to": next_state,
                "sub": next_substate,
                "action": action,
            }
        )
        self.state = next_state
        self.substate = next_substate
        if params:
            self.parameters.update(params)


def _make_ui_run_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(ch if ch.isalnum() else "_" for ch in prefix).strip("_") or "run"
    return f"ui_{safe}_{stamp}"


def _coach_state() -> dict:
    return st.session_state["rps_state"].setdefault(
        "coach",
        {"previous_response_id": None, "run_id": None},
    )


def _set_coach_output(text: str, status: str = "done", summary: str | None = None) -> None:
    st.session_state["rps_state"].setdefault("coach_output", {})
    st.session_state["rps_state"]["coach_output"] = {
        "status": status,
        "text": text,
        "summary": summary,
    }


def _clear_coach_output() -> None:
    st.session_state["rps_state"].setdefault("coach_output", {})
    st.session_state["rps_state"]["coach_output"].update(
        {"status": "idle", "text": "", "summary": None}
    )


def _ensure_session_state() -> None:
    if "rps_state" not in st.session_state:
        now = datetime.now(timezone.utc).isocalendar()
        st.session_state["rps_state"] = {
            "athlete_id": os.getenv("ATHLETE_ID") or "i150546",
            "year": now.year,
            "week": now.week,
            "scenario": "B",
            "messages": [],
            "system_logs": [],
            "preflight_done": False,
            "preflight_ok": None,
            "preflight_ctx": None,
            "preflight_error": None,
            "coach": {
                "previous_response_id": None,
                "run_id": None,
            },
            "coach_output": {
                "status": "idle",
                "text": "",
            },
            "state_machine": StateMachine(),
        }


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--athlete-id")
    parser.add_argument("--init", action="store_true")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args


def _reset_cached_artifacts(athlete_id: str) -> str:
    root = SETTINGS.workspace_root
    athlete_dir = Path(root) / "var" / "athletes" / athlete_id
    if not athlete_dir.exists():
        return f"No athlete workspace found at {athlete_dir}."
    targets = [
        athlete_dir / "latest",
        athlete_dir / "rendered",
        athlete_dir / "logs",
        athlete_dir / "data",
    ]
    cache_targets = [ROOT / ".cache" / "macro_scenarios"]
    removed: list[str] = []
    skipped: list[str] = []
    for path in targets + cache_targets:
        if not path.exists():
            skipped.append(str(path))
            continue
        shutil.rmtree(path, ignore_errors=True)
        removed.append(str(path))
    inputs_dir = athlete_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    if removed:
        parts.append("Removed: " + ", ".join(removed))
    if skipped:
        parts.append("Not found: " + ", ".join(skipped))
    parts.append(f"Preserved inputs at {inputs_dir}.")
    return "Init reset: " + " ".join(parts)


def _base_runtime() -> dict:
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


def _multi_runtime_for(agent_name: str) -> MultiRuntime:
    base = _base_runtime()
    return MultiRuntime(
        client=base["client"],
        model=SETTINGS.openai_model,
        temperature=SETTINGS.openai_temperature,
        reasoning_effort=SETTINGS.reasoning_effort_for_agent(agent_name),
        reasoning_summary=SETTINGS.reasoning_summary_for_agent(agent_name),
        prompt_loader=base["prompt_loader"],
        vs_resolver=base["vs_resolver"],
        schema_dir=SETTINGS.schema_dir,
        workspace_root=SETTINGS.workspace_root,
    )


def _append_message(role: str, content: str, fmt: str | None = None) -> None:
    message = {"role": role, "content": content}
    if fmt:
        message["format"] = fmt
    st.session_state["rps_state"]["messages"].append(message)


def _append_system_log(source: str, content: str, level: int = logging.INFO) -> None:
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


def _queue_action(
    *,
    state: str,
    substate: str | None,
    params: dict | None,
    action: str,
) -> None:
    sm: StateMachine = st.session_state["rps_state"]["state_machine"]
    sm.transition(state, substate, params=params, action=action)
    sm.parameters["pending_action"] = action
    _append_system_log("state", _state_log_line(sm, action))


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


def _capture_output(
    fn: Callable[[], object],
    *,
    loggers: list[logging.Logger] | None = None,
    on_log_line: Callable[[str], None] | None = None,
) -> tuple[object | None, str]:
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


def canonicalize_trigger(text: str) -> str | None:
    tl = (text or "").strip().lower()
    if tl.startswith("show "):
        return "show"
    for canon, syns in COMMAND_SYNONYMS.items():
        for synonym in syns:
            if synonym in tl:
                return canon
    return None


def _format_state_label(sm: StateMachine) -> str:
    state = STATE_LABELS.get(sm.state, sm.state)
    if sm.substate:
        sub = SUBSTATE_LABELS.get(sm.substate, sm.substate)
        return f"{state} / {sub}"
    return state


def _state_log_line(sm: StateMachine, action: str | None) -> str:
    state = STATE_LABELS.get(sm.state, sm.state)
    sub = SUBSTATE_LABELS.get(sm.substate, sm.substate) if sm.substate else "none"
    act = ACTION_LABELS.get(action or "", action or "none")
    return f"state={state} substate={sub} action={act}"


def _format_exception(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return f"{exc.__class__.__name__}: {text}"
    return exc.__class__.__name__


def _is_no_session_context(exc: BaseException) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    return "nosessioncontext" in name or "nosessioncontext" in msg


def _looks_like_no_session(text: str | None) -> bool:
    if not text:
        return False
    return "nosessioncontext" in text.lower()


def _clean_reasoning_summary(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("Summary("):
        marker = "Summary(text="
        if marker in cleaned:
            start = cleaned.find(marker) + len(marker)
            end = cleaned.rfind(")")
            snippet = cleaned[start:end].strip()
            if snippet and snippet[0] in ("'", '"'):
                quote = snippet[0]
                snippet = snippet.strip(quote)
            return snippet.strip()
    return cleaned


def _normalize_streamed_text(text: str) -> str:
    if not text:
        return text
    lines = [line for line in text.splitlines() if line.strip() != ""]
    if not lines:
        return text
    avg_len = sum(len(line.strip()) for line in lines) / max(len(lines), 1)
    short_lines = sum(1 for line in lines if len(line.strip()) <= 12)
    if avg_len > 20 and short_lines / max(len(lines), 1) < 0.6:
        return text
    parts = re.split(r"\n\s*\n", text.strip())
    cleaned: list[str] = []
    for part in parts:
        collapsed = re.sub(r"\s+", " ", part.replace("\n", " ")).strip()
        collapsed = re.sub(r"\s+([,.;:!?])", r"\1", collapsed)
        collapsed = re.sub(r"\(\s+", "(", collapsed)
        collapsed = re.sub(r"\s+\)", ")", collapsed)
        cleaned.append(collapsed)
    return "\n\n".join([c for c in cleaned if c])


class _TempEnv:
    def __init__(self, updates: dict[str, str]) -> None:
        self._updates = updates
        self._prior: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key, value in self._updates.items():
            self._prior[key] = os.getenv(key)
            os.environ[key] = value

    def __exit__(self, exc_type, exc, tb) -> None:
        for key, prior in self._prior.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


def _start_live_trace(action_label: str) -> tuple[Callable[[str], None], Callable[[bool], None]]:
    lines: list[str] = []
    if hasattr(st, "status"):
        box = st.status(f"Running: {action_label}", expanded=True)
    else:
        box = st.expander(f"Running: {action_label}", expanded=True)
    placeholder = box.empty()

    def _render() -> None:
        text = "\n".join(lines[-200:])
        placeholder.code(text or "…")

    def on_line(line: str) -> None:
        lines.append(line)
        _render()

    def finish(ok: bool) -> None:
        if hasattr(box, "update"):
            state = "complete" if ok else "error"
            label = f"{action_label} finished" if ok else f"{action_label} failed"
            box.update(label=label, state=state, expanded=False)
        else:
            _render()

    return on_line, finish


class _StreamingBuffer:
    def __init__(
        self,
        sink: "queue.Queue[object]",
        on_emit: Callable[[str], None] | None = None,
    ) -> None:
        self.sink = sink
        self.on_emit = on_emit
        self._chunks: list[str] = []

    def write(self, data: str) -> None:
        if data:
            self._chunks.append(data)
            self.sink.put(data)
            if self.on_emit:
                self.on_emit(data)

    def flush(self) -> None:  # pragma: no cover - no-op
        return None

    def getvalue(self) -> str:
        return "".join(self._chunks)


def _enter_coach_mode(source: str) -> None:
    rps_state = st.session_state["rps_state"]
    sm: StateMachine = rps_state["state_machine"]
    coach = _coach_state()
    coach.update({"previous_response_id": None, "run_id": _make_ui_run_id("coach")})
    sm.parameters["coach_history_start"] = len(rps_state["messages"])
    sm.transition("coach", None, action=source)
    msg = "Coach started. Ask anything. Use :quit to exit coach mode."
    _append_message("assistant", msg)
    _append_system_log("coach", msg)
    _set_coach_output(msg, status="done")


def find_artifact_key(token: str) -> str | None:
    t = (token or "").lower().strip()
    for key, aliases in ARTIFACT_ALIASES.items():
        if t in aliases:
            return key
    return None


def _resolve_artifact_key(token: str) -> str | None:
    t = (token or "").lower().strip()
    if not t:
        return None
    for key, aliases in ARTIFACT_ALIASES.items():
        for alias in aliases:
            if t == alias or alias in t:
                return key
    return None


def _parse_show_args(text: str) -> tuple[str | None, int | None, int | None]:
    match = re.search(r"show\s+([^\n\r]+)", text, flags=re.IGNORECASE)
    if not match:
        return None, None, None
    tail = match.group(1).strip()
    if not tail:
        return None, None, None
    parts = tail.split()
    year: int | None = None
    week: int | None = None
    token_parts = parts[:]
    if len(parts) >= 2 and parts[-1].isdigit() and parts[-2].isdigit():
        year = int(parts[-1])
        week = int(parts[-2])
        token_parts = parts[:-2]
    elif len(parts) >= 1 and parts[-1].isdigit():
        value = int(parts[-1])
        token_parts = parts[:-1]
        if value >= 1000:
            year = value
        else:
            week = value
    token = " ".join(token_parts).strip()
    return token or tail, week, year


def _rendered_markdown_for(athlete_id: str, artifact_key: str, version_key: str | None = None) -> str | None:
    rendered_dir = ROOT / "var" / "athletes" / athlete_id / "rendered"
    if not rendered_dir.exists():
        return None
    patterns = []
    if version_key:
        patterns.append(f"{artifact_key}_{version_key}*.md")
    else:
        patterns.append(f"{artifact_key}_*.md")
        patterns.append(f"{artifact_key}.md")
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(rendered_dir.glob(pattern))
    candidates = sorted({p for p in candidates}, key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    return candidates[0].read_text(encoding="utf-8")


def _json_preview_for(
    athlete_id: str,
    artifact_key: str,
    version_key: str | None = None,
) -> str | None:
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    artifact_type = ARTIFACT_TYPE_BY_KEY.get(artifact_key)
    if not artifact_type:
        return None
    try:
        if version_key:
            doc = store.load_version(athlete_id, artifact_type, version_key)
        else:
            doc = store.load_latest(athlete_id, artifact_type)
    except FileNotFoundError:
        return None
    return json.dumps(doc, ensure_ascii=False, indent=2)


def _input_markdown_for(athlete_id: str, prefix: str, year: int | None = None) -> str | None:
    input_dir = ROOT / "var" / "athletes" / athlete_id / "inputs"
    if not input_dir.exists():
        return None
    base_path = input_dir / f"{prefix}.md"
    if base_path.exists():
        return base_path.read_text(encoding="utf-8")
    if year:
        path = input_dir / f"{prefix}_{year}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
    candidates = sorted(input_dir.glob(f"{prefix}_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    return candidates[0].read_text(encoding="utf-8")


def _render_artifact_for_display(
    athlete_id: str,
    artifact_key: str,
    week: int | None = None,
    year: int | None = None,
) -> tuple[str, str] | None:
    version_key = None
    if week is not None and year is not None:
        version_key = f"{year:04d}-{week:02d}"
    if artifact_key == "season_brief":
        rendered_md = _input_markdown_for(athlete_id, "season_brief", year)
        if rendered_md:
            return "markdown", rendered_md
    if artifact_key == "events":
        rendered_md = _input_markdown_for(athlete_id, "events", year)
        if rendered_md:
            return "markdown", rendered_md

    rendered_md = _rendered_markdown_for(athlete_id, artifact_key, version_key)
    if rendered_md:
        return "markdown", rendered_md
    if artifact_key in RENDERABLE_ARTIFACT_KEYS:
        store = LocalArtifactStore(root=SETTINGS.workspace_root)
        artifact_type = ARTIFACT_TYPE_BY_KEY.get(artifact_key)
        if artifact_type:
            json_path = (
                store.versioned_path(athlete_id, artifact_type, version_key)
                if version_key
                else store.latest_path(athlete_id, artifact_type)
            )
            if json_path.exists():
                render_sidecar(json_path)
                rendered_md = _rendered_markdown_for(athlete_id, artifact_key, version_key)
                if rendered_md:
                    return "markdown", rendered_md
    preview = _json_preview_for(athlete_id, artifact_key, version_key)
    if preview:
        return "code", preview
    return "warning", f"No artifact found for: {artifact_key}"


def _action_preflight(athlete_id: str, year: int, week: int) -> str:
    result, output = _capture_output(
        lambda: _preflight(
            athlete_id=athlete_id,
            workspace_root=SETTINGS.workspace_root,
            schema_dir=SETTINGS.schema_dir,
            logger=LOGGER,
            year=year,
            week=week,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    if output:
        return output
    if isinstance(result, str) and result.strip():
        return result
    return "Preflight completed."


def _auto_preflight() -> tuple[bool, str | None]:
    rps_state = st.session_state["rps_state"]
    sm: StateMachine = rps_state["state_machine"]
    athlete_id: str = rps_state["athlete_id"]
    year: int = rps_state["year"]
    week: int = rps_state["week"]
    ctx = (athlete_id, year, week)

    if rps_state.get("preflight_done") and rps_state.get("preflight_ctx") == ctx:
        ok = bool(rps_state.get("preflight_ok"))
        return ok, rps_state.get("preflight_error")

    rps_state["preflight_done"] = True
    rps_state["preflight_ctx"] = ctx
    rps_state["preflight_ok"] = False
    rps_state["preflight_error"] = None
    _append_system_log("preflight", f"Starting preflight for {athlete_id} {year}-{week:02d}.")

    try:
        was_init = sm.state == "init"
        output = _action_preflight(athlete_id, year, week)
        rps_state["preflight_ok"] = True
        sm.transition("core", None, action="preflight_ok")
        if was_init:
            rps_state["preflight_state_changed"] = True
        _append_system_log("preflight", output)
        return True, None
    except SystemExit as exc:
        msg = str(exc) or "Preflight failed."
        rps_state["preflight_error"] = msg
        sm.transition("exit", action="preflight_failed")
        _append_system_log("preflight", msg)
        return False, msg
    except Exception as exc:  # pragma: no cover - UI safety net
        msg = f"Preflight error: {exc}"
        rps_state["preflight_error"] = msg
        sm.transition("exit", action="preflight_error")
        _append_system_log("preflight", msg)
        return False, msg


def _action_parse_availability(
    athlete_id: str,
    year: int,
    *,
    on_log_line: Callable[[str], None] | None = None,
) -> str:
    result, output = _capture_output(
        lambda: parse_and_store_availability(
            athlete_id=athlete_id,
            workspace_root=SETTINGS.workspace_root,
            schema_dir=SETTINGS.schema_dir,
            year=year,
            skip_validate=False,
        ),
        loggers=CAPTURE_LOGGERS,
        on_log_line=on_log_line,
    )
    if output:
        return output
    if result:
        return f"Availability written: {result.out_file}"
    return "Availability parsed."


def _action_parse_intervals(
    athlete_id: str,
    *,
    on_log_line: Callable[[str], None] | None = None,
) -> str:
    args = argparse.Namespace(
        year=None,
        week=None,
        from_date=None,
        to_date=None,
        athlete=athlete_id,
        skip_validate=False,
    )
    _, output = _capture_output(
        lambda: run_intervals_pipeline(args, logger=LOGGER),
        loggers=CAPTURE_LOGGERS,
        on_log_line=on_log_line,
    )
    return output or "Intervals pipeline completed."


def _format_agent_result(result: object | None, fallback: str) -> str:
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return fallback


def _action_scenarios(
    athlete_id: str,
    year: int,
    week: int,
    *,
    on_log_line: Callable[[str], None] | None = None,
) -> str:
    runtime = _multi_runtime_for("season_scenario")
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use workspace_get_input for Season Brief and Events. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIOS."
    )
    run_id = _make_ui_run_id(f"season_scenarios_{year}_{week:02d}")
    result, output = _capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
            user_input=user_input,
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
        on_log_line=on_log_line,
    )
    return output or _format_agent_result(result, f"Scenarios created: {run_id}")


def _action_select_scenario(
    athlete_id: str,
    year: int,
    week: int,
    scenario: str,
    rationale: str | None = None,
    *,
    on_log_line: Callable[[str], None] | None = None,
) -> str:
    runtime = _multi_runtime_for("season_scenario")
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    rationale_line = f"Rationale: {rationale.strip()}. " if rationale else ""
    user_input = (
        f"Select Scenario {scenario.upper()} for ISO week {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIOS as context. "
        f"{rationale_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIO_SELECTION."
    )
    run_id = _make_ui_run_id(f"season_scenario_selection_{year}_{week:02d}")
    result, output = _capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
            user_input=user_input,
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
        on_log_line=on_log_line,
    )
    return output or _format_agent_result(result, f"Scenario {scenario.upper()} selected.")


def _action_macro_overview(
    athlete_id: str,
    year: int,
    week: int,
    scenario: str,
    *,
    on_log_line: Callable[[str], None] | None = None,
) -> str:
    runtime = _multi_runtime_for("macro_planner")
    spec = AGENTS["macro_planner"]
    injected_block = _build_injection_block("macro_planner", mode="macro_overview")
    user_input = (
        f"Scenario {scenario.upper()}. Mode A. Create the MACRO_OVERVIEW. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for MACRO_OVERVIEW."
    )
    run_id = _make_ui_run_id(f"macro_overview_{year}_{week:02d}")
    result, output = _capture_output(
        lambda: run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=[AgentTask.CREATE_MACRO_OVERVIEW],
            user_input=user_input,
            run_id=run_id,
            model_override=SETTINGS.model_for_agent(spec.name),
            temperature_override=SETTINGS.temperature_for_agent(spec.name),
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
        on_log_line=on_log_line,
    )
    return output or _format_agent_result(result, f"Macro overview created: {run_id}")


def _action_plan_week(
    athlete_id: str,
    year: int,
    week: int,
    *,
    on_log_line: Callable[[str], None] | None = None,
) -> str:
    runtime = _multi_runtime_for("macro_planner")
    run_id = f"ui_plan_week_{year}_{week:02d}"
    result, output = _capture_output(
        lambda: plan_week(
            runtime,
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id=run_id,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
            reasoning_effort_resolver=SETTINGS.reasoning_effort_for_agent,
            reasoning_summary_resolver=SETTINGS.reasoning_summary_for_agent,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        ),
        loggers=CAPTURE_LOGGERS,
        on_log_line=on_log_line,
    )
    status = "ok" if getattr(result, "ok", False) else "error"
    return (output + "\n\n" if output else "") + f"plan-week finished: {status}"


def _action_coach(athlete_id: str, text: str, coach: dict) -> str:
    runtime = _multi_runtime_for("coach")
    spec = AGENTS["coach"]
    injection_text = _build_injection_block("coach", mode="coach")
    run_id = coach.get("run_id") or _make_ui_run_id("coach")
    coach["run_id"] = run_id

    def _call():
        try:
            with _TempEnv(
                {
                    "OPENAI_STREAM": "0",
                    "OPENAI_STREAM_REASONING": "none",
                    "OPENAI_STREAM_TEXT": "0",
                    "OPENAI_STREAM_USAGE": "0",
                }
            ):
                return run_agent_session(
                    runtime,
                    agent_name="coach",
                    agent_vs_name=spec.vector_store_name,
                    athlete_id=athlete_id,
                    user_input=text,
                    workspace_root=SETTINGS.workspace_root,
                    schema_dir=SETTINGS.schema_dir,
                    model_override=SETTINGS.model_for_agent("coach"),
                    include_debug_file_search=False,
                    force_file_search=False,
                    max_num_results=SETTINGS.file_search_max_results,
                    run_id=run_id,
                    previous_response_id=coach.get("previous_response_id"),
                    injection_text=injection_text,
                )
        except Exception as exc:
            if _is_no_session_context(exc):
                coach["previous_response_id"] = None
                with _TempEnv(
                    {
                        "OPENAI_STREAM": "0",
                        "OPENAI_STREAM_REASONING": "none",
                        "OPENAI_STREAM_TEXT": "0",
                        "OPENAI_STREAM_USAGE": "0",
                    }
                ):
                    return run_agent_session(
                        runtime,
                        agent_name="coach",
                        agent_vs_name=spec.vector_store_name,
                        athlete_id=athlete_id,
                        user_input=text,
                        workspace_root=SETTINGS.workspace_root,
                        schema_dir=SETTINGS.schema_dir,
                        model_override=SETTINGS.model_for_agent("coach"),
                        include_debug_file_search=False,
                        force_file_search=False,
                        max_num_results=SETTINGS.file_search_max_results,
                        run_id=run_id,
                        previous_response_id=None,
                        injection_text=injection_text,
                    )
            raise

    result, output = _capture_output(_call, loggers=CAPTURE_LOGGERS)
    if isinstance(result, dict) and _looks_like_no_session(str(result.get("text") or "")):
        coach["previous_response_id"] = None
        result, output = _capture_output(_call, loggers=CAPTURE_LOGGERS)
    summary_text = None
    if isinstance(result, dict) and result.get("response"):
        summaries = extract_reasoning_summaries(result.get("response"))
        if summaries:
            summary_text = _clean_reasoning_summary(summaries[0])
    if isinstance(result, dict) and result.get("response_id"):
        coach["previous_response_id"] = result["response_id"]

    log_text = output or (result.get("text") if isinstance(result, dict) else "")
    if log_text:
        pass

    if isinstance(result, dict) and result.get("text"):
        return _normalize_streamed_text(str(result["text"]))
    return "Coach did not return text."


ACTION_MAP: dict[str, Callable[..., str]] = {
    "preflight": _action_preflight,
    "parse_intervals": _action_parse_intervals,
    "parse_availability": _action_parse_availability,
    "scenarios": _action_scenarios,
    "select_scenario": _action_select_scenario,
    "macro_overview": _action_macro_overview,
    "plan_week": _action_plan_week,
}


def _handle_show_command(text: str, athlete_id: str) -> bool:
    token, week, year = _parse_show_args(text)
    if not token:
        return False
    if week is not None and year is None:
        year = st.session_state["rps_state"].get("year")
    if year is not None and week is None:
        week = st.session_state["rps_state"].get("week")
    key = _resolve_artifact_key(token)
    if not key:
        _append_message("assistant", f"Unknown artifact alias: {token}")
        return True
    sm: StateMachine = st.session_state["rps_state"]["state_machine"]
    st.session_state["rps_state"]["state_machine"].parameters.update(
        {
            "last_shown_artifact": key,
            "last_shown_week": week,
            "last_shown_year": year,
            "show_artifact": key,
            "show_week": week,
            "show_year": year,
            "show_label": None,
            "show_format": None,
            "show_content": None,
        }
    )
    label = key
    if week is not None and year is not None:
        label = f"{key} {week:02d} {year:04d}"
    sm.transition("core", "show", action="show")
    sm.parameters["show_label"] = label
    _append_message("assistant", f"Showing artifact: {label}")
    _append_system_log("show", f"Rendered artifact: {label}")
    return True


def handle_input(text: str) -> None:
    rps_state = st.session_state["rps_state"]
    sm: StateMachine = rps_state["state_machine"]
    athlete_id: str = rps_state["athlete_id"]
    year: int = rps_state["year"]
    week: int = rps_state["week"]
    coach = _coach_state()

    if not text:
        return

    _append_message("user", text)

    lower = text.strip().lower()
    if lower in STOP_WORDS:
        if sm.state == "coach":
            coach.update({"previous_response_id": None, "run_id": None})
            _clear_coach_output()
            sm.transition("core", None, action="coach_stop")
            msg = "Coach session ended. Back in core mode."
            _append_message("assistant", msg)
            _append_system_log("coach", msg)
            return
        sm.transition("exit", action="stopword")
        _append_message("assistant", "Session stopped (:quit).")
        _append_system_log("state", _state_log_line(sm, "stopword"))
        return

    if sm.state == "coach":
        _queue_action(
            state="coach",
            substate="message",
            params={"coach_input": text},
            action="coach_message",
        )
        return

    trigger = canonicalize_trigger(text)

    if trigger == "show":
        if _handle_show_command(text, athlete_id):
            return

    if trigger == "coach":
        _enter_coach_mode("coach_start")
        return

    if trigger in {"scenarios", "macro_overview"}:
        _queue_action(
            state="macro_overview",
            substate="create_scenarios",
            params={"year": year, "week": week},
            action="scenarios",
        )
        return

    if trigger == "select_scenario":
        sm.transition("macro_overview", "select_scenario", action="select_scenario")
        _append_system_log("state", _state_log_line(sm, "select_scenario"))
        _append_message("assistant", "Select a scenario from the picker to continue.")
        return

    if trigger == "stop":
        sm.transition("exit", action="stop")
        _append_message("assistant", "Stopped.")
        return

    action = ACTION_MAP.get(trigger or "")
    if not action:
        _append_message("assistant", "No command matched. Try: coach, macro overview, plan week, or show macro.")
        return

    params: dict = {}
    if trigger == "plan_week":
        params = {"year": year, "week": week, "iso_week": f"{year}-{week:02d}"}
    elif trigger == "parse_availability":
        params = {"year": year}
    _queue_action(state="core", substate=trigger, params=params, action=trigger)
    return


def _sidebar_controls() -> None:
    rps_state = st.session_state["rps_state"]
    athlete_id = st.sidebar.text_input("Athlete ID", value=rps_state["athlete_id"])
    year = st.sidebar.number_input("ISO Year", min_value=2020, max_value=2100, value=rps_state["year"], step=1)
    week = st.sidebar.number_input("ISO Week", min_value=1, max_value=53, value=rps_state["week"], step=1)

    rps_state.update({"athlete_id": athlete_id, "year": int(year), "week": int(week)})
    st.sidebar.markdown("---")
    sm: StateMachine = rps_state["state_machine"]
    st.sidebar.caption(f"State: {_format_state_label(sm)}")
    st.sidebar.caption(f"Scenario: {rps_state.get('scenario', 'B')}")
    st.sidebar.markdown("---")
    st.sidebar.caption("Actions")
    if st.sidebar.button("Coach"):
        _enter_coach_mode("coach_start")
    if st.sidebar.button("Plan Week"):
        _queue_action(
            state="core",
            substate="plan_week",
            params={"year": int(year), "week": int(week), "iso_week": f"{int(year)}-{int(week):02d}"},
            action="plan_week",
        )
    if st.sidebar.button("Fetch Intervals Data"):
        _queue_action(
            state="core",
            substate="parse_intervals",
            params={},
            action="parse_intervals",
        )
    st.sidebar.markdown("---")
    if st.sidebar.button("Fetch Availability"):
        _queue_action(
            state="core",
            substate="parse_availability",
            params={"year": int(year)},
            action="parse_availability",
        )
    st.sidebar.markdown("---")
    if st.sidebar.button("Create Macro Overview"):
        _queue_action(
            state="macro_overview",
            substate="create_scenarios",
            params={"year": int(year), "week": int(week)},
            action="scenarios",
        )


def _chat_window() -> None:
    for msg in st.session_state["rps_state"]["messages"]:
        with st.chat_message(msg["role"]):
            fmt = msg.get("format")
            if fmt == "markdown":
                st.markdown(msg["content"], unsafe_allow_html=True)
            elif fmt == "code":
                st.code(msg["content"])
            else:
                st.write(msg["content"])


def _active_chat_panel() -> None:
    sm: StateMachine = st.session_state["rps_state"]["state_machine"]
    if sm.state != "coach":
        return
    start_idx = sm.parameters.get("coach_history_start", 0)
    messages = st.session_state["rps_state"]["messages"][start_idx:]
    for msg in messages:
        with st.chat_message(msg["role"]):
            fmt = msg.get("format")
            if fmt == "markdown":
                st.markdown(msg["content"], unsafe_allow_html=True)
            elif fmt == "code":
                st.code(msg["content"])
            else:
                st.write(msg["content"])


def _coach_output_panel() -> None:
    output = st.session_state["rps_state"].get("coach_output", {})
    text = output.get("text") or ""
    summary = _clean_reasoning_summary(output.get("summary"))
    status = output.get("status")
    if not summary and status != "thinking":
        return
    with st.expander("Coach Reasoning", expanded=True):
        if status == "thinking" and not text:
            st.write("Thinking…")
        if summary:
            st.caption("Reasoning summary")
            st.write(summary)


def _history_panel() -> None:
    with st.expander("History", expanded=False):
        if not st.session_state["rps_state"]["messages"]:
            st.caption("No history yet.")
            return
        _chat_window()


def _athlete_phase_card() -> None:
    rps_state = st.session_state["rps_state"]
    athlete_id = rps_state["athlete_id"]
    year = int(rps_state["year"])
    week = int(rps_state["week"])
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    try:
        macro = store.load_latest(athlete_id, ArtifactType.MACRO_OVERVIEW)
    except FileNotFoundError:
        return
    phases = macro.get("data", {}).get("phases", []) if isinstance(macro, dict) else []
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

    overview = active.get("overview", {}) if isinstance(active, dict) else {}
    phase_name = active.get("name", "Phase")
    with st.expander(f"{phase_name}", expanded=False):
        st.caption(f"{active.get('cycle', '')} · {active.get('iso_week_range', '')}")
        date_range = active.get("date_range") or {}
        if date_range:
            st.caption(f"Dates: {date_range.get('from', '?')} → {date_range.get('to', '?')}")

        primary = overview.get("phase_goals", {}).get("primary")
        secondary = overview.get("phase_goals", {}).get("secondary")
        if primary:
            st.markdown(f"**Primary goal:** {primary}")

        focus = overview.get("core_focus_and_characteristics") or []
        if focus:
            st.markdown("**What to focus on:**")
            st.markdown("\n".join(f"- {item}" for item in focus))

        intensity = overview.get("typical_duration_intensity_pattern")
        if intensity:
            st.markdown(f"**Intensity pattern:** {intensity}")

        non_neg = overview.get("non_negotiables") or []
        if non_neg:
            st.markdown("**Non‑negotiables:**")
            st.markdown("\n".join(f"- {item}" for item in non_neg))

        deload = active.get("deload")
        if deload is not None:
            status = "Yes" if deload else "No"
            st.markdown(f"**Deload week in phase:** {status}")
        with st.expander("Details", expanded=False):
            if secondary:
                st.markdown(f"**Secondary goal:** {secondary}")
            rationale = active.get("deload_rationale")
            if rationale:
                st.markdown(f"**Deload rationale:** {rationale}")
            adaptations = overview.get("expected_adaptations") or []
            if adaptations:
                st.markdown("**Expected adaptations:**")
                st.markdown("\n".join(f"- {item}" for item in adaptations))
            eval_focus = overview.get("evaluation_focus") or []
            if eval_focus:
                st.markdown("**How to tell it’s working:**")
                st.markdown("\n".join(f"- {item}" for item in eval_focus))
            assumptions = overview.get("phase_exit_assumptions") or []
            if assumptions:
                st.markdown("**Phase exit assumptions:**")
                st.markdown("\n".join(f"- {item}" for item in assumptions))


def _show_panel() -> None:
    sm: StateMachine = st.session_state["rps_state"]["state_machine"]
    if sm.substate != "show":
        return
    params = sm.parameters
    key = params.get("show_artifact")
    if not key:
        return
    week = params.get("show_week")
    year = params.get("show_year")
    label = params.get("show_label") or key
    fmt = params.get("show_format")
    content = params.get("show_content")
    if not content:
        rendered = _render_artifact_for_display(
            st.session_state["rps_state"]["athlete_id"],
            key,
            week=week,
            year=year,
        )
        if rendered:
            fmt, content = rendered
            params["show_format"] = fmt
            params["show_content"] = content
    if not content:
        return
    st.caption(f"Showing: {label}")
    if fmt == "markdown":
        st.markdown(content, unsafe_allow_html=True)
    elif fmt == "code":
        st.code(content)
    elif fmt == "warning":
        st.warning(content)
    else:
        st.write(content)
    sm.substate = None
    for key_name in (
        "show_artifact",
        "show_week",
        "show_year",
        "show_label",
        "show_format",
        "show_content",
    ):
        params.pop(key_name, None)


def _process_pending_action() -> None:
    rps_state = st.session_state["rps_state"]
    sm: StateMachine = rps_state["state_machine"]
    pending = sm.parameters.get("pending_action")
    if not pending:
        return
    athlete_id: str = rps_state["athlete_id"]
    year: int = rps_state["year"]
    week: int = rps_state["week"]
    scenario: str = rps_state["scenario"]
    coach = _coach_state()
    chain_action: str | None = None
    chain_substate: str | None = None

    try:
        action_label = ACTION_LABELS.get(pending, pending)
        on_log_line: Callable[[str], None]
        finish_trace: Callable[[bool], None]
        if pending == "coach_message":
            on_log_line = lambda _line: None
            finish_trace = lambda _ok: None
        else:
            on_log_line, finish_trace = _start_live_trace(action_label)
        _append_system_log("action", f"Starting {action_label}…", level=logging.INFO)
        with st.spinner(f"Running: {action_label}"):
            if pending == "coach_message":
                text = sm.parameters.pop("coach_input", "")
                sentinel = object()
                stream_queue: "queue.Queue[object]" = queue.Queue()
                output_parts: list[str] = []
                summary_parts: list[str] = []
                result_holder: dict[str, object] = {}
                runtime = _multi_runtime_for("coach")
                spec = AGENTS["coach"]
                injection_text = _build_injection_block("coach", mode="coach")
                run_id = coach.get("run_id") or _make_ui_run_id("coach")
                coach["run_id"] = run_id

                def _on_output(delta: str) -> None:
                    output_parts.append(delta)
                    stream_queue.put(delta)

                def _on_summary(delta: str) -> None:
                    summary_parts.append(delta)

                def _run(prev_id: str | None):
                    return run_agent_session(
                        runtime,
                        agent_name="coach",
                        agent_vs_name=spec.vector_store_name,
                        athlete_id=athlete_id,
                        user_input=text,
                        workspace_root=SETTINGS.workspace_root,
                        schema_dir=SETTINGS.schema_dir,
                        model_override=SETTINGS.model_for_agent("coach"),
                        include_debug_file_search=False,
                        force_file_search=False,
                        max_num_results=SETTINGS.file_search_max_results,
                        run_id=run_id,
                        previous_response_id=prev_id,
                        injection_text=injection_text,
                        stream_handlers={"on_output": _on_output, "on_summary": _on_summary},
                    )

                _set_coach_output("Thinking…", status="thinking")
                def _worker() -> None:
                    try:
                        result_holder["result"] = _run(coach.get("previous_response_id"))
                    except Exception as exc:
                        if _is_no_session_context(exc):
                            coach["previous_response_id"] = None
                            result_holder["result"] = _run(None)
                        else:
                            result_holder["error"] = exc
                    finally:
                        stream_queue.put(sentinel)

                thread = threading.Thread(target=_worker, daemon=True)
                thread.start()
                with st.chat_message("assistant"):
                    def _stream():
                        while True:
                            chunk = stream_queue.get()
                            if chunk is sentinel:
                                break
                            yield str(chunk)

                    st.write_stream(_stream())
                thread.join()

                if "error" in result_holder:
                    raise result_holder["error"]

                result = result_holder.get("result")
                if isinstance(result, dict) and _looks_like_no_session(
                    str(result.get("text") or "")
                ):
                    coach["previous_response_id"] = None

                summary_text = "".join(summary_parts).strip() or None
                if not summary_text and isinstance(result, dict) and result.get("response"):
                    summaries = extract_reasoning_summaries(result.get("response"))
                    if summaries:
                        summary_text = str(summaries[0])
                if isinstance(result, dict) and result.get("response_id"):
                    coach["previous_response_id"] = result["response_id"]

                output = "".join(output_parts).strip()
                if not output and isinstance(result, dict):
                    output = str(result.get("text") or "")
                if not output:
                    output = "Coach did not return text."
                normalized = _normalize_streamed_text(output)
                _set_coach_output(normalized, status="done", summary=summary_text)
                _append_message("assistant", normalized)
            elif pending == "select_scenario":
                rationale = sm.parameters.pop("scenario_rationale", None)
                output = _action_select_scenario(
                    athlete_id,
                    year,
                    week,
                    scenario,
                    rationale,
                    on_log_line=on_log_line,
                )
                _append_message("assistant", output)
                _append_system_log("select_scenario", output)
                chain_action = "macro_overview"
                chain_substate = "create_macro_overview"
            elif pending == "macro_overview":
                output = _action_macro_overview(
                    athlete_id,
                    year,
                    week,
                    scenario,
                    on_log_line=on_log_line,
                )
                _append_message("assistant", output)
                _append_system_log("macro_overview", output)
                sm.state = "core"
                sm.substate = None
                _append_system_log("state", _state_log_line(sm, "macro_overview_done"))
            elif pending == "scenarios":
                output = _action_scenarios(athlete_id, year, week, on_log_line=on_log_line)
                _append_message("assistant", output)
                _append_system_log("scenarios", output)
                sm.state = "macro_overview"
                sm.substate = "select_scenario"
                _append_message("assistant", "Scenarios created. Select a scenario to continue.")
                _append_system_log("state", _state_log_line(sm, "scenarios_done"))
            elif pending == "parse_availability":
                output = _action_parse_availability(athlete_id, year, on_log_line=on_log_line)
                _append_message("assistant", output)
                _append_system_log("parse_availability", output)
            elif pending == "parse_intervals":
                output = _action_parse_intervals(athlete_id, on_log_line=on_log_line)
                _append_message("assistant", output)
                _append_system_log("parse_intervals", output)
            elif pending == "plan_week":
                sentinel = object()
                stream_queue: "queue.Queue[object]" = queue.Queue()
                stream_buf = _StreamingBuffer(stream_queue)
                result_holder: dict[str, object] = {}

                def _worker() -> None:
                    try:
                        runtime = _multi_runtime_for("macro_planner")
                        run_id = f"ui_plan_week_{year}_{week:02d}"
                        with redirect_stdout(stream_buf):
                            result_holder["result"] = plan_week(
                                runtime,
                                athlete_id=athlete_id,
                                year=year,
                                week=week,
                                run_id=run_id,
                                model_resolver=SETTINGS.model_for_agent,
                                temperature_resolver=SETTINGS.temperature_for_agent,
                                reasoning_effort_resolver=SETTINGS.reasoning_effort_for_agent,
                                reasoning_summary_resolver=SETTINGS.reasoning_summary_for_agent,
                                force_file_search=True,
                                max_num_results=SETTINGS.file_search_max_results,
                            )
                    except Exception as exc:  # pragma: no cover - UI safety net
                        result_holder["error"] = exc
                    finally:
                        stream_queue.put(sentinel)

                thread = threading.Thread(target=_worker, daemon=True)
                thread.start()
                with st.expander("Plan Week Output (live)", expanded=True):
                    def _stream():
                        while True:
                            chunk = stream_queue.get()
                            if chunk is sentinel:
                                break
                            on_log_line(str(chunk))
                            yield str(chunk)

                    st.write_stream(_stream())
                thread.join()

                if "error" in result_holder:
                    raise result_holder["error"]  # handled by outer except

                output = stream_buf.getvalue().strip()
                status = "ok"
                result_obj = result_holder.get("result")
                if hasattr(result_obj, "ok"):
                    status = "ok" if getattr(result_obj, "ok") else "error"
                summary = (output + "\n\n" if output else "") + f"plan-week finished: {status}"
                _append_message("assistant", summary)
                _append_system_log("plan_week", summary)
            else:
                _append_message("assistant", f"Unknown action: {pending}")
        finish_trace(True)
        _append_system_log("action", f"{action_label} done.", level=logging.INFO)
    except SystemExit as exc:
        msg = _format_exception(exc) or f"{pending} exited."
        sm.parameters["last_error"] = msg
        _append_message("assistant", msg)
        _append_system_log(pending, msg, level=logging.ERROR)
        if "finish_trace" in locals():
            finish_trace(False)
    except Exception as exc:  # pragma: no cover - UI safety net
        msg = _format_exception(exc)
        sm.parameters["last_error"] = msg
        _append_message("assistant", msg)
        _append_system_log(pending, msg, level=logging.ERROR)
        if "finish_trace" in locals():
            finish_trace(False)
    finally:
        sm.parameters.pop("pending_action", None)
        if pending == "coach_message":
            sm.substate = None
        elif sm.substate == pending:
            sm.substate = None
        if chain_action:
            sm.state = "macro_overview"
            sm.substate = chain_substate
            sm.parameters["pending_action"] = chain_action
            _append_system_log("state", _state_log_line(sm, chain_action))
            st.rerun()


def _macro_flow_panel() -> None:
    rps_state = st.session_state["rps_state"]
    sm: StateMachine = rps_state["state_machine"]
    if sm.state != "macro_overview" or sm.substate != "select_scenario":
        return
    if sm.parameters.get("pending_action"):
        return
    st.markdown("### Scenario selection")
    current = rps_state.get("scenario", "B")
    choice = st.radio(
        "Choose scenario",
        options=["A", "B", "C"],
        index=["A", "B", "C"].index(current),
        horizontal=True,
    )
    rationale = st.text_area("Rationale (optional)", value="")
    if st.button("Confirm scenario selection"):
        rps_state["scenario"] = choice
        sm.parameters["scenario_rationale"] = rationale.strip() or None
        _queue_action(
            state="macro_overview",
            substate="select_scenario",
            params={"scenario": choice},
            action="select_scenario",
        )


def _system_panel() -> None:
    logs: list[dict] = st.session_state["rps_state"].setdefault("system_logs", [])
    with st.expander("System output / logs", expanded=True):
        if not logs:
            st.caption("No system output yet.")
            return
        last = logs[-1]
        st.caption(f"{last['ts']} · {last['source']}")
        st.code(last["content"])
        if len(logs) > 1:
            with st.expander("History", expanded=False):
                for entry in reversed(logs[:-1]):
                    st.caption(f"{entry['ts']} · {entry['source']}")
                    st.code(entry["content"])


def _coach_status_panel() -> None:
    sm: StateMachine = st.session_state["rps_state"]["state_machine"]
    if sm.state == "coach":
        st.success("Coach: active. Use :quit to exit coach mode.")


def main() -> None:
    st.set_page_config(page_title="RPS - Randonneur Performance System", layout="wide")
    st.title("RPS - Randonneur Performance System")
    st.caption("Chat-style control surface for preflight, macro, and plan-week flows.")

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is missing. Set it in .env before using agent actions.")
        st.stop()

    cli_args = _parse_cli_args()
    if cli_args.init and not st.session_state.get("_init_reset_done"):
        athlete_id = cli_args.athlete_id or os.getenv("ATHLETE_ID") or "i150546"
        st.session_state.clear()
        st.session_state["_init_reset_done"] = True
        st.session_state["_pending_init_reset"] = athlete_id
        st.rerun()

    _ensure_session_state()
    if not st.session_state["rps_state"].get("_log_file_announced"):
        athlete_id = st.session_state["rps_state"]["athlete_id"]
        log_file = os.getenv("APP_LOG_FILE")
        if not log_file:
            log_file = str(SETTINGS.workspace_root / athlete_id / "logs" / "rps_ui.log")
        _append_system_log("log", f"Log file: {log_file}", level=logging.INFO)
        st.session_state["rps_state"]["_log_file_announced"] = True
    pending_reset = st.session_state.pop("_pending_init_reset", None)
    if pending_reset:
        summary = _reset_cached_artifacts(pending_reset)
        _append_system_log("init", summary)
    if cli_args.athlete_id:
        st.session_state["rps_state"]["athlete_id"] = cli_args.athlete_id
    _sidebar_controls()
    preflight_ok, preflight_err = _auto_preflight()
    if st.session_state["rps_state"].pop("preflight_state_changed", False):
        st.rerun()
    _show_panel()
    _macro_flow_panel()
    _active_chat_panel()
    _process_pending_action()

    if not preflight_ok:
        st.error(preflight_err or "Preflight failed. See system output for details.")
        st.stop()

    with st.form("chat_input", clear_on_submit=True):
        text = st.text_input("Command", placeholder="e.g., macro overview, plan week, show macro")
        submitted = st.form_submit_button("Send")
    if submitted:
        handle_input(text)
        st.rerun()
    _coach_output_panel()
    _athlete_phase_card()
    _system_panel()
    _history_panel()


if __name__ == "__main__":
    main()
