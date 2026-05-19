# report_artifact_writer

Write the final advisory report artefact data only. If an envelope is required
by the active task, treat `meta` as a non-authoritative placeholder: the RPS
Runtime owns and overwrites persisted metadata before validation and save.
