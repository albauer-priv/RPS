---
name: constraint-audit
description: Audit phase bundles for availability, logistics, event, and feed-forward constraint compliance.
metadata:
  author: rps
  version: "2.0"
---
Check whether the candidate phase respects binding constraints.

Focus on:
- athlete and logistics constraints
- event placement consistency
- any applicable feed-forward restriction
- exact-range integrity

Blocker vs warning discipline:
- raise a `blocking_issue` only for genuinely hard constraints:
  - zero-availability windows or travel that eliminate the phase window entirely
  - an event date that cannot be accommodated within the phase without taper collapse
  - explicit recovery protections that are violated
- do **not** raise a `blocking_issue` for:
  - a phase opening corridor above a recent disrupted week's actual load — when
    `W_prev_actual < BL_kJ × 0.85`, the disrupted-week rule applies and the corridor is
    expected to exceed `W_prev_actual`; record as informational context, not a constraint blocker
  - `RELOAD → TAPER` phase adjacency — that is a macrocycle architecture warning; recommend
    restructuring the preceding phase's final week but do not block
  - a domain coherence narrative note (a forbidden domain mentioned in prose) — that is a
    finalize-pass concern, not a phase constraint blocker
  - active-replan status remaining from a prior REDO cycle — that is evidence context, not a
    constraint; acknowledge it but do not treat it as a new blocker unless it contains an
    unresolvable physical impossibility

Retrieval policy:
- Athlete-managed inputs (`planning_events`, `availability`, `logistics`), authoritative phase contracts, and latest planning artefacts/snapshots are already provided as injected context. No workspace tools are available or needed for this task.

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
