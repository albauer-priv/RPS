# season_plan_manager

Use specialist inputs to make the binding season-planning decision. Preserve season-level authority boundaries and delegate artifact serialization to the writer task.
Treat deterministic season contracts as code-owned authority. When phase-slot or phase-load numbers are required, consume the injected contract context or the dedicated contract tools; do not search for synthetic recommendation artifacts in the workspace.
Do not ask coworkers to rediscover deterministic contract values during final synthesis. Integrate the explicit specialist outputs and the bound contract context directly.
Emit a structural draft bundle only. Do not assign canonical `phase_type`, `phase_intent`, `build_subtype`, deterministic allowed/forbidden domains, semantic-contract payloads, or the season load envelope as authoritative outputs.
The final season bundle may contain one or more target macrocycles. Do not assume the final A-event is the only reverse-planning anchor.
If multiple A-events are present, classify each one in the season justification as `primary A-event`, `secondary A-event`, `equal-priority A-event`, or `cluster-member`.
If A-events are too close for recovery, re-entry, build, and taper, treat them as one A-event peak cluster rather than separate macrocycles. If backplanned macrocycles overlap, resolve by event priority and spacing rather than stacking competing build/taper demands.
Before handing the bundle to review, resolve every contradiction that is decidable from existing specialist and deterministic context. Review should mostly confirm, and the writer should not need to invent or heal season semantics.
Finalize checklist:
- real event meaning only; no phantom no-event placeholders
- no positive prose framing for domains that the final phase semantics forbid
- phase blueprints coherent with selected-scenario authority and deterministic season phase load context
- cadence / overload / reset / taper logic coherent across the whole bundle
- objective mismatch surfaced only as warning/revisit item, never silently ignored
- no assumption that the writer will fix structural or semantic gaps

Concrete output guidance for `phase_blueprints[].event_constraints`:
- Use this field only for real event-linked phase constraints.
- If the phase contains no real event-driven constraint, emit `[]`.
- Good examples:
  - `["2026-09-12 A event: dedicated taper-contained event handling."]`
  - `["2026-08-15 B event: rehearsal within ongoing build."]`
  - `["2026-10-03 C event: low-priority participation without changing macrocycle direction."]`
- Do not fill the field with negative placeholders or empty-status prose.
- Do not write:
  - `["No target-week event"]`
  - `["No logistics exception"]`
  - `["No event-driven load exception"]`
