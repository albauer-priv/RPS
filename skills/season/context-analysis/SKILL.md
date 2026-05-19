---
name: context-analysis
description: Summarize authoritative season planning context, horizon, and constraint surfaces before design begins.
metadata:
  author: rps
  version: "3.0"
---
Read season context before any scenario or season design.

Method:
1. Identify the planning horizon from the authoritative planning-event window and selected season range.
2. Read planning events as the binding A/B/C event inventory. Preserve `type`, `priority_rank`, `event_name`, `date`, `event_type`, `goal`, `distance_km`, `elevation_m`, `expected_duration`, and `time_limit`.
3. Read athlete profile as stable athlete context only: objectives, body-mass/training-age/discipline context, strengths, limitations, risk flags, and success criteria. Keep planning decisions in planning artifacts.
4. Read availability as a persistent user-managed constraint surface. The latest valid availability artefact remains authoritative even if its stored week key predates the target planning week.
5. Read logistics as context only: travel, work, weather, health, family, equipment, and other non-training constraints. Use logistics to constrain feasibility and sequencing, while keeping governance-corridor changes tied to explicit planning authority.
6. Read selected scenario state as advisory context only. Scenario intent may guide emphasis, but binding truth remains with planning events, athlete profile, and explicit constraints.
7. Separate hard authority from advisory information:
   - Binding: planning events, athlete profile constraints, availability, explicit logistics blockers.
   - Informational/advisory: selected scenario, wellness, historical notes, KPI hints.
8. Return a structured context summary that downstream specialists must obey.

What to summarize:
- planning horizon and exact season window
- A/B/C event hierarchy and event clustering pressure
- athlete objectives and risk flags
- availability and fixed-rest patterns relevant to season feasibility
- logistics constraints that change timing, modality, or recovery assumptions
- unresolved unknowns that limit certainty

Hard rules:
- leave backplanning to the macrocycle architecture task
- treat advisory scenario guidance as advisory until selection and season planning make it binding
- use explicit event facts and availability from upstream context
- keep workout and week-level prescriptions for downstream tasks
- prefer the narrow configured workspace tools and injected deterministic context over broad rediscovery

Retrieval policy:
- Use `workspace_get_input` for athlete-managed inputs such as `planning_events`, `athlete_profile`, `availability`, and `logistics`.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots.
- Use `workspace_get_version` only when the task explicitly requires a week-sensitive historical artefact version.

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output as a compact context summary.
- Include authoritative inputs, selected ranges, constraints, missing data, and assumptions.
- Highlight only the facts that the downstream planning or review task needs to act correctly.
