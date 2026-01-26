"""Guarded, validated writes to the local workspace."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import json
from pathlib import Path
import re
from typing import Any

from rps.agents.tasks import OutputSpec
from rps.workspace.schema_registry import SchemaRegistry, SchemaValidationError, validate_or_raise
from rps.workspace.schema_utils import is_envelope_schema
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import envelope_week_range
from rps.workspace.paths import ARTIFACT_PATHS
from rps.workspace.types import ArtifactType
from rps.workspace.versioning import derive_version_key_from_envelope
from rps.workspace.local_store import LocalArtifactStore
from rps.rendering.auto_render import render_sidecar


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
        target=ArtifactType.BLOCK_GOVERNANCE,
        requires_latest=(ArtifactType.MACRO_OVERVIEW,),
    ),
    DependencyRule(
        target=ArtifactType.BLOCK_EXECUTION_ARCH,
        requires_latest=(ArtifactType.MACRO_OVERVIEW, ArtifactType.BLOCK_GOVERNANCE),
    ),
    DependencyRule(
        target=ArtifactType.BLOCK_EXECUTION_PREVIEW,
        requires_latest=(ArtifactType.BLOCK_EXECUTION_ARCH,),
    ),
    DependencyRule(
        target=ArtifactType.WORKOUTS_PLAN,
        requires_latest=(ArtifactType.BLOCK_EXECUTION_ARCH,),
    ),
    DependencyRule(
        target=ArtifactType.INTERVALS_WORKOUTS,
        requires_latest=(ArtifactType.WORKOUTS_PLAN,),
    ),
    DependencyRule(
        target=ArtifactType.DES_ANALYSIS_REPORT,
        requires_latest=(ArtifactType.ACTIVITIES_TREND, ArtifactType.WORKOUTS_PLAN),
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

    def _normalize_payload(self, payload: Any) -> str:
        """Normalize a payload into a searchable text blob."""
        try:
            raw = json.dumps(payload, ensure_ascii=False)
        except TypeError:
            raw = str(payload)
        return self._normalize_text(raw)

    def _macro_constraints(self, macro_doc: dict[str, Any]) -> dict[str, list[str]]:
        """Collect macro constraints for propagation checks."""
        data = macro_doc.get("data", {})
        global_constraints = data.get("global_constraints", {})
        availability = [
            str(item).strip()
            for item in (global_constraints.get("availability_assumptions") or [])
            if str(item).strip()
        ]
        risks = [
            str(item).strip()
            for item in (global_constraints.get("risk_constraints") or [])
            if str(item).strip()
        ]
        planned = [
            str(item).strip()
            for item in (global_constraints.get("planned_event_windows") or [])
            if str(item).strip()
        ]
        recovery = global_constraints.get("recovery_protection") or {}
        fixed_days = [
            str(item).strip()
            for item in (recovery.get("fixed_rest_days") or [])
            if str(item).strip()
        ]
        notes = [
            str(item).strip()
            for item in (recovery.get("notes") or [])
            if str(item).strip()
        ]
        return {
            "availability": availability,
            "risks": risks,
            "planned": planned,
            "fixed_days": fixed_days,
            "recovery_notes": notes,
        }

    def _load_block_governance_for_range(
        self,
        expected_range: Any,
    ) -> tuple[dict[str, Any], str]:
        """Load the block governance matching the expected range."""
        range_spec = envelope_week_range({"meta": {"iso_week_range": expected_range}})
        if range_spec:
            query = IndexExactQuery(root=self.store.root, athlete_id=self.athlete_id)
            version_key = query.best_exact_range_version(
                ArtifactType.BLOCK_GOVERNANCE.value,
                range_spec,
            )
            if version_key:
                return self.store.load_version(
                    self.athlete_id,
                    ArtifactType.BLOCK_GOVERNANCE,
                    version_key,
                ), version_key

        latest = self.store.load_latest(self.athlete_id, ArtifactType.BLOCK_GOVERNANCE)
        latest_key = latest.get("meta", {}).get("version_key", "latest")
        if range_spec:
            latest_range = envelope_week_range(latest)
            if latest_range and latest_range.key != range_spec.key:
                raise MissingDependenciesError(
                    f"Latest BLOCK_GOVERNANCE does not match range {range_spec.key}"
                )
        return latest, str(latest_key)

    def _load_block_execution_arch_for_range(
        self,
        expected_range: Any,
    ) -> tuple[dict[str, Any], str]:
        """Load the block execution architecture matching the expected range."""
        range_spec = envelope_week_range({"meta": {"iso_week_range": expected_range}})
        if range_spec:
            query = IndexExactQuery(root=self.store.root, athlete_id=self.athlete_id)
            version_key = query.best_exact_range_version(
                ArtifactType.BLOCK_EXECUTION_ARCH.value,
                range_spec,
            )
            if version_key:
                return self.store.load_version(
                    self.athlete_id,
                    ArtifactType.BLOCK_EXECUTION_ARCH,
                    version_key,
                ), version_key

        latest = self.store.load_latest(self.athlete_id, ArtifactType.BLOCK_EXECUTION_ARCH)
        latest_key = latest.get("meta", {}).get("version_key", "latest")
        if range_spec:
            latest_range = envelope_week_range(latest)
            if latest_range and latest_range.key != range_spec.key:
                raise MissingDependenciesError(
                    f"Latest BLOCK_EXECUTION_ARCH does not match range {range_spec.key}"
                )
        return latest, str(latest_key)

    def _enforce_block_governance_constraints(
        self,
        document: dict[str, Any],
        macro_doc: dict[str, Any],
    ) -> None:
        """Ensure macro constraints are propagated into block governance."""
        constraints = self._macro_constraints(macro_doc)
        data = document.get("data", {})
        blob = self._normalize_payload(data)
        errors: list[str] = []

        for label, items in (
            ("availability_assumptions", constraints["availability"]),
            ("risk_constraints", constraints["risks"]),
            ("planned_event_windows", constraints["planned"]),
            ("recovery_notes", constraints["recovery_notes"]),
        ):
            for item in items:
                normalized = self._normalize_text(item)
                if normalized and normalized not in blob:
                    errors.append(f"Macro {label} missing in block_governance: {item}")

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
                    errors.append(f"Fixed rest day missing in block_governance: {day}")

        if errors:
            raise SchemaValidationError("Macro constraint propagation failed", errors)

    def _enforce_block_execution_arch_constraints(
        self,
        document: dict[str, Any],
        macro_doc: dict[str, Any],
    ) -> None:
        """Ensure macro constraints and load ranges are propagated into execution arch."""
        constraints = self._macro_constraints(macro_doc)
        data = document.get("data", {})
        upstream_constraints = data.get("upstream_intent", {}).get("constraints", [])
        upstream_blob = self._normalize_text(" ".join(str(item) for item in upstream_constraints))
        errors: list[str] = []

        for label, items in (
            ("availability_assumptions", constraints["availability"]),
            ("risk_constraints", constraints["risks"]),
            ("planned_event_windows", constraints["planned"]),
            ("recovery_notes", constraints["recovery_notes"]),
        ):
            for item in items:
                normalized = self._normalize_text(item)
                if normalized and normalized not in upstream_blob:
                    errors.append(f"Macro {label} missing in upstream_intent.constraints: {item}")

        fixed_days = constraints["fixed_days"]
        exec_days = (
            data.get("execution_principles", {})
            .get("recovery_protection", {})
            .get("fixed_non_training_days", [])
        )
        if fixed_days:
            if sorted(exec_days) != sorted(fixed_days):
                errors.append(
                    "fixed_non_training_days must match macro fixed_rest_days."
                )

        load_ranges = data.get("load_ranges", {})
        expected_range = document.get("meta", {}).get("iso_week_range")
        try:
            block_governance, bg_version_key = self._load_block_governance_for_range(expected_range)
        except MissingDependenciesError as exc:
            raise SchemaValidationError("Macro constraint propagation failed", [str(exc)]) from exc

        bg_guardrails = block_governance.get("data", {}).get("load_guardrails", {})
        for label in ("weekly_kj_bands",):
            expected = bg_guardrails.get(label) or []
            actual = load_ranges.get(label) or []
            expected_map = {entry.get("week"): entry.get("band") for entry in expected}
            actual_map = {entry.get("week"): entry.get("band") for entry in actual}
            if expected_map != actual_map:
                errors.append(f"load_ranges.{label} must match block_governance.{label}.")

        expected_source = (
            f"{ARTIFACT_PATHS[ArtifactType.BLOCK_GOVERNANCE].filename_prefix}_{bg_version_key}.json"
        )
        source = load_ranges.get("source")
        if source != expected_source:
            errors.append(f"load_ranges.source must be '{expected_source}'.")

        if errors:
            raise SchemaValidationError("Macro constraint propagation failed", errors)

    def _enforce_block_execution_preview_traceability(
        self,
        document: dict[str, Any],
    ) -> None:
        """Ensure execution preview references execution architecture."""
        expected_range = document.get("meta", {}).get("iso_week_range")
        try:
            _, arch_version_key = self._load_block_execution_arch_for_range(expected_range)
        except MissingDependenciesError as exc:
            raise SchemaValidationError("Preview traceability failed", [str(exc)]) from exc

        expected_arch = (
            f"{ARTIFACT_PATHS[ArtifactType.BLOCK_EXECUTION_ARCH].filename_prefix}_"
            f"{arch_version_key}.json"
        )
        derived_from = (
            document.get("data", {})
            .get("traceability", {})
            .get("derived_from", [])
        )
        if expected_arch not in derived_from:
            raise SchemaValidationError(
                "Preview traceability failed",
                [f"data.traceability.derived_from must include '{expected_arch}'."],
            )

    def _round_numeric_fields(
        self,
        value: Any,
        schema_node: dict[str, Any] | None,
        root_schema: dict[str, Any],
        path: list[str] | None = None,
    ) -> Any:
        """Apply consistent rounding to numeric values using schema hints when possible."""
        if path is None:
            path = []

        def _joined_path(keys: list[str]) -> str:
            return "_".join(keys).lower()

        def _resolve_schema(node: dict[str, Any] | None) -> dict[str, Any] | None:
            if not isinstance(node, dict):
                return None
            ref = node.get("$ref")
            if not ref or not isinstance(ref, str) or not ref.startswith("#/"):
                return node
            parts = ref.lstrip("#/").split("/")
            cur: Any = root_schema
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
            rounded: dict[str, Any] = {}
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
            items_schema = schema_node.get("items") if isinstance(schema_node, dict) else None
            return [
                self._round_numeric_fields(item, items_schema, root_schema, path)
                for item in value
            ]

        if isinstance(value, (int, float)):
            joined = _joined_path(path)
            if "integer" in types and "number" not in types:
                return int(round(float(value)))
            if "integer" in types and "number" in types:
                if abs(float(value) - round(float(value))) < 1e-9:
                    return int(round(float(value)))
            if "number" in types or not types:
                decimals = 2
                if "hours_typical" in joined or "hours_max" in joined or "weekly_hours" in joined:
                    decimals = 1
                elif "kg" in joined:
                    decimals = 1
                elif "seconds" in joined or joined.endswith("_seconds") or joined.endswith("_sec"):
                    decimals = 0
                elif "bpm" in joined:
                    decimals = 0
                elif "mm_hg" in joined or "mmhg" in joined:
                    decimals = 0
                elif "hrv_ms" in joined or joined.endswith("_ms"):
                    decimals = 0
                elif "if_adj" in joined:
                    decimals = 2
                if "kj_per_kg" in joined or "w_per_kg" in joined or "per_kg" in joined:
                    decimals = 2
                elif "percent" in joined or "pct" in joined:
                    decimals = 1
                elif "ratio" in joined or "index" in joined or "intensity_factor" in joined or joined.endswith("_if"):
                    decimals = 2
                elif "kj" in joined or joined.endswith("_kj") or joined.endswith("kj"):
                    decimals = 0
                elif "watts" in joined or joined.endswith("_w") or joined.endswith("w"):
                    decimals = 0
                elif joined.endswith("_min") or joined.endswith("_mins") or "minutes" in joined:
                    decimals = 0

                if decimals == 0:
                    return int(round(float(value)))
                return round(float(value), decimals)
        return value

    def _apply_rounding(self, document: Any, schema: dict[str, Any]) -> Any:
        """Round numeric values on the document before validation/storage."""
        return self._round_numeric_fields(document, schema, schema, [])

    def guard_put_validated(
        self,
        *,
        output_spec: OutputSpec,
        document: Any,
        run_id: str,
        producer_agent: str,
        update_latest: bool = True,
    ) -> dict[str, Any]:
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
                validate_or_raise(validator, document)
                version_key = derive_version_key_from_envelope(document)
            else:
                document = self._apply_rounding(document, schema)
                validate_or_raise(validator, document)
                version_key = "raw"

            if target in (ArtifactType.BLOCK_GOVERNANCE, ArtifactType.BLOCK_EXECUTION_ARCH):
                macro_doc = self.store.load_latest(self.athlete_id, ArtifactType.MACRO_OVERVIEW)
                if target == ArtifactType.BLOCK_GOVERNANCE:
                    self._enforce_block_governance_constraints(document, macro_doc)
                else:
                    self._enforce_block_execution_arch_constraints(document, macro_doc)
            elif target == ArtifactType.BLOCK_EXECUTION_PREVIEW:
                self._enforce_block_execution_preview_traceability(document)

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

    def _format_payload(self, document: Any) -> str:
        """Return a formatted payload string for logging."""
        try:
            return json.dumps(document, ensure_ascii=False, indent=2)
        except TypeError:
            return repr(document)

    def _log_store_attempt(
        self,
        document: Any,
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
        document: Any,
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
