"""Guarded, validated writes to the local workspace."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from rps.agents.output_normalization import (
    normalize_phase_guardrails_document,
    normalize_phase_preview_document,
    normalize_phase_structure_document,
)
from rps.agents.tasks import OutputSpec
from rps.planning.contracts import (
    blocking_messages,
    validate_phase_against_execution_context,
    validate_season_plan_against_phase_load_context,
    validate_season_plan_against_phase_slots,
    validate_week_plan_against_week_context,
)
from rps.planning.deterministic_context import (
    build_load_capacity_block,
    build_phase_execution_context,
    build_season_phase_load_block,
    build_season_phase_slot_block,
    build_selected_scenario_contract_block,
    build_selected_scenario_structure_block,
    build_week_calendar_context,
)
from rps.planning.load_bands import selected_kpi_rate_band_from_selection
from rps.rendering.auto_render import render_sidecar
from rps.workouts.generator import canonicalize_workout_entry
from rps.workouts.validator import collect_week_plan_export_issues
from rps.workouts.week_plan_consistency import normalize_week_plan_consistency
from rps.workspace.artifact_metadata import canonicalize_artifact_envelope_meta
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import (
    envelope_week,
    envelope_week_range,
    next_iso_week,
    parse_iso_week,
    parse_iso_week_range,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.paths import ARTIFACT_PATHS
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.schema_utils import is_envelope_schema
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType
from rps.workspace.versioning import (
    derive_version_key_from_envelope,
    normalize_version_key,
    normalize_week_version_key,
)

JsonMap = dict[str, object]
StringListMap = dict[str, list[str]]
StoreResult = dict[str, object]
INTEGER_ROUNDING_EPSILON = 1e-9
_WEEKDAY_ORDER = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_NON_TRAINING_DAY_ROLES = frozenset({"REST", "OFF_BIKE", "TRAVEL"})


def normalize_artifact_owner(document: object, artifact_type: ArtifactType) -> object:
    """Set the canonical writer owner for persisted planning/report artefacts."""

    return canonicalize_artifact_envelope_meta(document, artifact_type=artifact_type)


class MissingDependenciesError(RuntimeError):
    """Raised when required upstream artifacts are missing."""
    pass


@dataclass(frozen=True)
class DependencyRule:
    """Defines required latest dependencies for a target artifact."""
    target: ArtifactType
    requires_latest: tuple[ArtifactType, ...]


DEFAULT_RULES = [
    DependencyRule(
        target=ArtifactType.PHASE_GUARDRAILS,
        requires_latest=(ArtifactType.SEASON_PLAN,),
    ),
    DependencyRule(
        target=ArtifactType.PHASE_STRUCTURE,
        requires_latest=(ArtifactType.SEASON_PLAN, ArtifactType.PHASE_GUARDRAILS),
    ),
    DependencyRule(
        target=ArtifactType.PHASE_PREVIEW,
        requires_latest=(ArtifactType.PHASE_STRUCTURE,),
    ),
    DependencyRule(
        target=ArtifactType.WEEK_PLAN,
        requires_latest=(ArtifactType.PHASE_STRUCTURE,),
    ),
    DependencyRule(
        target=ArtifactType.INTERVALS_WORKOUTS,
        requires_latest=(ArtifactType.WEEK_PLAN,),
    ),
    DependencyRule(
        target=ArtifactType.DES_ANALYSIS_REPORT,
        requires_latest=(ArtifactType.ACTIVITIES_TREND, ArtifactType.WEEK_PLAN),
    ),
]


@dataclass
class GuardedValidatedStore:
    """Schema-validated store that enforces dependency rules."""
    athlete_id: str
    schema_dir: Path
    workspace_root: Path

    logger = logging.getLogger(__name__)

    def __post_init__(self) -> None:
        """Initialize schema registry and local store."""
        self.schemas = SchemaRegistry(self.schema_dir)
        self.store = LocalArtifactStore(root=self.workspace_root)

    def _check_dependencies(self, target: ArtifactType) -> None:
        """Raise if required latest artifacts are missing."""
        for rule in DEFAULT_RULES:
            if rule.target == target:
                missing = [
                    item.value
                    for item in rule.requires_latest
                    if not self.store.latest_exists(self.athlete_id, item)
                ]
                if missing:
                    raise MissingDependenciesError(
                        f"Missing latest dependencies for {target.value}: {missing}"
                    )

    def _normalize_text(self, value: str) -> str:
        """Normalize text for loose matching."""
        cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower())
        return " ".join(cleaned.split())

    def _as_map(self, value: object) -> JsonMap:
        """Return a JSON object mapping when the value is a dict."""
        return value if isinstance(value, dict) else {}

    def _as_list(self, value: object) -> list[object]:
        """Return a JSON array when the value is a list."""
        return value if isinstance(value, list) else []

    def _as_string_list(self, value: object) -> list[str]:
        """Return stringified non-empty entries from a list-like value."""
        return [str(item).strip() for item in self._as_list(value) if str(item).strip()]

    def _normalize_payload(self, payload: object) -> str:
        """Normalize a payload into a searchable text blob."""
        try:
            raw = json.dumps(payload, ensure_ascii=False)
        except TypeError:
            raw = str(payload)
        return self._normalize_text(raw)

    def _normalized_string_list(self, value: object) -> list[str]:
        """Return normalized non-empty strings from a list-like or scalar input."""
        if isinstance(value, str):
            stripped = value.strip()
            return [self._normalize_text(stripped)] if stripped else []
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(self._normalize_text(text))
        return items

    def _season_constraints(self, season_plan: JsonMap) -> StringListMap:
        """Collect season plan constraints for propagation checks."""
        data = self._as_map(season_plan.get("data"))
        global_constraints = self._as_map(data.get("global_constraints"))
        availability = self._as_string_list(global_constraints.get("availability_assumptions"))
        risks = self._as_string_list(global_constraints.get("risk_constraints"))
        planned = self._as_string_list(global_constraints.get("planned_event_windows"))
        recovery = self._as_map(global_constraints.get("recovery_protection"))
        fixed_days = self._as_string_list(recovery.get("fixed_rest_days"))
        raw_notes = recovery.get("notes")
        if isinstance(raw_notes, str):
            notes = [raw_notes.strip()] if raw_notes.strip() else []
        else:
            notes = [
                str(item).strip()
                for item in self._as_list(raw_notes)
                if str(item).strip()
            ]
        return {
            "availability": availability,
            "risks": risks,
            "planned": planned,
            "fixed_days": fixed_days,
            "recovery_notes": notes,
        }

    def _parse_planned_event_window(self, value: str) -> tuple[str, str] | None:
        """Extract `(date, type)` from a planned-event-window string when possible."""
        match = re.search(
            r"(\d{4}-\d{2}-\d{2})\s*(?:\((A|B|C)\)|([ABC])\b)",
            value,
            re.IGNORECASE,
        )
        if not match:
            return None
        event_type = (match.group(2) or match.group(3) or "").upper()
        if not event_type:
            return None
        return match.group(1), event_type

    def _guardrails_event_pairs(self, document: JsonMap) -> set[tuple[str, str]]:
        """Return `(date, type)` pairs from guardrails event constraints."""
        data = self._as_map(document.get("data"))
        events_constraints = self._as_map(data.get("events_constraints"))
        events = self._as_list(events_constraints.get("events"))
        pairs: set[tuple[str, str]] = set()
        for event in events:
            if not isinstance(event, dict):
                continue
            date_value = str(event.get("date") or "").strip()
            type_value = str(event.get("type") or "").strip().upper()
            if date_value and type_value:
                pairs.add((date_value, type_value))
        return pairs

    def _extract_feasible_max_from_notes(self, notes: object) -> float | None:
        """Return an explicitly stated feasible max from notes when present."""
        if not isinstance(notes, str):
            return None
        match = re.search(
            r"feasible(?:[_ ]band)?\s*max(?:imum)?\s*(?:is|=|:)?\s*([0-9]+(?:[.,][0-9]+)?)",
            notes,
            re.IGNORECASE,
        )
        if match is None:
            return None
        raw = match.group(1).replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    def _contains_normalized_item(self, haystack: list[str], item: str) -> bool:
        """Return whether a normalized item exists in a normalized string list."""
        normalized = self._normalize_text(item)
        return bool(normalized and normalized in haystack)

    def _structure_constraint_has_event_window(self, upstream_blob: str, raw_item: str) -> bool:
        """Return whether a phase-structure constraint blob semantically contains the planned-event marker."""
        parsed = self._parse_planned_event_window(raw_item)
        if parsed is None:
            normalized = self._normalize_text(raw_item)
            return bool(normalized and normalized in upstream_blob)
        event_date, event_type = parsed
        date_token = self._normalize_text(event_date)
        type_token = self._normalize_text(event_type)
        return bool(date_token and type_token and date_token in upstream_blob and type_token in upstream_blob)

    def _structure_constraint_has_recovery_note(
        self,
        upstream_items: list[str],
        upstream_blob: str,
        raw_item: str,
    ) -> bool:
        """Return whether a recovery note is present as either a list item or a combined constraint string."""
        if self._contains_normalized_item(upstream_items, raw_item):
            return True
        normalized = self._normalize_text(raw_item)
        return bool(normalized and normalized in upstream_blob)

    def _load_phase_guardrails_for_range(
        self,
        expected_range: object,
    ) -> tuple[JsonMap, str]:
        """Load the phase guardrails matching the expected range."""
        range_spec = envelope_week_range({"meta": {"iso_week_range": expected_range}})
        if range_spec:
            query = IndexExactQuery(root=self.store.root, athlete_id=self.athlete_id)
            version_key = query.best_exact_range_version(
                ArtifactType.PHASE_GUARDRAILS.value,
                range_spec,
            )
            if version_key:
                loaded = self.store.load_version(
                    self.athlete_id,
                    ArtifactType.PHASE_GUARDRAILS,
                    version_key,
                )
                return self._as_map(loaded), version_key

        latest = self._as_map(self.store.load_latest(self.athlete_id, ArtifactType.PHASE_GUARDRAILS))
        latest_key = self._as_map(latest.get("meta")).get("version_key", "latest")
        if range_spec:
            latest_range = envelope_week_range(latest)
            if latest_range and latest_range.key != range_spec.key:
                raise MissingDependenciesError(
                    f"Latest PHASE_GUARDRAILS does not match range {range_spec.key}"
                )
        return latest, str(latest_key)

    def _load_phase_structure_for_range(
        self,
        expected_range: object,
    ) -> tuple[JsonMap, str]:
        """Load the phase structure matching the expected range."""
        range_spec = envelope_week_range({"meta": {"iso_week_range": expected_range}})
        if range_spec:
            query = IndexExactQuery(root=self.store.root, athlete_id=self.athlete_id)
            version_key = query.best_exact_range_version(
                ArtifactType.PHASE_STRUCTURE.value,
                range_spec,
            )
            if version_key:
                loaded = self.store.load_version(
                    self.athlete_id,
                    ArtifactType.PHASE_STRUCTURE,
                    version_key,
                )
                return self._as_map(loaded), version_key

        latest = self._as_map(self.store.load_latest(self.athlete_id, ArtifactType.PHASE_STRUCTURE))
        latest_key = self._as_map(latest.get("meta")).get("version_key", "latest")
        if range_spec:
            latest_range = envelope_week_range(latest)
            if latest_range and latest_range.key != range_spec.key:
                raise MissingDependenciesError(
                    f"Latest PHASE_STRUCTURE does not match range {range_spec.key}"
                )
        return latest, str(latest_key)

    def _weeks_in_range(self, range_value: object) -> list[str]:
        """Return canonical week keys for an inclusive ISO-week range."""
        parsed = parse_iso_week_range(range_value)
        if parsed is None:
            return []
        weeks: list[str] = []
        current = parsed.start
        while True:
            weeks.append(f"{current.year:04d}-{current.week:02d}")
            if current == parsed.end:
                break
            current = next_iso_week(current)
        return weeks

    def _season_phase_for_range(self, season_plan: JsonMap, range_key: object) -> JsonMap:
        """Return the season-plan phase matching an exact ISO-week range."""

        target = str(range_key or "").strip()
        for phase in self._as_list(self._as_map(season_plan.get("data")).get("phases")):
            phase_map = self._as_map(phase)
            if str(phase_map.get("iso_week_range") or "").strip() == target:
                return phase_map
        return {}

    def _enforce_phase_guardrails_constraints(
        self,
        document: JsonMap,
        season_plan: JsonMap,
    ) -> None:
        """Ensure season plan constraints are propagated into phase guardrails."""
        constraints = self._season_constraints(season_plan)
        data = self._as_map(document.get("data"))
        meta = self._as_map(document.get("meta"))
        season_phase = self._season_phase_for_range(season_plan, meta.get("iso_week_range"))
        blob = self._normalize_payload(data)
        guardrails_events = self._guardrails_event_pairs(document)
        phase_summary = self._as_map(data.get("phase_summary"))
        non_negotiables = self._normalized_string_list(phase_summary.get("non_negotiables"))
        key_risks = self._normalized_string_list(phase_summary.get("key_risks_warnings"))
        execution_non_negotiables = self._as_map(data.get("execution_non_negotiables"))
        recovery_rules = self._normalize_text(
            str(execution_non_negotiables.get("recovery_protection_rules") or "").strip()
        )
        errors: list[str] = []
        expected_phase_intent = str(season_phase.get("phase_intent") or "").strip()
        observed_phase_intent = str(self._as_map(data.get("body_metadata")).get("phase_intent") or "").strip()
        if expected_phase_intent and observed_phase_intent != expected_phase_intent:
            errors.append(
                f"phase_guardrails.body_metadata.phase_intent must match season plan phase_intent '{expected_phase_intent}'."
            )
        expected_build_subtype = season_phase.get("build_subtype")
        observed_build_subtype = self._as_map(data.get("body_metadata")).get("build_subtype")
        if expected_build_subtype != observed_build_subtype:
            errors.append(
                f"phase_guardrails.body_metadata.build_subtype must match season plan build_subtype {expected_build_subtype!r}."
            )
        expected_contract = self._as_map(self._as_map(season_plan.get("data")).get("selected_scenario_contract"))
        observed_contract = self._as_map(data.get("inherited_scenario_contract"))
        if expected_contract and not observed_contract:
            errors.append("phase_guardrails.data.inherited_scenario_contract must be present and inherited from season plan.")
        for field, expected in expected_contract.items():
            if field in observed_contract and observed_contract.get(field) != expected:
                errors.append(
                    f"phase_guardrails.data.inherited_scenario_contract.{field} must match season plan selected_scenario_contract."
                )

        errors.extend(
            f"Season plan availability_assumptions missing in phase_guardrails: {item}"
            for item in constraints["availability"]
            if not self._contains_normalized_item(non_negotiables, item)
        )
        errors.extend(
            f"Season plan risk_constraints missing in phase_guardrails: {item}"
            for item in constraints["risks"]
            if not self._contains_normalized_item(key_risks, item)
        )

        for item in constraints["recovery_notes"]:
            normalized = self._normalize_text(item)
            if normalized and normalized not in recovery_rules:
                errors.append(f"Season plan recovery_notes missing in phase_guardrails: {item}")

        for item in constraints["planned"]:
            parsed = self._parse_planned_event_window(item)
            if parsed is None:
                normalized = self._normalize_text(item)
                if normalized and normalized not in blob:
                    errors.append(f"Season plan planned_event_windows missing in phase_guardrails: {item}")
                continue
            if parsed not in guardrails_events:
                errors.append(f"Season plan planned_event_windows missing in phase_guardrails: {item}")

        if constraints["fixed_days"]:
            day_aliases = {
                "Mon": ["mon", "monday"],
                "Tue": ["tue", "tues", "tuesday"],
                "Wed": ["wed", "wednesday"],
                "Thu": ["thu", "thur", "thursday"],
                "Fri": ["fri", "friday"],
                "Sat": ["sat", "saturday"],
                "Sun": ["sun", "sunday"],
            }
            words = set(blob.split())
            for day in constraints["fixed_days"]:
                aliases = day_aliases.get(day, [day.lower()])
                if not any(alias in words for alias in aliases):
                    errors.append(f"Fixed rest day missing in phase_guardrails: {day}")

        load_guardrails = self._as_map(data.get("load_guardrails"))
        for entry in self._as_list(load_guardrails.get("weekly_kj_bands")):
            if not isinstance(entry, dict):
                continue
            week = str(entry.get("week") or "").strip() or "unknown"
            band = self._as_map(entry.get("band"))
            min_val = band.get("min")
            max_val = band.get("max")
            feasible_max = self._extract_feasible_max_from_notes(band.get("notes"))
            if feasible_max is None:
                continue
            if isinstance(min_val, (int, float)) and float(min_val) > feasible_max:
                errors.append(
                    f"weekly_kj_bands[{week}] min {float(min_val):g} exceeds explicit feasible max {feasible_max:g} stated in notes."
                )
            if isinstance(max_val, (int, float)) and float(max_val) > feasible_max:
                errors.append(
                    f"weekly_kj_bands[{week}] max {float(max_val):g} exceeds explicit feasible max {feasible_max:g} stated in notes."
                )

        if errors:
            raise SchemaValidationError("Season plan constraint propagation failed", errors)

    def _enforce_phase_structure_constraints(
        self,
        document: JsonMap,
        season_plan: JsonMap,
    ) -> None:
        """Ensure season plan constraints and load ranges are propagated into execution arch."""
        meta = self._as_map(document.get("meta"))
        expected_range = meta.get("iso_week_range")
        try:
            phase_guardrails, bg_version_key = self._load_phase_guardrails_for_range(expected_range)
        except MissingDependenciesError as exc:
            raise SchemaValidationError("Season plan constraint propagation failed", [str(exc)]) from exc
        normalize_phase_structure_document(
            document,
            season_plan_document=season_plan,
            phase_guardrails_document=phase_guardrails,
            phase_guardrails_version_key=bg_version_key,
        )

        constraints = self._season_constraints(season_plan)
        data = self._as_map(document.get("data"))
        season_phase = self._season_phase_for_range(season_plan, meta.get("iso_week_range"))
        upstream_intent = self._as_map(data.get("upstream_intent"))
        upstream_constraints = self._as_list(upstream_intent.get("constraints"))
        upstream_blob = self._normalize_text(" ".join(str(item) for item in upstream_constraints))
        upstream_items = self._normalized_string_list(upstream_constraints)
        errors: list[str] = []
        expected_phase_intent = str(season_phase.get("phase_intent") or "").strip()
        observed_phase_intent = str(upstream_intent.get("phase_intent") or "").strip()
        if expected_phase_intent and observed_phase_intent != expected_phase_intent:
            errors.append(
                f"upstream_intent.phase_intent must match season plan phase_intent '{expected_phase_intent}'."
            )
        expected_build_subtype = season_phase.get("build_subtype")
        observed_build_subtype = upstream_intent.get("build_subtype")
        if expected_build_subtype != observed_build_subtype:
            errors.append(
                f"upstream_intent.build_subtype must match season plan build_subtype {expected_build_subtype!r}."
            )
        expected_contract = self._as_map(self._as_map(season_plan.get("data")).get("selected_scenario_contract"))
        observed_contract = self._as_map(data.get("inherited_scenario_contract"))
        if expected_contract and not observed_contract:
            errors.append("phase_structure.data.inherited_scenario_contract must be present and inherited from season plan.")
        for field, expected in expected_contract.items():
            if field in observed_contract and observed_contract.get(field) != expected:
                errors.append(
                    f"phase_structure.data.inherited_scenario_contract.{field} must match season plan selected_scenario_contract."
                )

        errors.extend(
            f"Season plan availability_assumptions missing in upstream_intent.constraints: {item}"
            for item in constraints["availability"]
            if not self._contains_normalized_item(upstream_items, item)
        )
        errors.extend(
            f"Season plan risk_constraints missing in upstream_intent.constraints: {item}"
            for item in constraints["risks"]
            if not self._contains_normalized_item(upstream_items, item)
        )
        errors.extend(
            f"Season plan recovery_notes missing in upstream_intent.constraints: {item}"
            for item in constraints["recovery_notes"]
            if not self._structure_constraint_has_recovery_note(upstream_items, upstream_blob, item)
        )
        errors.extend(
            f"Season plan planned_event_windows missing in upstream_intent.constraints: {item}"
            for item in constraints["planned"]
            if not self._structure_constraint_has_event_window(upstream_blob, item)
        )

        fixed_days = constraints["fixed_days"]
        execution_principles = self._as_map(data.get("execution_principles"))
        recovery_protection = self._as_map(execution_principles.get("recovery_protection"))
        exec_days = self._as_string_list(recovery_protection.get("fixed_non_training_days"))
        if fixed_days and sorted(exec_days) != sorted(fixed_days):
            errors.append(
                "fixed_non_training_days must match season plan fixed_rest_days."
            )

        load_ranges = self._as_map(data.get("load_ranges"))
        phase_guardrails_data = self._as_map(phase_guardrails.get("data"))
        bg_guardrails = self._as_map(phase_guardrails_data.get("load_guardrails"))
        for label in ("weekly_kj_bands",):
            expected = self._as_list(bg_guardrails.get(label))
            actual = self._as_list(load_ranges.get(label))
            expected_map = {
                entry.get("week"): entry.get("band")
                for entry in expected
                if isinstance(entry, dict)
            }
            actual_map = {
                entry.get("week"): entry.get("band")
                for entry in actual
                if isinstance(entry, dict)
            }
            if expected_map != actual_map:
                errors.append(f"load_ranges.{label} must match phase_guardrails.{label}.")

        expected_source = (
            f"{ARTIFACT_PATHS[ArtifactType.PHASE_GUARDRAILS].filename_prefix}_{bg_version_key}.json"
        )
        source = load_ranges.get("source")
        if source != expected_source:
            errors.append(f"load_ranges.source must be '{expected_source}'.")

        if errors:
            raise SchemaValidationError("Season plan constraint propagation failed", errors)

    def _enforce_phase_preview_constraints(
        self,
        document: JsonMap,
    ) -> None:
        """Ensure execution preview stays derived from stored phase structure."""
        meta = self._as_map(document.get("meta"))
        expected_range = meta.get("iso_week_range")
        try:
            phase_structure, arch_version_key = self._load_phase_structure_for_range(expected_range)
        except MissingDependenciesError as exc:
            raise SchemaValidationError("Preview traceability failed", [str(exc)]) from exc

        expected_arch = (
            f"{ARTIFACT_PATHS[ArtifactType.PHASE_STRUCTURE].filename_prefix}_"
            f"{arch_version_key}.json"
        )
        normalize_phase_preview_document(
            document,
            phase_structure_document=phase_structure,
            phase_structure_version_key=arch_version_key,
        )
        data = self._as_map(document.get("data"))
        traceability = self._as_map(data.get("traceability"))
        derived_from = self._as_string_list(traceability.get("derived_from"))
        errors: list[str] = []
        if expected_arch not in derived_from:
            errors.append(f"data.traceability.derived_from must include '{expected_arch}'.")

        structure_data = self._as_map(self._as_map(phase_structure).get("data"))
        structure_upstream_intent = self._as_map(structure_data.get("upstream_intent"))
        expected_phase_intent = str(structure_upstream_intent.get("phase_intent") or "").strip()
        observed_phase_intent = str(self._as_map(data.get("phase_intent_summary")).get("phase_intent") or "").strip()
        if expected_phase_intent and observed_phase_intent != expected_phase_intent:
            errors.append(
                f"phase_preview.phase_intent_summary.phase_intent must match phase_structure upstream intent '{expected_phase_intent}'."
            )
        expected_build_subtype = structure_upstream_intent.get("build_subtype")
        observed_build_subtype = self._as_map(data.get("phase_intent_summary")).get("build_subtype")
        if expected_build_subtype != observed_build_subtype:
            errors.append(
                f"phase_preview.phase_intent_summary.build_subtype must match phase_structure upstream intent build_subtype {expected_build_subtype!r}."
            )
        structural_elements = self._as_map(structure_data.get("structural_phase_elements"))
        execution_principles = self._as_map(structure_data.get("execution_principles"))
        load_intensity = self._as_map(execution_principles.get("load_intensity_handling"))
        recovery_protection = self._as_map(execution_principles.get("recovery_protection"))
        allowed_day_roles = set(self._as_string_list(structural_elements.get("allowed_day_roles")))
        allowed_intensity_domains = set(
            self._as_string_list(structural_elements.get("allowed_intensity_domains"))
        )
        allowed_load_modalities = set(
            self._as_string_list(structural_elements.get("allowed_load_modalities"))
        )
        forbidden_intensity_domains = set(
            self._as_string_list(load_intensity.get("forbidden_intensity_domains"))
        )
        fixed_non_training_days = set(
            self._as_string_list(recovery_protection.get("fixed_non_training_days"))
        )
        max_quality_days_per_week = load_intensity.get("max_quality_days_per_week")
        quality_cap = (
            int(max_quality_days_per_week)
            if isinstance(max_quality_days_per_week, int)
            else None
        )

        structure_weeks = []
        week_skeleton_logic = self._as_map(structure_data.get("week_skeleton_logic"))
        week_roles = self._as_map(week_skeleton_logic.get("week_roles"))
        for entry in self._as_list(week_roles.get("week_roles")):
            if not isinstance(entry, dict):
                continue
            week_key = str(entry.get("week") or "").strip()
            if week_key:
                structure_weeks.append(week_key)
        expected_weeks = structure_weeks or self._weeks_in_range(expected_range)

        preview_weeks = []
        weekly_agenda_preview = self._as_list(data.get("weekly_agenda_preview"))
        for week_entry in weekly_agenda_preview:
            if not isinstance(week_entry, dict):
                continue
            week_key = str(week_entry.get("week") or "").strip()
            if week_key:
                preview_weeks.append(week_key)
        if expected_weeks and preview_weeks != expected_weeks:
            errors.append(
                "weekly_agenda_preview weeks must match stored phase_structure coverage exactly; "
                f"expected={expected_weeks}, observed={preview_weeks}."
            )

        for week_entry in weekly_agenda_preview:
            if not isinstance(week_entry, dict):
                continue
            week_key = str(week_entry.get("week") or "").strip() or "unknown-week"
            days = self._as_list(week_entry.get("days"))
            observed_days = [str(self._as_map(day).get("day_of_week") or "").strip() for day in days]
            if sorted(observed_days) != sorted(_WEEKDAY_ORDER):
                errors.append(
                    f"{week_key} weekly_agenda_preview must include each weekday exactly once; "
                    f"observed={observed_days}."
                )
            quality_days = 0
            for day in days:
                day_map = self._as_map(day)
                day_of_week = str(day_map.get("day_of_week") or "").strip()
                day_role = str(day_map.get("day_role") or "").strip()
                intensity_domain = str(day_map.get("intensity_domain") or "").strip()
                load_modality = str(day_map.get("load_modality") or "").strip()
                day_label = f"{week_key} {day_of_week or '?'}"

                if allowed_day_roles and day_role not in allowed_day_roles:
                    errors.append(
                        f"{day_label} day_role '{day_role}' is outside "
                        "phase_structure.structural_phase_elements.allowed_day_roles."
                    )
                if allowed_intensity_domains and intensity_domain not in allowed_intensity_domains:
                    errors.append(
                        f"{day_label} intensity_domain '{intensity_domain}' is outside "
                        "phase_structure.structural_phase_elements.allowed_intensity_domains."
                    )
                if forbidden_intensity_domains and intensity_domain in forbidden_intensity_domains:
                    errors.append(
                        f"{day_label} intensity_domain '{intensity_domain}' is forbidden by "
                        "phase_structure.execution_principles.load_intensity_handling.forbidden_intensity_domains."
                    )
                if allowed_load_modalities and load_modality not in allowed_load_modalities:
                    errors.append(
                        f"{day_label} load_modality '{load_modality}' is outside "
                        "phase_structure.structural_phase_elements.allowed_load_modalities."
                    )
                if day_role == "QUALITY":
                    quality_days += 1
                if day_of_week in fixed_non_training_days:
                    if day_role not in _NON_TRAINING_DAY_ROLES:
                        errors.append(
                            f"{day_label} must remain non-training because it is a fixed_non_training_day."
                        )
                    if intensity_domain != "NONE":
                        errors.append(
                            f"{day_label} must use intensity_domain 'NONE' because it is a fixed_non_training_day."
                        )
                    if load_modality != "NONE":
                        errors.append(
                            f"{day_label} must use load_modality 'NONE' because it is a fixed_non_training_day."
                        )
            if quality_cap is not None and quality_days > quality_cap:
                errors.append(
                    f"{week_key} preview exceeds max_quality_days_per_week "
                    f"({quality_days} > {quality_cap})."
                )

        if errors:
            raise SchemaValidationError("Preview derivation failed", errors)

    def _load_latest_optional(self, artifact_type: ArtifactType) -> JsonMap:
        """Return a latest workspace document when it is available and object-shaped."""

        try:
            if not self.store.latest_exists(self.athlete_id, artifact_type):
                return {}
            loaded = self.store.load_latest(self.athlete_id, artifact_type)
        except Exception:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _season_contract_contexts(self, document: JsonMap) -> tuple[JsonMap, JsonMap]:
        """Build selected-scenario phase slot and load contexts for a Season Plan write."""

        scenarios = self._load_latest_optional(ArtifactType.SEASON_SCENARIOS)
        selection = self._load_latest_optional(ArtifactType.SEASON_SCENARIO_SELECTION)
        if not scenarios or not selection:
            return {}, {}
        target_week = parse_iso_week(self._as_map(document.get("meta")).get("iso_week"))
        if target_week is None:
            range_spec = envelope_week_range(document)
            target_week = range_spec.start if range_spec else None
        if target_week is None:
            return {}, {}
        selected = build_selected_scenario_structure_block(
            season_scenarios_payload=scenarios,
            selection_payload=selection,
            selected_scenario_id=None,
        ).payload
        if not selected:
            return {}, {}
        selected_contract = build_selected_scenario_contract_block(
            season_scenarios_payload=scenarios,
            selection_payload=selection,
            selected_scenario_id=None,
        ).payload
        if not selected_contract:
            return {}, {}
        phase_slots = build_season_phase_slot_block(
            selected_structure_context=selected,
            target_week=target_week,
        ).payload
        if not phase_slots:
            return phase_slots, {}
        phase_load = build_season_phase_load_block(
            phase_slot_context=phase_slots,
            target_week=target_week,
            athlete_profile_payload=self._load_latest_optional(ArtifactType.ATHLETE_PROFILE),
            availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
            logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
            planning_events_payload=self._load_latest_optional(ArtifactType.PLANNING_EVENTS),
            zone_model_payload=self._load_latest_optional(ArtifactType.ZONE_MODEL),
            selected_structure_context=selected,
            selected_scenario_contract=selected_contract,
            wellness_payload=self._load_latest_optional(ArtifactType.WELLNESS),
            kpi_profile_payload=self._load_latest_optional(ArtifactType.KPI_PROFILE),
            kpi_rate_band=selected_kpi_rate_band_from_selection(selection),
        ).payload
        return phase_slots, phase_load

    def _phase_slot_context_for_store(self, document: JsonMap) -> JsonMap:
        """Build deterministic phase slot context when scenario authority is available."""

        scenarios = self._load_latest_optional(ArtifactType.SEASON_SCENARIOS)
        selection = self._load_latest_optional(ArtifactType.SEASON_SCENARIO_SELECTION)
        if not scenarios or not selection:
            return {}
        target_week = None
        range_spec = envelope_week_range(document)
        if range_spec:
            target_week = range_spec.start
        if target_week is None:
            target_week = parse_iso_week(self._as_map(document.get("meta")).get("iso_week"))
        if target_week is None:
            return {}
        selected = build_selected_scenario_structure_block(
            season_scenarios_payload=scenarios,
            selection_payload=selection,
            selected_scenario_id=None,
        ).payload
        if not selected:
            return {}
        return build_season_phase_slot_block(
            selected_structure_context=selected,
            target_week=target_week,
        ).payload

    def _load_capacity_context_for_store(self) -> JsonMap:
        """Build deterministic load-capacity context from available workspace inputs."""

        try:
            return build_load_capacity_block(
                athlete_profile_payload=self._load_latest_optional(ArtifactType.ATHLETE_PROFILE),
                availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
                logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
                zone_model_payload=self._load_latest_optional(ArtifactType.ZONE_MODEL),
                wellness_payload=self._load_latest_optional(ArtifactType.WELLNESS),
                kpi_profile_payload=self._load_latest_optional(ArtifactType.KPI_PROFILE),
                kpi_rate_band=selected_kpi_rate_band_from_selection(
                    self._load_latest_optional(ArtifactType.SEASON_SCENARIO_SELECTION)
                ),
            ).payload
        except TypeError:
            self.logger.exception(
                "Failed to build store load-capacity context due to invalid builder arguments."
            )
        except Exception:
            self.logger.exception(
                "Failed to build store load-capacity context from workspace inputs."
            )
            return {}
        return {}

    def _load_phase_capacity_context_for_store(
        self,
        *,
        target_week,
        phase_range,
        season_plan: JsonMap,
        phase_info,
        phase_slots: JsonMap,
    ) -> JsonMap:
        """Build phase-scoped deterministic load-capacity context for phase-store validation."""

        phase_execution_seed = build_phase_execution_context(
            target_week=target_week,
            phase_info=phase_info,
            phase_range=phase_range,
            season_plan_payload=season_plan,
            phase_slot_context=phase_slots,
            availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
            logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
            planning_events_payload=self._load_latest_optional(ArtifactType.PLANNING_EVENTS),
            load_capacity_context={},
        )
        week_role_raw = self._as_map(phase_execution_seed.get("week_role_by_iso_week"))
        week_role_by_week = {
            str(key): str(value)
            for key, value in week_role_raw.items()
            if str(key).strip() and str(value).strip()
        }
        phase_role = str(phase_execution_seed.get("phase_role") or "").strip()
        phase_role_by_week = {
            week_key: phase_role
            for week_key in week_role_by_week
            if phase_role
        }
        try:
            return build_load_capacity_block(
                target_week=target_week,
                phase_range=phase_range,
                athlete_profile_payload=self._load_latest_optional(ArtifactType.ATHLETE_PROFILE),
                availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
                logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
                zone_model_payload=self._load_latest_optional(ArtifactType.ZONE_MODEL),
                season_plan_payload=season_plan,
                wellness_payload=self._load_latest_optional(ArtifactType.WELLNESS),
                kpi_profile_payload=self._load_latest_optional(ArtifactType.KPI_PROFILE),
                kpi_rate_band=selected_kpi_rate_band_from_selection(
                    self._load_latest_optional(ArtifactType.SEASON_SCENARIO_SELECTION)
                ),
                week_role_by_week=week_role_by_week,
                phase_role_by_week=phase_role_by_week,
                scenario_cadence=phase_execution_seed.get("scenario_cadence"),
            ).payload
        except TypeError:
            self.logger.exception(
                "Failed to build phase-scoped load-capacity context due to invalid builder arguments "
                "for phase_range=%s target_week=%s week_roles=%s.",
                getattr(phase_range, "range_key", phase_range),
                target_week,
                sorted(week_role_by_week),
            )
        except Exception:
            self.logger.exception(
                "Failed to build phase-scoped load-capacity context for phase_range=%s target_week=%s.",
                getattr(phase_range, "range_key", phase_range),
                target_week,
            )
            return {}
        return {}

    def _enforce_store_contract_constraints(
        self,
        target: ArtifactType,
        document: JsonMap,
    ) -> None:
        """Apply final deterministic planning-contract guards when context is loadable."""

        errors: list[str] = []
        if target == ArtifactType.SEASON_PLAN:
            phase_slots, phase_load = self._season_contract_contexts(document)
            if phase_slots:
                errors.extend(
                    blocking_messages(
                        validate_season_plan_against_phase_slots(
                            season_plan_payload=document,
                            phase_slot_context=phase_slots,
                        )
                    )
                )
            if phase_load:
                errors.extend(
                    blocking_messages(
                        validate_season_plan_against_phase_load_context(
                            season_plan_payload=document,
                            season_phase_load_context=phase_load,
                        )
                    )
                )
        elif target == ArtifactType.PHASE_STRUCTURE:
            range_spec = envelope_week_range(document)
            season_plan = self._load_latest_optional(ArtifactType.SEASON_PLAN)
            phase_slots = self._phase_slot_context_for_store(document)
            if range_spec and season_plan and phase_slots:
                phase_info = resolve_season_plan_phase_info(season_plan, range_spec.start)
                if phase_info:
                    load_capacity_context = self._load_phase_capacity_context_for_store(
                        target_week=range_spec.start,
                        phase_range=range_spec,
                        season_plan=season_plan,
                        phase_info=phase_info,
                        phase_slots=phase_slots,
                    )
                    load_capacity_s5_bands = self._as_list(load_capacity_context.get("s5_bands"))
                    self.logger.info(
                        "Phase structure validation context phase_range=%s phase_slots=%s s5_band_weeks=%s week_roles=%s",
                        range_spec.range_key,
                        bool(phase_slots),
                        [
                            str(self._as_map(item).get("week"))
                            for item in load_capacity_s5_bands
                            if str(self._as_map(item).get("week")).strip()
                        ],
                        sorted(
                            str(key)
                            for key in self._as_map(
                                build_phase_execution_context(
                                    target_week=range_spec.start,
                                    phase_info=phase_info,
                                    phase_range=range_spec,
                                    season_plan_payload=season_plan,
                                    phase_slot_context=phase_slots,
                                    availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
                                    logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
                                    planning_events_payload=self._load_latest_optional(ArtifactType.PLANNING_EVENTS),
                                    load_capacity_context={},
                                ).get("week_role_by_iso_week")
                            )
                        ),
                    )
                    context = build_phase_execution_context(
                        target_week=range_spec.start,
                        phase_info=phase_info,
                        phase_range=range_spec,
                        season_plan_payload=season_plan,
                        phase_slot_context=phase_slots,
                        availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
                        logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
                        planning_events_payload=self._load_latest_optional(ArtifactType.PLANNING_EVENTS),
                        load_capacity_context=load_capacity_context,
                    )
                    errors.extend(
                        blocking_messages(
                            validate_phase_against_execution_context(
                                phase_payload=document,
                                phase_execution_context=context,
                            )
                        )
                    )
        elif target == ArtifactType.WEEK_PLAN:
            week = envelope_week(document)
            season_plan = self._load_latest_optional(ArtifactType.SEASON_PLAN)
            phase_structure = self._load_latest_optional(ArtifactType.PHASE_STRUCTURE)
            phase_guardrails = self._load_latest_optional(ArtifactType.PHASE_GUARDRAILS)
            if week and season_plan and phase_structure and phase_guardrails:
                phase_info = resolve_season_plan_phase_info(season_plan, week)
                if phase_info:
                    context = build_week_calendar_context(
                        target_week=week,
                        phase_info=phase_info,
                        phase_range=phase_info.phase_range,
                        availability_payload=self._load_latest_optional(ArtifactType.AVAILABILITY),
                        logistics_payload=self._load_latest_optional(ArtifactType.LOGISTICS),
                        planning_events_payload=self._load_latest_optional(ArtifactType.PLANNING_EVENTS),
                        phase_guardrails_payload=phase_guardrails,
                        phase_structure_payload=phase_structure,
                        load_capacity_context=self._load_capacity_context_for_store(),
                    )
                    errors.extend(
                        blocking_messages(
                            validate_week_plan_against_week_context(
                                week_plan_payload=document,
                                week_calendar_context=context,
                            )
                        )
                    )
        if errors:
            raise SchemaValidationError("Planning contract guard failed", errors)

    def _ensure_phase_range_matches_plan(
        self,
        document: JsonMap,
        season_plan_doc: JsonMap,
    ) -> None:
        """Normalize phase iso_week_range to the covering season plan phase."""
        range_spec = envelope_week_range(document)
        if not range_spec:
            return
        phase_info = resolve_season_plan_phase_info(season_plan_doc, range_spec.start)
        if not phase_info:
            raise SchemaValidationError(
                "Season plan phase mismatch",
                [f"No season plan phase covers phase range {range_spec.key}."],
            )
        if phase_info.phase_range.key != range_spec.key:
            self.logger.warning(
                "Normalized phase iso_week_range from %s to season plan phase %s (%s).",
                range_spec.key,
                phase_info.phase_range.key,
                phase_info.phase_id or phase_info.phase_name or "unknown",
            )
            meta = document.setdefault("meta", {})
            if not isinstance(meta, dict):
                meta = {}
                document["meta"] = meta
            meta["iso_week_range"] = phase_info.phase_range.key

    def _round_numeric_fields(
        self,
        value: object,
        schema_node: JsonMap | None,
        root_schema: JsonMap,
        path: list[str] | None = None,
    ) -> object:
        """Apply consistent rounding to numeric values using schema hints when possible."""
        if path is None:
            path = []
        schema_node = self._resolve_rounding_schema(schema_node, root_schema)
        joined = "_".join(path).lower()
        types = self._schema_types(schema_node)

        if isinstance(value, dict):
            rounded: JsonMap = {}
            for k, v in value.items():
                child_schema = self._child_rounding_schema(schema_node, k)
                rounded[k] = self._round_numeric_fields(
                    v,
                    child_schema,
                    root_schema,
                    path + [str(k)],
                )
            return rounded

        if isinstance(value, list):
            items_schema = self._list_item_rounding_schema(schema_node)
            return [
                self._round_numeric_fields(item, items_schema, root_schema, path)
                for item in value
            ]

        if isinstance(value, (int, float)):
            if "integer" in types and "number" not in types:
                return round(float(value))
            if "integer" in types and "number" in types and abs(float(value) - round(float(value))) < INTEGER_ROUNDING_EPSILON:
                return round(float(value))
            if "number" in types or not types:
                decimals = self._rounding_decimals(joined)
                if decimals == 0:
                    return round(float(value))
                return round(float(value), decimals)
        return value

    def _resolve_rounding_schema(
        self,
        schema_node: JsonMap | None,
        root_schema: JsonMap,
    ) -> JsonMap | None:
        """Resolve a local schema node, following local ``$ref`` targets when present."""
        if not isinstance(schema_node, dict):
            return None
        ref = schema_node.get("$ref")
        if not ref or not isinstance(ref, str) or not ref.startswith("#/"):
            return schema_node
        parts = ref.lstrip("#/").split("/")
        current: object = root_schema
        for part in parts:
            if not isinstance(current, dict):
                return schema_node
            current = current.get(part)
            if current is None:
                return schema_node
        if isinstance(current, dict):
            return current
        return schema_node

    @staticmethod
    def _schema_types(schema_node: JsonMap | None) -> list[str]:
        """Extract normalized ``type`` entries from a schema node."""
        node_type = schema_node.get("type") if isinstance(schema_node, dict) else None
        if isinstance(node_type, list):
            return [str(entry) for entry in node_type]
        if isinstance(node_type, str):
            return [node_type]
        return []

    @staticmethod
    def _child_rounding_schema(schema_node: JsonMap | None, key: str) -> object:
        """Return the schema node for a child mapping entry when available."""
        if not isinstance(schema_node, dict):
            return None
        props = schema_node.get("properties")
        if isinstance(props, dict) and key in props:
            return props[key]
        additional = schema_node.get("additionalProperties")
        if isinstance(additional, dict):
            return additional
        return None

    @staticmethod
    def _list_item_rounding_schema(schema_node: JsonMap | None) -> JsonMap | None:
        """Return the schema node for list items when available."""
        if not isinstance(schema_node, dict):
            return None
        raw_items_schema = schema_node.get("items")
        return raw_items_schema if isinstance(raw_items_schema, dict) else None

    def _apply_rounding(self, document: object, schema: JsonMap) -> object:
        """Round numeric values on the document before validation/storage."""
        return self._round_numeric_fields(document, schema, schema, [])

    @staticmethod
    def _rounding_decimals(joined: str) -> int:
        """Resolve decimal precision heuristics for numeric fields from their normalized path."""
        if (
            "hours_typical" in joined
            or "hours_max" in joined
            or "weekly_hours" in joined
            or "kg" in joined
        ):
            return 1
        if (
            "seconds" in joined
            or joined.endswith("_seconds")
            or joined.endswith("_sec")
            or "bpm" in joined
            or "mm_hg" in joined
            or "mmhg" in joined
            or "hrv_ms" in joined
            or joined.endswith("_ms")
            or "kj" in joined
            or joined.endswith("_kj")
            or joined.endswith("kj")
            or "watts" in joined
            or joined.endswith("_w")
            or joined.endswith("w")
            or joined.endswith("_min")
            or joined.endswith("_mins")
            or "minutes" in joined
        ):
            return 0
        if (
            "if_adj" in joined
            or "kj_per_kg" in joined
            or "w_per_kg" in joined
            or "per_kg" in joined
            or "ratio" in joined
            or "index" in joined
            or "intensity_factor" in joined
            or joined.endswith("_if")
        ):
            return 2
        if "percent" in joined or "pct" in joined:
            return 1
        return 2

    def guard_put_validated(
        self,
        *,
        output_spec: OutputSpec,
        document: object,
        run_id: str,
        producer_agent: str,
        update_latest: bool = True,
    ) -> StoreResult:
        """Validate, derive version key, and persist a document with guards."""
        target = output_spec.artifact_type
        raw_document = document
        try:
            self._check_dependencies(target)

            schema = self.schemas.get_schema(output_spec.schema_file)
            validator = self.schemas.validator_for(output_spec.schema_file)
            document = canonicalize_artifact_envelope_meta(
                document,
                artifact_type=target,
                schema=schema,
                run_id=run_id,
            )
            raw_document = document
            self._log_store_attempt(
                raw_document,
                output_spec=output_spec,
                run_id=run_id,
                producer_agent=producer_agent,
            )
            document, version_key = self._validate_and_version_document(
                document=document,
                schema=schema,
                validator=validator,
                target=target,
            )
            if target == ArtifactType.INTERVALS_WORKOUTS:
                version_key = self._derive_intervals_version_key(document)
            version_key = normalize_version_key(version_key, artifact_type=target)

            self._apply_phase_store_constraints(target, cast(JsonMap, document))
            self._enforce_store_contract_constraints(target, cast(JsonMap, document))
            if target == ArtifactType.WEEK_PLAN:
                document = self._enforce_week_plan_exportability(cast(JsonMap, document))

            path = self.store.save_document(
                athlete_id=self.athlete_id,
                artifact_type=target,
                version_key=version_key,
                document=document,
                producer_agent=producer_agent,
                run_id=run_id,
                update_latest=update_latest,
            )

            self.logger.info(
                "Stored artifact type=%s version_key=%s path=%s run_id=%s",
                target.value,
                version_key,
                path,
                run_id,
            )
            try:
                render_sidecar(Path(path))
            except Exception:
                self.logger.exception("Auto-render failed for %s", path)

            return {
                "ok": True,
                "artifact_type": target.value,
                "version_key": version_key,
                "path": str(path),
                "run_id": run_id,
                "producer_agent": producer_agent,
            }
        except Exception as exc:
            self._log_failed_payload(
                raw_document,
                output_spec=output_spec,
                run_id=run_id,
                producer_agent=producer_agent,
                error=exc,
            )
            raise

    def _validate_and_version_document(
        self,
        *,
        document: object,
        schema: JsonMap,
        validator: object,
        target: ArtifactType,
    ) -> tuple[object, str]:
        """Apply rounding, schema validation, and base version derivation."""
        if is_envelope_schema(schema):
            if not isinstance(document, dict) or "meta" not in document or "data" not in document:
                raise ValueError("Envelope artefact must be an object with meta and data")
            if isinstance(document.get("meta"), dict) and "data_confidence" not in document["meta"]:
                document["meta"]["data_confidence"] = "UNKNOWN"
            document = self._apply_rounding(document, schema)
            envelope_document = cast(JsonMap, document)
            validate_or_raise(validator, envelope_document)
            version_key = derive_version_key_from_envelope(envelope_document, target)
            return document, version_key
        document = self._apply_rounding(document, schema)
        validate_or_raise(validator, cast(JsonMap, document))
        return document, "raw"

    def _apply_phase_store_constraints(self, target: ArtifactType, document: JsonMap) -> None:
        """Apply phase-specific store guards after validation and versioning."""
        phase_targets = {
            ArtifactType.PHASE_GUARDRAILS,
            ArtifactType.PHASE_STRUCTURE,
            ArtifactType.PHASE_PREVIEW,
            ArtifactType.PHASE_FEED_FORWARD,
        }
        season_plan_doc: JsonMap | None = None
        if target in phase_targets:
            season_plan_doc = self._as_map(
                self.store.load_latest(self.athlete_id, ArtifactType.SEASON_PLAN)
            )
            self._ensure_phase_range_matches_plan(document, season_plan_doc)
        if target in {ArtifactType.PHASE_GUARDRAILS, ArtifactType.PHASE_STRUCTURE}:
            if season_plan_doc is None:
                season_plan_doc = self._as_map(
                    self.store.load_latest(self.athlete_id, ArtifactType.SEASON_PLAN)
                )
            if target == ArtifactType.PHASE_GUARDRAILS:
                normalize_phase_guardrails_document(
                    document,
                    season_plan_document=season_plan_doc,
                )
                self._enforce_phase_guardrails_constraints(document, season_plan_doc)
            else:
                self._enforce_phase_structure_constraints(document, season_plan_doc)
            return
        if target == ArtifactType.PHASE_PREVIEW:
            self._enforce_phase_preview_constraints(document)

    def _enforce_week_plan_exportability(self, document: JsonMap) -> JsonMap:
        """Normalize and validate WEEK_PLAN workout definitions before export/store."""
        data = self._as_map(document.get("data"))
        workouts = self._as_list(data.get("workouts"))
        try:
            data["workouts"] = [
                canonicalize_workout_entry(self._as_map(workout))
                if self._as_map(workout)
                else workout
                for workout in workouts
            ]
        except ValueError as exc:
            raise SchemaValidationError("Week plan exportability failed", [str(exc)]) from exc
        document["data"] = data
        document = normalize_week_plan_consistency(document)
        issues = collect_week_plan_export_issues(document)
        if not issues:
            return document
        raise SchemaValidationError(
            "Week plan exportability failed",
            [issue.format() for issue in issues],
        )

    def _format_payload(self, document: object) -> str:
        """Return a formatted payload string for logging."""
        try:
            return json.dumps(document, ensure_ascii=False, indent=2)
        except TypeError:
            return repr(document)

    def _derive_intervals_version_key(self, document: object) -> str:
        """Derive ISO week version key from Intervals workouts payload."""
        if not isinstance(document, list):
            return "raw"
        dates = []
        for item in document:
            if not isinstance(item, dict):
                continue
            start = item.get("start_date_local")
            if not isinstance(start, str):
                continue
            date_str = start.split("T")[0]
            try:
                dt = datetime.fromisoformat(date_str)
            except ValueError:
                continue
            dates.append(dt.date())
        if not dates:
            return "raw"
        iso = min(dates).isocalendar()
        week_key = f"{iso.year:04d}-{iso.week:02d}"
        return normalize_week_version_key(week_key, artifact_type=ArtifactType.INTERVALS_WORKOUTS)

    def _log_store_attempt(
        self,
        document: object,
        *,
        output_spec: OutputSpec,
        run_id: str,
        producer_agent: str,
    ) -> None:
        """Log store attempts (payload only at DEBUG)."""
        if not self.logger.isEnabledFor(logging.DEBUG):
            self.logger.info(
                "Store attempt artifact=%s run_id=%s producer=%s",
                output_spec.artifact_type.value,
                run_id,
                producer_agent,
            )
            return
        payload_text = self._format_payload(document)
        self.logger.debug(
            "Store attempt artifact=%s run_id=%s producer=%s. Payload:\n%s",
            output_spec.artifact_type.value,
            run_id,
            producer_agent,
            payload_text,
        )

    def _log_failed_payload(
        self,
        document: object,
        *,
        output_spec: OutputSpec,
        run_id: str,
        producer_agent: str,
        error: Exception | None = None,
    ) -> None:
        """Log the raw payload for failed store attempts."""
        payload_text = self._format_payload(document)
        reason = str(error) if error is not None else "unknown"
        if isinstance(error, SchemaValidationError) and error.errors:
            reason = "; ".join(error.errors[:12])
            if len(error.errors) > 12:
                reason = f"{reason}; ... and {len(error.errors) - 12} more"
        self.logger.error(
            "Store failed for artifact=%s run_id=%s producer=%s reason=%s. Payload:\n%s",
            output_spec.artifact_type.value,
            run_id,
            producer_agent,
            reason,
            payload_text,
        )
