---
name: recommendation-and-adjustment
description: Produce durability-first week advice or adjustment intent for coach and planning surfaces.
metadata:
  author: rps
  version: "2.0"
---
Give week advice using the same durability-first logic as the planner.

Method:
1. Read the selected week, actuals, and active constraints.
2. Prefer the smallest change that restores coherence.
3. Protect recovery and sustainable load before chasing perfect completion.
4. If a preview is needed, convert advice into one bounded adjustment intent.

Hard rules:
- no catch-up logic
- no cosmetic symmetry at the expense of recovery
- advice must remain inside active corridor and phase intent unless the task explicitly changes them
