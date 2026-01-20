# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Per-agent model overrides via `OPENAI_MODEL_<AGENT>` and CLI plumbing to honor them.
- Per-agent temperature overrides via `OPENAI_TEMPERATURE_<AGENT>` (plus global `OPENAI_TEMPERATURE`).
- `workspace_get_input` tool for athlete-specific markdown inputs (season brief, events).
- Vector store sync progress output and `--reset` to reinitialize stores.
- Schema bundling workflow (`scripts/bundle_schemas.py`) and bundled outputs under `knowledge/_shared/sources/schemas/bundled/`.
- Vector store smoke test script: `scripts/smoke_vectorstores.py`.
- Build checklist and recommended model guidance docs.
- Mode A macro helper script for scenarios + macro overview (`scripts/macro_mode_a.py`).

### Changed
- Force `file_search` by default in agent runs; add `--no-file-search` to disable.
- Shared knowledge manifests now reference bundled schemas; rendered KPI sidecars removed.
- Schema bundler handles `jsonref` serialization for bundled outputs.
- Agent prompts now treat instructions as a single file with section-based guidance; removed bundle/BEGIN/END marker references.
- JSON schemas normalized for strict tool compatibility (explicit types/required, flattened `allOf`, removed unsupported constraints).
- Version key derivation now supports string-based `iso_week` and `iso_week_range` metadata.
- Docs and README now document the two-step Macro Mode A workflow.
- Model guidance notes include Macro Mode A scenario token-throughput tip.
- Agent runners now pass optional temperature settings; `.env.example` and model docs reflect temperature overrides.

### Removed
- Legacy schema copies under `knowledge/_shared/sources/schemas/` (replaced by bundled variants).
- Obsolete shared schemas `data_confidence` and `macro_cycle_enum` from knowledge sources.

## [0.1.0] - 2026-01-20

### Changed
- Complete rewrite targeting OpenAI Responses API.

### Added
- Local workspace docs and validation guide under `doc/`.
- Data pipeline validator script: `scripts/validate_outputs.py`.
- Artefact flow overview with updated Mermaid diagrams.
- Vector store operations and incident guidance in `doc/system_architecture.md`.

### Changed
- Data pipeline docs updated to reference `get_intervals_data.py`.
- System docs updated for workspace handling and validation flow.
