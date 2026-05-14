# Workout Intent Mapping

Every workout must map to exactly one agenda/day-role/intensity combination.

Canonical examples:
- Recovery -> RECOVERY
- Endurance low/high -> ENDURANCE
- Tempo / Sweet Spot / Threshold / VO2 -> QUALITY
- K3 stays QUALITY but with explicit load modality semantics

Invalid behavior:
- mixed intent workouts without one governing role
- intensity domains that contradict the day role
