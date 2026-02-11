---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Overview
---
# Planning Principles

This document captures scheduling and data guardrails for weekly planning.

## 1) Planning timing
- Planning the **following week** happens in the **current week**, typically on the **week anchor (Sunday)** after the last workouts are completed.
- Planning may also occur on Monday or Tuesday of the **following week** if needed.

## 2) Scope and horizon
- **Planning scope:** current week or next week.
- **Planning horizon:** exactly one week (current or next).
- **Week definition:** always ISO week.

## 3) Season plan constraints
- A week can only be planned if it falls **within the ISO-week range** covered by the **current Season Plan**.
- A week can only be planned if higher-level artifacts exist:
  - `season_plan`
  - `phase_*`

## 4) Performance report constraints
- A Performance Report is created **only for the past**, never for future weeks.
- It is based on Intervals.icu activity data (`activities_*`), which only exists for completed workouts.
- A Performance Report can be created for any week that has the required data coverage.

## 5) Feed Forward constraints
- Feed Forward is run for a **completed training week**, typically around the **week anchor (Sunday)** or Monday.
- It should run once the full week’s activities are present in Intervals data.
- A new Performance Report is created if Intervals data is newer than the current report for the completed week.
- The Performance Report is an **input** to the Feed Forward request that updates the Season Plan.

## 6) Consistency check
- No internal contradictions detected across the rules above.
- If planning occurs on Monday/Tuesday, it still targets either the current or next ISO week, and remains within the Season Plan range.
