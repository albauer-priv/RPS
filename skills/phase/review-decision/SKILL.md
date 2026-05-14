---
name: review-decision
description: Integrate phase review outputs into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "1.0"
---
Turn phase review outputs into one explicit decision.

Method:
1. Treat guardrail, governance, and exact-range violations as approval gates.
2. Keep replan scope as small as possible.
3. Preserve approved upstream decisions and unaffected phase sections.
