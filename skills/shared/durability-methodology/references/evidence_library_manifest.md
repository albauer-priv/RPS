# Evidence Library Manifest

This repository uses one canonical local evidence library for operative literature/reference lookup.

## Operative Sources

1. `library/core_studies.yaml`
2. `library/applied_sources.yaml`
3. Generated markdown tables and study briefs derived from the canonical library

## Rules

- Bibliographic verification is not enough for activation.
- Active evidence must pass curation plus deterministic quality gate.
- Long-form study briefs are generated from structured curation output.
- Only verified locators belong in active prompts, skills, runtime, or persisted outputs.
- Primary-source verification is limited to PubMed, DOI/Crossref, official journal/publisher landing pages, NIH/PMC, and official OA repositories.

## Migration

- Legacy entries may remain visible as `legacy_active` until structured curation backfill completes.
- Non-active candidates are excluded from operative evidence surfaces.
