---
Version: 1.0
Status: Accepted
Last-Updated: 2026-02-04
Owner: Architecture
---
# ADR-024: Parquet Cache for Intervals Pipeline Outputs

## Context

Analytics pages repeatedly parse JSON/CSV outputs from the Intervals pipeline.
This is slower than a columnar cache, but JSON/CSV remain important for
validation, traceability, and schema transparency.

## Decision

Add a **best-effort Parquet cache** written by the Intervals pipeline for
activities_actual and activities_trend outputs. Parquet is **non-canonical**
and must not replace JSON/CSV artifacts.

## Alternatives Considered

1) **Parquet-only canonical storage**  
   Rejected: would break existing tooling, reduce transparency, and require a
   wide migration across workspace, validation, and UI readers.

2) **No cache**  
   Rejected: analytics performance remains limited by JSON/CSV parsing.

## Consequences

- Pipeline writes `.parquet` alongside `.csv`/`.json`.
- If Parquet writes fail, the pipeline still succeeds and logs a warning.
- Future UI readers may optionally prefer Parquet for performance.

## Links

- Feature spec: [[doc/specs/features/FEAT_parquet_cache.md](doc/specs/features/FEAT_parquet_cache.md)](doc/[specs/features/FEAT_parquet_cache.md](specs/features/FEAT_parquet_cache.md))
- Data pipeline: [[doc/architecture/subsystems/data_pipeline.md](doc/architecture/subsystems/data_pipeline.md)](doc/architecture/subsystems/data_pipeline.md)

