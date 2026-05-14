---
name: runtime-boundaries
description: Authority boundaries, preview/apply discipline, and no-overwrite rules for RPS planning agents.
metadata:
  author: rps
  version: "1.0"
---
Follow strict runtime boundaries:
- Artefacts, schemas, and guarded persistence are the authority boundary.
- Never claim persistence unless the task/tool explicitly persists.
- Preview and apply are different operations.
- Do not invent missing athlete facts. Use tools for runtime truth.
- Keep tool authorization code-owned. `allowed-tools` metadata is advisory only.
