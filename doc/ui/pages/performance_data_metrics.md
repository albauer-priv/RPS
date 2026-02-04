---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-04
Owner: UI
---
# Analyse → Data & Metrics

## Purpose
- Visualize activity trends and planning corridors.
- Trigger Intervals data refresh.

## Charts
- Planning load corridors (Season/Phase/Week + actual/planned overlays)
- Weekly load + durability metrics
- Weekly dose → outcome
- Daily durability scatter

## Data Sources
- Prefers `latest/activities_trend.parquet` when present; falls back to `latest/activities_trend.json`.

## Actions
- Refresh Intervals Data
