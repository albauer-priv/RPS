---
name: replan-instruction-authoring
description: Write structured replan instructions that send planning crews back with bounded, targeted corrections.
metadata:
  author: rps
  version: "1.0"
---
When review rejects or requests replan:
- name the exact issues to fix
- preserve already-correct decisions
- constrain scope of change
- target only the specialists that need to revisit their drafts

Output format:
- Return the task expected_output as bounded replan instructions.
- Include scope, blocking reason, required changes, preserved decisions, and acceptance criteria for the next attempt.
- Make the instruction specific enough that the planner can execute it without guessing.
