"""Pydantic models backed by canonical RPS JSON Schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, model_validator

from rps.workspace.artifact_metadata import canonicalize_artifact_envelope_meta

JsonMap = dict[str, Any]
ROOT = Path(__file__).resolve().parents[3]
BUNDLED_SCHEMA_DIR = ROOT / "specs" / "knowledge" / "_shared" / "sources" / "schemas" / "bundled"
BUNDLED_OUTPUT_SCHEMA_DIR = (
    ROOT / "specs" / "knowledge" / "_shared" / "sources" / "schemas" / "bundled_output"
)
SOURCE_SCHEMA_DIR = ROOT / "specs" / "schemas"


def _normalize_schema_backed_metadata(payload: Any, schema: JsonMap | None = None) -> Any:
    """Normalize schema-sensitive metadata before canonical JSON Schema validation."""

    return canonicalize_artifact_envelope_meta(payload, schema=schema)


class JsonSchemaArtifactModel(BaseModel):
    """Generic artifact envelope whose concrete contract is a JSON Schema file."""

    model_config = ConfigDict(extra="forbid")

    __schema_file__: ClassVar[str]
    __canonical_schema_file__: ClassVar[str]
    __output_schema_file__: ClassVar[str]
    __schema_cache__: ClassVar[dict[str, JsonMap]] = {}
    __output_schema_cache__: ClassVar[dict[str, JsonMap]] = {}
    __source_schema_cache__: ClassVar[dict[str, JsonMap]] = {}
    __validator_cache__: ClassVar[dict[str, Draft202012Validator]] = {}

    meta: JsonMap = Field(default_factory=dict)
    data: JsonMap = Field(default_factory=dict)

    @classmethod
    def _canonical_schema_file_name(cls) -> str:
        return getattr(cls, "__canonical_schema_file__", cls.__schema_file__)

    @classmethod
    def _output_schema_file_name(cls) -> str:
        return getattr(cls, "__output_schema_file__", cls.__schema_file__)

    @classmethod
    def _schema_path(cls) -> Path:
        bundled_path = BUNDLED_SCHEMA_DIR / cls._canonical_schema_file_name()
        if bundled_path.exists():
            return bundled_path
        return SOURCE_SCHEMA_DIR / cls._canonical_schema_file_name()

    @classmethod
    def _output_schema_path(cls) -> Path:
        bundled_path = BUNDLED_OUTPUT_SCHEMA_DIR / cls._output_schema_file_name()
        if bundled_path.exists():
            return bundled_path
        return cls._schema_path()

    @classmethod
    def json_schema_contract(cls) -> JsonMap:
        """Return the canonical JSON Schema contract used for persisted artifact validation."""

        cache_key = f"{cls.__module__}.{cls.__qualname__}:{cls._canonical_schema_file_name()}"
        if cache_key not in cls.__schema_cache__:
            path = cls._schema_path()
            cls.__schema_cache__[cache_key] = json.loads(path.read_text(encoding="utf-8"))
        return cls.__schema_cache__[cache_key]

    @classmethod
    def output_json_schema_contract(cls) -> JsonMap:
        """Return the LLM-safe JSON Schema contract used for structured outputs."""

        cache_key = f"{cls.__module__}.{cls.__qualname__}:{cls._output_schema_file_name()}"
        if cache_key not in cls.__output_schema_cache__:
            path = cls._output_schema_path()
            cls.__output_schema_cache__[cache_key] = json.loads(path.read_text(encoding="utf-8"))
        return cls.__output_schema_cache__[cache_key]

    @classmethod
    def source_json_schema_contract(cls) -> JsonMap:
        """Return the source schema contract when available for metadata const overlays."""

        cache_key = f"{cls.__module__}.{cls.__qualname__}:{cls._canonical_schema_file_name()}"
        if cache_key not in cls.__source_schema_cache__:
            path = SOURCE_SCHEMA_DIR / cls._canonical_schema_file_name()
            if path.exists():
                cls.__source_schema_cache__[cache_key] = json.loads(path.read_text(encoding="utf-8"))
            else:
                cls.__source_schema_cache__[cache_key] = cls.json_schema_contract()
        return cls.__source_schema_cache__[cache_key]

    @classmethod
    def schema_validator(cls) -> Draft202012Validator:
        """Return a cached JSON Schema validator for this generated model."""

        cache_key = f"{cls.__module__}.{cls.__qualname__}:{cls._canonical_schema_file_name()}"
        if cache_key not in cls.__validator_cache__:
            cls.__validator_cache__[cache_key] = Draft202012Validator(cls.json_schema_contract())
        return cls.__validator_cache__[cache_key]

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> JsonMap:
        """Expose the LLM-safe JSON Schema to CrewAI structured-output construction."""

        return cls.output_json_schema_contract()

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> JsonMap:
        """Return the LLM-safe artifact schema instead of the generic envelope schema."""

        return cls.output_json_schema_contract()

    @model_validator(mode="before")
    @classmethod
    def normalize_before_json_schema_validation(cls, value: Any) -> Any:
        """Repair metadata fields that are deterministic schema semantics, not agent choices."""

        return _normalize_schema_backed_metadata(value, cls.source_json_schema_contract())

    @model_validator(mode="after")
    def validate_against_json_schema(self) -> JsonSchemaArtifactModel:
        """Validate the full model payload against the canonical JSON Schema."""

        payload = self.model_dump()
        errors = sorted(self.schema_validator().iter_errors(payload), key=str)
        if errors:
            rendered_errors: list[str] = []
            for err in errors[:8]:
                loc = ".".join(str(item) for item in err.path) or "<root>"
                rendered_errors.append(f"{loc}: {err.message}")
            if len(errors) > len(rendered_errors):
                rendered_errors.append(f"... and {len(errors) - len(rendered_errors)} more")
            raise ValueError("JSON schema validation failed: " + "; ".join(rendered_errors))
        return self
