---
name: blueprint-contract-validation
description: Validate internal blueprints and writer outputs against deterministic contracts.
---
# Blueprint Contract Validation

Review internal bundles and final artifacts against approved deterministic contracts.

Rules:

1. Season `phase_blueprints` must match selected scenario phase slots exactly.
2. Phase `week_blueprints` must match active phase week roles and S5 bands exactly.
3. Week `day_blueprints` and `workout_blueprints` must match active week calendar, load band, availability, quality cap, and workout policy.
4. Writers must not introduce phases, weeks, days, workouts, load bands, domains, or event implications absent from approved blueprints.
5. If artifact prose contradicts blueprints or deterministic context, the contract wins and the output is not writer-ready.
6. Prefer catching semantic contradictions in finalize/review; writer-stage validation is the last technical protection, not the main repair stage.

Output expectation:

- Report blocker paths and the exact contract value expected.
- Approve only when the writer can serialize from blueprints without inventing structure.
