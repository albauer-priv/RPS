---
name: execution-rules
description: Define included and excluded execution semantics for the exact phase range using canonical agenda vocabulary.
metadata:
  author: rps
  version: "2.0"
---
Author execution rules for the exact phase range.

Method:
1. Use canonical agenda vocabulary only: `DAY_ROLE`, `INTENSITY_DOMAIN`, and `LOAD_MODALITY` semantics from the agenda enum.
2. Set included, suppressed, and excluded phase-level semantics while leaving workout prescription to week/workout tasks.
3. Express recovery protection, event-week handling, and quality-density limits in semantic terms.

Agenda rules:
- `DAY_ROLE` is mandatory.
- `QUALITY` and `EVENT` require a non-`NONE` intensity domain.
- `K3` is only valid with `QUALITY` or `EVENT`, and only with `ENDURANCE_HIGH` or `SWEET_SPOT`.
- Pair `ENDURANCE` and `OPTIONAL` with endurance-compatible domains.
- Pair `QUALITY` with trainable quality domains above recovery/endurance-low semantics.
- Keep power zones, `%FTP`, durations, interval structures, kJ values, and progression language in downstream week/workout artifacts.

Phase execution framing:
- recovery weeks reduce density and protect spacing
- build weeks may allow more quality intent, but still inside cadence and recovery limits
- event weeks inherit event semantics and should not be treated like generic quality weeks
- optional/flex semantics must remain removable without compensation unless explicitly protected upstream

Hard rules:
- keep day-by-day planning in week tasks
- keep workouts and interval prescriptions in workout tasks
- agenda combinations stay inside the allowed role/domain matrix
- keep numeric daily targets in downstream week artifacts or zone language

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
