---
Type: Template
Template-For: SEASON_BRIEF
Template-ID: SeasonBriefGeneric
Version: 1.0

Scope: Shared
Authority: Binding

Owner-Agent: Macro-Planner

Dependencies:
  - Specification-ID: DurabilityFirstPrinciples
    Version: 1.0
  - Specification-ID: EvidenceManifest
    Version: 1.0
  - Specification-ID: TraceabilitySpec
    Version: 1.0
  - Specification-ID: FileNamingSpec
    Version: 1.0

Notes: >
  Human-centered season brief template capturing the athlete's context,
  goals, constraints, and event priorities for one season.
  This template is input only and does not define training logic,
  KPI thresholds, or execution rules. Planning decisions derived
  from this brief must be justified via the Principles Paper and
  validated by the KPI / DES system.

Implements:
  Interface-ID: SeasonBriefInterface
  Version: 1.0
    
---

# Season Brief - Athlete Intake Template
## Human-centered season anamnesis (coach + athlete)
Use this document as a joint intake that focuses on the athlete as a person.
It frames the season before any training decisions are made.

---

## 1. Overview and Purpose
Write a short overview of what this brief covers and how it supports planning.
This keeps expectations aligned before details are added.

Season overview:
- 

### What this season brief is for
List the outcomes this brief should enable and the boundaries of its use.
- Capture the person, context, and intent for the season.
- Align athlete and coach on priorities, constraints, and expectations.
- Provide inputs for planning (this document is not a training plan).

### How it should be used
Explain how to complete and maintain the document so it stays current.
- Fill in plain language; keep answers short and honest.
- Update when life circumstances or goals change.
- If data is unknown, leave it blank and add a note.

---

## 2. Season
Define the season scope and identifiers for traceability and planning context.
This ensures the brief maps to a specific time window.

### 2.1 Season identity
Fill in identifiers and dates so the season is unambiguous and file naming stays consistent.
- Season-ID:
- Year (YYYY):
- Athlete-ID:
- Valid-From (YYYY-MM-DD):
- Valid-To (YYYY-MM-DD):

---

## 3. Personal Data
Capture who the athlete is and the context they bring to this season.
This informs decisions without prescribing training.

### 3.1 Basic information
Record stable identity and context details used for communication and logistics.
- Athlete name (optional, if different from Athlete-ID):
- Age:
- Age group:
  - Example: Masters 50+
  - Example: Senior 30-39
- Sex (optional):
- Location / time zone:
- Primary discipline(s):

### 3.2 Experience
Summarize training history and endurance exposure to calibrate assumptions and progression.
> Example: 3 years structured training; 2 brevets completed.
- Training age (years of structured training):
- Experience level (long-distance exposure):
  - [ ] none
  - [ ] 1-2 events
  - [ ] regular
  - [ ] extensive
- Short athlete story (why this season matters):

### 3.3 Primary goal orientation
Choose the dominant motivation so planning emphasizes the right trade-offs.
> Example: performance / ranking with a strong finish focus.
- Primary goal orientation:
  - [ ] finish / completion
  - [ ] performance / ranking
  - [ ] health / longevity

### 3.4 Baseline characteristics (optional, if known)
Add physiological or equipment baselines if known; leave blank if unknown to avoid guesswork.
- Height (typical range):
- Weight (typical range):
- Resting HR / max HR:
- FTP or threshold power:
- Recent tests or notable PBs:
- Equipment constraints (bike, indoor trainer, etc):

### 3.5 Historical performance baseline (last 3 years, if available)
Provide year-level data to show load history and trends.
Keep measured and derived values separate for transparency.

**Measured values (directly recorded)**
Enter raw totals from the source without additional calculations.
| Year | Rides | Distance (km) | Time (h) | Work (kJ) | TSS/Load | Notes |
|------|-------|----------------|---------|----------|------------|------|
| 2023 | | | | | | |
| 2024 | | | | | | |
| 2025 | | | | | | |

**Derived values (calculated or estimated)**
Enter calculated metrics and note any estimation method in Notes.
| Year | TSS/Load per ride | kJ/ride | kJ/h | h/ride | kJ/day | Notes |
|------|-------------------|---------|------|--------|--------|------|
| 2023 | | | | | | |
| 2024 | | | | | | |
| 2025 | | | | | | |

**Data sources and assumptions**
List where the data comes from and any missing or estimated parts.
- Data source(s) (e.g., TrainingPeaks, Strava, Garmin):
- Coverage (full year, partial months, missing data):
- Assumptions (e.g., indoor rides included, power estimated):

### 3.6 Diagnostics & evaluation intent (optional)
Declare if and why formal evaluation is expected this season.
This does not define tests or thresholds.

- Planned diagnostics:
  - [ ] none
  - [ ] field-based
  - [ ] lab-based
- Primary intent:
  - baseline calibration
  - durability assessment
  - fueling / energetics
  - confirmation only
- Expected timing (relative):
  - pre-season
  - mid-base
  - pre-A event

---

## 4. Risks
Document risks and constraints that could affect training quality or safety.
This helps the coach plan conservatively where needed.

### 4.1 Injury and medical history
Note past injuries and current issues so training avoids repeat flare-ups.
- Past injuries or recurring issues:
- Current limitations or pain:

### 4.2 Load, recovery, and stress capacity
Describe current recovery resources and stress load to set realistic training ranges.
- Typical weekly training hours (min / typical / max sustainable):
- Sleep quality (average hours, consistency):
- Work / life stress level (low / medium / high):
- Fixed rest days:
- Travel or high-stress periods:

### 4.3 Availability confidence
Indicate how reliable training time will be across the season.
This helps with deload timing and risk management.
- Weeks with high reliability:
- Weeks with low reliability:
- Absolute no-training periods (if any):

### 4.4 External constraints
List outside factors that can limit training choices or available environments.
- Job / family constraints:
- Environment (weather, indoor-only periods, travel):
- Nutrition, fueling, or GI constraints:

### 4.5 Non-negotiables for this season
List hard boundaries that should not be violated even if goals are at risk.
These guide trade-offs when conflicts arise.
- Example: no training on weekdays X/Y
- Example: max 2 intensity days per week
- 
- 

### 4.6 Red flags (if any)
Check any standard risk flags that require conservative progression.
- [ ] Masters athlete (50+)
- [ ] History of overuse injuries
- [ ] Limited recovery capacity
- [ ] Time-crunched (<6 h/week)

---

## 5. Events
List key events and milestones that anchor the season calendar.
These guide timing, priority, and specificity.

| Priority | Event name | Event type | Date | Distance | Elevation | Target time | Goal | Notes |
|----------|------------|------------|------|----------|-----------|-------------|------|------|
| A | | | | | | | | |
| B | | | | | | | | |
| C | | | | | | | | |

**Priority meaning**
- A = season anchors (structure the plan)
- B = important supports (specificity, rehearsal)
- C = training or diagnostics

---

## 6. Goals
Translate intent into clear, trackable outcomes and behaviors.
This separates what you want to achieve from how you want to train.

### 6.1 Primary season goal (one sentence)
State the single most important outcome of the season in plain language.
> Example: Ride 300-400 km at steady pacing with low HR drift.

### 6.2 Performance goals (measurable)
Add measurable targets that indicate progress toward the primary goal.
- Example metrics (power, pace, duration, HR drift, ranking):
- Target dates or checkpoints:

### 6.3 Process goals (behavior and habits)
Describe routines and behaviors that support consistent training and recovery.
- Consistency targets:
- Recovery and fueling habits:
- Skills or technique focus:

### 6.4 Success criteria (season-level)
Capture how success should feel and include measurable signals where helpful.
Keep this distinct from the goals list to support a fair season review.
- What should feel easier by the end of the season?
- What failure modes must be avoided?

### 6.5 Goal priority order (if conflicts arise)
Rank the goal axes so planning decisions are consistent under trade-offs.
This prevents later disputes about what matters most.
1. 
2. 
3. 
4. 

---

## 7. Ambitions
Share longer-term aspirations beyond the current season.
This helps balance short-term choices against the bigger picture.

- Longer-term vision beyond this season:
- Dream events or milestones:
- Personal meaning / motivation:

---

# Appendix - Decision Traceability (coach/agent use)
Explain how planning decisions map back to principles for accountability.
This section is for coach or agent use, not athlete input.
## Decision to Principle Mapping
Clarify when and how to reference principles during planning.

**Purpose:**
Keep planning decisions aligned with the Principles Paper. Reference at least one
principle when:
- defining a macro phase
- selecting training content
- approving progression or deload

---

## Traceability Table (coach/agent use)
Record decisions, the principle they rely on, and the rationale in one place.

| Planning Decision | Reference Principle | Rationale |
|------------------|--------------------|-----------|
| Example: Limit VO2 to 1x/week in Base | Principles 4.2, 5 | Preserve durability and recovery |
| Example: kJ-based long ride progression | Principles 2 | Energetic robustness over CTL |

---

## Mandatory Rule
Define the minimum documentation required for any decision.

For any generated plan or recommendation, the agent must:
1. State the decision
2. Reference the principle section (by number)
3. Explain the causal rationale in one sentence

If no clear principle applies, flag the decision as an assumption.

---

## Quality Control
State when a plan is invalid so checks are consistent and enforceable.

A plan is considered invalid if:
- Decisions contradict the Principles Paper
- Decisions cannot be traced to at least one principle
- Short-term metrics override durability-first logic

---

## End of Template
