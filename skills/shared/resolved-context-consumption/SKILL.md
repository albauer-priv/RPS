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
4. Never override selected versions or pending state using memory or guesswork.
