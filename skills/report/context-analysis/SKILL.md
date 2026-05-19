---
name: context-analysis
description: Summarize selected report-week evidence, readiness context, and data-quality limits before DES interpretation.
metadata:
  author: rps
  version: "2.0"
---
Read the report week as diagnostic input only.

Method:
1. Use `Deterministic Report Evidence Context` for the exact report ISO week, activity version keys, missing-data flags, and diagnostic-only boundary.
2. Summarize actual load, execution context, and recent trend context for the completed week.
3. Read wellness as informational readiness context only. Use wellness to flag risk or uncertainty while training prescription and governance remain in their authoritative artifacts.
4. Read evidence quality and confidence explicitly. Low or unknown confidence limits interpretation.
5. Separate factual observations from later diagnostic interpretation.

What to summarize:
- completed-week actual load and key deviations
- phase week and phase focus context
- short-horizon trend signals
- anomalies, missing data, and comparability caveats
- wellness/recovery context that may limit confidence

Hard rules:
- keep outputs diagnostic and route planning changes to planning tasks
- interpret wellness as diagnostic context for governed action
- calibrate diagnosis strength to evidence confidence
- prefer the narrow configured workspace tools and injected deterministic context over broad rediscovery

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
