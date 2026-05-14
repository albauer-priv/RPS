---
name: review-decision
description: Integrate season review findings into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "1.0"
---
Turn season review outputs into one binding decision.

Method:
1. Treat macrocycle, governance, and constraint blockers as approval gates.
2. Prefer bounded replan over broad restarts.
3. Replan instructions must preserve valid event anchors and unaffected macrocycle decisions.
