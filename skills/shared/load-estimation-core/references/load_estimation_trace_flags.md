# Load Estimation Trace Flags

When available, emit and preserve:
- zone-model `meta.schema_version`
- zone-model `data.model_metadata.filename`
- resolved `IF_ref_load`
- `IF_ref_load_source`
- `used_fallback_IF_direct` as boolean
- `segment_parse_status` as `OK` or `FAIL`
- selected KPI rate-band selector and selected `kj_per_kg_per_hour` values when KPI gating is active
- S5 fallback trace for weekly corridors: `fallback_level`, `fallback_reason`, `kpi_rate_band_selector_used`, and final min/max band

These values explain why a corridor or workout estimate looks the way it does.
