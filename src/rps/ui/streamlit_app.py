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
import re
from typing import Callable

import streamlit as st

from rps.agents.registry import AGENTS
from rps.agents.runner import run_agent_session
from rps.agents.multi_output_runner import AgentRuntime as MultiRuntime
from rps.core.config import load_app_settings, load_env_file
from rps.data_pipeline.intervals_data import run_pipeline as run_intervals_pipeline
from rps.data_pipeline.season_brief_availability import parse_and_store_availability
from rps.main import _preflight
from rps.openai.client import get_client
from rps.openai.vectorstore_state import VectorStoreResolver
from rps.orchestrator.plan_week import _build_injection_block, plan_week
from rps.prompts.loader import PromptLoader
from rps.rendering.auto_render import render_sidecar
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

try:
    from scripts import macro_mode_a
except Exception:  # pragma: no cover - UI fallback only
    macro_mode_a = None


ROOT = Path(__file__).resolve().parents[3]
load_env_file(ROOT / ".env")
SETTINGS = load_app_settings()
LOGGER = logging.getLogger("rps.streamlit")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO)
LOGGER.setLevel(logging.WARNING)

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
            "state_machine": StateMachine(),
        }


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


def _append_system_log(source: str, content: str) -> None:
    logs: list[dict] = st.session_state["rps_state"].setdefault("system_logs", [])
    logs.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "content": content,
        }
    )


class _BufferHandler(logging.Handler):
    def __init__(self, sink: list[str]) -> None:
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - simple glue
        msg = self.format(record)
        if msg:
            self.sink.append(msg)


def _capture_output(
    fn: Callable[[], object],
    *,
    loggers: list[logging.Logger] | None = None,
) -> tuple[object | None, str]:
    buf = io.StringIO()
    log_lines: list[str] = []
    handler = _BufferHandler(log_lines)
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


def _action_parse_availability(athlete_id: str, year: int) -> str:
    result, output = _capture_output(
        lambda: parse_and_store_availability(
            athlete_id=athlete_id,
            workspace_root=SETTINGS.workspace_root,
            schema_dir=SETTINGS.schema_dir,
            year=year,
            skip_validate=False,
        ),
        loggers=CAPTURE_LOGGERS,
    )
    if output:
        return output
    if result:
        return f"Availability written: {result.out_file}"
    return "Availability parsed."


def _action_parse_intervals(athlete_id: str) -> str:
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
    )
    return output or "Intervals pipeline completed."


def _action_scenarios(athlete_id: str, year: int, week: int) -> str:
    if macro_mode_a is None:
        raise RuntimeError("scripts/macro_mode_a.py not importable.")
    run_id = f"macro_scenarios_{year}_w{week:02d}"
    args = argparse.Namespace(
        athlete=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        scenario_run_id=None,
        out=None,
        model=None,
        max_num_results=SETTINGS.file_search_max_results,
        no_file_search=False,
    )
    code, output = _capture_output(lambda: macro_mode_a.run_scenarios(args), loggers=CAPTURE_LOGGERS)
    if code not in (0, None):
        raise RuntimeError(output or f"Scenario run failed with code {code}.")
    return output or f"Scenarios created: {run_id}"


def _action_select_scenario(athlete_id: str, year: int, week: int, scenario: str) -> str:
    if macro_mode_a is None:
        raise RuntimeError("scripts/macro_mode_a.py not importable.")
    run_id = f"macro_scenario_selection_{year}_w{week:02d}"
    scen_run_id = f"macro_scenarios_{year}_w{week:02d}"
    args = argparse.Namespace(
        athlete=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        scenario=scenario.upper(),
        scenario_run_id=scen_run_id,
        rationale=None,
        model=None,
        max_num_results=SETTINGS.file_search_max_results,
        no_file_search=False,
    )
    _, output = _capture_output(lambda: macro_mode_a.run_select(args), loggers=CAPTURE_LOGGERS)
    return output or f"Scenario {scenario.upper()} selected."


def _action_macro_overview(athlete_id: str, year: int, week: int, scenario: str) -> str:
    if macro_mode_a is None:
        raise RuntimeError("scripts/macro_mode_a.py not importable.")
    run_id = f"macro_overview_{year}_w{week:02d}"
    scen_run_id = f"macro_scenarios_{year}_w{week:02d}"
    args = argparse.Namespace(
        athlete=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        scenario=scenario.upper(),
        scenario_run_id=scen_run_id,
        allow_missing_events=False,
        moving_time_rate_band=None,
        model=None,
        max_num_results=SETTINGS.file_search_max_results,
        no_file_search=False,
    )
    code, output = _capture_output(lambda: macro_mode_a.run_overview(args), loggers=CAPTURE_LOGGERS)
    if code not in (0, None):
        raise RuntimeError(output or f"Macro overview failed with code {code}.")
    return output or f"Macro overview created: {run_id}"


def _action_plan_week(athlete_id: str, year: int, week: int) -> str:
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
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
            run_id=run_id,
            previous_response_id=coach.get("previous_response_id"),
            injection_text=injection_text,
        )

    result, output = _capture_output(_call, loggers=CAPTURE_LOGGERS)
    if isinstance(result, dict) and result.get("response_id"):
        coach["previous_response_id"] = result["response_id"]

    log_text = output or (result.get("text") if isinstance(result, dict) else "")
    if log_text:
        _append_system_log("coach", log_text)

    if isinstance(result, dict) and result.get("text"):
        return str(result["text"])
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
    scenario: str = rps_state["scenario"]
    coach = _coach_state()

    if not text:
        return

    _append_message("user", text)

    lower = text.strip().lower()
    if lower in STOP_WORDS:
        if sm.state == "coach":
            coach.update({"previous_response_id": None, "run_id": None})
            sm.transition("core", None, action="coach_stop")
            msg = "Coach session ended. Back in core mode."
            _append_message("assistant", msg)
            _append_system_log("coach", msg)
            return
        sm.transition("exit", action="stopword")
        _append_message("assistant", "Session stopped (:quit).")
        return

    if sm.state == "coach":
        sm.transition("coach", action="coach_message")
        try:
            with st.spinner("Coach is thinking..."):
                output = _action_coach(athlete_id, text, coach)
        except Exception as exc:  # pragma: no cover - UI safety net
            sm.parameters["last_error"] = str(exc)
            _append_message("assistant", f"Coach error: {exc}")
            _append_system_log("coach", f"Error: {exc}")
            return
        _append_message("assistant", output)
        return

    trigger = canonicalize_trigger(text)

    if trigger == "show":
        if _handle_show_command(text, athlete_id):
            return

    if trigger == "coach":
        coach.update({"previous_response_id": None, "run_id": _make_ui_run_id("coach")})
        sm.parameters["coach_history_start"] = len(st.session_state["rps_state"]["messages"])
        sm.transition("coach", action="coach_start")
        msg = "Coach mode active. Ask anything. Use :quit to leave coach mode."
        _append_message("assistant", msg)
        _append_system_log("coach", msg)
        return

    if trigger == "stop":
        sm.transition("exit", action="stop")
        _append_message("assistant", "Stopped.")
        return

    action = ACTION_MAP.get(trigger or "")
    if not action:
        _append_message("assistant", "No command matched. Try: coach, scenarios, plan week, or show macro.")
        return

    sm.transition("core", trigger, action=trigger)
    try:
        with st.spinner(f"Running: {trigger}"):
            if trigger == "select_scenario":
                output = action(athlete_id, year, week, scenario)
            elif trigger == "macro_overview":
                output = action(athlete_id, year, week, scenario)
            elif trigger == "scenarios":
                output = action(athlete_id, year, week)
            elif trigger == "preflight":
                output = action(athlete_id, year, week)
            elif trigger == "parse_availability":
                output = action(athlete_id, year)
            elif trigger == "parse_intervals":
                output = action(athlete_id)
            else:
                output = action(athlete_id, year, week)
    except SystemExit as exc:
        msg = str(exc) or f"{trigger} exited."
        sm.parameters["last_error"] = msg
        _append_message("assistant", msg)
        _append_system_log(trigger or "system", msg)
        return
    except Exception as exc:
        sm.parameters["last_error"] = str(exc)
        _append_message("assistant", f"Error: {exc}")
        _append_system_log(trigger or "error", f"Error: {exc}")
        return

    if output:
        _append_message("assistant", output)
        _append_system_log(trigger or "system", output)


def _sidebar_controls() -> None:
    rps_state = st.session_state["rps_state"]
    athlete_id = st.sidebar.text_input("Athlete ID", value=rps_state["athlete_id"])
    year = st.sidebar.number_input("ISO Year", min_value=2020, max_value=2100, value=rps_state["year"], step=1)
    week = st.sidebar.number_input("ISO Week", min_value=1, max_value=53, value=rps_state["week"], step=1)
    scenario = st.sidebar.selectbox("Scenario", options=["A", "B", "C"], index=["A", "B", "C"].index(rps_state["scenario"]))

    rps_state.update({"athlete_id": athlete_id, "year": int(year), "week": int(week), "scenario": scenario})
    coach = _coach_state()

    st.sidebar.markdown("---")
    sm: StateMachine = rps_state["state_machine"]
    state_label = sm.state
    if sm.substate:
        state_label = f"{state_label} / {sm.substate}"
    st.sidebar.caption(f"State: {state_label}")
    st.sidebar.markdown("---")
    st.sidebar.caption("Actions")
    if st.sidebar.button("Coach"):
        handle_input("coach")
    if st.sidebar.button("Plan Week"):
        handle_input("plan week")
    st.sidebar.markdown("---")
    if st.sidebar.button("Fetch Availability"):
        handle_input("parse availability")
    if st.sidebar.button("Fetch Intervals Data"):
        handle_input("parse intervals")
    st.sidebar.markdown("---")
    if st.sidebar.button("Create Scenarios"):
        handle_input("scenarios")
    if st.sidebar.button("Select Scenario"):
        handle_input("select scenario")
    if st.sidebar.button("Create Macro Overview"):
        handle_input("macro overview")


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


def _history_panel() -> None:
    with st.expander("History", expanded=False):
        if not st.session_state["rps_state"]["messages"]:
            st.caption("No history yet.")
            return
        _chat_window()


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


def _system_panel() -> None:
    logs: list[dict] = st.session_state["rps_state"].setdefault("system_logs", [])
    with st.expander("System output / logs", expanded=False):
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

    _ensure_session_state()
    _sidebar_controls()
    preflight_ok, preflight_err = _auto_preflight()
    if st.session_state["rps_state"].pop("preflight_state_changed", False):
        st.rerun()
    _show_panel()
    _active_chat_panel()

    if not preflight_ok:
        st.error(preflight_err or "Preflight failed. See system output for details.")
        st.stop()

    with st.form("chat_input", clear_on_submit=True):
        text = st.text_input("Command", placeholder="e.g., scenarios, plan week, show macro")
        submitted = st.form_submit_button("Send")
    if submitted:
        handle_input(text)
        st.rerun()

    _system_panel()
    _history_panel()


if __name__ == "__main__":
    main()
