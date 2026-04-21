---
Type: Specification
Specification-For: WORKOUT_SYNTAX_SUBSET
Specification-ID: WorkoutSyntaxAndValidation
Version: 1.0

Scope: Shared
Authority: Binding

Normative-Role: StructuralRules
Decision-Authority: None

Applies-To:
  - Workout Export
  - Week-Planner

Dependencies:
  - Specification-ID: IntervalsWorkoutEBNF
    Version: 1.0

Notes: >
  Defines the project-specific allowed syntax subset, constraints, and
  validation rules for Intervals.icu workout text. This specification
  may only restrict the formal EBNF grammar and must never extend it.
  It governs linting, validation, and export safety, not training intent
  or planning decisions.
---


# 📘 workout_syntax_and_validation.md - RPS Project
> **Purpose:**  
> This document defines the **valid syntax subset** of  
> `intervals_workout_ebnf.md` for the RPS planner.  
>
> **The EBNF is the only formal grammar.**  
> This document restricts it for the project (prohibitions and requirements).

---

## 1. Roles and Boundaries

- **Formal grammar:** `intervals_workout_ebnf.md`  
- **Project subset and prohibitions:** `workout_syntax_and_validation.md` (this document)

**Rule:**  
No other document may contradict the EBNF.  
This document may only **restrict**, not extend.

---

## 2. Scope

These rules apply to **all workouts** that:

- are produced by the planner and
- are exported as **Intervals.icu text** or embedded in `week_plan_yyyy-ww.json` (`workout_text`).

In particular:

- WeekOps artefact (`week_plan_yyyy-ww.json`)
- Isolated workout definitions in chat (code blocks)
- Corrected workouts after builder error messages

---

## 3. Allowed Syntax Subset (Project Rules)

### 3.1 Top-Level Document

Allowed (must be EBNF-conform):

- Description (paragraphs before the first block, optional)
- Blocks:
  - Section blocks (e.g., `Warmup`, `Main Set`, `Cooldown`)
  - Loop blocks with `Nx` header
  - Standalone steps

Forbidden or not used:

- Multiple `Category:` lines
- Zwift-specific category folder control (max one `Category:` line)

---

### 3.2 Sections (Workout Blocks)

**Expected sections in the project:**

In workout code blocks (WeekOps), use the following order:

1. `Warmup`
2. `#### Activation` (optional, recommended)
3. `Main Set`
4. `#### Add-On` or `#### Z2 Add-On` (optional, recommended)
5. `Cooldown`

Project rule:

- Section headers are **free text lines** (per EBNF `<section-header>`),  
  but the project **only uses the forms above**.
- Order as above, no additional top-level sections.
- Optional sections may be omitted entirely; if omitted, leave out header and content (no empty headings).

---

### 3.3 Step Lines (Required Structure)

```text
- <Duration> <Target> <Cadence> [Flags]
```
- Targets MAY be percent, percent-range, or ramp targets as defined by EBNF; ramp is explicitly allowed in this project subset.


**Project requirements:**

- **Every step line starts with `-`** followed by a space or tab.
- **Duration** is **always** a **time token** (no distance):
  - `s`, `m`, `h`, `1m30`, `2h35m` are allowed, e.g.:
    - `30s`, `45s`, `1m`, `3m`, `10m`, `1h30m`
- **Target** is **always power**, no HR/pace:
  - Percent:
    - `90%`, `110%`, `65%-72%`
  - Ramp:
    - `ramp 60%-75%`
    - `ramp 55%-70%`
- **Cadence is always required**:
  - `85rpm` or `85-95rpm`

Examples:

```
- 10m 65%-72% 85-95rpm
- 30s 115% 95-100rpm
- 8m ramp 60%-45% 80-85rpm
```

---

## 4. Allowed and Forbidden Tokens

### 4.1 Duration

**Allowed:**

- Time-only durations:
  - `30s`, `45s`, `1m`, `3m`, `10m`, `1h`, `1h30m`, `2h35m`
  - `1m30` (minute-second combo)

**Forbidden (do not use in this project):**

- Distance durations:
  - `10km`, `5mi`, `1000m`, `400m`, `250m`, `200y`, etc.

---

### 4.2 Targets

Allowed:

- Percent: `90%`, `110%`
- Ranges: `65%-72%`
- Ramp: `ramp 50%-75%`

Forbidden:

- Absolute watts (`250w`)
- HR, pace, zones (`Z2`, `90%HR`, `4:30/km`)
- `freeride`

---

### 4.3 Cadence

**Project requirement:**

- **Every step line includes a cadence value**.

Allowed:

- Absolute cadence:
  - `85rpm`, `90rpm`
- Cadence range:
  - `85-95rpm`, `58-62rpm`

Forbidden:

- Step lines without `rpm`
- Step lines with free text instead of `rpm` (e.g., `85U/min`)

---

### 4.4 Forbidden Tokens and Patterns (Single Source of Truth)
This list is **normative** and the **only place** where project-wide token prohibitions
for workout step lines are defined. Output templates must not introduce additional
prohibited tokens.

**Forbidden in step lines (must be recognized as substring/token):**
- `@` (e.g., `4m@110%` or similar shorthand)
- `cadence` (as a word/label; cadence must be encoded as `NNrpm`/`NN-NNrpm`)
- `Z1`, `Z2`, `Z3`, `Z4`, `Z5`, `Z6`, `Z7` and `z1`-`z7` (zone shorthand)
- `MM:SS` time notation in step lines (e.g., `04:00`), since duration is encoded as `4m`/`240s`
- `HH:MM:SS` time notation in step lines

**Additional project prohibitions (tokens/targets):**
- Ramp base tokens in step lines are forbidden: `FTP`, `HR`, `LTHR`, `Pace`, `MMP`
  - Ramp must be encoded without a base: `ramp 50%-75%` (no `... FTP`)
- Heart-rate tokens: `HR`, `hr`, `LTHR`, `lthr` (targets)
- Pace tokens/units: `Pace`, `/km`, `/mi`, `/100m`, `/500m`, `min/km`, etc.
- Absolute power: `w` / `W` as a target (e.g., `250w`)
- `freeride` / `FreeRide`

**Permission/scope clarification:**
- `HH:MM:SS` is **allowed** only in the meta lines `# Duration: HH:MM:SS`
  (not in step lines).

---

### 4.5 Flags

Default: **no flags**  
Optional allowed:

- `intensity=warmup`
- `intensity=recovery`
- `intensity=interval`
- `intensity=cooldown`

---

## 5. Loops

Loops are defined in the EBNF as `loop-block`.

**Project convention:**

- Repetitions are **always** expressed via `Nx`:

```
6x
- 30s 115% 95-100rpm
- 30s 55% 85-90rpm
```

- Or with a text header:

```
# Block 2 - Middle section

8x
- 40s 115% 92-95rpm
- 20s 55% 85-88rpm
```

**Forbidden:**

- Shorthand in a single line (`2x5x30s/30s 110%-115% ...`)
- Nested loops (n-level), even if the EBNF only says "no nested loops":
  - Project rule: **max one loop level (directly under a section).**

---

## 6. Comments and Blank Lines

- Comments in the workout text:
  - start with `#`
  - are on their **own line**
  - are **separated by blank lines** from steps/loops

Example:

```
Main Set

# Block 1 - Entry

8x
- 40s 110% 92-95rpm
- 20s 55% 85-88rpm

- 5m 55% 85rpm
```

Project rule:

- Always include at least **one blank line** between **blocks, comment blocks, and pauses** so Intervals.icu can parse the text reliably.

---

## 7. Validation (Required)

Before each export or WeekOps output, apply the following checks:

### 7.1 EBNF Conformance

- Each workout definition is **formally valid** per `intervals_workout_ebnf.md`.
- Document structure: paragraphs, blocks, loops, steps match the grammar.

### 7.2 Project Subset

- All step lines use **time durations**, not distance durations.
- Targets are **power percent only** (including ranges and ramp).
- Each step line includes a **cadence value** (`rpm` or `x-yrpm`).
- No HR, pace, or zone-only targets.
- No shorthand like `2x5x30s/30s`.
- No forbidden flags (`press lap`, `power=lap`, etc.).

### 7.3 Structure and Template Check

- Workouts in the WeekOps artefact follow the order:
  `Warmup` -> `#### Activation` (optional) -> `Main Set` -> `#### Add-On`/`#### Z2 Add-On` (optional) -> `Cooldown`.
- The headers (`# Workout-ID:...`, `# Title: ...`, `# Notes: ...`, `# Date: ...`, ...) match the template.
- Workout code blocks in chat and file are **bit-identical**.

---

## 8. Examples (Project Conformant)

### 8.1 Simple Z2 Endurance Workout

```
Warmup
- 10m ramp 50%-75% 85-90rpm

Main Set

- 60m 70% 85-95rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

### 8.2 VO2 Interval Block with Loop

```
Warmup
- 10m ramp 50%-75% 85-90rpm

#### Activation

3x
- 20s 120% 95rpm
- 40s 60% 85rpm

Main Set

# Block 1 - Entry

8x
- 40s 110% 92-95rpm
- 20s 55% 85-88rpm

- 5m 55% 85rpm

# Block 2 - Middle section

8x
- 40s 115% 92-95rpm
- 20s 55% 85-88rpm

- 5m 55% 85rpm

Cooldown
- 8m ramp 60%-45% 80-85rpm
```

Both workouts are:

- EBNF-conform
- Project-conform (time only, %FTP, rpm, no forbidden targets/flags)
- Importable and physiologically sensible per `workout_richtlinie_planner.md`.

------

## 9. Self-Check

Before final output of a workout:

   1. **Grammar:** Does the workout match `intervals_workout_ebnf.md`?
   2. **Subset:** Do all steps use only the allowed project subset?
   3. **Cadence:** Is any step line missing `rpm`?
   4. **Targets:** Do HR/pace/distance or other forbidden targets appear?
   5. **Structure:** Do sections and order match the templates?

If any answer is "no":

   > Correct the workout, regenerate the full code block,
   > and only then output WeekOps/file.
