---
Type: InterfaceSpecification
Interface-For: SEASON_BRIEF
Interface-ID: SeasonBriefInterface
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Season-Planner
  - Phase-Architect

Binding-Specs:
  - Specification-ID: TraceabilitySpec
    Version: 1.0
  - Specification-ID: FileNamingSpec
    Version: 1.0

Notes: >
  Canonical interface for season briefs. A season brief captures athlete-specific
  context, constraints, priorities, and event intent for a season/year. It is an
  input document only; it must not contain planning decisions, load corridors,
  governance, or workout prescriptions.
---

# Season Brief Interface Specification

## 1) Purpose (Binding)
A **SEASON_BRIEF** provides the foundational context for season-level planning:
- athlete profile and constraints
- season time window
- prioritized events and goals
- availability, risks, and non-negotiables (as context)
- data assumptions and known limitations

It is consumed by Season-Planner (authoring context), and read by downstream agents to understand intent and constraints.

## 2) Required Fields (Binding)
A SEASON_BRIEF artefact or template implementing this interface MUST include the following sections (headings may vary, but semantics MUST be present):

### 2.1 Season Identity
- `Season-ID` (string; stable identifier)
- `Year` (YYYY)
- `Athlete-ID` (string or pseudonym)
- `Valid-From` (YYYY-MM-DD)
- `Valid-To` (YYYY-MM-DD)

### 2.2 Primary Objective
- `Primary-Objective` (short text)
- `Success-Criteria` (bullets; measurable where possible, but not thresholds)
- `Goal-Priority-Order` (ordered list for resolving trade-offs)

### 2.3 Events & Priorities
For each event:
- `Event-Name`
- `Event-Date` (YYYY-MM-DD or range)
- `Event-Type` (e.g., brevet, race, tour)
- `Priority` (A / B / C)
- `Goal` (finish, time, experience; descriptive)

### 2.4 Constraints & Availability
- `Weekly-Availability-Table` (required; Mon-Sun rows with columns:
  `Typical-Available-Hours`, `Indoor-Possible` (Y/N), `Travel-Risk` (low/med/high);
  fixed rest days must be marked as `0 h / locked`)
- `Weekly-Availability` (summary hours or sessions; descriptive ranges allowed)
- `Availability-Confidence` (weeks with high/low reliability, no-training periods)
- `Non-Negotiables` (hard boundaries that must not be violated)
- `Fixed-Rest-Days` (if any)
- `Recovery-Context` (sleep quality, work/life stress)
- `External-Constraints` (job/family, environment, nutrition/GI)
- `Injury-History` (past injuries, current limitations)
- `Injury-Risk-Flags` (if any)

### 2.5 Athlete Profile (Context Only)
- `Athlete-Name` (optional; if different from Athlete-ID)
- `Age`
- `Age-Group` (e.g., Masters 50+ / Senior 30-39)
- `Sex` (optional)
- `Location-Time-Zone`
- `Primary-Discipline(s)`
- `Training-Age` (years of structured training)
- `Experience-Level` (long-distance event exposure)
- `Primary-Goal-Orientation` (finish / performance / health)
- `Athlete-Story` (short text; why this season matters)

### 2.6 Data & Measurement Assumptions
- `Data-Sources` (devices/platforms)
- `Coverage` (full year, partial months, missing data)
- `Assumptions` (e.g., indoor rides included, power estimated)

### 2.7 Locator Guidance (Informational)
Recommended locations in the Season Brief template (headings may vary):
- Season identity: `## 2. Season` -> `### 2.1 Season identity`
- Athlete profile: `## 3. Personal Data` -> `### 3.1 Basic information`,
  `### 3.2 Experience`, `### 3.3 Primary goal orientation`
- Data & measurement assumptions: `### 3.5 Historical performance baseline`
  -> `Data sources and assumptions`
- Constraints & availability: `## 4. Risks` (injury history, **weekday availability table**,
  load/recovery, availability confidence, external constraints, non-negotiables)
- Events & priorities: `## 5. Events` table (Priority, Event name, Event type, Date, Goal)
- Goals and success criteria: `## 6. Goals` (primary goal, performance goals,
  success criteria, goal priority order)
- Ambitions: `## 7. Ambitions`

## 3) Optional Fields (Informational)
A SEASON_BRIEF MAY include:
- baseline characteristics (height/weight, HR, FTP, PBs, equipment constraints)
- `Body-Mass-kg` (current or typical range)
- historical performance baseline (measured and derived values, if available)
- ambitions or long-term vision beyond this season
- current zone model reference
- confidence notes about data quality or estimates
- nutrition considerations
- travel logistics
- preferred long-ride days
- coaching preferences
- diagnostics and evaluation intent (planned diagnostics, primary intent, expected timing)

## 4) Validation Rules (Binding)
- Dates MUST be coherent (`Valid-From` < `Valid-To` and within `Year` unless justified).
- At least one event or one explicit season goal MUST be provided.
- Constraints MUST be explicit if they are described as "non-negotiable".
- A SEASON_BRIEF MUST be traceable (TraceabilitySpec) and filename-compliant (FileNamingSpec).

## 5) Forbidden Content (Binding)
A SEASON_BRIEF implementing this interface MUST NOT contain:
- weekly kJ corridors or progression ramps
- phase guardrails (PHASE_GUARDRAILS / PHASE_FEED_FORWARD semantics)
- phase structures (PHASE_STRUCTURE / PREVIEW)
- weekly schedules (Mon-Sun planning)
- workout prescriptions or interval definitions
- KPI thresholds / GREEN-YELLOW-RED gates
- recommendations framed as decisions ("therefore do X", "must increase volume")

If such content is required, it MUST live in the appropriate downstream artefact type (SEASON_PLAN, KPI_PROFILE, PHASE_GUARDRAILS, WEEK_PLAN).
