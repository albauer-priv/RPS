---
name: artifact-writing
description: Serialize week-planning results into persistence-safe week artefact envelopes.
metadata:
  author: rps
  version: "1.0"
---
When producing a week artefact:
- Return only the final artefact envelope.
- Keep meta and data complete.
- Respect canonical week-plan ownership and naming.
- Do not add analysis chatter outside the envelope.
