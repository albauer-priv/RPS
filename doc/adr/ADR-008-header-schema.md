# ADR-008: Header Schema for Artefacts

**Status:** Accepted  
**Date:** 2026-02-01  

## Context

Artefact metadata is required for indexing, rendering, and validity checks. Missing headers cause downstream errors.

## Decision

Define a required artefact header schema (meta) with:
- `version_key`
- `created_at`
- `iso_week` or `iso_week_range`
- `producer_agent`
- `run_id`

## Consequences

- Indexing and latest pointers remain consistent.
- Validation can be stricter and more reliable.

## Exceptions

None.
