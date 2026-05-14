---
name: artifact-writing
description: Serialize the final approved week plan envelope without adding planning decisions.
metadata:
  author: rps
  version: "3.0"
---
Write the final approved `WEEK_PLAN` envelope only.

Method:
1. Emit exactly one top-level `{meta,data}` object.
2. Preserve approved planning content exactly; do not reinterpret the week during writing.
3. Fill constants exactly:
   - `artifact_type = WEEK_PLAN`
   - `schema_id = WeekPlanInterface`
   - `authority = Binding`
   - `owner_agent = Week-Planner`
4. Validate against `week_plan.schema.json` before storing.

Required content:
- `data.week_summary.week_objective`
- `data.week_summary.weekly_load_corridor_kj`
- `data.week_summary.planned_weekly_load_kj`
- `data.week_summary.notes`
- `data.agenda` with exactly 7 entries from Mon..Sun
- `data.workouts` with all referenced `workout_id`s resolved

Writer rules:
- `agenda` days must carry `day`, `date`, `day_role`, `planned_duration`, `planned_kj`, `workout_id`
- any `workout_id` referenced in `agenda` must appear in `workouts`
- workout objects require `workout_id`, `title`, `date`, `start`, `duration`, `workout_text`, and `notes`
- required strings must be non-empty unless the schema explicitly allows empty notes

Hard rules:
- no raw JSON in chat
- no tool call until the envelope is schema-valid
- no missing workout references
- no guessed fields if required content is absent
