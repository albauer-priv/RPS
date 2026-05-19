---
name: context-analysis
description: Summarize exact phase-range authority, upstream season intent, and active constraint surfaces.
metadata:
  author: rps
  version: "3.0"
---
Read phase context before authoring any guardrails or structure.

Method:
1. Fix the exact `iso_week_range` and corresponding upstream temporal scope from the season plan, using that range as the phase boundary.
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
- summarize upstream guardrails here
- use injected date ranges and deterministic context
- interpret wellness through active governance
- keep week and workout content for downstream tasks
- prefer the narrow configured workspace tools and injected deterministic context over broad rediscovery

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
