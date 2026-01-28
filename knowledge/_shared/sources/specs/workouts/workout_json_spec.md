---
Type: Specification
Specification-For: WORKOUT_EXPORT_TRANSFORMATION
Specification-ID: WorkoutJSONExportSpec
Version: 1.0

Scope: Shared
Authority: Binding

Normative-Role: Execution
Decision-Authority: None

Applies-To:
  - Workout-Builder
  - Micro-Planner

Notes: >
  Defines a deterministic, technical transformation from a planner-produced
  week_plan_yyyy-ww.json into an Intervals.icu-compatible JSON format.
  This specification performs parsing, validation, and formatting only.
  It MUST NOT introduce, modify, interpret, or decide any training content.
---



# ⚙️ Workout Guideline - Workout-Builder (JSON / intervals.icu)

This guideline defines how the **Workout-Builder** turns the planner-produced  
`week_plan_yyyy-ww.json` into an **Intervals.icu-compatible JSON file**.

Goal:

- Input: weekly plan as JSON (`week_plan_yyyy-ww.json`, schema: `week_plan.schema.json`)
- Output: `workouts_yyyy-ww.json` with valid workout objects
- No physiological planning, only **parsing, validation, and formatting**

---

## 🧂 Role of the Workout-Builder

The Workout-Builder:

1. receives the planner-produced `week_plan_yyyy-ww.json` (JSON),
2. extracts **all workouts**,
3. validates the **workout syntax**, and
4. generates a **JSON list** of workouts that can be imported into Intervals.icu.

It changes **no training content** (no edits to duration, %, rpm, etc.),  
only ensuring **technically clean, compatible output**.

---

## 1️⃣ Input Format: `week_plan_yyyy-ww.json`

The Workout-Builder expects JSON validated against:
- `week_plan.schema.json` (input)
- `workouts.schema.json` (output)

This spec does not redefine JSON fields; it defines transformation rules and
validation behavior. The schemas are authoritative.

Each `workout_id` in the agenda must appear exactly once in `data.workouts`.

---

## 2️⃣ JSON Output Format

The Workout-Builder outputs exactly one **JSON list** of objects:

```json
[
  {
    "start_date_local": "2025-11-24T18:00:00",
    "category": "WORKOUT",
    "type": "Ride",
    "name": "Z2 Indoor - Winter Foundation",
    "description": "Warmup
- 10m ramp 50%-70% 85-95rpm

Main Set
6x
- 4m 110%-115% 92-98rpm
- 3m 55%-60% 85-90rpm

Cooldown
- 10m ramp 60%-45% 80-85rpm
"
  }
]
```

### 2.1 Fields (binding)

Field definitions are authoritative in `workouts.schema.json`. The list below
describes the required mapping and formatting rules.

For each workout:

- `start_date_local`  
  - String in format `YYYY-MM-DDTHH:MM:SS`
  - Combined from `date` + `start` of the workout object
  - Seconds always `:00`

- `category`  
  - Always `"WORKOUT"`

- `type`  
  - Always `"Ride"` (cycling)

- `name`  
  - Exact content of `title` (trimmed)

- `description`  
  - Plain text block from `workout_text` (trimmed), without meta lines.

---

## 3️⃣ Parsing Rules

### 3.1 Identify Workouts

1. Use `data.workouts` from the input JSON.
2. Each object corresponds to **exactly one workout**.

### 3.2 Extract Meta Information

From the workout object:

- `workout_id` -> workout ID (for mapping, not exported)
- `title` -> `name`
- `notes` -> optional, ignored for JSON
- `date` + `start` -> `start_date_local`
- `duration` -> plausibility check only (not exported)

### 3.3 Build Description Text

The description section is the content of `workout_text`.

The Workout-Builder:

1. Removes extra blank lines at the start and end of the description.
2. Preserves section headings **exactly**, in particular:
   - `#### Activation` stays `#### Activation`
   - `#### Add-On` stays `#### Add-On`
3. Leaves repetition lines like `3x`, `5x`, `8x` unchanged.
4. Does not remove any content lines as long as they conform to syntax.

The result is a text block with line breaks (`\n`) that is used directly as `description`.

---

## 4️⃣ Formal Syntax Requirements for `description`

Each line in `description` must be one of the following forms:

1. **Section lines:**

   - `Warmup`
   - `#### Activation`
   - `Main Set`
   - `#### Add-On`
   - `Cooldown`

2. **Repetition lines:**

   - Regex:  

     ```regex
     ^\d+x$
     ```

     Examples:

     - `6x`
     - `3x`
     - `4x`

3. **Interval/block lines:**

   - Regex:

     ```regex
     ^(- )?(((\d+h(\d+m)?)|(\d+m)|(\d+s)) )?(ramp )?(\d+%(-\d+%)?) (\d+(-\d+)?rpm)$
     ```

     Examples:

     - `- 10m ramp 50%-75% 85-90rpm`
     - `- 40s 110% 92-95rpm`
     - `- 3m 70% 85rpm`
     - `- 2h10m 65%-72% 85-95rpm`

4. **Empty lines:**  

   - `""` (just a line break)

Lines that do not meet these requirements make the workout **invalid**.

---

## 5️⃣ Character and Format Rules

For `description`:

- Allowed characters:
  - Letters: `A-Z`, `a-z`
  - Digits: `0-9`
  - Special characters: `% - + : .`
  - Unit markers: `m`, `s`, `h`
  - Spaces and `\n` (line break)

- Not allowed:
  - Backslashes `\` (except JSON escape sequences)
  - Tabs
  - Control characters (except linefeed `\n`)
- Meta lines such as `# Title:`, `# Notes:`, `# Date:`, `# Start:`, `# Duration:`

### 5.1 Layout Rules

- No comments inside the description (no extra `# ...` lines beyond the section headings above).
- Include a **blank line** between sections (if the section exists).
- Percent values always **without spaces** (`65%-72%`, not `65% - 72%`).
- Each interval line contains an **rpm value or range** (`85rpm` or `85-90rpm`).

---

## 6️⃣ Error Handling

If a workout in `week_plan_yyyy-ww.json` does not comply, the Workout-Builder must:

1. **Not** include the affected workout in the JSON list.

2. Instead, output a **clear error message** (text), e.g.:

   > ERROR in workout "VO2 6x4min - Build 3 High":  
   > Invalid line "- 4m 110% 92-98rpm" - does not match the expected syntax.

3. Do not perform silent corrections of intensities, durations, or rpm.  
   Only the following are allowed:

   - Removing excessive blank lines,
   - Preserving the given section headings and repetition lines.

---

## 7️⃣ Summary of JSON Export Rules (binding)

1. **One workout object in `data.workouts` => one JSON object.**
2. `name` = `title` from the input JSON.
3. `start_date_local` = `date` + `start` in format `YYYY-MM-DDTHH:MM:SS`.
4. `category` = `"WORKOUT"`, `type` = `"Ride"`.
5. `description` contains only:
   - `Warmup`, `#### Activation`, `Main Set`, `#### Add-On`, `Cooldown`
   - repetition lines like `6x`
   - interval lines `- ...`
   - blank lines
6. Each line in `description` matches the regex rules or is empty.
7. No metadata, backticks, or additional Markdown structures in `description`.
8. If all workouts are valid, the Workout-Builder outputs **only** the JSON list - no extra explanations.
