"""Guarded, validated writes to the local workspace."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from rps.agents.tasks import OutputSpec
from rps.rendering.auto_render import render_sidecar
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import envelope_week_range
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
        match = re.search(r"(\d{4}-\d{2}-\d{2})\s*\((A|B|C)\)", value, re.IGNORECASE)
        if not match:
            return None
        return match.group(1), match.group(2).upper()

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

    def _enforce_phase_guardrails_constraints(
        self,
        document: JsonMap,
        season_plan: JsonMap,
    ) -> None:
        """Ensure season plan constraints are propagated into phase guardrails."""
        constraints = self._season_constraints(season_plan)
        data = self._as_map(document.get("data"))
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

        for item in constraints["availability"]:
            if not self._contains_normalized_item(non_negotiables, item):
                errors.append(f"Season plan availability_assumptions missing in phase_guardrails: {item}")

        for item in constraints["risks"]:
            if not self._contains_normalized_item(key_risks, item):
                errors.append(f"Season plan risk_constraints missing in phase_guardrails: {item}")

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

        if errors:
            raise SchemaValidationError("Season plan constraint propagation failed", errors)

    def _enforce_phase_structure_constraints(
        self,
        document: JsonMap,
        season_plan: JsonMap,
    ) -> None:
        """Ensure season plan constraints and load ranges are propagated into execution arch."""
        constraints = self._season_constraints(season_plan)
        data = self._as_map(document.get("data"))
        upstream_intent = self._as_map(data.get("upstream_intent"))
        upstream_constraints = self._as_list(upstream_intent.get("constraints"))
        upstream_blob = self._normalize_text(" ".join(str(item) for item in upstream_constraints))
        upstream_items = self._normalized_string_list(upstream_constraints)
        errors: list[str] = []

        for item in constraints["availability"]:
            if not self._contains_normalized_item(upstream_items, item):
                errors.append(f"Season plan availability_assumptions missing in upstream_intent.constraints: {item}")

        for item in constraints["risks"]:
            if not self._contains_normalized_item(upstream_items, item):
                errors.append(f"Season plan risk_constraints missing in upstream_intent.constraints: {item}")

        for item in constraints["recovery_notes"]:
            if not self._contains_normalized_item(upstream_items, item):
                errors.append(f"Season plan recovery_notes missing in upstream_intent.constraints: {item}")

        for item in constraints["planned"]:
            if not self._structure_constraint_has_event_window(upstream_blob, item):
                errors.append(f"Season plan planned_event_windows missing in upstream_intent.constraints: {item}")

        fixed_days = constraints["fixed_days"]
        execution_principles = self._as_map(data.get("execution_principles"))
        recovery_protection = self._as_map(execution_principles.get("recovery_protection"))
        exec_days = self._as_string_list(recovery_protection.get("fixed_non_training_days"))
        if fixed_days and sorted(exec_days) != sorted(fixed_days):
            errors.append(
                "fixed_non_training_days must match season plan fixed_rest_days."
            )

        load_ranges = self._as_map(data.get("load_ranges"))
        meta = self._as_map(document.get("meta"))
        expected_range = meta.get("iso_week_range")
        try:
            phase_guardrails, bg_version_key = self._load_phase_guardrails_for_range(expected_range)
        except MissingDependenciesError as exc:
            raise SchemaValidationError("Season plan constraint propagation failed", [str(exc)]) from exc

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

    def _enforce_phase_preview_traceability(
        self,
        document: JsonMap,
    ) -> None:
        """Ensure execution preview references phase structure."""
        meta = self._as_map(document.get("meta"))
        expected_range = meta.get("iso_week_range")
        try:
            _, arch_version_key = self._load_phase_structure_for_range(expected_range)
        except MissingDependenciesError as exc:
            raise SchemaValidationError("Preview traceability failed", [str(exc)]) from exc

        expected_arch = (
            f"{ARTIFACT_PATHS[ArtifactType.PHASE_STRUCTURE].filename_prefix}_"
            f"{arch_version_key}.json"
        )
        data = self._as_map(document.get("data"))
        traceability = self._as_map(data.get("traceability"))
        derived_from = self._as_string_list(traceability.get("derived_from"))
        if expected_arch not in derived_from:
            raise SchemaValidationError(
                "Preview traceability failed",
                [f"data.traceability.derived_from must include '{expected_arch}'."],
            )

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

        def _joined_path(keys: list[str]) -> str:
            return "_".join(keys).lower()

        def _resolve_schema(node: JsonMap | None) -> JsonMap | None:
            if not isinstance(node, dict):
                return None
            ref = node.get("$ref")
            if not ref or not isinstance(ref, str) or not ref.startswith("#/"):
                return node
            parts = ref.lstrip("#/").split("/")
            cur: object = root_schema
            for part in parts:
                if not isinstance(cur, dict):
                    return node
                cur = cur.get(part)
                if cur is None:
                    return node
            if isinstance(cur, dict):
                return cur
            return node

        schema_node = _resolve_schema(schema_node)
        node_type = schema_node.get("type") if isinstance(schema_node, dict) else None
        types: list[str] = []
        if isinstance(node_type, list):
            types = [str(t) for t in node_type]
        elif isinstance(node_type, str):
            types = [node_type]

        if isinstance(value, dict):
            props = schema_node.get("properties") if isinstance(schema_node, dict) else None
            additional = schema_node.get("additionalProperties") if isinstance(schema_node, dict) else None
            rounded: JsonMap = {}
            for k, v in value.items():
                child_schema = None
                if isinstance(props, dict) and k in props:
                    child_schema = props[k]
                elif isinstance(additional, dict):
                    child_schema = additional
                rounded[k] = self._round_numeric_fields(
                    v,
                    child_schema,
                    root_schema,
                    path + [str(k)],
                )
            return rounded

        if isinstance(value, list):
            raw_items_schema = schema_node.get("items") if isinstance(schema_node, dict) else None
            items_schema = raw_items_schema if isinstance(raw_items_schema, dict) else None
            return [
                self._round_numeric_fields(item, items_schema, root_schema, path)
                for item in value
            ]

        if isinstance(value, (int, float)):
            joined = _joined_path(path)
            if "integer" in types and "number" not in types:
                return int(round(float(value)))
            if "integer" in types and "number" in types and abs(float(value) - round(float(value))) < 1e-9:
                return int(round(float(value)))
            if "number" in types or not types:
                decimals = self._rounding_decimals(joined)
                if decimals == 0:
                    return int(round(float(value)))
                return round(float(value), decimals)
        return value

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
            self._log_store_attempt(
                raw_document,
                output_spec=output_spec,
                run_id=run_id,
                producer_agent=producer_agent,
            )
            self._check_dependencies(target)

            schema = self.schemas.get_schema(output_spec.schema_file)
            validator = self.schemas.validator_for(output_spec.schema_file)

            if is_envelope_schema(schema):
                if not isinstance(document, dict) or "meta" not in document or "data" not in document:
                    raise ValueError("Envelope artefact must be an object with meta and data")
                if isinstance(document.get("meta"), dict) and "data_confidence" not in document["meta"]:
                    document["meta"]["data_confidence"] = "UNKNOWN"
                document = self._apply_rounding(document, schema)
                envelope_document = cast(JsonMap, document)
                validate_or_raise(validator, envelope_document)
                version_key = derive_version_key_from_envelope(envelope_document, target)
            else:
                document = self._apply_rounding(document, schema)
                validate_or_raise(validator, cast(JsonMap, document))
                version_key = "raw"
            if target == ArtifactType.INTERVALS_WORKOUTS:
                version_key = self._derive_intervals_version_key(document)
            version_key = normalize_version_key(version_key, artifact_type=target)

            season_plan_doc: JsonMap | None = None
            if target in (
                ArtifactType.PHASE_GUARDRAILS,
                ArtifactType.PHASE_STRUCTURE,
                ArtifactType.PHASE_PREVIEW,
                ArtifactType.PHASE_FEED_FORWARD,
            ):
                season_plan_doc = self._as_map(
                    self.store.load_latest(self.athlete_id, ArtifactType.SEASON_PLAN)
                )
                self._ensure_phase_range_matches_plan(cast(JsonMap, document), season_plan_doc)
            if target in (ArtifactType.PHASE_GUARDRAILS, ArtifactType.PHASE_STRUCTURE):
                if season_plan_doc is None:
                    season_plan_doc = self._as_map(
                        self.store.load_latest(
                            self.athlete_id, ArtifactType.SEASON_PLAN
                        )
                    )
                if target == ArtifactType.PHASE_GUARDRAILS:
                    self._enforce_phase_guardrails_constraints(cast(JsonMap, document), season_plan_doc)
                else:
                    self._enforce_phase_structure_constraints(cast(JsonMap, document), season_plan_doc)
            elif target == ArtifactType.PHASE_PREVIEW:
                self._enforce_phase_preview_traceability(cast(JsonMap, document))

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
        except Exception:
            self._log_failed_payload(
                raw_document,
                output_spec=output_spec,
                run_id=run_id,
                producer_agent=producer_agent,
            )
            raise

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
    ) -> None:
        """Log the raw payload for failed store attempts."""
        payload_text = self._format_payload(document)
        self.logger.error(
            "Store failed for artifact=%s run_id=%s producer=%s. Payload:\n%s",
            output_spec.artifact_type.value,
            run_id,
            producer_agent,
            payload_text,
        )
