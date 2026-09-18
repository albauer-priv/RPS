---
name: event-integration
description: Integrate B/C event implications into phase structure without breaking season authority.
metadata:
  author: rps
  version: "1.1"
---
Integrate secondary events into the phase conservatively.

B and C event semantics (from `skills/shared/periodization-methodology`):
- **B event ≤ 4 weeks before A event**: the B event week = last hard specificity stimulus; all subsequent
  weeks in the phase = A-event taper; do not insert a new build or reload block between B event and A-event taper
- **B event > 4 weeks before A event**: minor load adjustment in event week only; 3–7 day recovery inside
  existing structure; resume normal build
- **C event**: no load adjustment, no taper, no post-event recovery window; fits as training day

Method:
1. Respect the season event hierarchy and existing peak windows.
2. Propagate B/C event implications into week roles and taper touches only as allowed by season authority.
3. Preserve the season-defined peak objective inside the phase.
4. Apply B/C event semantics above; never treat a B event as a mini-A with independent taper unless the
   season authority explicitly designates it as such.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
