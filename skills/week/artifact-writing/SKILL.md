---
name: artifact-writing
description: Serialize the final approved week plan envelope without adding planning decisions.
metadata:
  author: rps
  version: "3.1"
---
Write the final approved `WEEK_PLAN` data only.

Method:
1. Prefer emitting the approved `data` payload. If the active task still requires an envelope, emit exactly one top-level `{meta,data}` object.
2. Preserve approved day/workout blueprints exactly and write only the approved week interpretation.
3. Do not invent persisted `meta`. Runtime owns `artifact_type`, `schema_id`, `schema_version`, `authority`, `owner_agent`, `run_id`, and `created_at`.
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
- `agenda` must match the deterministic Mon-Sun date matrix
- `week_summary.weekly_load_corridor_kj` must mirror the active Phase/S5 band from deterministic context
- fixed rest days must be `00:00`, `0`, and `workout_id null`
- any `workout_id` referenced in `agenda` must appear in `workouts`
- workout objects require `workout_id`, `title`, `date`, `start`, `duration`, `workout_text`, and `notes`
- workout text must include Warmup, Main Set, Cooldown, mandatory Activation where applicable, ordered sections, step duration, power target, and cadence
- required strings must be non-empty unless the schema explicitly allows empty notes

Hard rules:
- render user-facing chat as readable prose/tables instead of raw JSON
- call tools only after the envelope is schema-valid
- include all required workout references
- use available approved content for required fields and mark blockers when content is absent

Output format:
- Return only the schema-compliant object required by the active task expected_output.
- Focus on `data`; if an envelope is requested, `meta` is a runtime-overwritten placeholder/hint.
- Preserve approved bundle content, review decisions, deterministic context, and trace references.
- Emit only the artifact object.
