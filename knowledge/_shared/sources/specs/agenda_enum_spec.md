---
Type: Specification
Specification-For: AGENDA_ENUM
Specification-ID: AgendaEnumSpec
Version: 1.2

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder

Notes: >
  Defines the canonical agenda vocabulary and allowed combinations
  for block and micro-level planning artefacts.
  This specification is semantic and normative; enum values are defined in schema and
  this spec defines meanings and combination constraints.
---

# AGENDA ENUM SPECIFICATION
​
This document defines the **authoritative agenda semantics**
used for phase previews and phase structures.
​
It provides:
- standardized day roles
- standardized intensity domains
- standardized load modalities
- strict combination rules
​
This specification is **binding**.
Any artefact violating this spec is INVALID.

## Schema Reference (Normative)

The canonical enum values are defined in:
- `agenda_enum.schema.json`

This spec defines semantics and combination rules only. If there is any mismatch, the schema prevails.
​
---
​
## 1) DAY_ROLE_ENUM
**(Mandatory · exactly one per day)**
​
Describes the **structural role of a day** in the block.

### Semantics

| DAY\_ROLE | Meaning                            |
| --------- | ---------------------------------- |
| REST      | No training                        |
| RECOVERY  | Very light / regenerative          |
| ENDURANCE | Endurance without focused stimulus |
| QUALITY   | One focused training stimulus      |
| OPTIONAL  | Can be dropped without replacement |
| FLEX      | Freely movable                     |
| TRAVEL    | Travel / logistics                 |
| EVENT     | Race, brevet, test                 |
| OFF\_BIKE | No cycling activity                |

## 2) INTENSITY_DOMAIN_ENUM

(Optional · max. one · default = NONE)

Describes the physiological intensity domain (label only).

### Semantics

| Domain    | Meaning                      |
| --------- | ---------------------------- |
| NONE      | No explicit intensity domain |
| RECOVERY  | Regenerative intensity       |
| ENDURANCE_LOW | Aerobic base (lower Z2)  |
| ENDURANCE_HIGH | Aerobic base (upper Z2) |
| TEMPO     | Upper endurance / tempo      |
| SWEET_SPOT       | Sweet Spot                   |
| THRESHOLD | Threshold-oriented           |
| VO2MAX    | VO₂max-oriented              |

Legacy alias:
- `ENDURANCE` (if present) MUST be normalized to `ENDURANCE_LOW`.

⚠️ These are labels, not zones, not targets.

## 3) LOAD_MODALITY_ENUM

(Optional · max. one · default = NONE)

Describes how load is generated, not how intense it is.

### Semantics

|Modality	|Meaning|
|---|---|
|NONE	|No special load modality|
|K3	|Kraftausdauer (high torque / low cadence)|

Binding note:
K3 denotes a **focused torque stimulus**. Therefore, when `LOAD_MODALITY = K3`,
`DAY_ROLE` MUST be `QUALITY` or `EVENT` per allowed combinations, even if
`INTENSITY_DOMAIN = ENDURANCE_HIGH`.

## 4) Combination Rules (BINDING)

### 4.1 Base Rules

- DAY_ROLE is mandatory.
- INTENSITY_DOMAIN defaults to NONE **except** when `DAY_ROLE = QUALITY` or
  `DAY_ROLE = EVENT`, where a non‑NONE domain is required.
- LOAD_MODALITY defaults to NONE.

Only one value per enum is allowed.

### 4.2 Allowed Combinations

| DAY\_ROLE | INTENSITY\_DOMAIN             | LOAD\_MODALITY |
| --------- | ----------------------------- | -------------- |
| REST      | NONE                          | NONE           |
| OFF\_BIKE | NONE                          | NONE           |
| TRAVEL    | NONE                          | NONE           |
| FLEX      | NONE                          | NONE           |
| RECOVERY  | NONE, RECOVERY                | NONE           |
| ENDURANCE | NONE, ENDURANCE_LOW, ENDURANCE_HIGH | NONE     |
| OPTIONAL  | NONE, ENDURANCE_LOW, ENDURANCE_HIGH | NONE     |
| QUALITY   | TEMPO, SWEET_SPOT, THRESHOLD, VO2MAX | NONE           |
| QUALITY   | SWEET_SPOT                           | K3             |
| QUALITY   | ENDURANCE_HIGH                | K3             |
| EVENT     | ENDURANCE_LOW, ENDURANCE_HIGH, TEMPO, SWEET_SPOT, THRESHOLD, VO2MAX | NONE |
| EVENT     | ENDURANCE_HIGH, SWEET_SPOT            | K3             |

### 4.3 Forbidden Combinations (Examples)

- DAY_ROLE = ENDURANCE AND INTENSITY_DOMAIN ∈ {SWEET_SPOT, TEMPO, THRESHOLD, VO2MAX}
- DAY_ROLE = OPTIONAL AND INTENSITY_DOMAIN ∈ {SWEET_SPOT, TEMPO, THRESHOLD, VO2MAX}
- DAY_ROLE = QUALITY AND INTENSITY_DOMAIN ∈ {NONE, ENDURANCE_LOW}
- DAY_ROLE = QUALITY AND INTENSITY_DOMAIN = ENDURANCE_HIGH AND LOAD_MODALITY = NONE
- LOAD_MODALITY = K3 AND INTENSITY_DOMAIN ∉ {ENDURANCE_HIGH, SWEET_SPOT}
- Any day with multiple intensity domains
- Any day with multiple load modalities

Violations invalidate the artefact.

## 5) Explicitly Forbidden Content

Agenda artefacts MUST NOT contain:

- Power zones (Z1–Z7)
- %FTP values
- Durations or time targets
- Interval structures
- kJ / load numbers
- Progression or ramp language

If such content appears, the artefact is INVALID.

## 6) Governance & Usage

This specification is referenced by:

- `phase_structure_yyyy-ww--yyyy-ww.json`
- `phase_preview_yyyy-ww--yyyy-ww.json`
- Micro-Planner validation logic

Higher-level artefacts (Meso-Architect, DES)  
may restrict allowed combinations further,  
but may not expand them.

---
End of AGENDA ENUM SPECIFICATION v1.2
