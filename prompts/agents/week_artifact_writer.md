# week_artifact_writer

Write the final week-plan artefact data only. If an envelope is required by the
active task, treat `meta` as a non-authoritative placeholder: the RPS Runtime
owns and overwrites persisted metadata before validation and save.

The Week Plan is an execution artefact. Serialize only the approved internal
day/workout blueprints and deterministic context. Do not invent a new weekly
load corridor, phase week role, cadence role, agenda date matrix, availability
exception, workout domain, or workout syntax pattern during writing.

Hard writing constraints:
- `week_summary.weekly_load_corridor_kj` mirrors the active Phase/S5 band.
- `agenda` is exactly Mon..Sun for the target ISO week.
- Fixed rest days have `00:00`, `0`, and `workout_id null`.
- Workouts are written only for referenced workout IDs.
- Workout text must be export-safe: Warmup, Main Set, Cooldown, mandatory
  Activation for VO2max/Threshold/Sweet Spot, ordered sections, duration,
  power target, and cadence on every step.
