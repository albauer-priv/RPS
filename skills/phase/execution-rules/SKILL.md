---
name: execution-rules
description: Define allowed and forbidden execution semantics for the exact phase range using canonical agenda vocabulary.
metadata:
  author: rps
  version: "2.0"
---
Author execution rules for the exact phase range.

Method:
1. Use canonical agenda vocabulary only: `DAY_ROLE`, `INTENSITY_DOMAIN`, and `LOAD_MODALITY` semantics from the agenda enum.
2. Set what is allowed, suppressed, and forbidden at phase level without drifting into workout prescription.
3. Express recovery protection, event-week handling, and quality-density limits in semantic terms.

Agenda rules:
- `DAY_ROLE` is mandatory.
- `QUALITY` and `EVENT` require a non-`NONE` intensity domain.
- `K3` is only valid with `QUALITY` or `EVENT`, and only with `ENDURANCE_HIGH` or `SWEET_SPOT`.
- `ENDURANCE` and `OPTIONAL` must not carry `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, or `VO2MAX`.
- `QUALITY` must not use `NONE` or `ENDURANCE_LOW`.
- No power zones, `%FTP`, durations, interval structures, kJ values, or progression language belong here.

Phase execution framing:
- recovery weeks reduce density and protect spacing
- build weeks may allow more quality intent, but still inside cadence and recovery limits
- event weeks inherit event semantics and should not be treated like generic quality weeks
- optional/flex semantics must remain removable without compensation unless explicitly protected upstream

Hard rules:
- no day-by-day planning
- no workouts or interval prescriptions
- no forbidden agenda combinations
- no numeric daily targets or zone language
