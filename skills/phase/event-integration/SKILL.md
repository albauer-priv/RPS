---
name: event-integration
description: Integrate B/C event implications into phase structure without breaking season authority.
metadata:
  author: rps
  version: "1.0"
---
Integrate secondary events into the phase conservatively.

Method:
1. Respect the season event hierarchy and existing peak windows.
2. Propagate B/C event implications into week roles and taper touches only as allowed by season authority.
3. Preserve the season-defined peak objective inside the phase.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
