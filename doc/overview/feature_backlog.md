---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-04
Owner: Product
---
# Feature Backlog

This backlog tracks upcoming features and refactors. Each item should link to a
feature spec (`doc/specs/features/FEAT_<slug>.md`) before implementation.

## Next Up

- [ ] FEAT_parquet_cache — Parquet cache writes in data pipeline.
- [ ] FEAT_parquet_readers — Parquet-first reads in Data & Metrics.

## Planned

- [ ] FEAT_user_inputs_io — Upload/Download user inputs (Season Brief, events.md) for editing and re-ingestion.
- [ ] FEAT_user_inputs_modular — Split user inputs into core profile/goals, race events, availability for independent updates.
- [ ] FEAT_user_data_editors — UI editors for availability, events, logistics, and related inputs.
- [ ] FEAT_user_management — Auth/login with per-user Intervals + OpenAI API keys and athlete ID.
- [ ] FEAT_user_input_examples — Provide example Season Brief and Logistics (events.md) inputs.
- [ ] FEAT_docker_deploy — Docker image build, registry publish, and deployment workflow.
- [ ] FEAT_plan_adjustments — Adjust existing Season/Phase plans when constraints change; preserve past phases.
- [ ] FEAT_backup_restore_cli — CLI data ops for backups and restores.
- [~] FEAT_vectorstore_monitor — background monitor + reset behavior. (Implemented)
- [ ] FEAT_run_scheduler_resilience — stuck-run detection and recovery.
- [~] FEAT_posting_receipts_review — receipts diff + conflict UX. (Receipt inspection exists; UX diff pending)

## Deferred / Ideas

- [ ] FEAT_parquet_rollups — precomputed analytics rollups for long ranges.
- [ ] FEAT_archival_policy — archive/restore old athlete data.
