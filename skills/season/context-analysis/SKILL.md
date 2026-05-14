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
3. Read athlete profile as stable athlete context only: objectives, body-mass/training-age/discipline context, strengths, limitations, risk flags, and success criteria. Athlete profile must not contain planning decisions.
4. Read availability as a persistent user-managed constraint surface. The latest valid availability artefact remains authoritative even if its stored week key predates the target planning week.
5. Read logistics as context only: travel, work, weather, health, family, equipment, and other non-training constraints. Logistics can constrain feasibility and sequencing but do not directly change governance corridors on their own.
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
- do not start backplanning here
- do not convert advisory scenario guidance into binding truth
- do not invent missing event facts or availability
- do not include workout or week-level prescriptions
