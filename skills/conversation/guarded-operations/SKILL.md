---
name: guarded-operations
description: Bounded operational rules for Coach-style preview, apply, and scoped replan actions.
metadata:
  author: rps
  version: "1.0"
---
Operate only on the selected athlete and selected week context.

Method:
1. Read current context before previewing or applying anything.
2. Prefer preview-first operations whenever a change would persist or rebuild artifacts.
3. Keep scope bounded to the requested operation; do not branch into unrelated planning.
4. When the action is ambiguous, return a preview or clarification-oriented result instead of applying.
5. Report affected artifacts, confirmation requirements, and downstream rebuild effects explicitly.

Hard rules:
- never persist outside guarded store operations
- never widen the requested scope on your own
- never invent follow-up planning that was not requested
