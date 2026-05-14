---
name: context-analysis
description: Summarize exact phase-range authority, upstream season intent, and active constraint surfaces.
metadata:
  author: rps
  version: "3.0"
---
Read phase context before authoring any guardrails or structure.

Method:
1. Fix the exact `iso_week_range` and corresponding upstream temporal scope from the season plan. Do not invent or recompute the phase range.
2. Read the season plan as binding authority for phase purpose, phase type, event windows, global constraints, and recovery protection.
3. Read planning events, availability, logistics, and selected feed-forward inputs as constraint surfaces for the exact phase range.
4. Treat wellness and recent diagnostics as informational only unless they arrive through an explicit approved feed-forward artefact.
5. Separate what is binding now versus advisory:
   - Binding: season plan, approved season feed-forward, planning events, availability, explicit logistics blockers.
   - Informational: wellness, trend context, scenario rationale.
6. Return the exact upstream intent and the constraint surfaces the phase specialists must preserve.

What to summarize:
- exact phase range and dates copied from upstream
- phase type and primary objective
- relevant event windows inside and near the phase
- availability assumptions, risk constraints, planned event windows, and recovery protection inherited from season constraints
- logistics and travel limitations affecting modality or recovery
- any explicit upstream feed-forward deltas

Hard rules:
- do not derive new guardrails here
- do not compute dates from scratch
- do not turn wellness into automatic governance
- do not create week or workout content
