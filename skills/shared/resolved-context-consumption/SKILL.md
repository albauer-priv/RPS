---
name: resolved-context-consumption
description: Consume resolved athlete and planning context conservatively and trace assumptions explicitly.
metadata:
  author: rps
  version: "1.0"
---
Consume resolved context in this order:
1. Use already-resolved workspace context and snapshots first.
2. Read additional runtime truth only when the task still lacks a required fact.
3. When context is partial, state the assumption and tighten claims.
4. Preserve selected versions and pending state using runtime context rather than memory or guesswork.

Output format:
- Return the active task expected_output without adding a separate artifact or unrelated prose.
- Include only the runtime-boundary, context-consumption, traceability, or naming guidance needed for the current task.
- Keep the contribution concise and directly usable by downstream tasks.
